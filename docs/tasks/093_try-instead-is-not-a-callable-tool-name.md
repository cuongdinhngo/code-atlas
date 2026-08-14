---
id: 093
slug: try-instead-is-not-a-callable-tool-name
title: '`try_instead: "find_references_on_method_qname"` is not a tool, but every other `try_instead` is'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [065, 076, 069]
---

## Goal
`try_instead` is the field that tells an agent where to go when the answer is empty. Two of its
values are real tool names (`search_symbol`, seen twice in one session); one is not:
`find_references_on_method_qname` (`code_atlas/tools/nav_result.py:57`). It is an instruction shaped
like an identifier. The evaluator had to *infer* that it meant "call `find_references` with a
fully-qualified method qname" — and inferred it correctly, but only after treating the string as a
tool name first and finding no such tool.

A field whose values are usually callable trains the reader to call them. One value that isn't makes
the whole field ambiguous: an agent cannot tell, without trying, whether a given `try_instead` is a
route it can execute or prose it must interpret.

## Evidence (field retro round 5, 2026-08-14, **real work**)
- `try_instead` appeared **3 times** in the session; the evaluator followed one.
- Verbatim, from `find_references` on a class consumed via a `::class` constant:
  `reason: "relationship_not_modelled"` + `try_instead: "find_references_on_method_qname"`.
- Following it did not produce an answer, but did convert an ambiguous nothing into a definite one
  (`no_matches`) — so the *routing* was right and only the *encoding* was wrong. Retro §4:
  "the string is *not a callable tool name* … it is an instruction shaped like an identifier".
- The other two occurrences were `try_instead: "search_symbol"` — a real tool — which is what set the
  expectation. §9 runner-up.
- Source confirms the field mixes registers: `TRY_INSTEAD_FIND_REFERENCES_ON_METHOD_QNAME` and
  `TRY_INSTEAD_PATH_BASENAME_SEARCH` (`nav_result.py:57-58`) are both instructions, not tools.

## Scope / Deliverables
- **Audit every `try_instead` value** the core can emit and split them into two registers: a
  **callable tool name** and a **human/agent-readable hint**. Neither register may contain a member
  of the other.
- **Decide the shape** — either `try_instead` stays a tool name and a sibling field (`try_instead_hint`
  or similar) carries the qualifier, or `try_instead` becomes a small object. Prose in an identifier
  slot is not an option. Record the choice with 061's payload-weight rule in view (one more field on
  every empty answer has a cost).
- **Rewrite the two non-tool values** (`find_references_on_method_qname`, `path_basename_search`)
  under the chosen shape.
- **Pin the invariant with a test:** every `try_instead` tool-name value the core can emit is a
  registered MCP tool name. This is the gate that stops the next one being added.
- **Update the consumers** — the conformance suite, `which_tool`, and any doc that quotes the field.

## Constraints
- R3 — `try_instead` is tool-output vocabulary; changing its shape breaks payload-pinning tests and
  must be reflected in the conformance suite. Decide in design whether it warrants a
  `contract_version` bump (075/076's precedent says reason codes did not).
- R1.1 — the invariant test must derive tool names from the registry, not a hand-kept list, or it
  will drift.
- R4 — deterministic: the same miss must yield the same `try_instead` every run.
- 065 stays authoritative for *when* an empty answer carries a route; this ticket only fixes *what the
  route says*.

## Acceptance criteria
- A test enumerates every `try_instead` value reachable from the core and asserts each callable value
  is a real registered tool name — failing if a future value is prose.
- The `relationship_not_modelled` payload from §4 row 2 carries a callable route plus a hint that
  states the qualifier, and the whole payload is pinned.
- `which_tool` and the conformance suite agree with the new shape.
- No empty-answer payload loses a route it has today.

## References
Field retro round 5 §4 (`try_instead` paragraph), §9 runner-up; candidate 2.
Related: [065](065_empty-answer-cannot-explain-itself.md) (the field's origin),
[076](076_bare-name-subject-reads-as-absence.md) (`try_instead: "search_symbol"` — the well-formed
case), [069](069_tool-names-do-not-say-what-they-answer.md) (routing lives in names and descriptions),
[092](092_untracked-files-are-invisible-and-answer-no-such-symbol.md) (adds a new route and must obey
this shape).
