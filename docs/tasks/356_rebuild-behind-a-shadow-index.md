---
id: 356
slug: rebuild-behind-a-shadow-index
title: 'A full rebuild empties the live index first, so every read waits minutes or answers a false empty'
phase: 2
milestone: Adoption
status: done
depends_on: [202, 219]
---

## Why this exists

A full build stamps itself incomplete (`code_atlas/indexer.py:215`), then truncates nodes, edges and
FTS in the live DB (`:218`, `store.truncate_graph` at `code_atlas/store.py:948`) and refills it file
by file over ~9 min on an anchor repo (128 min before 0.2.0). Every read opens the live DB per call
(`code_atlas/tools/read_symbol.py:166`) and never checks `build_in_progress`, so mid-build:

- a dirty tree or moved HEAD with an unnameable subject answers `index_stale`
  (`code_atlas/tools/freshness.py:113`) — the field retro's report (2026-09-30, 2 PRs);
- a **clean** tree answers `ensure_miss` → `ok` (`:103`) and the tool gives a plain not-found for a
  symbol that exists but is not re-parsed yet. A confident false empty (R5.x).

An agent cannot work for the length of a rebuild. The fix is to keep serving the last good index.

## Approach (from the 2026-09-30 investigation; design confirms or replaces it)

Build into a shadow file beside `config.db_path`, then publish with the SQLite backup API
(`shadow.backup(live)`, one destination transaction) under `write.lock`.

- Readers already reopen per call (PLAN §19 concurrency decision, "no descriptor outlives a call"),
  so WAL snapshot isolation makes the switch atomic with no inode/generation detection.
- The live path, inode and `-wal`/`-shm` never change: no `os.replace` over an open file (fails on
  native Windows; stale `-wal` beside a new main file on POSIX) — the reasons shadow + rename lost.
- Rejected: shadow tables + rename (every table, FTS5 and trigger name across `store.py`);
  `graph.<gen>.db` + pointer (touches every `db_path` consumer, hooks and `CA_DB_PATH`).

## Scope

1. `build_or_update_index._build`: a full build (and the schema-older path, which today unlinks
   first) writes the shadow; publish only when the shadow stamps `build_complete`; drop a leftover
   shadow at start; checkpoint after publish, best effort. One helper names the shadow path (R6.7).
2. Incremental stays in place (short transactions); whether a large delta goes via the shadow is
   measured, not assumed.
3. Reads during a build carry `build_in_progress` + the live phase (omit when absent); `reason`
   stays computed against the live index, which is the last good one.
4. A PLAN §19 entry: this reverses 219's reader-visible effect; 202's marker stays for in-place
   incrementals and legacy DBs.

## Risks to settle in design

- Publish holds the destination write lock for seconds on a ~1 GB index: fit-counter writes
  (`store.py:636`) and read-through repair (`indexer.py:647`) may hit `busy_timeout`.
- Publish overwrites rows readers wrote mid-build (fit counters, repairs): merge or accept, stated.
- Disk: up to ~3x the index briefly (shadow + WAL); no free-space preflight exists today.
- Backup in WAL mode needs matching page sizes.

## Acceptance criteria

- **AC1:** A reader looping `read_symbol` / `find_callers` during a full rebuild never sees fewer
  nodes than the previous build, and never a not-found for a symbol the previous build held.
- **AC2:** Killing the build at any phase leaves the live DB byte-identical and `build_complete`.
- **AC3:** After publish, the next call answers from the new index; results equal an in-place
  build row for row (R4.2).
- **AC4:** Mid-build payloads carry `build_in_progress` and the phase; none says `ok` + current
  while live `last_commit` is not HEAD.
