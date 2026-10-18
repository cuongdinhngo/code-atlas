---
id: 400
slug: incremental-mid-build-partial-answer
title: "An answer read while an incremental build writes the live index drops callers and still says ok"
phase: 2
milestone: Freshness
status: in-progress
depends_on: [356, 365, 388]
---

## Why this exists

This comes from the anchor project's Round-3 feedback (2026-09-20 → 10-18), PR #3179 (2026-10-07).
`find_callers CateringHandoffToken::assemble` answered while a build was running. It listed
`build()` and the tests, but not the production caller `CateringSyncClient::buildServiceToken`,
and nothing marked the answer as partial. `git grep` found the caller. On a finished build the
edge is there and `RESOLVED` (anchor `graph.db`, `CateringSyncClient.php:86`). #3180 and #2927
report the same thing: answers during a build come back `reason: ok` with `build_in_progress: true`.

356 serves the last good index during a **full** rebuild by writing to a shadow. An **incremental**
still writes the live DB in place:

- F1: `incremental_update` stamps `build_complete = 0` (`indexer.py:561`), then reconciles and
  re-parses `changed ∪ dependents` (`indexer.py:516-548`), committing **one file at a time**
  (`store.replace_file_rows`, `store.py:1122`). The re-parsed rows carry adapter targets that only
  the late resolve phase links (`_count_late_writes`, `indexer.py:617`). So between a dependent's
  re-parse and the resolve, its CALLS edges are not linked to the subject. A change to the subject's
  file is exactly what makes its callers dependents.
- F2: that snapshot reads `staleness: incomplete`, but `read_subject` gathers dirty paths and labels
  only on `behind` (`freshness.py:302`). The subject's own file is current, so the answer stays
  `reason: ok`.
- F3: the only signal is `build_in_progress` (`schema_guard.attach_build_state`), whose comment says
  "a newer graph is coming, not this one is partial". That is true of a 356 full rebuild and false
  of an in-place incremental.

This is the one Round-3 finding where an answer was wrong rather than missing. It is also the
failure the PRs describe as the costliest: a caller list that looks complete.

## Scope

1. Decide in design whether readers must never see a half-written incremental (the whole write
   phase in one transaction, or 356's shadow, for incrementals too), or whether an answer read from
   one is labelled. Either way, the pick goes in PLAN §19 with its measured cost.
2. Whichever route is picked: an inbound answer (`find_callers`, `find_references`, `impact`) read
   from an index whose `build_complete` is `0` never answers `ok` with an empty or partial caller
   set. It answers from a complete graph, or it says the set may be partial.
3. Correct the `BUILD_IN_PROGRESS` comment and doc to match: a writer in flight means "partial"
   unless the served graph is the shadowed last good one.

## Acceptance criteria

- **AC1 (proving test):** a fixture where the subject's file changes and a caller lives in a
  dependent file. Pause an incremental between the dependent's re-parse and the resolve, then call
  `find_callers` on the subject. It either lists the dependent's caller, or does not answer `ok`
  and names the partial state.
- **AC2:** with no build running, every answer is byte-identical to before (R4.2).
- **AC3:** a 356 full rebuild still serves the last good index unlabelled as partial.
- **AC4:** the cost of the picked route on the anchor-sized incremental is measured and recorded:
  wall time, plus WAL growth if it is a transaction.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 400 · **work_doc_mode:** embed · **Current phase:** 3 execute · **Next action:** the full suite, then review (gates delegated by the maintainer).
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `solve 400` — `REVIEWER: ON` · `CHALLENGER: ON`.

## Phase 0 — refine

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 12 unresolved surfaced | 2 want-decision asked | 10 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** `incremental_update` (`indexer.py:422`, stamp at :561), `replace_file_rows` (`store.py:1107`, txn
:1122), `_count_late_writes` (`indexer.py:688`, called :618), `read_subject` (`freshness.py:292`, BEHIND-only
dirty at :302), `attach_build_state` (`schema_guard.py:73`), tasks 356 / 365 / 388 resolve. Ambiguous: "the
anchor-sized incremental" (AC4).

**Recall (by handle).** `a-transaction-probe-misses-the-writer-between-transactions` (365-C1): today's in-place
incremental commits per file — the very gap this ticket closes. `widen-every-query-that-shares-the-page`
(362-C1): every reader, not only the three named. `an-absent-reason-is-ok` (396-C1): `impact` has no `reason`.
`confirm-the-blocked-path-runs` (360-C1): the proving test must really pause a running incremental.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 43,786 tokens) raised ten; they are H3–H10 and W2
(its item 5 folded into W1).

