---
id: 410
slug: column-readers
title: "`READS` onto a `Table::Column` — who reads this column (reopens 390 W3)"
phase: 2
milestone: Coverage
status: todo
depends_on: [390, 329]
---

## Why this exists

Issue [#102](https://github.com/cuongdinhngo/code-atlas/issues/102), 2026-10-24. 390 W3 shipped as
*ASSUMED (awaiting ratification): a `SELECT`'s source is a table; a column subject's readers are not
modelled.* Four anchor PRs in 20–23 Oct asked the column question (`InjuryInformation.HasLocation`,
a search's `gender`, `GBE_RULES`), each a data-fix migration whose risk was *which screens and
reports change*. Today `find_references(<Table::Column>, kinds=["READS"])` lands in `kinds_ignored`
(`find_references._kinds_ignored`). **W3 is reopened by this field evidence.**

## Scope

1. T-SQL routines and views: `READS` onto a `Column` when it appears in the select list, `WHERE`,
   `JOIN … ON` or `CASE` of a `SELECT` whose `FROM`/`JOIN` source is its table, alias-resolved —
   `RESOLVED`.
2. Host strings 390 already reads as `SELECT … FROM t` (PHP/TS/Python): an identifier matching a
   column of `t`, or `alias.col` — `HEURISTIC`. Language spec only (R2).
3. `find_references(<Table::Column>, kinds=["READS"])` lists them; `READS` on the table unions the
   column reads, as `WRITES` does (329).
4. `select *` counts as a table read only and says so (`column_reads_unknown`) — the column answer
   never claims completeness it lacks.

Contract: new edges onto an existing kind; decide in design whether that is a `contract_version`
bump (R3). Out of scope: runtime-built SQL; PHP views reading `$row['col']` (a model→view trace).

## Acceptance criteria

- AC1: A view selecting `t.flag` and a proc filtering `WHERE flag = 1` both appear as `RESOLVED`
  readers of `t::flag`; a proc reading only `t.other` does not.
- AC2: A PHP string `SELECT flag FROM t` is a `HEURISTIC` reader of `t::flag`.
- AC3: A `select *` reader is counted in `column_reads_unknown`, not listed as a column reader.
- AC4: Table-level `READS` answers are unchanged except for the union; P8 counts re-floored.