- **AC5:** Measured on the anchor-size sample and recorded: publish time, peak disk, reader
  latency during publish. Green on POSIX and the Windows lock arm.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 356 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer reviews and merges the PR, and ratifies ASSUMED A1–A4. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`, batch 356 → 354 → 355;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `feat/356-rebuild-behind-a-shadow-index` off `main` (`5b4f1667`). Contract `.mango/run-contract-356.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 11 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 6 unresolved surfaced | 4 want-decision asked | 2 how-decision resolved+cited | 4 ASSUMED | skip: no`

**Premise.** All eleven resolve on `5b4f1667`: `indexer.py:215` (the incomplete stamp), `:218`
(`store.truncate_graph()`), `store.py:948`, `read_symbol.py:166` (`with GraphStore(config.db_path)`),
`freshness.py:103` / `:113`, `config.db_path`, `write.lock` (`index_lock.py`), PLAN §19's
"no descriptor outlives a call" (`PLAN.md:741`), `build_or_update_index._build`, the fit counter
(`store.py:636`), read-through repair (`indexer.py:647` `reparse_file`).

**Recall (by handle — the change edits shared core modules).** `343-C2`
`formatter-rewrites-untouched-lines`; `344-C3` `verify-the-shipped-artifact-not-the-working-tree`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 37,046 tokens) surfaced four; two more
are the run's own (a sample and a host this machine does not have).

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | reader writes a publish overwrites (fit counters, repairs) | how | carry `fit:*` rows into the shadow just before publish; repairs are not merged — the next read-through re-detects the hash drift. Fit is "not a ranking signal" (`tools/fit.py:5`); "a counter that loses its last few increments … is still a counter" (`store.py:647`) |
| H2 | reads mid-build when there is no last good index | how | first build: the live file does not exist until publish, so reads answer as today with no index (`read_symbol.py:157` `db_path.is_file()`); a legacy incomplete index keeps its `index_complete: false` (202, `get_index_status.py:252`) |
| A1 | not enough disk for the shadow | want (bar) | **ASSUMED:** no preflight and no in-place fallback. The shadow write fails loud (R5.3) and the live index stays untouched; falling back would bring back the false empty AC1 forbids |
| A2 | AC5's numbers | want (bar) | **ASSUMED:** report-only, as the ticket words it ("measured … and recorded"); no ceiling fails the ticket |
| A3 | AC5 names the anchor-size sample; it is operator-provisioned and absent here (`docs/runbooks/scale-sample.md`) | want (bar) | **ASSUMED:** measure on the largest real index on this host (`wwi_dw`, 211 MB) and the pinned `pydantic` sample; record the anchor run as a coverage-gap exclusion |
| A4 | "Green on … the Windows lock arm" — no Windows host or CI job | want (bar) | **ASSUMED:** the Windows arm stays skipped here; recorded as a coverage-gap exclusion. The design adds no platform branch (backup API, no rename) |

Every **ASSUMED** row rests on the maintainer's hand-back in the run's invocation ("You have my
approval to choose the best approach, make the necessary decisions … without waiting for further
confirmation"). None reverses a prior decision. Each is surfaced in the PR for ratification.

**Spikes (SQLite 3.53.1, this host).**

| Spike | Result |
|---|---|
| backup shadow → live WAL DB while a reader holds a read transaction | reader keeps `1000` rows; a fresh reader sees `2000`; journal stays `wal`; FTS carries over |
| backup into a page-size-mismatched WAL DB | `OperationalError: attempt to write a readonly database` → the shadow must take the live page size |
| preset `page_size` then `journal_mode=WAL` on a new file, then `GraphStore` | the shadow keeps page size `1024`, `wal` |
| backup over an old-schema (v5) WAL DB via a raw connection | the destination reads `schema_version` `6`; `GraphStore` opens it |
| `GraphStore` open while another connection holds `BEGIN IMMEDIATE` | 0.0 s — an open never blocks on a writer |
| publish a real 211 MB index (`wwi_dw`) under a reader loop + fit bumps every 50 ms | backup 0.51 s · checkpoint 0.28 s · reader max 12 ms (p50 1.5 ms, 1,146 calls) · fit bump max wait 0.531 s |

## Phase 1 — analysis

`PREMISE: 11 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 6 found (title, Why this exists, Approach, Scope, Risks to settle in design, Acceptance criteria) | 6 decomposed | ROWS: C=3 R=5 G=1 AC=5`
`CLARIFICATION: 6 raised | 6 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/12 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