| # | Decision | Class | Resolution |
|---|---|---|---|
| W1 | route | want | **asked, answered 2026-10-18:** readers keep the last complete index — an incremental publishes in one step, as 356 does for a full rebuild. No partial label. |
| W2 | the cost bar (AC4) | want | **asked, answered 2026-10-18:** the incremental may be at most 10% slower on this repo's own incremental; above that the route goes back to design. |
| H1 | which tools | how | all — under W1 no reader sees a half-written graph, so no tool needs a label (362-C1 satisfied by construction) |
| H2 | a crashed incremental | how | under W1 it rolls back to the last complete graph; 202's `build_complete = 0` escalation stays for a pre-400 or full-rebuild crash (`indexer.py:450`) |
| H3 | label wording | how | moot under W1 — no new `reason`, no contract change (R3 untouched) |
| H4 | older clients | how | additive by construction: every answer's shape is unchanged (AC2) |
| H5 | rows vs refusal | how | moot under W1 — the answer is complete |
| H6 | precision of "partial" | how | moot under W1 |
| H7 | readers during the write | how | WAL readers read the last committed snapshot and do not wait (`store.py:117` `journal_mode=WAL`) |
| H8 | outbound tools | how | covered by H1 |
| H9 | release | how | a `CHANGELOG.md` *Unreleased* line (`CHANGELOG.md:16`); no schema or contract bump, so no rebuild entry |
| H10 | `build_in_progress` meaning | how | unchanged and now true of both builds: "a newer graph is coming" (`schema_guard.py:19-20`); the comment is kept, the ticket's Scope 3 is satisfied by it becoming correct |

**Correction to H7 (found in analysis).** WAL readers do not wait, but a reader that *writes* does. Under a held
builder transaction a `GraphStore` opens and reads in 0.001 s, while one fit-counter bump waits the full 5.006 s
busy timeout and drops its count (scratch probe, `store.py:834`). Every served call bumps twice (`fit.py:50`,
`fit.py:94`), so W1 without a fix costs every call made during an incremental ~10 s. This is C1 below.

## Phase 1 — analysis

