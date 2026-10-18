---
id: 403
slug: read-symbol-latest-routine-definition
title: "`read_symbol` on a routine several migrations redefine refuses as ambiguous instead of answering the latest"
phase: 2
milestone: Retrieval
status: todo
depends_on: [394]
---

## Why this exists

From the anchor project's Round-3 feedback: three PRs read a procedure that Flyway-style migrations redefine
(`CREATE OR ALTER`), and got `subject_ambiguous` (or `path_excluded` under a `path_prefix`). They fell back to
`Read` on the newest migration. On `main`, more than one definition always refuses (`read_symbol.py:289-292`);
394's `test_copies` precedence is the only tie-break.

## Scope

1. When every competing definition of a routine is a migration-ordered redefinition, `read_symbol` answers the
   latest one and lists the rest (as `aliases` / `implemented_by` do). The ordering comes from the migration
   tool's standard naming (R2.1), never a repo's paths.
2. A genuine ambiguity, such as two schemas or two unordered files, still refuses.

## Acceptance criteria

- **AC1:** `V1__x.sql` and `V7__x.sql` both define `dbo.P`: `read_symbol dbo.P` returns V7's body, naming V1.
- **AC2:** two unordered definitions still answer `subject_ambiguous`.
