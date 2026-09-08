# 233 — SQL cross-repo floors (137-shaped before table)

**Status:** run, pinned public SQL samples via `sparse_paths`, 2026-09-08 (Linux host `dev-host`).
**Ticket:** [`../tasks/233_python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything.md`](../tasks/233_python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything.md).
**Depends on:** 228 dialect honesty (merged) — floors measured after refuse-reserved / `File.extra.dialect=tsql`.
**Protocol:** `python scripts/cross_repo_validate.py --public-only` (or the smoke driver over the two SQL ids).

## The pins

| sample | shape | SHA | files | nodes | edges | failed | floor (≈80%) |
|---|---|---|---|---|---|---|---|
| `adventureworks_oltp` | T-SQL OLTP install script (`instawdb.sql`) | `fd84be9` | 1 | 590 | 1 301 | 0 | 1 / 472 / 1 040 |
| `wwi_dw` | Wide World Importers DW SSDT tables | `fd84be9` | 73 | 549 | 1 254 | 0 | 58 / 439 / 1 003 |

Both come from `microsoft/sql-server-samples` with `sparse_paths` so the pin is public and reproducible without cloning the multi-GB tree. Materialization is a nested git commit of the archived paths — required because a bare directory under this worktree still answers `git ls-files` for the parent and collects zero paths.

## What this unlocks

Later SQL tickets (224 REFERENCES, field parity) can state a before/after on these floors the same way 137 did for PHP. Edge-health cause tables are PHP/TS-oriented; SQL samples are asserted by cross-repo floors + layer_report shape rows, not by CALLS HEURISTIC share.

