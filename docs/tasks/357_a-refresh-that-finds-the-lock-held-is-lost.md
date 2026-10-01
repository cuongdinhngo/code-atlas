---
id: 357
slug: a-refresh-that-finds-the-lock-held-is-lost
title: 'A refresh that finds the write lock held is dropped, so the index can stop short of HEAD'
phase: 2
milestone: Freshness
status: todo
depends_on: [053, 355, 360]
---

## Why this exists

`code-atlas-refresh` skips cleanly when another writer holds `write.lock` (053, R4.3). The skip is
right for the writer, but the request is lost: nothing re-runs once the holder is done. An
incremental costs about a minute on a large index (052), so a second request inside that window is
common:

- `git rebase` of N commits: `post-commit` fires per pick and `post-rewrite rebase` once at the end
  (355's spike). The first pick's refresh holds the lock; the rest, the final one included, skip.
  The index stops at a pick's HEAD.
- Two commits a minute apart, or a `git pull` (`post-merge`) right after a commit.

Once 360 lands, answers stay honest: the state line says `behind`, and 035's read-through repairs
the files a query touches. Even then, the index the hooks were installed to keep current is not
current until the next refresh. `contrib/git/README.md` documents the gap (355).

**Land 360 first.** Today the build stamps the HEAD it reads at the end, so a dropped refresh can
leave the index falsely `current` (360). The re-run in Scope 1 would then diff an empty
`last_commit..HEAD` and parse nothing, and AC1 would pass on `last_commit` alone.

## Scope

1. A refresh that finds the lock held leaves a "pending" marker beside the lock instead of only
   skipping. The holder, before it releases the lock, re-runs an incremental while a marker is
   pending — so the last request always lands, with no waiting and no extra process.
2. Applies to every writer that shares the lock (`code-atlas-refresh` and `build_or_update_index`),
   not only the git hooks — it is the lock's contract, not a hook's.
3. A full rebuild in progress is not repeated: a marker left during one is served by one
   incremental after it publishes.
4. **No lost wake-up.** A marker written after the holder's last check but before its unlock must
   still land. So the holder releases, re-checks the marker, and if it is set tries the lock again,
   looping until the marker is clear. Checking only before release leaves a window AC1 can fail in.
5. The marker is a stateless "dirty" flag (one overwritable file, no PID, no owner). Nothing has to
   be reclaimed when a holder dies: the next writer reads it, clears it and runs (AC3, 177).

## Acceptance criteria

- **AC1 (proving test):** a real `git rebase` of two picks with the hooks installed and a real
  index ends with the index's `last_commit` equal to HEAD, and with its file and symbol counts
  equal to a fresh full build at HEAD. `last_commit` alone cannot prove it, because before 360 it
  equals HEAD by construction.
- **AC2:** two refreshes requested while one runs cost exactly one extra incremental, not two.
- **AC3:** a holder killed with a marker pending leaves no claim that outlives it (177): the next
  writer starts clean and the marker is consumed or ignored, never a permanent "pending".
- **AC4:** `contrib/git/README.md`'s rebase row no longer carries the gap.
- **AC5:** a unit test drives two writers deterministically through the window between the
  holder's last check and its unlock, and the late request still runs. AC1's real rebase is slow
  and timing-dependent, so it cannot be the only proof of Scope 4.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 357 · **work_doc_mode:** embed · **Current phase:** 3 execute · **Next action:** review. **Revert path:** `git revert` the branch's commits.
- `TRACK: backend` · `TIER: full` · `SCOPE: M` · `STRUCTURE: native` · Run mode: `autorun`, batch 360 → 357 → 358 → 359;
  *"with skipped reviewer"* = `--no-reviewer` only, the challenger keeps its seat.
- Branch `fix/357-a-refresh-that-finds-the-lock-held-is-lost`, stacked on `fix/360-build-stamps-head-read-at-the-end`
  (`d555d158`, PR #27); its PR targets that branch. Contract `.mango/run-contract-357.txt`.
  RECONCILE t0: 5 declared | 3 re-run | 0 holding | 3 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 7 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 13 unresolved surfaced | 0 want-decision asked | 13 how-decision resolved+cited | 0 ASSUMED | skip: no`

**Premise.** All seven resolve: `code-atlas-refresh` (`code_atlas/hooks/refresh.py:50`),
`build_or_update_index` (`code_atlas/tools/build_or_update_index.py`), `write.lock`
(`index_lock.py:27`, `try_index_write_lock`), `contrib/git/README.md`'s rebase row, the
`post-commit` / `post-rewrite` hooks (355), and 360's stamp (PR #27, the base of this branch).

**Recall (by handle — a new lock contract other modules call).** `343-C2`
`formatter-rewrites-untouched-lines`; `356-C1` `child-build-inherits-adapter-env`.

**Exposure-checker** (ticket-blind `challenger`, 1 dispatch, 46,332 tokens) surfaced X1–X6; H1–H7 are
the run's own. Its seventh item (a re-run count in the payload) it marked settled by H4.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | the marker | how | one overwritable file `write.pending` beside `write.lock`, one path helper (Scope 1, 5; R6.7) |
| H2 | where the protocol lives | how | the build tool's lock section: `code-atlas-refresh` (`hooks/refresh.py:50`) and `code-atlas-build` (`cli.py:101`) both call `create(config)` (Scope 2) |
| H3 | the re-run's flags | how | the holder's own call with `full=False`; the marker carries none (Scope 3, 5) |
| H4 | the payload a re-running holder returns | how | its first build's — the caller asked for that one; no re-run count (R7.1) |
| H5 | a request that lands after the holder's post-unlock look | how | the requester writes the marker, then tries the lock once more; if that wins, it runs its own call (Scope 4: "the last request always lands") |
| H6 | when the holder clears the marker | how | on taking the lock — its build reads the tree after that, so it covers every earlier request; after unlock it loops while the marker is set (Scope 4) |
| H7 | a holder whose build raises | how | the exception propagates; a marker written during the build stays for the next writer (Scope 5, AC3) |
| X1 | does a marking requester still answer `busy` | how | yes — `busy` carries staleness and `performed: false` (072); the payload shape is pinned by `tests/test_busy_build_staleness.py` |
| X2 | a `full=True` requester that finds the lock held | how | it leaves the same marker; a marker only ever asks for an incremental (Scope 3) |
| X3 | a refused re-run | how | the loop is driven by the marker, which each pass clears, so it ends unless a new request lands — no spin |
| X4 | `repair_incomplete=False` from a hook holder | how | carried with the other flags (H3), so a hook never escalates to a repair (`refresh.py:47-49`) |
| X5 | requests a refused holder dropped | how | the next writer reads current HEAD and serves them (H6/H7) |
| X6 | Windows | how | the marker is a plain create/unlink, no lock, so no platform branch (R1.1; `index_lock.py:39-80`) |

## Phase 1 — analysis

`PREMISE: 7 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`SECTIONS: 4 found (title, Why this exists, Scope, Acceptance criteria) | 4 decomposed | ROWS: C=2 R=5 G=1 AC=5`
`CLARIFICATION: 13 raised | 13 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/9 touched files under UI paths`
`BASELINE: green`
`SCOPE: M`
`TIER: full`

### BASELINE

The base is `d555d158`, the tip of PR #27, whose `scripts/gate.sh` ran GATE GREEN (21/21) on
`c1b8cd23`; `d555d158` changes only docs. Ran at c1b8cd23.

### Requirements matrix

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | title / Why | "the index can stop short of HEAD" | the last request to a busy lock lands | ✅ |
| C1 | Why | "Land 360 first" | stacked on PR #27 | ✅ |
| C2 | Scope 5 | stateless dirty flag | no PID, no owner, nothing to reclaim | ✅ |
| R1 | Scope 1 | a refused refresh leaves a marker; the holder re-runs while it is set | `mark_pending` + the post-unlock loop | ✅ |
| R2 | Scope 2 | every writer sharing the lock | the protocol lives in `create(config)` | ✅ |
| R3 | Scope 3 | a full rebuild is not repeated | the re-run is `full=False` | ✅ |
| R4 | Scope 4 | no lost wake-up | the holder looks after the unlock; the requester retries after marking (H5) | ✅ |
| R5 | Scope 5 | next writer reads, clears and runs | `take_pending` on acquire | ✅ |
| AC1 | AC | real rebase of two picks → `last_commit == HEAD`, counts == fresh full build | integration test | ✅ |
| AC2 | AC | two requests during a run → exactly one extra incremental | unit | ✅ |
| AC3 | AC | killed holder + marker → next writer starts clean, marker consumed | unit | ✅ |
| AC4 | AC | README rebase row loses the gap | doc | ✅ |
| AC5 | AC | deterministic two-writer test through the window | unit, both orderings | ✅ |

### AC validation

| AC | Falsifiable? | Note |
|---|---|---|
| AC1 | yes — `last_commit == HEAD` and `(files, nodes, edges)` equal a fresh `full_build` at HEAD | a slow-starting adapter (2 s) and `rebase -x "sleep 0.7"` make the overlap deterministic |
| AC2 | yes — the stand-in `_build` is called exactly twice | |
| AC3 | yes — a planted marker with no holder: one build, then no marker | a real kill leaves exactly that state: the OS drops the lock, the file stays |
| AC4 | yes — grep: the row no longer says "can stop at a pick's HEAD" | |
| AC5 | yes — ordering 1 (request inside the holder's build, before its unlock) and ordering 2 (request after the holder's post-unlock look) both end with two builds | |

### Gap analysis (enhancement)

- **Now.** `try_index_write_lock` yields `False` and the tool returns `busy`
  (`build_or_update_index.py:108-110`); nothing records the request.
- **Target.** The refused request is a marker; the holder serves it after its unlock; a requester
  that lands after that look serves itself.

### Blast radius

- `create(config)` callers: the MCP tool, `cli.build` (`cli.py:101`), `hooks.refresh` (`refresh.py:50`).
- Tests that pin "exactly one build": `tests/test_busy_build_staleness.py::test_two_concurrent_builds_run_exactly_one_and_the_loser_carries_staleness` (`runs == 1` → 2).
- Tests holding the lock externally (`busy_while_locked`, `test_git_refresh_hook`) leave a marker in
  their tmp dirs; nothing reads it after.
- Docs: `contrib/git/README.md` (AC4 and the lock row), `docs/runbooks/parallel-agents.md` (the busy
  section), `docs/design/indexing.md` (exit `4`), `docs/PLAN.md` (the tool row), `index_lock`'s docstring.

### Rule sections

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §R1.1 (change-type) ✅ the marker is a plain file on every OS: no platform or language branch, §R1.4 (change-type) ✅ the marker helpers live in index_lock.py beside the lock and the tool only calls them, §R4.3 (change-type) ✅ still one writer: a re-run happens only under the lock, §R5.3 (change-type) ✅ a marker write that fails is best-effort, like publish_build_progress; the lock still refuses, §R6.5 (change-type) ✅ AC1 is red 3/3 on d555d158's code and AC5's window tests need the change, §R6.7 (change-type) ✅ one pending_path_for, §R7.5 (change-type) ✅ every new comment ≤ 3 lines`

## Phase 2 — design

### Approach

1. **`index_lock`**: `PENDING_NAME`, `pending_path_for`, `mark_pending` (touch, best-effort),
   `take_pending` (unlink, True when set), `is_pending`.
2. **`build_or_update_index`**: the locked section loops. Holding the lock: `take_pending`, then one
   build (`_locked_build`, which keeps the adapter-refusal payload), `full` only on the first pass.
   After the unlock: marker set → loop. Not holding: answer `first` if this call already built
   (a new holder now owns the marker); else write the marker and try once more; a second miss
   answers `busy`.
3. **Docs**: README rows (AC4 and the lock row), runbook busy section, exit `4`, PLAN tool row,
   `index_lock` docstring.

### Rejected alternatives

- **Check the marker before unlocking.** The window Scope 4 names: a request after that look and
  before the unlock is lost.
- **A blocking wait in the requester.** A hook must return at once (README: "Why background?").
- **A counter or a queue file.** Two requests cost two re-runs (AC2) and need an owner to reclaim.

### Assumptions

| # | Assumption | Tag |
|---|---|---|
| S1 | `post-commit` fires per rebase pick | verified — 355's spike and AC1 |
| S2 | a killed holder leaves the marker file and no lock | verified — `flock` dies with the process (177); the marker is a plain file |

### Smallest change list

| # | Change | File | Blast radius | Ph2 covered by | k/N |
|---|---|---|---|---|---|
| 1 | marker helpers | `code_atlas/index_lock.py` | build tool only | R1, R5, C2 | 1/1 |
| 2 | the locked loop + `_locked_build` | `code_atlas/tools/build_or_update_index.py` | MCP tool, `code-atlas-build`, `code-atlas-refresh` | R1–R4, G1 | 1/1 |
| 3 | proving tests | `tests/test_a_refused_refresh_is_served.py` (new) | — | AC1–AC3, AC5 | 1/1 |
| 4 | the one-build pin | `tests/test_busy_build_staleness.py` | — | R4 | 1/1 |
| 5 | docs | `contrib/git/README.md`, `docs/runbooks/parallel-agents.md`, `docs/design/indexing.md`, `docs/PLAN.md` | doc budgets | AC4 | 4/4 |
| 6 | bookkeeping | this file, `docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md` | `tests/test_backlog_bookkeeping.py` | — | 4/4 |

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- **`formatter-rewrites-untouched-lines`** — traced: `ruff format --diff` on `build_or_update_index.py`
  proposes two hunks (lines ~268, ~292), both outside this change; not applied. The new test file is
  wholly this change's and was formatted.
- **`child-build-inherits-adapter-env`** — traced: AC1's hook environment drops every inherited `CA_*`
  variable before adding the fake adapter (`_hook_env`).

### Verification plan

| AC | risk layer | proof artifact | fixture provenance | layer-match? |
|---|---|---|---|---|
| AC1 | integration | real `git rebase` with the four contrib hooks installed, a real index and real `code-atlas-refresh` processes | n/a | ✅ |
| AC2 | logic | two `busy` calls while a stand-in build is held; build count | n/a | ✅ |
| AC3 | logic | a planted marker with no holder; build count and marker absent | n/a | ✅ |
| AC4 | doc | the README row | n/a | ✅ |
| AC5 | logic | two writers in threads, both orderings, the second paused on `mark_pending` | n/a | ✅ |

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

### Proving test

`.venv/bin/python -m pytest -q tests/test_a_refused_refresh_is_served.py`. AC1 fails on the 360 tree
(the index stops at a pick's HEAD) and passes after the change.

### Rollback

`git revert` the branch commits. A leftover `write.pending` is inert to the old code.

## Phase 3 — execute

Commit on `fix/357-a-refresh-that-finds-the-lock-held-is-lost`: `208c66f1` (rebased onto `d555d158`).

**Proving test, red first.** AC1 alone, copied onto a worktree of the 360 tree (the marker helpers
stubbed so the file imports): 3 runs, 3 failed (`assert stamped_at_head()`, 64 s each — the poll
timed out at a pick's HEAD). After the change: 3 runs of the whole file, 6 passed each (~7 s).

**Sweep.**
- Axis 1 — file set: the change list exactly; the `index_lock` docstring sits in item 1's file.
- Axis 2 — design conformance: Approach bullets 1–3 implemented as approved. `ruff check`,
  `mypy code_atlas` clean.
- Lock-path suites (12 files: busy, cli, payload, progress, refresh hook, state hook, status, Windows
  lock, silent refresh, shadow rebuild, killed build): 98 passed, 3 skipped (the Windows arm).
