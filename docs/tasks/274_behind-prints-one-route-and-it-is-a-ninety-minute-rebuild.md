---
id: 274
slug: behind-prints-one-route-and-it-is-a-ninety-minute-rebuild
title: 'A `behind` index still serves `search_symbol` and `read_symbol` and still has `serve_behind` for the caller families it refuses, but `get_index_status` names exactly one route — `build_or_update_index`, ~91 minutes on the anchor repo — so two agents on the same day read "behind" as "rebuild before asking anything" and learned the real rule only by trying'
phase: 1.5b
milestone: Agent-trust
status: done
depends_on: [257, 267, 246, 073]
---

## Why this exists (field retro — the anchor repo, 2026-09-14, round 23 §4 / §4e / §4g)

`staleness: "behind"`, `dirty_indexed_files: 0`. What followed, in one session:

- `find_references` ×3 → `reason: index_stale`, zero rows, each time.
- `search_symbol` ×4 (15 subjects) and `read_symbol` ×6 → served from the **same** index,
  `reason: ok`. Two of those answers were the session's decisive findings.

So "behind" does not disable the index; it disables one family of questions. Nothing says so.
`_suggestions` (`get_index_status.py:500–508`) returns `[build_or_update_index]` for any staleness
that is not `CURRENT`, and that array is the payload's only route. The honest reading is *rebuild
before asking anything*, which for a ~91-minute build deters everything.

`serve_behind` already exists on both caller tools (257/267) and is exactly what that session needed
— an unchanged subject on a behind index answers `index_behind` rather than refusing. **No payload
ever names it.** A second agent working the same repo the same day declined the caller family
outright for the same reason, independently, which makes this a reliable trap rather than one
agent's misreading.

The workaround the retro had to derive by hand — `git diff --name-only <last_commit> <head_commit>
-- <area>`, empty ⇒ every symbol answer about that area is still accurate — is a route the status
payload has both commits to name.

## Scope / Deliverables

- **`behind` carries what it still serves.** A `behind` status names the tool families that answer
  from it (search / read, via read-through repair) and the families that refuse without opt-in,
  instead of implying a rebuild is the only move.
- **Name `serve_behind` where it is the route** (R5.4c: a warning an agent cannot act on is a
  warning it learns to ignore — 267's own finding, one round later, on the other side of the same
  payload).
- **A subject-scoped verdict, not only a global flag.** The status holds `last_commit` and
  `head_commit`; the files changed between them are the set that decides whether *this* question is
  affected. Name the count, and the route that narrows it, rather than colouring every subject.
- Applies to the refusal side too: an `index_stale` refusal names `serve_behind` when the subject's
  own file is the drifted one.

## Constraints

- 061 / 223: `minimal` stays cheap — this lands where `staleness` already lands, and adds no field
  to a `current` index.
- **No claim the index cannot back** (R5.6): "search still serves" is true of read-through repair
  within its cap ([246](246_ensure-miss-refuses-on-the-count-of-drifted-files-not-on-the-subject.md)),
  and the wording must not promise a repair the budget may not have.
- No git spawn added to the unbuilt path (077) or to `minimal`.
- The rebuild route stays; this widens the answer, it does not replace it.

## Acceptance criteria

- A behind-index status names the served families and `serve_behind`; a current-index status is
  byte-identical to today's.
- A test pins that `next_tool_suggestions` on `behind` is not *only* the build tool.
- An `index_stale` refusal on a drifted subject names `serve_behind` in its route.
- The runbook sentence a reader can act on — behind ⇒ check the changed set, then search/read freely,
  expect the caller family to refuse — lands in `docs/runbooks/onboarding-a-repo.md`, not in AGENTS.md.

## References
`code_atlas/tools/get_index_status.py:500–508`, `code_atlas/tools/freshness.py:173–188`,
`code_atlas/tools/nav_result.py` (`REASON_INDEX_BEHIND`, `REASON_INDEX_BEHIND_SUBJECT_CHANGED`),
field retro round 23 §4 / §4b / §4e / §4g #1,
[257](257_the-index-goes-blind-at-the-moment-it-is-most-wanted.md),
[267](267_the-warning-an-autonomous-agent-cannot-act-on.md),
[246](246_ensure-miss-refuses-on-the-count-of-drifted-files-not-on-the-subject.md).

---

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 274 — behind status names served routes (working doc)

- **TIER:** full · **TRACK:** backend — 0/0 UI · **SCOPE:** M · **BASELINE:** green · **INPUT KIND:** ticket

## Phase 0 — Refine

`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`

**refine skipped:** ticket locks behind_serves + serve_behind_opt_in + changed_indexed_files (standard) + widen suggestions + index_stale route; current byte-identical; no git on unbuilt/minimal; runbook not AGENTS.md.

## Requirements matrix

