---
id: 093
slug: try-instead-is-not-a-callable-tool-name
title: '`try_instead: "find_references_on_method_qname"` is not a tool, but every other `try_instead` is'
phase: 1.5b
milestone: Agent-fit
status: done
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

---

# Working doc — 093

`work_doc_mode: embed` (plain local-file ticket; raw ticket above the separator, working doc below).

## Session status
- **Phase:** finalise. `TIER: lite` (quick lane), `SCOPE: S`, cause: `validation`.
- **Branch:** `fix/093-try-instead-is-not-a-callable-tool-name`.
- **Gates:** refine skipped (0 unresolved product-decisions) · Gate 1 + Gate 2 surfaced in-conversation
  and passed on the maintainer's standing approval for this run · **review waived by the run args**
  (`with skipped review`) — no reviewer/challenger dispatched, and the waived gate is not reintroduced.

## Phase 0 — refine (skipped)
`refine skipped: 0 unresolved product-decisions.` Premise check passed: every source the ticket cites
as already existing resolves — `nav_result.py:59-60` held exactly the two prose constants, and 065 /
069 / 076 / `which_tool` / `tests/contract/` are all present.

The one decision the ticket poses ("either `try_instead` stays a tool name and a sibling field carries
the qualifier, or `try_instead` becomes a small object") is a **how-decision already resolved by
citation**, not an open want: 092 shipped `try_instead_hint` (`nav_result.py:66,300`;
`CONVENTION.md:139`) and this ticket's own References say 092 "adds a new route and must obey this
shape". Nothing was handed back as `ASSUMED`.

## Phase 1 — analysis

### R1 audit — every `try_instead` value the core can emit
Exhaustive: `grep -rn TRY_INSTEAD code_atlas/` → 6 constants, 5 routes + 1 hint. No tool builds the
field from a literal; every emitter imports a constant.

| constant | value (before) | register | emitter | verdict |
|---|---|---|---|---|
| `TRY_INSTEAD_FIND_REFERENCES_ON_METHOD_QNAME` | `find_references_on_method_qname` | **prose** | `find_references.py:135` | rewrite |
| `TRY_INSTEAD_PATH_BASENAME_SEARCH` | `path_basename_search` | **prose** | `include_graph.py:75` | rewrite |
| `TRY_INSTEAD_FILE_OUTLINE` | `file_outline` | tool | `search_symbol`, `find_callers`, `find_references`, `find_implementations`, `find_view_data`, `read_symbol` | keep |
| `TRY_INSTEAD_SEARCH_SYMBOL` | `search_symbol` | tool | `nav_result.py:283`, `read_symbol.py:172` | keep |
| `TRY_INSTEAD_BUILD_OR_UPDATE_INDEX` | `build_or_update_index` | tool | `nav_result.py:299` | keep |
| `TRY_INSTEAD_HINT_UNTRACKED` | prose | hint | `nav_result.py:300` | keep |

### Coverage matrix

| # | source | requirement | evidence | verdict |
|---|---|---|---|---|
| R1 | Scope | audit every value; split into two registers | table above | ✅ |
| R2 | Scope | decide the shape, 061 payload-weight in view | sibling `try_instead_hint`; both hints ride misses that were already conditional, so no common-path payload gains weight | ✅ |
| R3 | Scope | rewrite the two non-tool values | `find_references.py`, `include_graph.py` | ✅ |
| R4 | Scope | pin the invariant with a test | `tests/test_try_instead_is_a_callable_tool_name.py` | ✅ |
| R5 | Scope | update consumers — conformance suite, `which_tool`, docs | see *Not changed* below; docs updated | ✅ |
| AC1 | AC | test enumerates every value, asserts callable ones are registered | `test_every_try_instead_route_is_a_registered_tool_name` | ✅ |
| AC2 | AC | §4 row 2 payload carries route + hint, pinned whole | `test_the_field_reported_payload_is_pinned_whole` (full-dict equality) | ✅ |
| AC3 | AC | `which_tool` + conformance agree with the new shape | both are silent on the field (0 hits) — reported, not skipped | ✅ |
| AC4 | AC | no empty-answer payload loses a route | every emitter still sets `try_instead`; two gained a hint | ✅ |
| C1 | R3 | decide on a `contract_version` bump | **no bump** — `contract.py` has 0 hits for `try_instead`; it is tool-output vocabulary (075/076 precedent) | ✅ |
| C2 | R1.1 | derive tool names from the registry | test reads `main.TOOL_NAMES` + `vars(nav_result)` | ✅ |
| C3 | R4 | deterministic — same miss, same route | constants only; no branch on clock, path order or state | ✅ |
| C4 | 065 | 065 owns *when* a route is carried; 093 owns *what it says* | no reason code added, removed or re-gated | ✅ |

## Phase 2 — design

**Shape chosen: `try_instead` = a registered MCP tool name; the qualifier moves to the sibling
`try_instead_hint`.** The object shape was rejected: it would break 092's already-shipped flat field
for no gain, and 061 favours a flat conditional sibling over nesting on an empty answer.

| old value | new `try_instead` | new `try_instead_hint` |
|---|---|---|
| `find_references_on_method_qname` | `search_symbol` | `list the class's methods, then re-ask find_references with a method qname (Class::method) — the class-level reference is not modelled` |
| `path_basename_search` | **none — hint only** | `no indexed tool answers this — the include path is bare or dynamic, so search the file's basename as text outside the index` |

**Both rows were revised by review; see Phase 4.** The first draft self-routed
`find_references` → `find_references` and routed the include miss to `search_symbol`. Callable is
not the same as useful: a route must also **make progress** and **be able to answer**.

**The naming rule is the mechanism.** `TRY_INSTEAD_*` is a tool name, `TRY_INSTEAD_HINT_*` is prose.
The test derives both sets from the module namespace rather than a list, so the rule holds for values
that do not exist yet (R1.1 — a hand-kept list is the thing that drifts).

### Change list (approved at Gate 2, not widened)
- `code_atlas/tools/nav_result.py` — rename/replace the two prose constants, add the two hints, give
  `attach_try_instead` an optional `hint` (a hint without a route is dropped).
- `code_atlas/tools/find_references.py`, `code_atlas/tools/include_graph.py` — emit route + hint;
  docstrings name the new shape.
- `tests/test_try_instead_is_a_callable_tool_name.py` (new) — the invariant + both payloads.
- `tests/test_empty_answer_cannot_explain_itself.py` — 065's consumers follow the new constants.
- `docs/` — PLAN (2 tool-table rows + §round-5 shipped paragraph), CONVENTION (the two-register
  rule), BACKLOG (status + token row), this working doc, LESSONS.

## Phase 3 — execute

**Verification, in order:**
1. New test file green on the branch: `6 passed`.
2. **The gate is real** — `git stash` back to the pre-093 shape and re-run: **4 failed, 2 passed**
   (`test_every_try_instead_route_is_a_registered_tool_name`,
   `test_the_two_field_reported_prose_values_are_gone`,
   `test_the_field_reported_payload_is_pinned_whole`,
   `test_the_route_out_of_include_graph_is_callable`). A test that passes on both shapes is not a gate.
3. Full Docker gate `scripts/docker-test.sh` (ruff · mypy · pytest): **1173 passed**, 0 skipped.
   `main` baseline **1167**; +6 new tests, none removed or renamed. Two ruff E501s were fixed on the
   first run and the gate re-run clean end-to-end.
4. **After review** (Phase 4): +2 more tests (the dead-route guard's own proof, and the no-self-route
   pin) — full gate re-run, see the count in BACKLOG's token row.

### Not changed, and why (R5, reported rather than silently skipped)
- **The conformance suite** (`tests/contract/`) — `grep -rn try_instead tests/contract/` returns
  **nothing**. The suite pins the *adapter* contract (`contract.py`), and `try_instead` is tool-output
  vocabulary that never crosses the adapter seam. Nothing to reconcile; this is also why C1 is "no
  bump" rather than a judgment call.
- **`which_tool`** (`code_atlas/tools/prompts.py`) — the map routes *questions to tools*; it never
  quotes `try_instead`. Editing it to mention the field would have added agent-scan weight (081/069)
  to serve a field the prompt does not carry.
- **README** — 0 hits for `try_instead`.

## Phase 4 — review (on PR #103)

Review was waived at solve time by the run args; the maintainer then ran `/code-review` on the PR.
Four findings, all verified against the tree before acting — two of them substantive, and one of them
a false-green in a test written *to be* a gate.

| # | finding | verified how | verdict |
|---|---|---|---|
| R1 | `test_every_route_constant_is_reachable_from_a_tool_module` **can never fail** — `pkgutil.iter_modules` includes `nav_result`, the definition site, so every constant is always "found" | ran the scan by hand: `TRY_INSTEAD_BUILD_OR_UPDATE_INDEX` → `['nav_result']` only, and the test still passed | **confirmed — fixed** |
| R2 | `include_graph`'s new route is callable but **cannot answer the question** | ran the route end-to-end: `search_symbol("lib.php")` returns `reason: ok`, `total_count: 2`, includer absent | **confirmed, worse than reported — fixed** |
| R3 | the `find_references` self-route **loops** for a reader that follows routes mechanically | payload is byte-identical on re-call, hint is the only exit and needs a method name the agent lacks | **confirmed — fixed** |
| R4 | callability is checked against `TOOL_NAMES`, not the `CA_TOOLS` subset a server actually serves | `main.allowed_tools` does filter; `nav_result` has no `Config` | **confirmed, pre-existing — documented, not closed** |

**R1 — the guard was vacuous.** Fixed by skipping assignment lines rather than the defining module
(skipping `nav_result` wholesale would wrongly flag `TRY_INSTEAD_BUILD_OR_UPDATE_INDEX`, which is
legitimately attached inside `nav_result.py`). Added
`test_the_dead_route_guard_can_actually_fail`, which injects a dead constant and asserts the guard
reports it — a guard that cannot fail is worth nothing, and this one now proves it can. The
`pkgutil`/`ispkg` fragility went away with the switch to `Path.glob("*.py")`.

**R2 — no route is the honest answer.** The unlinked-include evidence lives in `edges.target_raw`
(`store.py:701-714`); `nodes_fts` indexes `name, qualified_name, file_path, params` only
(`store.py:90-92`). Measured, not argued: following the route returns a **confident non-empty**
`reason: ok` with the two symbols declared *in* `lib.php` and no includer. That is precisely the
"empty ≠ unknown / confident wrong answer" failure 065/075/076 exist to prevent — the prose value it
replaced was at least honest that no tool covered this. So the payload now carries the **hint alone**
and no `try_instead`, and `attach_try_instead` allows a hint to stand without a route.

**Does that violate AC4** ("no empty-answer payload loses a route it has today")? No. Under 093's own
two-register framing, `path_basename_search` was never a route — it was a hint in the wrong field.
Reclassifying it loses nothing; the payload keeps its guidance and gains honesty.

**R3 — a route must make progress.** `search_symbol` on the class name returns the class *and its
methods*, verified against the store — exactly the qnames the hint asks the reader to supply. So the
class-level miss routes there instead of to itself. `test_no_route_points_a_tool_back_at_itself`
pins it.

**R4 — documented, not closed.** Closing it means threading the `CA_TOOLS` allow-list into
`nav_result`, which has no `Config` — a change 093 did not buy, and the exposure predates it
(`TRY_INSTEAD_FILE_OUTLINE` has it too). Stated in the test module docstring and in CONVENTION so it
does not read as covered.

**Not changed:** nothing in the review touched the audit table, the contract-bump decision, or the
065 reason-code boundary.

### Follow-up surfaced, deliberately not ticketed
No tool searches unlinked include text, so "who includes this file?" is unanswerable whenever the
include path is dynamic. That is a **capability gap**, not a 093 encoding defect, and ticketing it
here would widen an S-scope ticket. Recorded in `PLAN.md` (§round-5, *Open, not ticketed*) and raised
with the maintainer.

## Decision log
- **Sibling field, not an object.** 092 precedent + 061 payload weight. Cost: one more top-level key
  on two conditional misses. Accepted.
- ~~**`find_references` self-routes.**~~ **Reversed by review (R3):** a self-route loops for the
  mechanical reader the field exists for. It routes to `search_symbol`, which enumerates the method
  qnames the hint asks for.
- **A hint may stand alone (review R2).** Where no registered tool can answer, naming one that cannot
  is worse than naming none: the reader spends a call and gets a confident wrong answer.
- **No `contract_version` bump.** `try_instead` is not in `contract.py`; 075/076 set the precedent
  that nav vocabulary changes do not bump it.
- **Invariant derived, not listed.** R1.1 — the test reads `main.TOOL_NAMES` and `vars(nav_result)`,
  so it covers constants nobody has written yet.
- **A fourth test guards the audit itself** (`test_every_route_constant_is_reachable_from_a_tool_module`):
  a route constant no tool references is dead vocabulary that would quietly falsify R1's table.

## Cost ledger

| phase | dispatch | round | tokens |
|---|---|---|---|
| refine | none — skipped (0 unresolved product-decisions) | — | 0 dispatch |
| analysis / design / execute | none — in-session, main loop only | — | 0 dispatch |
| review | waived at solve time by the run args; then `/code-review` on PR #103 | 1 | **61.7k** (20 tool-uses, 205 s) |
| review fixes | none — in-session, main loop only | — | 0 dispatch |

**Total: 1 subagent dispatch → 1 row.** The solve run itself dispatched none; the review arrived as a
`task-notification`, which carries its `<usage>` block, so the row holds a real number rather than an
`unmeasured` marker. Main-loop output is not measured by mango. Top cost driver: the review dispatch
(61.7k), then the Docker gate runs.
