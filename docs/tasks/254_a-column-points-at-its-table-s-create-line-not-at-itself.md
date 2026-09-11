---
id: 254
slug: a-column-points-at-its-table-s-create-line-not-at-itself
title: 'Every column of a CREATE TABLE is emitted at the CREATE statement''s own line, so a Column node cannot point at its own definition'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [247, 248]
---

## Why this exists

Split out of [247](247_the-column-reader-keeps-type-and-default-and-discards-nullability-identity-and-primary-key.md),
which carried this as a fourth scope item on the premise that declaration order was unrecoverable
and the line was the only fallback. Half of that premise is now false: 248 reads the DDL order off
the `CONTAINS` edge ids, proven end to end against a real indexed `CREATE TABLE`, so the declaration
*ordinal* has no remaining caller. The *line* is still wrong, and that is this ticket.

Measured on the anchor index (read-only):

```
tables whose columns ALL share one line_start:  1348 / 1548
  dbo.ContractAssets   585 cols, 1 distinct line (13)
  dbo.AwardStructure     173 cols, 1 distinct line (13)
  dbo.Member_Site       316 cols, 8 distinct lines    <- multi-statement ALTER, not per-column
```

A `Column` node's position is its table's position, so `read_symbol` on a column returns the
`CREATE` header and `file_outline` puts 585 columns on one line. The position is not wrong in a way
that lies — it is the table's real line — it is simply not the column's.

## Root cause

`scan.js` walks a table body with `for (const col of ddl.readColumns(body.body)) column(qname, col, line)`
and passes **one** `line`, the `CREATE` statement's, for every column. It has nothing better to
pass: `readColumns` calls `splitTopLevel(body, ",")`, which builds each piece by accumulating
characters and then `trim()`s and filters the result, so the offset of a column definition inside
the body is discarded before the caller ever sees it.

## Scope

1. Carry the byte offset of each top-level piece out of the body split, without changing what the
   existing callers of `splitTopLevel` receive.
2. Emit each `Column` at the line its own definition starts on, counted from the body's own start so
   a `(` on the `CREATE` line still lands the first column correctly.
3. `line_end` stays equal to `line_start` unless a definition genuinely spans lines.

## Constraints

- **No `CONTRACT_VERSION` bump.** `line_start` is already a `NODE_FIELD`; this changes a value, not
  the vocabulary.
- **R4.2 — deterministic.** Identical DDL gives identical lines.
- **`_NODE_ORDER` is `qualified_name, file_path, line_start, id`,** so a per-column line does not
  reorder anything: the qname already separates the rows. Column order still comes from 248's
  `CONTAINS` edge ids, and this ticket must not be read as a second answer to that question.
- A full rebuild is needed before existing indexes carry the new lines; say so in the PR.

## Acceptance criteria

- **AC1** Each column of a multi-line `CREATE TABLE` reports the line its own definition begins on.
- **AC2** A single-line `CREATE TABLE (a int, b int)` reports the `CREATE` line for both — the
  existing behaviour, and correct there.
- **AC3** A column declared by `ALTER TABLE … ADD` keeps that statement's line.
- **AC4** `read_symbol` on a column returns that column's definition, not the `CREATE` header.
- **AC5** Every existing `Column` assertion in `tests/contract/` and the SQL adapter suite still
  passes, except line numbers a test pins deliberately, which are re-pinned in the same commit.

## References

- `adapters/sql/src/scan.js` (table body loop, `ALTER` path); `adapters/sql/src/ddl.js`
  (`readColumns`, `splitTopLevel`).
- `code_atlas/store.py` (`_NODE_ORDER`) — why per-column lines change no ordering.
- 247 (the capture this was split from), 248 (why the ordinal half is closed).
