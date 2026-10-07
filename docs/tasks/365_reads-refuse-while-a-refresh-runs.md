---
id: 365
slug: reads-refuse-while-a-refresh-runs
title: 'While a background refresh runs, read_symbol and find_references answer index_stale, so the agent drops to Grep'
phase: 2
milestone: Adoption
status: done
depends_on: [356, 357, 274]
---

## Why this exists

356 keeps a full rebuild behind a shadow index. The anchor project's field retro shows that the
incremental path still refuses. This is the most frequent reason the agent fell back to Grep (the
7 PRs below), and it still happens after 356 landed.

- F1 (2 PRs, 2026-10-07): `find_references` on a table → `index_stale` "during the background
  build".
- F2 (1 PR): index `behind`, and `read_symbol` on a controller class → `index_stale`.
- F3 (3 PRs): `read_symbol` → `index_stale` while a build ran.
- F4 (1 PR): `read_symbol` on a table → `subject_ambiguous` mid-rebuild.

**Reproduced (2026-10-07, real PHP adapter, scratch repo).** Build, commit an edit to `A.php`, then
hold `write.lock` and a SQLite write transaction the way an incremental refresh does:

| Call while the lock is held | Answer | Wall |
|---|---|---|
| `read_symbol` / `find_callers` / `find_references`, subject **unchanged** | `ok` | 0.0 s |
| `read_symbol A::m`, subject **changed** | `index_stale`, no route | 5.0 s |
| `find_callers A::m`, subject changed | `index_stale` | 5.0 s |
| `find_callers` / `find_references A::m`, `serve_behind=true` | `index_behind_subject_changed`, 1 hit | 5.0 s |
| Any of the above, lock released | `ok` | 0.0 s |

So an unchanged subject already answers. The refusal hits only the subject the commit just changed,
which is exactly the file an agent asks about next. Read-through repair (035) calls
`reparse_file`, which writes to the live DB, waits out `busy_timeout=5000` behind the refresh's
transaction, fails, and the guard answers `index_stale`. The caller cannot cure that refusal: the
cure, a refresh, is already running. `read_symbol` has no `serve_behind` and no route at all.

**Decision.** Treat a held lock as "repair is in progress", not as a repair failure. This narrows
257's opt-in (PLAN §19) to one condition instead of reversing it, so it needs a one-line §19 entry.

- *Rejected: serve unchanged subjects labelled.* The table shows they already answer `ok`, so this
  would change nothing.
- *Rejected: flip the `serve_behind` default.* It changes every behind answer to fix one condition.
- *Rejected: wait for the refresh.* An incremental costs about a minute on a large index (052, 357).

## Scope

1. Read-through repair probes `write.lock` without blocking (`index_lock.try_index_write_lock`)
   before it writes. When the lock is held, skip the write and the 5 s wait.
2. With the lock held, `find_callers`, `find_references` and `impact` on a changed subject answer
   from the built graph as 267's `index_behind_subject_changed`, with the built revision, without
   `serve_behind`. Add `refresh_in_progress: true`. Inbound edges come from other files, which a
   per-file staleness check vouches for.
3. With the lock held, `read_symbol` on a changed subject parses the file *without writing*. Split
   `reparse_file` into a parse half and a write half; the store is untouched (R1.4). It serves the
   current bytes and span, labelled as read through this call. If the parse fails, it refuses as
   today, but with a route and with `refresh_in_progress`.
4. `get_index_status` says that a refresh is running and the served graph is usable.
5. Out of reach of this repro, and still to reproduce: F1 ran during a 356 *full* rebuild, which
   writes the shadow and leaves the live DB unlocked. F4 is `subject_ambiguous`.
   Fix them here only if they share this cause; otherwise file them.

## Acceptance criteria

- **AC1:** With the lock held, `find_callers` and `find_references` on a subject changed since the
  build answer `index_behind_subject_changed` with the built revision and `refresh_in_progress`,
  in under 1 s.
