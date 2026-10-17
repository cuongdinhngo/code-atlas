---
id: 392
slug: bare-table-name
title: 'find_references refuses a bare table name that check_column_defaults resolves'
phase: 2
milestone: Retrieval
status: todo
depends_on: [320]
---

## Why this exists

This comes from the anchor project's second field retro (2026-10-10 → 10-17). F1 (1 PR):
`find_references RefType` (a bare table name) answered `name_not_qualified`, so the agent switched to
`git grep`. `check_column_defaults` already resolves a bare table name "to its one
schema-qualified table, or refuses with the candidates" (320). The same name in the same index
gets two different contracts, depending on the tool.

## Scope

1. `find_references` and `impact` resolve a bare name that matches exactly one `Table` or
   `Procedure`, and `find_callers` one `Procedure`, by the same rule as 320, and report `resolved_from: "bare"`.
2. More than one match: refuse with the candidates, as 320 does.

## Acceptance criteria

- **AC1:** A fixture with one `dbo.Items`: `find_references Items` answers as
  `find_references dbo.Items` does, plus `resolved_from`.
- **AC2:** `dbo.Items` and `audit.Items`: the refusal lists both.
- **AC3:** Qualified names are byte-identical.

- **AC-field:** the F-cases' query shapes, replayed on the anchor index after the build, answer
  without a Grep fallback; record the before/after counts in the working doc.
