---
id: 245
slug: the-truncated-substring-answer-is-the-one-search-shape-with-no-route
title: '`search_symbol` attaches `try_instead` only when the answer is empty *and* `index_stale`, so the shape that measurably sends the reader to grep — `reason: substring_match` with `total_count` far above `max_results` — is the one answer in the payload that names no narrower query, while the two registry entries that would answer it already exist unused'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [167, 065, 093, 123]
---

## Why this exists (field retro rounds 16 and 17)

065 established the rule this project keeps re-learning: a refusal with no route is a trap. The
routes were built — `TRY_INSTEAD_*` for a callable tool, `TRY_INSTEAD_HINT_*` for prose naming the
qualifier (093), with the explicit design note that *"the route must MAKE PROGRESS"*.

`search_symbol` attaches one, at exactly one condition:

```
if hits.reason == REASON_INDEX_STALE and hits.total_count == 0:
    return attach_try_instead(payload, TRY_INSTEAD_FILE_OUTLINE)
```

`code_atlas/tools/search_symbol.py:265-267`, and the same guard on the batch path at :281-283. So the
empty-and-stale case is routed and **every other partial answer is not** — including the one the
field keeps walking into:

```
search_symbol("QuickAccessModel", kind=Method)
→ reason: "substring_match", truncated: true, total_count: 80, 10 rows returned
```

Ten rows out of eighty, four of them from test doubles, and the wanted method not among them. The
answer is honest — 167's `substring_match` says *near-miss, not hit*, and `truncated` says the page
is short — but honesty without a route leaves the reader to invent the next query. Both rounds
invented the same one: **grep the file, read the qname off the hit, call `read_symbol` directly.**
Round 17 priced that detour at ~90 seconds and noted it was the second consecutive round to take it.

The narrowing advice is already written down. `TRY_INSTEAD_HINT_METHOD_QNAME` exists for a
neighbouring miss and says *"list the class's methods, then re-ask …"*; `TRY_INSTEAD_FILE_OUTLINE`
is the tool that lists them. Neither is reachable from this answer. The retro asked for a
`members_of(qname)` tool; `file_outline` already is one, which makes this a routing defect and not a
surface gap — the 24-tool count stays as it is.

## Scope

- **Route the truncated near-miss.** When `reason` is `substring_match`, or `truncated` is true with
  `total_count` above the returned page, attach the route and the hint that name a narrower query.
- **Make the hint say something true about *this* answer.** A class-name substring over-matching a
  class's own members is a different miss from a bare name colliding across namespaces; if one
  sentence cannot serve both, say which cases get which, and which get none (R5.4c: naming a tool
  that cannot answer is worse than naming none).
- **Reuse the registry.** `TRY_INSTEAD_FILE_OUTLINE` and `TRY_INSTEAD_HINT_METHOD_QNAME` exist; a
  third spelling of the same advice is the drift 093's two-register rule exists to stop.
- **Check the sibling tools for the same gap** and state the verdict: `file_outline`,
  `find_callers` and `find_references` each have a truncation path, and this ticket either fixes the
  class or says why `search_symbol` is the only instance.
- **Out of scope:** a `members_of` tool, changing the ranking (180 owns that), changing `max_results`
  or its double duty (a standing follow-up), and suppressing test-file rows — a separate question
  with its own trade-off.

## Constraints

- **093** — `TRY_INSTEAD_*` holds a registered tool name, `TRY_INSTEAD_HINT_*` holds prose. Neither
  carries the other's kind; the invariant test pins it.
- **R5.4c** — a route must make progress. Routing `search_symbol` back to itself loops for the
  mechanical reader the field exists for.
- **061** — omit when empty. A confident, complete answer gains no field.
- **123 / 067** — `result_kinds` already tells a one-page reader what the page omitted; the hint must
  not restate it.
- **R4.2** — deterministic: the same query returns the same route.

## Acceptance criteria