- **AC2:** With the lock held, `read_symbol` on that subject returns its current source, in under
  1 s, and the store is byte-identical afterwards.
- **AC3:** Unchanged subjects, and every call with no lock held, are byte-identical to today.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 365 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews and merges the PR. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`, batch 365 → 366 → 361 → 362 → 364 → 363;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `fix/365-reads-refuse-while-a-refresh-runs` from `main` (`fb256ec5`). Contract `.mango/run-contract-365.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 10 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 4 want-decision asked | 8 how-decision resolved+cited | 4 ASSUMED | skip: no`

**Premise.** All ten resolve: `index_lock.try_index_write_lock` (`index_lock.py:101`), `indexer.reparse_file`
(`indexer.py:705`), `busy_timeout=5000` (`store.py:110`), `index_behind_subject_changed`
(`nav_result.py:57`), `serve_behind` (`find_callers.py:123`, `find_references.py:240`), and the tools
`read_symbol`, `find_callers`, `find_references`, `impact`, `get_index_status`. Ambiguous: "the way
257/267 label it" names archived tasks; the label is `label_serve_behind` (`freshness.py:224`).

**Recall (by handle — the change threads a guard verdict through its callers).** `360-C1`
`confirm-the-blocked-path-runs`; `343-C2` `formatter-rewrites-untouched-lines`. Retired skipped: `349-C1`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 56,527 tokens) surfaced X1–X12. The four
want-decisions were handed back by the run's handover ("make the necessary decisions") and are
**ASSUMED (awaiting ratification)**.

| # | Decision | Class | Resolution |
|---|---|---|---|
| X1 | `impact` in Scope 2 | how | dropped: `impact` never refuses on a stale subject — it computes and attaches `staleness` (`impact.py:231,245`) and is no `FreshnessGuard` consumer. Recorded as a deviation (P3) |
| X2 | the other guard consumers (`find_implementations`, `find_view_data`, `file_outline`, `search_symbol`) | want | **ASSUMED:** the probe lives in `FreshnessGuard.ensure`, so all of them stop waiting 5 s and refuse at once (R1.8, one implementation); only the two tools that already carry `serve_behind` semantics serve labelled, plus `read_symbol`'s parse path. The other four keep `index_stale`, now with `build_in_progress` beside it (`schema_guard.py:66`) |
| X3 | `refresh_in_progress` | how | reuse `build_in_progress`: the schema guard already stamps it on every answer while a writer holds the lock (`schema_guard.py:20,69`); CONVENTION §6 "one name per fact". Deviation from the ticket text (P3) |
| X4 | Scope 4 | how | `get_index_status` already sets `build_in_progress` and `build_progress_route` (`get_index_status.py:241-245`). What is missing: the summary does not say the served graph answers, and `behind_refuses` still names callers/references (`get_index_status.py:305`), which would now be false while the DB is held (R5.5) |
| X5 | full rebuild vs in-place incremental | how | probe the **live DB's** write lock, not `write.lock`: a 356 full rebuild writes `graph.db.shadow` and leaves the live DB writable (`store.py:774-790`), so read-through repair keeps working there exactly as today; only an in-place writer makes the probe fire |
| X6 | the bar for Scope 5's "same cause" | want | **ASSUMED:** one reproduction attempt each in this ticket. A full rebuild holding only `write.lock` is pinned as *repair still works* (X5); `subject_ambiguous` mid-rebuild is not reproduced and goes to BACKLOG Follow-ups |
| X7 | `read_symbol`'s label | want | **ASSUMED:** `reason: ok` (the body is the file's current bytes, parsed this call) plus a sibling `parsed_unstored: true`; no new `NavReason` |
| X8 | the route on a failed parse | how | none: no registered tool can return a body the index lacks while the writer holds it (R5.4c); the refusal is today's, plus `build_in_progress` |
| X9 | where the parse half lives | how | `indexer.py` beside `reparse_file`, which it is split from (R1.4: the indexer drives adapters, `store.py` owns SQLite). A deleted file never reaches it — `ensure` refuses a missing path first (`freshness.py:98`) |
| X10 | AC2's "byte-identical" and "under 1 s" | want | **ASSUMED:** byte-identical = the `iterdump()` of `graph.db` (logical content; WAL/SHM sidecars excluded); "under 1 s" asserted as under half the 5 s busy timeout, so the test proves "no busy wait" without timing flake |
| X11 | Scope items with no AC | how | Scope 1, Scope 4 and X5 get their own matrix rows and tests (below) |
| X12 | the probe's race and whether it holds a lock | how | a zero-wait `BEGIN IMMEDIATE` + `ROLLBACK` on the reader's own connection: never touches `write.lock` (so 357's requester protocol is undisturbed) and holds nothing. A writer that frees the DB right after the probe only costs a labelled answer where a repair would have worked |

## Phase 1 — analysis

`PREMISE: 10 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 1 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=5 G=1 AC=3`
`CLARIFICATION: 12 raised | 12 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/8 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

