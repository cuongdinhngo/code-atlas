---
id: 364
slug: php-table-name-string-writes-nothing
title: 'A PHP write that names its table as a string argument emits no WRITES, so find_references on a table lists SQL writers only'
phase: 2
milestone: Coverage
status: todo
depends_on: [352, 278, 328]
---

## Why this exists

This comes from field feedback on evaran-care/rac-anz.

- #2825: `find_references dbo.Beds` listed only the SQL writers (`authoritative: false`). The
  page's `HmDatabase::SQL_INSERT` on `'Beds'` and `BedAPIModel`'s `insert('Beds')` were found with
  Grep.
- #2906: the `WoundsTran` insert writers came back at `HEURISTIC` only and needed `git grep`.

278/281 read a PHP string that *begins* a T-SQL write. A wrapper call whose only argument naming
the table is the bare table name does not have that shape: `queryInsert('Beds', $row)`,
`queryUpdate`, `queryDelete`. And 352's string-argument rule emits only `NEW` or `CALLS`, never
`WRITES` or `DELETES`.

## Scope

1. A 352 string-argument rule can declare `WRITES` or `DELETES` as its edge kind. The target is a
   `Table` resolved by name, with the default schema applied the way the SQL adapter applies it.
2. Rule edges carry `rule: true` at `HEURISTIC`. A name that matches no table stays unlinked and is
   counted in `unlinked_writes_count`.

## Acceptance criteria

- **AC1:** With a rule `queryInsert arg 0 → WRITES`, `find_references dbo.Beds` lists the PHP call
  site beside the SQL writers.
- **AC2:** `check_column_defaults` keeps reading only writers that carry a column list. A rule edge
  without a column list is not reported as omitting every column.
- **AC3:** With no rule, the graph is unchanged.
