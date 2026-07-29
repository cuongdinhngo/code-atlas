---
id: 009
slug: full-build-indexer
title: Full build indexer + workers (M1)
phase: 1
milestone: M1
status: todo
depends_on: [004, 005, 007]
---

## Goal
Index a whole repo end-to-end into SQLite (§8.1).

## Scope / Deliverables
- `indexer.full_build`: collect files (`git ls-files` per adapter extensions, minus ignores; walk fallback); reconcile vanished paths.
- Fan paths across N adapter processes (`min(cpu-2, 8)`); hash bytes; upsert `files`, replace `nodes`+bare `edges`. Single SQLite writer.
- Store `meta.last_commit`, `contract_version`, `built_at`; build `nodes_fts`.

## Acceptance criteria
- Builds a small PHP repo to a queryable DB; re-run is idempotent.
- Single writer (no SQLite lock contention); worker count honors `CA_WORKERS`.

## References
Plan §8.1, §15 (M1).
