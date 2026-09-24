---
id: 329
slug: a-table-writer-list-repeats-each-statement-per-column
title: "find_references on a Table unions its columns' WRITES, so one INSERT naming eight columns is eight rows — six statements filled a 50-row page and read as duplicates"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [278]
---

## Why this exists (field retro, 2026-09-24 — FIELD-1426)

`find_references` on a hot table returned **866 `WRITES`, capped at 50**. Page 1 was *"the same six
`INSERT` lines … repeated ~8 times"*; `path_prefix` narrowed it to 368 rows, page 1 still "all
duplicates". The session rated the tool 3/10 for the question and asked for dedupe.

**They are not duplicates.** Since 278 a Table subject unions the writers of the table with the
writers of each `CONTAINS` column (`find_references.py:236-240,368`), and the SQL adapter emits one
`WRITES` per named column onto `T::col` (`scan.js:590-595`). An INSERT naming eight columns is eight
correct rows at one `(file, line)`. The answer is right; its unit is wrong for the question a Table
subject asks — *which statements write this table* — and it buries the statement list.

## Goal

A Table subject answers one row per writing statement, with the columns it names folded into that
row; a Column subject is unchanged.

## Scope / Deliverables

1. **Group Table-subject rows by `(source, file, line)`**, carrying the named columns as a list
   on the row. Counts (`total_count`, test/production census) count statements.
2. **Paging walks statements**, so page 1 of a 50-cap is 50 statements.
3. **Column subjects and the writer set `check_column_defaults` reads are untouched** (278 shares
   the set; only this tool's rendering changes).

## Constraints

- **061** — Column subjects and non-Table subjects are byte-identical.
- **R4.2** — deterministic column order within a row.
- **R1.4** — grouping is a `GraphStore` query, not a Python pass over an unbounded fetch.

## Acceptance criteria

- **AC1** Fixture: two INSERTs naming 3 and 2 columns + one column-less write → 3 rows, not 6.
- **AC2** `total_count` is 3; a `limit=2` page returns 2 statements and `truncated: true`.
- **AC3** `find_references T::col` is byte-identical to today.

## References
`code_atlas/tools/find_references.py:88,155,236-240,368`; `adapters/sql/src/scan.js:573-595`;
ticket 278.
