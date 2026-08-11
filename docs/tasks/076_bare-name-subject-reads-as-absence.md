---
id: 076
slug: bare-name-subject-reads-as-absence
title: 'A bare method name still answers `no_such_symbol` while its qualified form has 82 callers'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [054, 011, 013]
---

## Goal
`find_callers("isEnabled")` returns `{"results": [], "reason": "no_such_symbol", "total_count": 0}`.
`find_callers("\Ns\Sub\Flags::isEnabled")` returns **82**. The bare form is the one an agent reaches
for when it has a method name from a diff, a log line, or a review comment and not a namespace — and
the answer it gets is the vocabulary's word for *this symbol does not exist*. [054](054_bare-name-callers-silent-drop.md)
fixed the resolver-side drop (call sites discarded at `max_candidates`); the **subject** side was
never brought into that honesty. Round 4 reproduced it on two different names.

## Evidence (field retro round 4, 2026-08-10, post-hoc probes P2/P3)
- Verbatim, `find_callers("isEnabled")`:
  ```json
  {"results":[],"reason":"no_such_symbol","total_count":0,
   "frontier_skipped_non_resolved":0,"limit_capped_to":10}
  ```
  while the qualified form on the same session returned `total_count: 82` with
  `result_subtrees: {"public":26,"src":37,"tests":19}`.
- `find_callers("get")` → `no_such_symbol`, while `\Ns\Sub\Enum::get` demonstrably exists (its body
  was read in the same session, lines 94–97).
- Neither payload carried `bare_name_truncated` nor any other 054 field. The retro's verdict on the
  054 verification item is **NOT FIXED (reproduced)** — the only such verdict in the round.
- The evaluator's R-2 caveat is itself the finding: *from outside* there is no way to tell whether
  bare-name resolution was attempted and capped, was attempted and found nothing, or was never
  attempted for this name shape. Three very different situations, one payload.
- Consequence recorded in the same retro's verdict section: the repo's standing instruction ("never
  `grep` for symbols, code-atlas is mandatory") had to be given a written carve-out for bare names,
  because following it produces a wrong answer.

## What "honest" looks like here
Three outcomes must be distinguishable without reading code-atlas source:
1. **The name is not a qname we hold, but N indexed symbols end with it** — the question was
   under-specified, not answered. Name the route: `try_instead: "search_symbol"`, and say how many
   candidates exist.
2. **The name resolves to exactly one symbol** — answer it, and say what it was resolved to, so the
   agent can tell the answer is about the symbol it meant.
3. **Nothing in the index ends with that name** — `no_such_symbol` is then true, and this ticket
   changes nothing about it.

## Scope / Deliverables
- **Classify a bare subject before answering.** Count indexed symbols whose qname ends with the bare
  name (`::name` for methods, trailing segment for classes/functions) and branch on 0 / 1 / many.
- **Give the "many" case its own reason value** (e.g. `name_not_qualified`) plus the candidate count
  and `try_instead: "search_symbol"`. An empty result with a reason that means "you asked a broader
  question than this tool answers" is a correct answer; `no_such_symbol` is not.
- **Decide the "exactly one" case explicitly** — answer it and echo the resolved qname, or refuse
  uniformly. Either is defensible; silently returning zero is not. Record the choice and why.
- **Cover every single-subject tool**, not just `find_callers`: `find_references`,
  `find_implementations`, `impact`, `read_symbol`, `find_view_data`, `explain_path`.
- **Re-verify 054's Part B against a live index** and state whether it still holds on the path it
  was built for; if the field can no longer observe it, that is a test-surface gap to close here.
- **Coordinate with [075](075_read-symbol-confident-zero-on-unnormalised-qname.md)** — the malformed
  and the under-qualified subject are the same defect class ("my question was wrong" reported as "the
  world is empty"). One reason-vocabulary change may serve both; decide in design, not in review.

## Constraints
- R3 — a new reason value bumps `contract_version` and extends the conformance suite.
- R4 — the candidate count must be deterministic; no ranking heuristics that reorder run to run.
- Cost: the classification runs on the miss path only. A hit must not pay for it, and a bare-name
  miss must not fan out into an unbounded scan — bound it and disclose the bound (066's precedent).
- 054 stays authoritative for the resolver-side drop; this ticket does not re-open that mechanism.

## Acceptance criteria
- A bare method name with indexed candidates returns a reason that is **not** `no_such_symbol`,
  carries the candidate count, and names a tool that then finds them; a test pins the whole payload.
- A bare name with zero candidates still returns `no_such_symbol`.
- The qualified form's answer is byte-identical to today (R4).
- Every single-subject tool has a test for the bare-name path, or a recorded reason why it cannot
  receive one.
- 054's Part B has a live-index verdict written into that ticket.

## Resolution (2026-08-11)
Delivered together with **075** under one shared design — the mango working doc lives in
[`075`](075_read-symbol-confident-zero-on-unnormalised-qname.md) (below its raw-ticket separator).
One language-agnostic classifier (`nav_result.classify_missing_subject`) serves both: a bare/under-
qualified subject with candidates returns `name_not_qualified` + `candidate_count` +
`try_instead: search_symbol` across every single-subject tool; a zero-candidate bare name stays
`no_such_symbol`. No adapter `contract_version` bump (reason codes are tool-output vocabulary, not the
adapter contract). 054's Part-B live verdict is written into that ticket.

## References
Field retro round 4 §A.10 (`NOT FIXED (reproduced)`), §4 rows 3–4, §10 carve-out (a); probes P2/P3.
Related: [054](054_bare-name-callers-silent-drop.md) (resolver-side drop — the fix that this one is
the other half of), [065](065_empty-answer-cannot-explain-itself.md) (reason + `try_instead`),
[075](075_read-symbol-confident-zero-on-unnormalised-qname.md) (same class, malformed qname),
[013](013_nav-tools.md), [011](011_resolver.md).