`PREMISE: 8 reference(s) checked | 0 missing | 1 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 3 found (Why this exists · Scope · Acceptance criteria) | 3 decomposed | ROWS: C=2 R=3 G=1 AC=4`
`CLARIFICATION: 14 raised | 12 self-resolved (cited) | 2 for human decision`
`TRACK: backend — 0/6 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

The two for human decision are W1 and W2, answered in Phase 0 (2026-10-18), so Gate 0 is closed.

### Root cause

`config.cause_taxonomy` class: **concurrency / visibility of an intermediate state.** `incremental_update` writes
the live DB in many short transactions (`store.py:1122` per file, then enrichment and resolve), with
`build_complete = 0` committed first (`indexer.py:561`). A reader between two of them sees a dependent re-parsed
but not re-linked: the CALLS rows carry the raw target and `target_qname` is filled only by `resolve_edges`
(`indexer.py:722`). The answer is `reason: ok` because `read_subject` only labels `behind` (`freshness.py:302`).

### Blast radius

- Writer: `incremental_update` (`indexer.py:422`) → `_reconcile`, `_parse_all` → `_write` (`indexer.py:1372`),
  `fold_column_extras`, `_count_late_writes` (enrichment `enrichment.py:220-274`, `resolve_edges`, `publish_routes`),
  `_record_meta`. One writer thread, one connection (`indexer.py:1230`, R4.3).
- Store: every write method commits with `with self._conn:` — 11 sites (`store.py:1032`, `:1087`, `:1101`,
  `:1122`, `:1169`, `:1245`, `:1282`, `:1291`, `:1307`, `:1351`, `:1363`, `:3105`) plus `truncate_graph`'s explicit
  `BEGIN` (`store.py:1258`). An exception inside `with self._conn:` rolls back — under an outer transaction that
  would roll back the whole build, so R5.1's per-file soft-fail (`indexer.py:1391`) needs a savepoint.
- Callers of `incremental_update`: `build_or_update_index` (`tools/build_or_update_index.py:388`), the refresh
  hooks and `code-atlas-build` (through the same function).
- Readers that write (the inventory, N = 4): fit bump (`fit.py:50`), cost bump (`fit.py:94`), read-through repair
  (`freshness.py:137`, already gated by `live_index_held` at `:134`), the poke hook (`hooks/poke.py:74`, not gated).

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Ph1 evidence | Status |
|---|---|---|---|---|---|
| G1 | Why | "an answer was wrong rather than missing" | no reader ever sees a half-written incremental | `freshness.py:302`, `store.py:1122` | ⏳ |
| R1 | Scope 1 | "Decide in design … the pick goes in PLAN §19 with its measured cost" | W1 (one publish step) + a §19 entry with AC4's numbers | W1 | ⏳ |
| R2 | Scope 2 | "never answers `ok` with an empty or partial caller set" | by construction under W1; every tool (H1) | H1 | ⏳ |
| R3 | Scope 3 | "Correct the `BUILD_IN_PROGRESS` comment and doc" | the comment becomes true of both builds (H10); TOOLS.md wording checked | `schema_guard.py:19-20` | ⏳ |
| C1 | derived (H7 correction) | — | a reader's own writes never wait behind the held build: inventory items 1–4 each skip or fail fast | probe above | ⏳ |
| C2 | R5.1 | — | one file's write error still soft-fails that file only | `indexer.py:1391` | ⏳ |
| AC1 | AC | "Pause an incremental … lists the dependent's caller" | W1 → the caller is listed, `reason: ok` | — | ⏳ |
| AC2 | AC | "with no build running … byte-identical" | existing suites unchanged | — | ⏳ |
| AC3 | AC | "a 356 full rebuild still serves the last good index" | existing 356 tests unchanged | — | ⏳ |
| AC4 | AC | "the cost … is measured and recorded" | W2: ≤ 10 % wall time on this repo's own incremental, plus WAL growth | — | ⏳ |

**C1 per-item checklist (N = 4 — review confirms every item):** (1) `fit.py:50` fit bump · (2) `fit.py:94` cost
bump · (3) `freshness.py:137` read-through repair · (4) `hooks/poke.py:74` poke repair.

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — a paused build, a caller row present | 360-C1: the pause must be a real running incremental, not a stub |
| AC2 | yes — the existing suites | |
| AC3 | yes — the existing 356 suites | |
| AC4 | yes — a wall-time ratio ≤ 1.10 and a WAL byte count | W2 pins "this repo's own incremental"; the ticket's "anchor-sized" is not on this machine |

### Rule sections

`RULE SECTIONS: 10 applicable — 10 by change-type | 0 by recalled handle — §R1.4 (change-type) ✅ the transaction API lives in store.py; the indexer asks for it, never names sqlite3 · §R1.8 (change-type) ✅ one "a build holds the DB" predicate for the four reader-side writers (live_index_held) · §R4.2 (change-type) ✅ the same rows as today, only their visibility moves; AC2 · §R4.3 (change-type) ✅ still one writer, now one transaction · §R5.1 (change-type) ✅ C2, a savepoint per file · §R6.1 (change-type) ✅ the proving test plus C1/C2 tests · §R6.5 (change-type) ✅ the proving test is observed red on main · §R6.8 (change-type) ✅ AC1 is a failure mode, so its guard really pauses a running build · §R7.2 (change-type) ✅ the PLAN decision log plus BACKLOG and the ledger · §R7.6 (change-type) ✅ TOOLS.md wording edited in place`

### BASELINE

`.venv/bin/python -m pytest -q -p no:cacheprovider` on the untouched checkout (this ticket file moved aside):
`4738 passed, 4 skipped, 1 xfailed in 607.41s (0:10:07)`. Ran at 289818ee.

**Gate 1 approved** by the maintainer, 2026-10-18. The maintainer then delegated every later gate ("choose the best
approach, make the necessary decisions, and complete the work autonomously"). Each decision is recorded below as
the maintainer's delegated call; nothing past the PR (merge, release) is in that delegation.

## Phase 2 — design

### Approach

1. `store.py` gains one batch: `begin_batch()` opens `BEGIN IMMEDIATE`, and `batched()` commits it on a clean exit
   or rolls it back on any exception. It is a no-op when `begin_batch()` never ran. While it is open, every write
   unit (`_tx()`, which replaces the 12 `with self._conn:` sites) is a `SAVEPOINT`, so one file's error still rolls
   back that file only (C2, R5.1). A write unit that finds the batch's transaction gone, after SQLite rolled it back
   itself, raises instead of continuing in autocommit.
2. `indexer.incremental_update` wraps its body in `store.batched()` and calls `begin_batch()` where it stamps
   `build_complete = 0` today (`indexer.py:561`), below every escalation. An escalated full build therefore still
   reaches 356's shadow publish with no lock held on the live file. Readers see the previous graph until the commit
   (G1, R2, AC1), and a killed incremental leaves it untouched (H2).
3. C1 uses one predicate. `freshness.build_holds_live_db(db_path)` is true when a build holds `write.lock` and
   is not a shadow rebuild. `live_index_held` keeps its 365 probe and reads that predicate first. The fit and cost
   bumps (`fit.py`) and `poke` skip while it holds, so a call during an incremental neither waits 5 s nor spoils
   its answer. A dropped count is the cost (`store.py:826`: "a counter … is still a counter").
4. Docs: the `schema_guard` comment names both builds; TOOLS.md's 365 sentence; PLAN §19; CHANGELOG *Unreleased*.

### Rejected alternatives

- **Label a mid-incremental answer `partial`** — W1 (maintainer, 2026-10-18).
- **356's shadow for incrementals** — it copies the whole 1.1 GB anchor DB per incremental; the transaction moves
  only the delta.
- **A zero busy timeout on the counter handle** — it would drop counts on any brief contention, such as two servers
  bumping at once, not only during a build.

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | batch + `_tx` | `code_atlas/store.py` | every store write | R2, C2 | 1/1 |
| 2 | one publish per incremental | `code_atlas/indexer.py` | `build_or_update_index`, refresh, `code-atlas-build` | G1, R1, R2 | 1/1 |
| 3 | the shared predicate | `code_atlas/tools/freshness.py` | read-through repair | C1 | 1/1 |
| 4 | counters skip | `code_atlas/tools/fit.py` | every served call during a build | C1 (1, 2) | 1/1 |
| 5 | poke skips | `code_atlas/hooks/poke.py` | the edit hook | C1 (4) | 1/1 |
| 6 | comment | `code_atlas/tools/schema_guard.py` | — | R3 | 1/1 |
| 7 | tests | `tests/test_incremental_publishes_once.py` (new), plus any 202 test whose kill semantics move | — | AC1–AC3, C1, C2, H2 | 1/1 |
| 8 | docs | `docs/TOOLS.md`, `docs/PLAN.md` §19, `CHANGELOG.md` | doc budgets | R1, R3 | 3/3 |
| 9 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | bookkeeping tests | — | 4/4 |

`HANDLES: 4 recalled | 4 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- 365-C1 → the proving test reads at every progress tick of a real `incremental_update`, inside and between writes.
- 362-C1 → C1's four reader-side writers are enumerated (Phase 1 checklist), not only the two counters.
- 396-C1 → nothing relabels a `reason`, so an absent one cannot slip past.
- 360-C1 → the pause is a real running incremental (its progress callback), and the test is observed red first.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration — build + tool on a file DB | `find_callers` at every progress tick of a real incremental | authored (fake adapter, `tests/fixtures/adapter`) | ✅ |
| AC2 | integration | the full suite | existing | ✅ |
| AC3 | integration | `tests/test_rebuild_behind_a_shadow_index.py` | existing | ✅ |
| AC4 | runtime — this repo | a recorded before/after incremental on this repo | real corpus (this repo) | ✅ |
| C1 | integration | a served call during a held incremental returns in < 1 s | authored | ✅ |
| C2 | unit — store | one failing file in a batch, the others committed | authored | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_incremental_publishes_once.py` — red on `main` (289818ee), green after.

### Rollback

`git revert`. Nothing on disk changes shape: no schema or contract bump, so no rebuild is needed.

**Gate 2 closed** under the maintainer's delegation, 2026-10-18.

## Phase 3 — execute

Branch `fix/400-incremental-mid-build-partial-answer` from 289818ee.

**Reproduced on `main`** (289818ee, the fake-adapter fixture, `find_callers` at each progress tick). The answers by
phase were: `announce`…`hashing` → `index_behind_subject_changed`, 2 callers · `parse` → `index_stale`, 0 ·
`parse`…`resolve` → `relationship_not_modelled`, **0** · after the resolve → `ok`, 2. The field case kept its other
callers, so the same gap read as `ok` with one missing.

**Red first.** `tests/test_incremental_publishes_once.py` on `main`: `4 failed` (callers lost during parse ·
`a served call waited [10.02, 10.03]` · the stamp read `'0'` after a kill · no `batched`). The new real-SIGKILL test in
`tests/test_killed_build_is_honest.py`, run in a `main` worktree: `1 failed` (`build_incomplete` True).
**Green after.** `4 passed` and `9 passed`. Ruff and mypy are clean on `code_atlas` (`mypy`: 103 files).

**Found during execute.** `_fill_delta_temps` committed through a local alias, `with conn:` (`store.py:3104`), which
the first sweep missed. The batch guard raised `BatchLostError` at the resolve, so it is now a `_tx()` too, 13 sites
in all. Task 202's fixture can no longer produce a half-written index by a kill. Its child now runs with
`begin_batch` disabled, as a pre-400 server wrote, so the escalation it guards stays tested. A new test proves today's
kill leaves the graph intact (H2, R6.8).

**AC4 (W2: ≤ 10 %).** This repo, base dfac9a82 → 289818ee (48 files, 336 re-parsed of 730), each run on a copy of
one base index, `main`'s core vs the branch's, three alternating runs:

| core | seconds | peak WAL |
|---|---|---|
| `main` 289818ee | 7.28 · 7.36 · 7.27 | 5.39 · 5.40 · 5.43 MB |
| branch | 3.73 · 3.65 · 3.65 | 33.78 · 33.76 · 33.80 MB |

The branch is about 50 % faster, with one commit in place of one per file. The WAL peak is transient, about the size
of the delta's pages. Both cores leave identical rows: sha256 `ead5042d1a7ce673` over files, nodes and edges (R4.2).
The anchor's 1.1 GB index will peak higher on a large delta; 212's crossover is the existing cap.

**Axis 1 (the diff ⊆ the change list).** Rows 1–9. Row 7 gained `tests/test_killed_build_is_honest.py`, which the
design named ("any 202 test whose kill semantics move"). **Axis 2.** Approach bullets 1–4 as approved.