`main` at `fb256ec5` has the tree of `4e05c246` (`git diff 4e05c246 fb256ec5` is empty), on which
`scripts/gate.sh` printed `GATE GREEN — all 21 checks passed`. Ran at 4e05c246.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "the agent fell back to Grep" while a refresh ran | a read on a changed subject answers while the DB is held | ✅ |
| C1 | Decision | "narrows 257's opt-in … instead of reversing it" | no change when nothing holds the DB | ✅ |
| C2 | X5 | full rebuild keeps today's repair | the probe reads the live DB, not `write.lock` | ✅ |
| R1 | Scope 1 | probe before writing; skip the write and the 5 s wait | `GraphStore.write_locked` in `FreshnessGuard.ensure` | ✅ |
| R2 | Scope 2 | callers/references serve `index_behind_subject_changed` without `serve_behind` | the stale branch turns `serve_behind` on when the guard saw the DB held | ✅ |
| R3 | Scope 3 | `read_symbol` parses without writing | `indexer.parse_file` + a `parsed_unstored` answer | ✅ |
| R4 | Scope 4 | status says the served graph is usable | summary clause + `behind_serves`/`behind_refuses` while held | ✅ |
| R5 | Scope 5 | full-rebuild and ambiguous cases | X6: X5 pinned by a test; `subject_ambiguous` to Follow-ups | ✅ |
| AC1 | AC | callers + references on a changed subject, held → labelled, revision, `build_in_progress`, fast | integration test through `schema_guard.guard` | ✅ |
| AC2 | AC | `read_symbol` on it returns current source, fast, store unchanged | integration test, `iterdump` before/after | ✅ |
| AC3 | AC | unchanged subjects and lock-free calls byte-identical | payload equality, held vs free, and lock-free repair still `ok` | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `reason == "index_behind_subject_changed"`, `last_commit` == built SHA, `build_in_progress is True`, elapsed < 2.5 s | the real PHP adapter, a SQLite `BEGIN IMMEDIATE` holder plus `write.lock` |
| AC2 | yes — `source` contains the post-commit body, `parsed_unstored is True`, elapsed < 2.5 s, `iterdump` equal | |
| AC3 | yes — `payload_held == payload_free` for an unchanged subject (bare tool, no guard); lock-free changed subject → `ok` | |

### Gap analysis (enhancement)

- **Now.** `FreshnessGuard.ensure` calls `reparse_file` on a dirty subject (`freshness.py:103`); its
  write waits `busy_timeout` (5 s) behind the refresh's transaction, fails, and the tool refuses
  `index_stale` (repro table in the ticket).
- **Target.** The guard sees the DB held at once; callers/references label the built graph;
  `read_symbol` reads the current file through the adapter without storing it.

### Blast radius

- `FreshnessGuard.ensure` consumers: `search_symbol`, `find_implementations`, `find_references`,
  `find_callers`, `find_view_data`, `file_outline`, `read_symbol` (grep). Only the DB-held case changes.