- A `substring_match` answer over a class with more methods than `max_results` carries a route and a
  hint naming the narrower query, pinned by a test built on the shape the field hit (a class name,
  `kind=Method`, test doubles present).
- The batch (`queries`) path carries it per subject, never on the envelope (101).
- A complete, confident answer is byte-identical to today — asserted.
- No new `TRY_INSTEAD_*` constant duplicates an existing one; the 093 invariant test still passes.
- A written verdict on `file_outline` / `find_callers` / `find_references`.

## References

Field retro round 17 (2026-09-11, maintainer-local) §2.2 and §5 asks 3 and 5; round 16 recorded the
same detour. Related: [065](065_empty-answer-cannot-explain-itself.md) (the rule),
[167](167_a-substring-near-miss-is-reported-as-reason-ok.md) (`substring_match`),
[093](093_try-instead-is-not-a-callable-tool-name.md) (the two registers),
[123](123_file-outline-total-count-is-the-page-length.md) (what the capped page already discloses),
[180](180_search-ranks-a-near-miss-above-exact-matches.md) (ranking, deliberately untouched),
[101](101_nav-tools-take-one-subject-at-a-time.md) (per-subject routes on the batch path).

## Token usage

| Phase | Tokens |
|---|---|
| autorun | unmeasured (see TOKEN_LEDGER 245) |

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **Ticket:** 245
- **Type:** bug
- **Repo(s):** app
- **SCOPE:** S
- **STRUCTURE:** native
- **TRACK:** backend
- **TIER:** full
- **BASELINE:** green
- **work_doc_mode:** embed
- **working-doc path:** docs/tasks/245_the-truncated-substring-answer-is-the-one-search-shape-with-no-route.md
- **branch:** fix/245-truncated-substring-answer-no-route
- **plugin:** mango 1.16.1 @ /home/you/.claude/plugins/cache/mango-plugins/mango/1.16.1 (candidates: 6)
- **reviewer:** off · **challenger:** on
- **Phase:** finalise

---

## Phase 0 — Refine