H1–H2 cite the code; A1–A4 cite the maintainer's up-front hand-back, so `j = 0`. (The first draft
counted A1–A4 in neither bucket; `check_lines.py` refused `U != a + b` and `M != k + j`, and the
counts were corrected to the classification above.)

### BASELINE

`main` at `5b4f1667` is the merge of #16; its tree is identical to `a2ee376e`
(`git diff --quiet a2ee376e 5b4f1667` → exit 0), which CI run 36730042133 passed on py3.12 and
py3.13 (4094 passed / 4 skipped each). Per SG-2 that run is not pasted as a `$` evidence block.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "keep serving the last good index" | no read during a full rebuild answers from a half-built graph | |
| C1 | Approach | "no `os.replace` over an open file" | the live path, inode and WAL siblings never change | |
| C2 | Approach / R1.4 | backup API under `write.lock` | only `store.py` touches SQLite | |
| C3 | R4.2 | "row for row" | a shadow build writes what an in-place build writes | |
| R1 | Scope 1 | full build + schema-older path write the shadow; publish only on `build_complete`; drop a leftover; checkpoint; one path helper | every `full_build` caller, including the four incremental escalations | |
| R2 | Scope 2 | incremental stays in place; a large delta measured | measure; the `full_build_crossover` escalation (212) already routes a large delta to the shadowed full path | |
| R3 | Scope 3 | reads carry `build_in_progress` + phase | every guarded tool, omitted when no writer holds the lock | |
| R4 | Scope 4 | PLAN §19 entry | replaces the 219 line it reverses | |
| R5 | Risks | lock window, overwritten reader writes, disk, page size | each settled in design and measured | |
| AC1 | AC | never fewer nodes, never a not-found for a held symbol | reads at every build phase | |
| AC2 | AC | killed at any phase → live byte-identical + `build_complete` | raise at each phase, and a real SIGKILL | |
| AC3 | AC | next call answers from the new index; equals in-place row for row | shadow build vs `:memory:` in-place build | |
| AC4 | AC | mid-build payloads carry the fields; no `ok` + current off HEAD | read + status during a held lock | |
| AC5 | AC | publish time, peak disk, reader latency; POSIX + Windows arm | A2–A4 | |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — node count ≥ previous, `read_symbol`/`find_callers` hit, at each phase | the fixture build is instrumented through `progress` |
| AC2 | yes — sha256 of `graph.db` and a row dump, before vs after, `build_complete == "1"` | "byte-identical" is read as the main file's bytes plus an empty-or-absent `-wal`; no reader writes during the test |
| AC3 | yes — `snapshot()` equality with a `:memory:` in-place build; a symbol added before the rebuild is found right after it | |
| AC4 | yes — field presence while the lock is held; `staleness != current` when HEAD moved | |
| AC5 | manual-recorded (A2) | numbers pasted in Phase 3; anchor run and Windows arm excluded (A3, A4) |

### Gap analysis (enhancement)

- **Now.** `full_build` stamps the live DB incomplete and truncates it (`indexer.py:215`/`:218`), so
  every read until the late writes finish answers from a partial graph. `_build`'s schema-older
  path unlinks first (`build_or_update_index.py` `_unlink_index`). Four escalations inside
  `incremental_update` call `full_build` on the live store; two of them (`_ScopeChanged`,
  `_TooLarge`) have already stamped the live DB incomplete, and `_TooLarge` has already reconciled it.
- **Target.** Every full build fills a fresh shadow and publishes it in one destination transaction;
  a failed or killed build never touches the live DB.

### Blast radius

- `full_build` callers: `build_or_update_index._run` (3), `incremental_update` escalations (3 sites),
  `scripts/cross_repo_validate.py`, `scripts/scale_full_build.py`, `scripts/tokens_to_answer.py`,
  ~80 test modules. A `:memory:` store (tests) keeps the in-place path.