`SECTIONS: 5 found (Why this exists · Scope / Deliverables · Constraints · Acceptance criteria · References) | 5 decomposed | ROWS: C=4 R=4 G=1 AC=4`

| ID | Source | Verbatim | Interpretation | Ph2 | Ph3/4 | Status |
|----|--------|----------|----------------|-----|-------|--------|
| G1 | Why | behind read as rebuild-only | name served families + serve_behind | D1 D2 | AC1 | ✅ |
| C1 | Constraints | minimal cheap; no field on current | behind-only fields | D1 | AC1 | ✅ |
| C2 | Constraints | no claim index cannot back | wording via families, not repair promise | D1 | — | ✅ |
| C3 | Constraints | no git on unbuilt/minimal | changed count standard-only | D1 | AC1 | ✅ |
| C4 | Constraints | rebuild route stays | BUILD still in suggestions | D1 | AC2 | ✅ |
| R1 | Scope | name served families | behind_serves + suggestions | D1 | AC1 AC2 | ✅ |
| R2 | Scope | name serve_behind | serve_behind_opt_in field | D1 D2 | AC1 AC3 | ✅ |
| R3 | Scope | subject-scoped count | changed_indexed_files | D1 | AC1 | ✅ |
| R4 | Scope | refusal names serve_behind | attach_serve_behind_route | D2 | AC3 | ✅ |
| AC1 | AC | behind names served + serve_behind; current identical | proving | D3 | proving | ✅ |
| AC2 | AC | suggestions not only build | proving | D3 | proving | ✅ |
| AC3 | AC | index_stale names serve_behind | proving | D3 | proving | ✅ |
| AC4 | AC | runbook sentence in onboarding-a-repo.md | runbook in onboarding-a-repo.md | D4 | proving | ✅ |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis

- Root cause (bug, `config`/honesty): `_suggestions` returns only `build_or_update_index` for any non-CURRENT staleness; caller `index_stale` refusals route to `file_outline`.
- TRACK: backend — 0/0 UI

`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — R5.4 ✅ · R5.6 ✅ · R1.1 ✅ · R6.1 ✅ · R7.6 ✅`

```
Ran at e192a957a8173c7df441909b7120041cd017cc9c
$ .venv/bin/python -m pytest tests/test_mcp_server.py::test_a_current_index_is_not_told_to_rebuild -q --tb=no
1 passed
```

`BASELINE: green`

## Phase 2 — Design

- Approach: widen `_suggestions` for BEHIND; attach `behind_serves` + `serve_behind_opt_in` (+ `changed_indexed_files` at standard via `dirty_indexed_paths`); `attach_serve_behind_route` on caller `index_stale` when opt-in off; runbook + CONVENTION + §19.
- Rejected: putting `serve_behind` in `next_tool_suggestions` (R5.4 — not a tool). Rejected: changed count on minimal (extra git). Rejected: replacing rebuild suggestion.

`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

**Proving test:** `.venv/bin/python -m pytest tests/test_behind_status_routes.py -q`

| # | Change | File | Blast | k/N |
|---|--------|------|-------|-----|
| D1 | behind suggestions + disclosure fields | get_index_status.py | status consumers | 4/4 |
| D2 | attach_serve_behind_route on stale refuse | nav_result.py, find_callers.py, find_references.py | caller tools | 2/2 |
| D3 | proving tests + mcp pin update | tests/ | — | 4/4 |
| D4 | runbook + CONVENTION + §19 | docs | bookkeeping | 1/1 |

## Phase 3 — Execute

**Branch:** feat/274-behind-prints-one-route-and-it-is-a-ninety-minute-rebuild
**Axis 1:** get_index_status.py, nav_result.py, find_callers.py, find_references.py, tests, runbook, CONVENTION, PLAN.
**Axis 2:** implemented-as-approved.

**Verification sweep**

```
Ran at 83d4108ba73343d8f43440577a2efa958a9b9cc7
$ .venv/bin/python -m pytest tests/test_behind_status_routes.py tests/test_mcp_server.py::test_a_behind_index_suggests_more_than_a_build tests/test_try_instead_is_a_callable_tool_name.py -q --tb=line
13 passed in 1.50s
```

`DIFF ⊆ approved list: yes`
`DESIGN-CONFORMANCE: self-check passed`

## Phase 4 — Review

REVIEWER: off (waived --no-reviewer)
CHALLENGER: on — round 1 NOT CLEAN (2 NOT MET: behind_refuses unnamed; narrowing route unnamed). Fixes in 83d4108; verify-only (no re-dispatch). Addressed: behind_refuses + changed_indexed_between.

## Phase 5 — Finalise

`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop (challenger x1)`

Outward actions: push feature branch; open PR. Deferred: merge, tracker writes, force-push.

## Cost ledger

| Phase | Notes |
|-------|-------|
| autorun | reviewer off; challenger x1 NOT CLEAN then verify-fix; main-loop unmeasured; gate GREEN |