`PREMISE: 12 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

refine skipped: 0 unresolved product-decisions

**PREMISE detail.** Present: `code_atlas/tools/search_symbol.py` (`_single_payload` / `_batch_answer` stale-empty guard), `REASON_SUBSTRING_MATCH`, `TRY_INSTEAD_FILE_OUTLINE`, `TRY_INSTEAD_HINT_METHOD_QNAME` in `nav_result.py`, `attach_try_instead`, `file_outline` / `find_callers` / `find_references` truncation paths, tickets 065/093/167/123/101. **Ambiguous (surfaced, not blocking):** field subject `QuickAccessModel` — private field evidence; AC pins the *shape*, not the name (R2).

**INPUT KIND:** ticket (not epic).

**Recalled claims (ADVISORY).**

| # | Claim (id) | Type | Matched by | Relevant here? |
|---|------------|------|------------|----------------|
| 1 | `try-instead-tool-name` | 2 | handle | Yes — 093 two-register reuse |
| 2 | `route-must-answer` | 2 | handle | Yes — R5.4c progress, not self-loop |
| 3 | `prove-the-guard-fails` | 2 | handle | Yes — AC red-before on missing try_instead |
| 4 | `derived-not-listed-invariant` | 2 | handle | Yes — no new TRY_INSTEAD_* spelling |

**Exposure-checker:** skipped (refine skip: yes).

---

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=5 R=5 G=1 AC=5`

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Ph2 covered by | Ph3/4 proven by | Status |
|----|--------|----------|----------------|--------------|----------------|-----------------|--------|
| G1 | Why this exists | substring_match + truncated flood has no route while registry entries exist | Routing defect on the field shape, not a surface gap | `search_symbol.py:266-267` only routes empty stale | D1 | proving test | ✅ |
| C1 | Constraints | 093 two registers | TRY_INSTEAD_* tool name; HINT_* prose; no cross-kind | `nav_result.py:90-99`; invariant test | D1 | `test_try_instead_is_a_callable_tool_name` | ✅ |
| C2 | Constraints | R5.4c route must make progress | Never `try_instead=search_symbol` on this path | ticket Constraints | D1 | assert try_instead == file_outline | ✅ |
| C3 | Constraints | 061 omit when empty | Complete confident answer gains no field | ticket Constraints | D1 | byte-identical AC3 | ✅ |
| C4 | Constraints | 123/067 hint must not restate result_kinds | Hint names the narrower query, not the kind census | ticket Constraints | D1 | hint is HINT_METHOD_QNAME | ✅ |
| C5 | Constraints | R4.2 deterministic | Same query → same route | ticket Constraints | D1 | fixture deterministic | ✅ |
| R1 | Scope | Route substring_match or truncated with total above page | Attach FILE_OUTLINE + HINT_METHOD_QNAME | `_single_payload` / `_batch_answer` | D1 | proving + truncated test | ✅ |
| R2 | Scope | Hint true for this answer; split cases if needed | Both cases get the same registry pair; confident complete gets none | ticket Scope 2 | D1, D3 | design sibling verdict + AC3 | ✅ |
| R3 | Scope | Reuse registry; no third spelling | Import existing constants only | `nav_result.py:96-101` | D1 | 093 invariant still green | ✅ |
| R4 | Scope | Sibling truncation verdict | search_symbol only; siblings differ | file_outline result_kinds; callers/refs already-narrow subject | D3 | written verdict in design | ✅ |
| R5 | Scope | Out of scope: members_of, ranking, max_results, test-row suppress | Do not touch | ticket Out of scope | — | diff excludes those | ✅ |
| AC1 | AC | substring_match over class with more methods than max_results carries route+hint; field shape fixture | Class name, kind=Method, test doubles | today's answer has no try_instead | D2 | proving test | ✅ |
| AC2 | AC | batch path per subject, never envelope (101) | `_batch_answer` attaches inside subject | `:281-283` | D1 | batch proving test | ✅ |
| AC3 | AC | complete confident answer byte-identical | REASON_OK, not truncated → no new keys | ticket AC | D1 | identity assertion | ✅ |
| AC4 | AC | no new TRY_INSTEAD_* duplicate; 093 invariant passes | | | D1 | invariant test | ✅ |
| AC5 | AC | written sibling verdict | | | D3 | design + work doc | ✅ |

## AC validation

| AC ID | Ticket states | Independently computed | Match? | Falsifiable? | If mismatch / not falsifiable → Gate-1 question |
|-------|---------------|------------------------|--------|--------------|-------------------------------------------------|
| AC1 | route+hint on substring_match truncated class/Method | Confirmed: `_single_payload` only routes empty stale | Y | greppable try_instead / hint keys | — |
| AC2 | per-subject on queries path | `_batch_answer` is the subject arm | Y | subject entry keys, not envelope | — |
| AC3 | complete confident byte-identical | omit-when-empty today | Y | dict equality vs pre-change | — |
| AC4 | no new constant; 093 green | grep for new TRY_INSTEAD_ | Y | invariant test | — |
| AC5 | written sibling verdict | design D3 | Y | prose in work doc | — |

## Inventory (universal "all/every/no")

- **Denominator / total N:** 2 payload builders that must grow the arm
  1. `_single_payload`
  2. `_batch_answer`

| # | Item | Ph3/4 proven by | Status |
|---|------|-----------------|--------|
| 1 | _single_payload | proving test | ✅ |
| 2 | _batch_answer | batch AC2 test | ✅ |

## Clarifications

`CLARIFICATION: 3 raised | 3 self-resolved (cited) | 0 for human decision`

