---
id: 420
slug: index-artifact-trust
title: "The index directory is trusted only if code-atlas wrote it — a committed or linked artifact is refused, and every write refuses a link"
phase: 2
milestone: Trust
status: done
depends_on: [419]
---

## Why this exists

Internal security audit, 2026-10-27; advisory GHSA-66g7-7jr3-j5rc (private until 0.9.1).
`SECURITY.md` treats the indexed repo as untrusted, but the index directory (`.code-atlas/`, or the
parent of a repo-relative `db_path`) is read and written as if code-atlas had made it. A repository
can commit that directory, so:

- **Writes follow links.** A committed `.code-atlas/write.lock` that links to a file outside the
  repo is opened `a+` and its first bytes rewritten on every progress tick; the refusal record,
  the adapter-skew record, the nudge state and log, and the LLM cache are written the same way.
- **`db_path` is checked as a string only.** `config.py` refuses absolute and `..` paths but never
  resolves links, so `db_path = "cache/graph.db"` with a committed `cache → /elsewhere` aims SQLite
  outside the repo. Only a linked `.code-atlas/` itself is a known limitation today.
- **A database from the repo is opened with default trust:** its views and triggers run with
  `trusted_schema` on.

## Acceptance

1. **A tracked index is refused (D4, R5.3).** When `git ls-files` lists anything under the index
   directory or the database path, every entry point (build, server start, `get_index_status`, each
   hook) refuses with one fix line: untrack it (`git rm -r --cached <dir>`) and ignore it. The hooks
   inject no context in that state.
2. **One writer.** A `safe_write` helper (create with `O_NOFOLLOW`, parent checked by
   `resolves_inside`, temp file plus `os.replace` in the same contained directory, mode `0600`)
   carries every write under the index directory: `index_lock.py` (the lock, its progress rewrite,
   the refusal record), `adapter_skew.py`, `hooks/nudge.py` (state and log), the adapter stderr log
   if it lives there (`adapter.py`, verify), and `onboarding_llm/cache.py`. The lock keeps its
   locking semantics; only the open changes.
3. **`db_path` contained.** The database file and its parent are resolved and must stay inside the
   repo; a linked database, `-wal`, `-shm` or shadow file is refused.
4. **A database is opened defensively:** `PRAGMA trusted_schema=OFF` and
   `SQLITE_DBCONFIG_DEFENSIVE` on every `sqlite3.connect` in `store.py` (read-only opens included).
5. **Permissions:** the index directory is created `0700`, its files `0600`.
6. **Proving tests**, each seen failing on the pre-fix tree (R6.5):
   - `write.lock`, `nudge.log` and the refusal temp file linked to a victim outside the repo: a
     build and each hook leave the victim byte-identical;
   - a committed `.code-atlas/`: refused with the fix line, no context injected;
   - `db_path` under a linked directory: refused;
   - a database carrying a view and trigger that write a sentinel: the sentinel never changes.
7. **Guard test:** no `open(…)` in a write mode, `write_text`, `write_bytes` or `os.replace` on a
   path under the index directory outside `safe_write` (AST walk, like 419's spawn guard).

Out of scope: text from the index reaching logs and instructions (421); the plugin's hook activation
condition and other public hardening (Track B). `generate_onboarding` already writes through
`require_writable` and stays as it is.

## Call sites

Writers: `index_lock.py` (lock open `a+`, progress `r+`, staged record), `adapter_skew.py`
(refusal record), `hooks/nudge.py` (state temp + replace, log append), `adapter.py` (stderr log,
check its path), `onboarding_llm/cache.py` (temp + replace).
Database: `store.py` (`connect` at the read-only meta read, the writer, the shadow build and the
publish), `config.py` (`db_path` resolution and `_is_repo_relative`).

## Resolution

- `index_trust.check_index` runs inside `load_config`, which every entry point calls, and again on
  each `get_index_status` call. It refuses (`IndexTrustError`, a `ConfigError`) when `gitutil.tracked`
  lists anything under the index directory or the database family, or when the directory, the
  database, a `-wal`/`-shm` or the shadow is a link or resolves outside the repo. The server prints
  the fix and exits 2; each hook prints its existing skip line on stderr and nothing on stdout.
- The index directory is `db_path.parent`; when that is the repo root, only the database family
  counts. An absolute `CA_DB_PATH` outside the repo is the operator's and is not checked. git is
  asked only when part of the index exists on disk.
- `containment.safe_open` is the one open: `O_NOFOLLOW` (a link check on Windows), its directory not
  a link and inside the root, mode `0600`. `safe_write` stages a random temp file and `os.replace`s
  it; `safe_append` serves `nudge.log`. Deviation from AC2: the lock and the log keep their
  in-place open (locking, appending), so only the no-follow open applies to them, not the replace.
- `store._connect` sets `trusted_schema=OFF` and `SQLITE_DBCONFIG_DEFENSIVE` on all six connects;
  `GraphStore` and the shadow create their file `0600` first, and SQLite gives the WAL files that
  mode. `trusted_schema` stops a view or trigger from calling a function, not plain DML, so the
  proving database calls a function registered on code-atlas's connections.
- `adapter.py`'s stderr log: no core caller passes `stderr_path` (tests only), so it never lives
  under the index directory; the AC7 guard exempts it with that reason, beside `query.py --out`
  and `generate_onboarding` (`require_writable`, out of scope).
- Review: `GraphStore` refuses a database that is a link even past `load_config`; the git answer
  is kept per `.git/index` stamp, so `get_index_status` spawns git only after a commit or pull.
  Not done: where git cannot answer (the runtime image's ownership refusal) a tracked index is not
  refused; the onboarding cache keeps default modes. Both are in BACKLOG.
- Deviation from AC4: SQLite 3.40 (the runtime image's) refuses the index's own fts5 triggers
  under `trusted_schema=OFF`, so `store.schema_distrust_supported` probes once and leaves it on
  there; defensive mode always applies, and the sentinel tests skip on such a build.
- Tests: `tests/conftest.py` adds `.code-atlas/` to git's excludes for the session, since fixtures
  `git add -A` a built repo; two module-count pins move to 106.
- A committed LLM cache at the default `.code-atlas/` path is now refused; its env knob moves it.
- Proving: `tests/test_index_artifact_trust.py` — 21 red on b87572ac (the later store-link and
  shadow-wal arms red on e5b6d2fb), each for its own reason,
  green after; the AC7 AST guard is in the same file.