- Tests pinning the old write order: `tests/test_full_build_truncates_before_writing.py` (219's spy on
  the live store's `replace_file_rows`), `tests/test_schema_version_recovery.py` (`schema_rebuilt`).
  `tests/test_killed_build_is_honest.py` kills an **incremental**, which stays in place — unaffected.
- Every guarded tool gains two omit-when-quiet fields; `get_index_status` already carries
  `build_in_progress`, so its constant moves to `schema_guard` to avoid an import cycle.
- Docs: PLAN §19 (the 219 line), AGENTS.md ("A full rebuild bulk-clears (219)"),
  `docs/design/indexing.md` (the `build_in_progress` row), `docs/design/payload.md`.

### Rule sections

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ no language or platform branch is added: the shadow uses the SQLite backup API on every OS, §R1.4 (change-type) ✅ open_shadow/publish/discard live in store.py and the indexer only calls them, §R4.2 (change-type) ✅ a shadow build is compared row for row with an in-place build, §R5.3 (change-type) ✅ a failed shadow write raises and leaves the live index untouched (A1), §R6.5 (change-type) ✅ every AC is seen red on the pre-change tree, §R6.7 (change-type) ✅ one shadow_db_path helper and one build_phase parser, §R7.6 (change-type) ✅ the PLAN 219 line and the AGENTS.md bulk-clear line are replaced, not appended to`

## Phase 2 — design

### Approach

1. **Store (`store.py`).** `shadow_db_path(db_path)` names `graph.db.shadow` (R6.7).
   `GraphStore.open_shadow(db_path)` removes a leftover shadow and its WAL siblings, presets the live
   file's page size, and returns a store that publishes to `db_path`. `publish()` carries the live
   `fit:*` rows in, backs the shadow up into the live DB through its own connection, checkpoints
   (TRUNCATE, best effort), and deletes the shadow. `discard()` closes and deletes it.
2. **`full_build`.** A file-backed live store is filled through a shadow and published only after
   `_record_meta` stamps `build_complete`; any exception discards the shadow and re-raises. A
   `:memory:` store, or a store that is itself a shadow, is filled in place — the old body, stamp and
   truncate unchanged. The live store reloads its mirror stamp after publish.
3. **`incremental_update`.** The incomplete stamp and `_reconcile` move below the crossover check, so
   the `_ScopeChanged` and `_TooLarge` escalations reach the shadowed full build with the live DB
   untouched. The reconcile reads stay where they are.
4. **Schema-older path.** `_build` opens a shadow instead of unlinking; readers keep the
   `schema_version_mismatch` answer until the publish replaces the old file. `_unlink_index` goes.
5. **Reads mid-build.** `index_lock.build_phase()` parses the live progress line.
   `schema_guard.guard` adds `build_in_progress: true` and `build_phase` to every answer while a
   writer holds the lock, and nothing when it does not.
6. **Docs.** PLAN §19 replaces the 219 line; AGENTS.md, `design/indexing.md`, `design/payload.md`.

### Rejected alternatives

- **`os.replace` of a finished file.** Fails over an open file on native Windows; leaves a stale
  `-wal` beside a new main file on POSIX; breaks the fit counter's inode-keyed handle (`store.py:636`).
- **Shadow in `_build` only.** The four escalations inside `incremental_update` would still truncate
  the live DB.
- **A disk preflight.** Its threshold would be a guess, and the failure it predicts is already safe:
  the shadow write fails and the live index is untouched (A1).

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | a WAL reader keeps its snapshot across a backup into its DB, and the next one sees the new DB | verified — spike |
| S2 | backup needs matching page sizes, and presetting the shadow's works | verified — spike |
| S3 | backup overwrites an old-schema DB into a current one | verified — spike |
| S4 | a 211 MB publish holds the write lock well under `busy_timeout` (5 s) | verified — spike (0.51 s) |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | shadow path, open/publish/discard | `code_atlas/store.py` | `GraphStore` users; fit handle keyed on inode (unchanged inode) | R1, C1, C2, R5 | 1/1 |
| 2 | shadowed `full_build`; incremental stamp/reconcile order | `code_atlas/indexer.py` | every `full_build` caller; incremental escalations | R1, G1, AC1–AC3 | 1/1 |
| 3 | schema-older path via shadow; drop `_unlink_index` | `code_atlas/tools/build_or_update_index.py` | `tests/test_schema_version_recovery.py` | R1 | 1/1 |
| 4 | `build_phase()` | `code_atlas/index_lock.py` | `cli --status`, state hook (read-only) | R3 | 1/1 |
| 5 | mid-build riders in `guard`; `BUILD_IN_PROGRESS` moves here | `code_atlas/tools/schema_guard.py`, `code_atlas/tools/get_index_status.py` | every guarded tool payload | R3, AC4 | 2/2 |
| 6 | tests | `tests/test_rebuild_behind_a_shadow_index.py` (new), `tests/test_full_build_truncates_before_writing.py` | proof collateral: 219's spy moves to the class | AC1–AC4 | 2/2 |
| 7 | docs | `docs/PLAN.md`, `AGENTS.md`, `docs/design/indexing.md`, `docs/design/payload.md` | doc budgets (`tests/test_doc_size_budget.py`) | R4 | 4/4 |
| 8 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md` | `tests/test_backlog_bookkeeping.py` | — | 3/3 |

`HANDLES: 2 recalled | 1 traced (command + result) | 1 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced in Phase 3 with `ruff format --diff` over the
  edited files; only hunks on changed lines are applied.
- **`verify-the-shipped-artifact-not-the-working-tree`** — does not apply because this change ships no
  generated or installed artifact: no plugin file, manifest or marketplace entry moves.

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | real `full_build` over a file DB (fake adapter); `read_symbol`/`find_callers` tools called at every progress tick | n/a | ✅ |
| AC2 | runtime | raise at each phase; plus a real subprocess build SIGKILLed mid-parse; sha256 + row dump | n/a | ✅ |
| AC3 | integration | shadow build vs `:memory:` in-place build `snapshot()`; a new symbol found after publish | n/a | ✅ |
| AC4 | integration | tool payloads while a held `write.lock` carries a progress line; status with HEAD moved | n/a | ✅ |
| AC5 | runtime | manual-recorded measurement (Phase 3) | n/a | ✅ (A2) |

Coverage-gap exclusions (human hand-back, A3/A4):

| Item | Risk tier | Why deferred | Follow-up | Expiry | Seen |
|---|---|---|---|---|---|
| AC5 on the anchor-size sample | medium | the ~112k-file sample is operator-provisioned, absent here | run `scripts/scale_full_build.py` then a `--full` rebuild with a reader loop | when `CODE_ATLAS_SCALE_SAMPLE` is provisioned on a maintainer host | — |
| AC5 "green on the Windows lock arm" | low | no Windows host; CI has no Windows job | run `scripts/verify.ps1` on native Windows | when a Windows CI job or host run is recorded | — |

`EXCLUSIONS: 2 recorded | 2 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_rebuild_behind_a_shadow_index.py`. It fails on `5b4f1667`
(mid-build reads see a truncated graph; a raise mid-build leaves `build_complete = 0`), and passes
after the change.

### Rollback

`git revert` the branch commits. No index needs deleting: a published shadow is an ordinary
`graph.db`, and a leftover `graph.db.shadow` is inert to the old code.

## Phase 3 — execute

Commits on `feat/356-rebuild-behind-a-shadow-index`: `5970568f` (the change), `b38cdd5a` (the
challenger's round-1 findings, below).

**Sweep.**
- Axis 1 — file set. The diff is the change list plus three proof-collateral test files the
  blast-radius trace missed, each a test that pinned the old write order (deviations D2–D4).
- Axis 2 — design conformance. Approach bullets 1–6 implemented as approved, with one addition
  (D1). `ruff check` and `mypy` are clean.
- Handle `formatter-rewrites-untouched-lines`, traced. `ruff format --diff` over the edited files
  proposes many hunks. Only one sat on a changed line (a missing blank line before `DDL`, `store.py`),
  and that one was applied. The rest are on untouched lines and were left alone.

| # | Approved | Implemented instead | `path:line` | Surfaced |
|---|---|---|---|---|
| D1 | bullet 2: publish after `_record_meta` | also a `publish` phase (`PUBLISH_PHASE`, `BUILD_PHASES` derived from `INCREMENTAL_PHASES`) and `removed` measured against the live index, because an empty shadow reads 0 | `code_atlas/indexer.py` `full_build` | yes |
| D2 | — | `tests/test_killed_build_is_honest.py`: the child inherited the host's `CA_<LANG>_CMD`, so on this host its "incremental" escalated to a full build (`scope_change`). Before 356 the test passed by killing that escalated in-place full build; `child_env()` now gives the child the parent's one adapter | `child_env` | yes |
| D3 | — | `tests/test_indexer.py`: `RecordingStore.writers` became one set shared by all instances, because the build writes a shadow of the store it was handed | `RecordingStore` | yes |
| D4 | — | `tests/test_status_during_a_build.py`, `tests/test_build_progress.py`: 178's killed-link test now asserts that the live index was never stamped; the phase vocabulary is `BUILD_PHASES` | — | yes |

**Proving test, red on the pre-change tree.** On `5b4f1667` the new test file does not import
(`shadow_db_path`, `BUILD_PHASE`). A probe script shows the old behaviour directly:

Ran at 5b4f1667

    reads per phase (phase, live nodes, found): [('announce', 0, False), ('tree_walk', 0, False), ('reconcile', 0, False), ('parse', 0, False), ('enrichment', 3, True), ('resolve', 3, True), ('meta', 3, True)]
    after a death at parse: build_complete = 0 nodes = 0

**AC5 and Scope 2, measured.** These ran on a copy of the cached `wwi_dw` checkout (1,736 files,
22,362 nodes, 327,734 edges, 4 adapters) at `5970568f`'s tree:
`scratchpad/ac5.py` and `scratchpad/r2.py`. Each run used a reader thread looping `read_symbol`,
plus a 20 ms disk poller.

    rebuild: full 60.7 s | publish 0.656 s
    peak disk: 649.2 MiB = 3.09 x the index
    reads during build: 39601 p50 1.19 ms max 777.79 ms | not found: 0
    reads during publish: 545 p50 1.14 ms max 3.64 ms
    after: ['graph.db', 'write.lock']
    incremental of 100 files: incremental 11.96 s | wrote 107 | reads 7504 max 782.1 ms | not found 0

- The ~780 ms maximum on both runs comes from the build and the reader sharing one process (GIL);
  the maximum during publish is 3.6 ms.
- **R2 decision:** the incremental stays in place. A per-file replace is one transaction, and no
  read missed during a 100-file delta. A delta large enough to matter escalates to the shadowed
  full build through `full_build_crossover` (212).

Ran at b38cdd5a

```
$ scripts/gate.sh
  PASS bytecode invalidation (checked-hash, 146)
  PASS entry points (derived from [project.scripts])  — code_atlas.egg-info
  PASS ruff check .
  PASS mypy (code_atlas + onboarding_llm)
  PASS npm ci (adapters/typescript)
  PASS npm ci (adapters/sql)
  PASS php adapter runtime deps present (pytest coverage)
  PASS pytest -q
  PASS tokens-to-answer (ratio >= 0.63, recall 1.0, precision 1.0)
  PASS composer validate --strict (R8.3)
  PASS php -l (authored source)  — 8 file(s)
  PASS phpstan level max (R6.6)
  PASS tsc --checkJs --strict (R6.6, TS adapter)
  PASS tsc --checkJs --strict (R6.6, SQL adapter)
  PASS ruff check (R6.6, Python adapter)
  PASS mypy --strict (R6.6, Python adapter)
  PASS R1.1 no language branch in core
  PASS R2.2 no repo/framework name
  PASS R4.1 no LLM in core
  PASS R7.3 no AI-attribution trailer  — 2 commit(s)
  PASS R2.4 commit identity  — 2 commit(s)
  21 passed · 0 failed · 0 skipped
GATE GREEN — all 21 checks passed
```

The earlier bare `pytest` on the working tree of `5970568f` read `4104 passed, 4 skipped in 468.56s`.


## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`

**Challenger (ticket-blind, round 1, on `5970568f`, 76,233 tokens): 11 met · 0 not met · 3 can't
tell.** It ran 36 targeted tests read-only in place. The three it could not judge:

- S1c. `publish()` never read the stamp. Fixed in `b38cdd5a`: it now refuses an unstamped shadow,
  with a test.
- S2's measurement and AC5's numbers. These live in this working doc, which it may not read, so
  the repo itself carries no evidence for them. `design/indexing.md` now carries the measured
  cost.

Its findings, and what happened to each:

1. A 5 s `busy_timeout` could lose a finished build to a stray writer. **Fixed:** 60 s on the
   publish connection (`PUBLISH_BUSY_TIMEOUT_MS`).
2. The window between the carry and the backup can overwrite a bump or a repair. **Accepted and
   documented** (H1).
3. The schema-older path never reported the `publish` phase. **Fixed.** Its `removed` stays 0 —
   an outgrown index cannot be read, as before.
4. No reader crossed the real swap. **Fixed:** `test_a_reader_thread_never_misses_across_the_swap`
   runs three real rebuilds. A kill during the backup itself stays untested; it rests on SQLite's
   transaction atomicity.
5. The AGENTS.md test count is not updated. **Left:** that line is a dated measurement ("after
   351"), and re-measuring the Docker count is outside this ticket.
6. Scope: nothing beyond the ticket.

The fixes stay inside the approved files, so the round-1 verify ran in the main loop with no
re-dispatch: 64 tests passed, then the gate below on `b38cdd5a`.

`Ph3/4 proven by`: G1, C1–C3, R1–R5, AC1–AC4 — 13/13; AC5 manual-recorded, with the anchor run and
the Windows arm excluded (A3, A4).

Verdict: **clean (challenger only — REVIEWER: OFF)**.

Reviewed at b38cdd5a — the diff `main..b38cdd5a`. Working doc:
`docs/tasks/356_rebuild-behind-a-shadow-index.md` (embedded).

## Phase 5 — finalise

Stale-review guard: after `b38cdd5a` only bookkeeping changed, and all of it is exempt — this doc,
`docs/BACKLOG.md` (the row closed), `docs/TOKEN_LEDGER.md` and `docs/LESSONS.md`.

`CLAIMS: 1 claim(s) from 1 lesson entr(ies) | T1=0 T2=1 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: none | mango files written: 0`

`356-C1` is type 2 (code), handle `child-build-inherits-adapter-env`: a child build inherits the
host's `CA_<LANG>_CMD`. It is recorded in `docs/LESSONS.md` as a first sighting.

### Outward actions

1. Push `feat/356-rebuild-behind-a-shadow-index` — pre-authorised.
2. Open the PR — pre-authorised.

Deferred to the maintainer:
- the merge;
- ratifying ASSUMED A1–A4;
- the anchor-size run (A3);
- a Windows run (A4).

### Cost ledger

| # | Phase | Dispatch | Tokens |
|---|---|---|---|
| 1 | refine | exposure-checker (`challenger`) | 37,046 |
| 2 | review | `challenger`, round 1 | 76,233 |
| — | main loop | — | unmeasured |

`LEDGER TOTAL: 113,279 · top cost driver: review/challenger`

**Revert path.** `git revert` the branch commits. A published index is an ordinary `graph.db`, and
a leftover `graph.db.shadow` is inert to the old code.
