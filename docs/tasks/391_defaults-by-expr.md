---
id: 391
slug: defaults-by-expr
title: 'check_column_defaults takes one table, so "every column that defaults to user_name(), and its writers" is a Grep over the schema'
phase: 2
milestone: Coverage
status: todo
depends_on: [320]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17). F1 (1 PR, from a
ticket family of five): audit columns declared `DEFAULT (user_name())` record the SQL login
instead of the app user, unless a writer sets them. Each fix starts with the same question: which
tables carry that default, and which of their writers leave it to the default. The tables came from
`git grep` over the schema baseline, and then the tool ran once per table.

TOOLS.md §"one table" rejects a *list of tables* (N independent scans, with no shared
arithmetic). This is a different subject: a default expression, which the index already stores per
column.

## Scope

1. `check_column_defaults(default_expr=…)` as an alternative subject to `table`: the columns whose
   stored `DEFAULT` matches the expression (normalised for case, brackets and whitespace), each
   with the omitter / total count that today's answer gives.
2. Page it like the other tools. Unmeasured writers stay unmeasured.

## Acceptance criteria

- **AC1:** Two fixture tables with `DEFAULT (user_name())` and one with `DEFAULT (getdate())`:
  `default_expr="user_name()"` lists the first two, with their omitters.
- **AC2:** `[USER_NAME]()` and `user_name ( )` match the same columns.
- **AC3:** A `table=` call is byte-identical.

- **AC-field:** the F-cases' query shapes, replayed on the anchor index after the build, answer
  without a Grep fallback; record the before/after counts in the working doc.
