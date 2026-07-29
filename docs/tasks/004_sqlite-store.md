---
id: 004
slug: sqlite-store
title: SQLite store & schema
phase: 1
milestone: Core
status: todo
depends_on: [001, 002]
---

## Goal
Persist and query the graph (§10). Single-writer, WAL, indexed.

## Scope / Deliverables
- `store.py` `GraphStore`: create schema (`files`, `nodes`, `edges`, `nodes_fts` fts5, `meta`), WAL mode.
- Upsert file + replace-per-file nodes/edges; meta get/set (`schema_version`, `contract_version`, `last_commit`, `built_at`).
- Query helpers used by tools (by name/kind/file, edges by source/target).
- Only component that touches SQLite (SRP): adapters never import it.

## Acceptance criteria
- Schema matches §10; re-indexing a file replaces its rows idempotently.
- FTS search returns expected rows; identical input → identical rows (determinism test).

## References
Plan §10, §2 (SRP boundary).
