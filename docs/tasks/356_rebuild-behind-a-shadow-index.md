---
id: 356
slug: rebuild-behind-a-shadow-index
title: 'A full rebuild empties the live index first, so every read waits minutes or answers a false empty'
phase: 2
milestone: Adoption
status: todo
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