- Self-resolved (with citation):
  1. Reuse the `TRY_INSTEAD_HINT_METHOD_QNAME` *constant* (no third spelling) but widen its prose so it stays true for both `find_references` and `search_symbol` (R5.4c / ticket Scope 2). Cite ticket Scope 2–3 + challenger R3.
  2. Attach when `reason == substring_match` **or** (`truncated` and `total_count > len(results)`); empty stale path unchanged. Cite ticket Scope bullet 1.
  3. Sibling tools: `search_symbol` only — `file_outline` truncation already carries `result_kinds` (123); `find_callers`/`find_references` truncate an already-narrow qname subject, not a class-name substring flood. Cite ticket Scope sibling bullet + `file_outline.py:100-101`.
- For human decision: none

---

## Phase 1 — Analysis

- Root cause (bug, `logic`): `_single_payload` / `_batch_answer` attach `try_instead` only when `reason == index_stale` and `total_count == 0` (`search_symbol.py:266-267`, `:281-283`). A `substring_match` truncated flood — the field shape — carries honesty (`reason`, `truncated`, `total_count`) but no route, so the reader invents grep.
- Handler / entry point + blast radius: `search_symbol.create` → `_single_payload` / `_batch_answer`; `nav_result` constants (read-only reuse); 093 invariant test; search exactness tests (must stay green); no contract bump.
- `TRACK: backend — 0/0 touched files under UI paths`
- `SCOPE: S`
- `TIER: full`

`RULE SECTIONS: 7 applicable — 6 by change-type | 1 by recalled handle — R4.2 (change-type) ✅ same query same route · R5.4 (change-type) ✅ file_outline not self-loop · R5.4c (change-type) ✅ route makes progress · R6.1 (change-type) ✅ fixture proving test · R6.5 (recalled handle) ✅ red-before missing try_instead · R6.7 (change-type) ✅ no new derived list · R7.5 (change-type) ✅ comments ≤3 lines`

### BASELINE

Related suite on untouched code:

```
Ran at 0081474e6fbb1ae051cf6dd2023bb0116d5766ed
$ /home/you/WORKSPACE/PROJECTS/code-atlas/.venv/bin/python -m pytest tests/test_search_exactness_band.py tests/test_try_instead_is_a_callable_tool_name.py tests/test_search_symbol_column_references.py -q --tb=line
25 passed in 6.88s
```

`BASELINE: green` for the change-adjacent suite. No baseline exclusions.

- Self-audit: sections 5=5; AC falsifiable; j=0; RULE SECTIONS named; TRACK/TIER/SCOPE declared.
- **Gate 1 status:** cleared (autorun closes on artifacts)

---

## Phase 2 — Design

- **Approach.** In `_single_payload` and `_batch_answer`, after the existing empty-stale arm, when `hits.reason == REASON_SUBSTRING_MATCH` or (`hits.truncated` and `hits.total_count > len(hits.results)`), call `attach_try_instead(payload, TRY_INSTEAD_FILE_OUTLINE, TRY_INSTEAD_HINT_METHOD_QNAME)`. Reuse both registry constants; add no new `TRY_INSTEAD_*`. Leave ranking, caps, and sibling tools untouched. Prove with a fixture: class `QuickAccessModel` with >`max_results` Method nodes (including a test-double file), `search_symbol("QuickAccessModel", kind="Method")` → `reason=substring_match`, truncated, `try_instead=file_outline`, hint is `TRY_INSTEAD_HINT_METHOD_QNAME`. Batch path: same keys on the subject entry, absent on the envelope. Confident complete answer: byte-identical (no try_instead keys).

- **Rejected alternatives.**
  1. New `members_of` tool — rejected: ticket Out of scope; `file_outline` already enumerates.
  2. New HINT constant tailored to search_symbol — rejected: ticket Scope 3 / 093 drift.
  3. Route `try_instead=search_symbol` — rejected: R5.4c self-loop.
  4. Attach on every truncated answer across find_callers/find_references/file_outline — rejected: sibling shapes already disclose differently (D3).

**Assumptions**

