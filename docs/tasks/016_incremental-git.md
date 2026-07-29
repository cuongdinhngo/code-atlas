---
id: 016
slug: incremental-git
title: Incremental update via git diff (M5)
phase: 1
milestone: M5
status: todo
depends_on: [011, 009]
---

## Goal
Keep the index fresh cheaply (§8.3).

## Scope / Deliverables
- `gitutil.py`: `git diff <last_commit>..HEAD` → changed files.
- `indexer.incremental_update`: add single-hop dependents; reparse `changed ∪ dependents` (hash-skip unchanged); re-run resolver scoped to affected qnames; bump `meta.last_commit`.
- Staleness reported in `get_index_status`.

## Acceptance criteria
- Editing one file updates only affected rows; result equals a full rebuild for that state.
- Status shows staleness (commits behind) accurately.

## References
Plan §8.3, §15 (M5).
