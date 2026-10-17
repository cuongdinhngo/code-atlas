---
id: 390
slug: table-readers
title: 'A table lists its writers but never its readers, and a trigger that writes a column is not among them'
phase: 2
milestone: Coverage
status: todo
depends_on: [278, 328, 364, 371]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17). The schema
questions that still went to Grep:

- F1 (1 PR): "who reads `dbo.X`" before a reference-data change. `find_references` returns
  `WRITES` and `DELETES` only, so the reader sweep over the PHP and SQL trees was Grep.
- F2 (1 PR): the writer of `Resident.InActive` was an `AFTER` trigger. Asking which SQL writes
  a column inside a trigger was not a one-call question.
- F3 (2 PRs): a column written by an `UPDATE` inside a PHP string, and a T-SQL function
  (`USER_NAME()`) compared inside PHP SQL strings. 371 reads a string that *begins* a write.
  These were mid-string fragments, or strings built across several concatenations.

## Scope

1. Measure first: on the anchor index, count the trigger bodies whose `INSERT`, `UPDATE` and
   `DELETE` statements emit `WRITES` today. Fix the trigger case here only if it is a gap in
   the SQL adapter. Otherwise record the cause.
2. A `READS` edge from a `SELECT … FROM` / `JOIN` table reference: in T-SQL bodies at
   `RESOLVED`, and in host strings at `HEURISTIC` (the same reader as 371). This is a contract
   change (a new edge kind), so it is decided in design against R1.2 and PLAN §19.
3. `find_references` on a Table takes `kinds` (default: today's writers). `READS` is opt-in, so
   today's answers stay byte-identical.

## Acceptance criteria

- **AC1:** An `AFTER UPDATE` trigger that sets `T.C` is listed by `find_references T::C`, labelled
  with the trigger as its writer.
- **AC2:** With `kinds=["READS"]`, a proc that selects from `T` and a PHP string
  `"SELECT … FROM dbo.T"` are both listed, with their tiers.
- **AC3:** Without `kinds`, `find_references` on a table is byte-identical.