| Assumption | verified / novel-untested | If novel-untested → spike / proving test |
|------------|---------------------------|------------------------------------------|
| Class-name Method flood yields `reason=substring_match` when no Method is an exact/prefix of the class name | verified | existing 167 band + fixture will assert reason |
| `attach_try_instead` accepts tool+hint | verified | `nav_result.py:447-459` |

**Smallest change-list**

| # | Change | File/area | Blast radius | Ph2 covered by | k/N |
|---|--------|-----------|--------------|----------------|-----|
| D1 | Attach FILE_OUTLINE+HINT on substring_match / truncated-above-page in single+batch builders | `code_atlas/tools/search_symbol.py` | search_symbol callers; exactness tests must stay green | G1,C1–C5,R1–R3,AC1–AC4 | 2/2 |
| D2 | Proving tests: field-shape fixture + batch per-subject + byte-identical confident | `tests/test_search_symbol_truncated_substring_route.py` (new) | none identified beyond new module | AC1–AC4 | — |
| D3 | Written sibling verdict (this design section) | work doc only | none | R4,AC5 | — |

**Sibling verdict (AC5 / R4).** `search_symbol` is the only instance to fix. `file_outline` truncation already attaches `result_kinds` (123/067) — a census of what the page omitted, not a near-miss needing a different tool. `find_callers` / `find_references` truncate pages of an already-resolved qname subject; their `try_instead` arms cover empty / unmodelled / under-qualified subjects, not a class-name substring flood. No class-wide change.