- `reparse_file` callers: `FreshnessGuard.ensure` only (`grep -rn reparse_file code_atlas`).
- Status: `_attach_behind_routes` and `_compose_state` (`get_index_status.py:289,335`); `hooks/state.py`
  reads `build_in_progress` and is unchanged.
- Tests pinning `behind_refuses`: `tests/test_behind_status_routes.py` (lock-free, unchanged).
- Docs: `docs/TOOLS.md` freshness lines, CONVENTION §6's `behind_serves` row, PLAN §19's 365 line (wording).

### Rule sections

`RULE SECTIONS: 10 applicable — 10 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the probe and the parse split name no language · §R1.4 (change-type) ✅ the probe is a GraphStore method; the parse half stays in indexer.py and never touches SQLite · §R1.8 (change-type) ✅ one probe in FreshnessGuard.ensure serves all seven consumers · §R4.2 (change-type) ✅ with nothing holding the DB every payload is byte-identical (AC3) · §R4.3 (change-type) ✅ the probe writes nothing and rolls back; read_symbol's parse path writes nothing (AC2) · §R5.4 (change-type) ✅ no route on the parse-failure refusal: no registered tool can answer · §R5.6 (change-type) ✅ a changed subject is never ok from stale rows: labelled index_behind_subject_changed, or parsed_unstored from the file itself · §R6.5 (change-type) ✅ AC1/AC2 run red on fb256ec5 (5 s, index_stale) · §R6.7 (change-type) ✅ BUSY_TIMEOUT_MS becomes the one definition the pragma and the probe share · §R7.6 (change-type) ✅ TOOLS/CONVENTION/PLAN lines edited in place`

## Phase 2 — design

### Approach

1. **`GraphStore.write_locked()`** — zero-wait `BEGIN IMMEDIATE`, `ROLLBACK`, restore the busy
   timeout; `False` inside an open transaction. `BUSY_TIMEOUT_MS = 5000` feeds the pragma and the restore.
2. **`FreshnessGuard.ensure`** — after the hash check and the cap, `store.write_locked()` → set
   `build_held = True`, return `stale` without calling `reparse_file`.
3. **`find_callers` / `find_references`** — in the `stale` branch, when `guard.build_held` and the
   caller did not opt in, turn `serve_behind` on for this call and read the census it needs
   (`compute_staleness`, `dirty_indexed_paths`); `unrepaired_subject_served` and `label_serve_behind`
   then label it as 267 does.
4. **`indexer.parse_file`** — the announce/parse half of `reparse_file`, returning the `ParseResult`
   (or `None`); `reparse_file` calls it and writes.
5. **`read_symbol`** — on the found-node `stale` branch with `guard.build_held`: `parse_file`, pick the
   one parsed node with this qname, serve its current span from disk with `reason: ok` and
   `parsed_unstored: true`. No such node, or a failed parse → today's refusal.
6. **`get_index_status`** — while `build_in_progress` and `behind`: `behind_serves` adds callers and
   references, `behind_refuses` is omitted, and the summary says a build is running and the last
   graph answers. `build_in_progress` is attached before the summary at every detail level.
7. **Docs** — TOOLS.md freshness lines, CONVENTION §6 `behind_serves` row, PLAN §19 365 line.

### Rejected alternatives

- **Probe `write.lock` (`build_in_progress`).** True for a 356 full rebuild too, where the live DB
  is writable and repair works today — it would trade a current answer for a labelled stale one.
