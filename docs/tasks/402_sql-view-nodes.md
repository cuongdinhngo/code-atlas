---
id: 402
slug: sql-view-nodes
title: "A T-SQL view is not in the graph, so its definition, its predicate and its redefinitions answer nothing"
phase: 2
milestone: Coverage
status: todo
depends_on: [390]
---

## Why this exists

From the anchor project's Round-3 feedback (2026-09-20 → 10-18). Four PRs asked a view question, and each was
answered from the live DB or `git grep`: what filters this view, which migrations redefine it, what a view reads.
On `main` the SQL adapter emits no node for `CREATE VIEW` (no `view` in `adapters/sql/src`), so `search_symbol`,
`read_symbol` and `find_references` have nothing to answer with. `search_symbol`'s `altered_by` covers only
`Table` and `Function` (`search_symbol.py:70`).

## Scope

1. The SQL adapter emits `CREATE` / `ALTER` / `CREATE OR ALTER VIEW` as a node, following T-SQL's grammar
   (R2.1). The kind is chosen in design: a new kind bumps `contract_version` (R3).
2. A view's `SELECT … FROM` sources are `READS` edges, as a routine's are (390).
3. `altered_by` covers views.

## Acceptance criteria

- **AC1:** a fixture view is found by `search_symbol` and read by `read_symbol`.
- **AC2:** `find_references(<table>, kinds=["READS"])` lists the view.
- **AC3:** two migrations that redefine one view both appear in its `altered_by`.