`HANDLES: 4 recalled | 4 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

| Handle | Answer | Command + result (trimmed) |
|--------|--------|----------------------------|
| try-instead-tool-name | traced | `rg -n 'TRY_INSTEAD_FILE_OUTLINE|TRY_INSTEAD_HINT_METHOD_QNAME' code_atlas/tools/nav_result.py` → constants at 96–101; reuse both |
| route-must-answer | traced | ticket Constraints R5.4c; assert try_instead=file_outline not search_symbol |
| prove-the-guard-fails | traced | proving test will KeyError/assert missing try_instead on pre-fix behaviour via fixture shape |
| derived-not-listed-invariant | traced | `rg -n '^TRY_INSTEAD_' code_atlas/tools/nav_result.py` — no new constant added |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Verification plan**

| AC | Proof layer | Named command / assertion | ❌? |
|----|-------------|---------------------------|-----|
| AC1 | unit | proving test below | — |
| AC2 | unit | batch subject has keys; envelope lacks them | — |
| AC3 | unit | confident complete dict equality / no try_instead | — |
| AC4 | unit | `tests/test_try_instead_is_a_callable_tool_name.py` | — |
| AC5 | design artifact | sibling verdict above | — |

**Proving test (named, runnable):**
`/home/you/WORKSPACE/PROJECTS/code-atlas/.venv/bin/python -m pytest tests/test_search_symbol_truncated_substring_route.py::test_substring_match_truncated_carries_file_outline_route -q`

- **Gate 2 status:** cleared (autorun closes on artifacts)



---

## Phase 3 — Execute

**Branch:** `fix/245-truncated-substring-answer-no-route` (isolated worktree `/tmp/code-atlas-wt-245`)

**Implemented (approved list only):**
- D1: `_needs_narrowing_route` + attach FILE_OUTLINE+HINT on single/batch paths in `search_symbol.py`; docstring updated.
- D2: `tests/test_search_symbol_truncated_substring_route.py` (AC1–AC3).
- D3: sibling verdict already in Phase 2.

**Verification sweep**

```
diff ⊆ approved list: code_atlas/tools/search_symbol.py, tests/test_search_symbol_truncated_substring_route.py, docs/tasks/245_*.md (work doc)
Ran proving suite (pre-commit tree; evidence re-run after commit for Gate 3):
$ /home/you/WORKSPACE/PROJECTS/code-atlas/.venv/bin/python -m pytest tests/test_search_symbol_truncated_substring_route.py -q --tb=line
3 passed in 0.34s
```

**Design-conformance self-check:** passed — no deviations; no new TRY_INSTEAD_* constant; siblings untouched.

**Deviations from approved list:**
- D1b (post-challenger): widen `TRY_INSTEAD_HINT_METHOD_QNAME` prose in `nav_result.py` so the shared hint is true for both call sites (R5.4c). Same constant name; no third spelling. Challenger finding R3.

**Sibling verdict location (AC5):** Phase 2 Design — search_symbol only; file_outline has result_kinds; find_callers/find_references truncate an already-narrow qname.


---

## Phase 4 — Review

- **Reviewer:** waived (`--no-reviewer`) — no rule-book-grounded review of this diff exists.
- **Challenger:** ON — round 1 NOT CLEAN (R3 hint truth / find_references-framed prose); round 2 CLEAN after hint widen at `a14e16d`.
- **Scope vs approved list:** D1 + D1b (nav_result prose) + D2 + D3; diff ⊆ list with D1b recorded.
- **Proving test:** green on reviewed tree (`tests/test_search_symbol_truncated_substring_route.py` 3 passed).
- **Gate 4 status:** clean (challenger CLEAN; reviewer waived)
- **Reviewed at** `a14e16d43e249f759734feba16133c6c477f181b`

---

### Review round 2 — maintainer review on PR #316

**Finding (accepted, fixed): reuse was taken one step too far.** Design clarification 1 kept the
`TRY_INSTEAD_HINT_METHOD_QNAME` *constant* and widened its prose to cover both callers. That made
the hint less true for the consumer that already had it. `find_references` emits it on
`reason=relationship_not_modelled` with `try_instead=search_symbol`, and the widened text

- dropped **find_references** — the tool the reader is meant to re-ask after enumerating — leaving a
  reader routed to `search_symbol` with no named second step, which is the progress R5.4c is about;
- replaced *"the class-level reference is not modelled"* with *"not a method hit"*, which does not
  describe that answer at all: nothing was near-missed there, a relation was unmodelled.

**Fix:** `TRY_INSTEAD_HINT_METHOD_QNAME` restored verbatim, and the near-miss gets its own
`TRY_INSTEAD_HINT_NARROW_BY_QNAME`. Scope bullet 2 authorises exactly this — *"if one sentence
cannot serve both, say which cases get which"* — and bullet 3 bans a second spelling of the **same**
advice, which two different findings with two different re-ask tools are not. The 093 invariant is
unaffected: it pins that a hint is prose and never shadows a tool name, and its dead-constant guard
covers routes, not hints.

**Sibling verdict is unchanged** — `search_symbol` remains the only instance.

```
$ scripts/gate.sh
20 passed · 0 failed · 0 skipped
GATE GREEN — all 20 checks passed
```

## Phase 5 — Finalise

**Durable lesson:** Shared `TRY_INSTEAD_HINT_*` prose must stay true at every attach site (245-C1 / `route-must-answer`).

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`FALSIFY: 1 candidate(s) checked | 1 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`
`RECURRENCE: 1 recurring | 0 superseded (0 retired) | 1 promotion candidate(s)`
`RECURRING-T2: 1 type-2 claim(s) with seen ≥ 2 | 1 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`LEDGER TOTAL: unmeasured · top cost driver: challenger×2 + main-loop`

**Outward actions (autorun-authorised):**
1. Push feature branch `fix/245-truncated-substring-answer-no-route`
2. Open PR from template

**Deferred to morning (not authorised):** merge, force-push, tracker transitions beyond PR.

**Token usage (working doc)**

| Phase | Tokens |
|---|---|
| refine–design | unmeasured (main-loop) |
| execute | unmeasured (main-loop) |
| review | 2× challenger dispatch unmeasured; reviewer waived |
| finalise | unmeasured (main-loop) |