- **Hold `write.lock` across the repair.** A refresh arriving then would mark pending and, after one
  retry, be dropped (357's requester), and the reader is no holder that serves the marker.
- **Shorten `busy_timeout` for the repair.** Still spawns the adapter and still waits; the probe
  answers in microseconds without either.
- **Flip `serve_behind`'s default** — changes every behind answer to fix one condition (the ticket).

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | an in-place incremental holds a SQLite write transaction long enough that `reparse_file` fails | verified — the ticket's repro; field refusals at 5 s |
| S2 | `BEGIN IMMEDIATE` with `busy_timeout=0` fails at once when another connection holds RESERVED | verified — spike (WAL, a `BEGIN IMMEDIATE` holder): `locked: database is locked 0.0`; freed → acquired, rolled back, `in_transaction False` |
| S3 | a 356 full rebuild leaves the live DB writable | verified — `open_shadow` writes another file; `publish` is one short transaction (`store.py:774-820`) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | `BUSY_TIMEOUT_MS`, `write_locked` | `code_atlas/store.py` | every store connection's pragma (value unchanged) | R1, C2 | 1/1 |
| 2 | probe in `ensure`, `build_held` | `code_atlas/tools/freshness.py` | 7 guard consumers | R1, C1 | 1/1 |
| 3 | serve labelled while held | `code_atlas/tools/find_callers.py`, `code_atlas/tools/find_references.py` | both tools' stale branch only | R2, AC1 | 2/2 |
| 4 | `parse_file` split | `code_atlas/indexer.py` | `reparse_file` (one caller) | R3 | 1/1 |
| 5 | parse-only answer | `code_atlas/tools/read_symbol.py` | the found-node stale branch only | R3, AC2 | 1/1 |
| 6 | status while held | `code_atlas/tools/get_index_status.py` | `behind_*` fields, summary | R4 | 1/1 |
| 7 | proving tests | `tests/test_reads_during_a_refresh.py` (new) | — | AC1–AC3, R4, R5, C2 | 1/1 |
| 8 | docs | `docs/TOOLS.md`, `docs/CONVENTION.md`, `docs/PLAN.md` | doc budgets | R4 | 3/3 |
| 9 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `tests/test_backlog_bookkeeping.py` | R5 | 4/4 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`confirm-the-blocked-path-runs`** — traced: the ticket's repro ran the blocked path before the design
  (`read_symbol A::m` → `index_stale`, 5.0 s; lock released → `ok`, 0.1 s), and the design keys on
  what the repro showed (only changed subjects refuse) rather than the ticket's first theory.
- **`formatter-rewrites-untouched-lines`** — traced: `ruff format --diff` proposes 49 / 8 / 8 / 14 / 3 / 3
  hunks in `store.py` / `indexer.py` / `find_callers.py` / `find_references.py` / `read_symbol.py` /
  `get_index_status.py` before any edit; none is applied. Only the new test file is formatted.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | real PHP build, a committed edit, a real SQLite writer + `write.lock` held, tools through `schema_guard.guard` | n/a | ✅ |
| AC2 | integration | same, `read_symbol`, `iterdump` before/after | n/a | ✅ |
| AC3 | integration | same repo: unchanged subject held vs free; changed subject lock-free → `ok` | n/a | ✅ |
| R4 | integration | `get_index_status` minimal/standard with the DB held | n/a | ✅ |
| C2 | integration | `write.lock` held, live DB free → changed subject repaired, `ok` | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_reads_during_a_refresh.py`. AC1 and AC2 fail on `fb256ec5`
(`index_stale` after the 5 s busy timeout) and pass after the change.

### Rollback

`git revert` the branch commits. Nothing persistent changes: no schema, no contract, no stored row.

## Phase 3 — execute

Commit on `fix/365-reads-refuse-while-a-refresh-runs`: `ce2366cc` (the change set).

**Proving test, red first** — on `fb256ec5` plus only the `BUSY_TIMEOUT_MS` constant (so the file
imports), the proving file gave `4 failed, 3 passed in 22.08s`: AC1 answered `index_stale` with
`results: []`, AC2 answered `found: True, stale: True`, and `find_implementations` took
`5.047585876003723` s; the status test failed too.

The three that pass there are the regression guards (AC3 ×2, X5), which must hold on both trees.

On `ce2366cc` the same file gave `7 passed in 1.86s` (superseded by Phase 4's run on `e745cfc6`).

**Sweep.**
- Axis 1 — file set: `git diff --name-only main..HEAD` lists the 12 files of change-list items 1–8
  exactly. `ruff check code_atlas` and `mypy code_atlas` clean ("Success: no issues found in 96
  source files"). Only the new test file was formatted.
- Axis 2 — design conformance: Approach 1–7 implemented as approved, with one wording deviation.
  The summary says "the last built graph answers until the build lands", not "a build is running",
  because `hooks/state.py:_build_clause` already appends that phrase to the same line. The rest of
  bullet 6 is as approved.
- Neighbouring suites (freshness, serve_behind, behind routes, status summary, instructions, status
  during a build, state hook, stale warnings, batched sweep, store, shadow rebuild, poke):
  `213 passed in 43.30s`, run on the uncommitted tree that became `ce2366cc`.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `ce2366cc`, 73,940 tokens): 3 met · 3 not met · 3 can't tell.**
It saw four line numbers of this doc through a grep and says it used none of them. Dispositions:

1. **An in-place refresh between its transactions read as free** (medium). **Fixed** in `e745cfc6`:
   `_index_held` also counts `write.lock` held with no `graph.db.shadow`. Test
   `test_an_in_place_refresh_between_its_transactions_still_counts_as_held`; with the clause
   removed it fails (`1 failed, 8 passed`).
2. **Any `OperationalError` read as held** (medium). **Fixed:** only "locked"/"busy" counts.
3. **`refresh_in_progress` not emitted** (medium). **Left, recorded:** X3 reuses `build_in_progress`
   (CONVENTION §6). The test now proves the flag on `read_symbol` too, and TOOLS.md names it.
4. **No route on the parse-failure refusal** (medium). **Left, recorded:** X8, R5.4c — no registered
   tool can return a body the index lacks while a writer holds it.
5. **2.5 s bound vs the ticket's 1 s** (low). **Fixed:** the tests assert 1.0 s.
6. **`impact` untested** (low). **Fixed:** `test_impact_never_refused_and_still_answers_while_held`
   pins X1 (it answers `staleness: behind`, never `index_stale`).
7. **Columns/supertypes from the built graph on a `parsed_unstored` answer** (low). **Documented**
   in TOOLS.md: body and span are current, those fields are the built graph's.
8. PLAN §19 line present — no action. 9. **F1 field case not filed** — **fixed:** BACKLOG names it.

Verify-only (main loop, no re-dispatch — every fix is inside the approved files):

Ran at e745cfc6:
```
$ .venv/bin/python -m pytest -q tests/test_reads_during_a_refresh.py
9 passed in 3.55s
``` The neighbouring suites plus the doc tests gave `235 passed in 68.53s (0:01:08)` on
the tree committed as `e745cfc6`.

`Ph3/4 proven by`: G1, C1, C2, R1–R5, AC1–AC3 — 11/11.

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at e745cfc6 — the diff `main..e745cfc6`. Working doc:
`docs/tasks/365_reads-refuse-while-a-refresh-runs.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `e745cfc6` only bookkeeping changes — this doc, `docs/BACKLOG.md`,
`docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`, all exempt.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

`365-C1` is type 2 (code), handle `a-transaction-probe-misses-the-writer-between-transactions`: asking
SQLite whether it is locked right now misses a writer that holds its own claim across transactions;
probe the writer's claim too. First sighting. Per P1, `360-C1` and `343-C2` gain 365 (both traced).
`343-C2` was already at `seen ≥ 2` before this run, so it is not counted as new recurrence here;
`/mango:promote` remains the cross-ticket pass for it.

### Outward actions

1. Push `fix/365-reads-refuse-while-a-refresh-runs` — pre-authorised.
2. Open the PR against `main` — pre-authorised.

Deferred to the maintainer: the merge; `/mango:promote` on `343-C2` and `360-C1`.

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 56,527 |
| 2 | review | `challenger`, round 1 | 73,940 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 130,467 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits; nothing persistent changes.
