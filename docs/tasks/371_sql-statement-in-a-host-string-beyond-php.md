---
id: 371
slug: sql-statement-in-a-host-string-beyond-php
title: 'A TS or Python string that begins an INSERT, DELETE or EXEC writes nothing, so a table lists only its PHP and SQL writers'
phase: 2
milestone: Coverage
status: todo
depends_on: [278, 281, 335, 364]
---

## Why this exists

278/281/335 taught the PHP adapter to read a string literal that *begins* a SQL statement:
`adapters/php/src/SqlLiteral.php` takes a leading keyword and one object name and requires the
clause that keyword needs (`insert` → `(`/`values`/`select`, `update` → `set`, `delete` → `where`,
`exec` → a parameter). `insert`/`update`/`merge` give `WRITES`, `delete` gives `DELETES`, `exec`
gives `CALLS`. Prose such as "Update settings" has no clause and emits nothing. It never keys on a
wrapper's name (R2.2). Measured with each adapter's `--file` mode on 2026-10-08:

- **TypeScript:** `db.query("INSERT INTO dbo.Items (a) VALUES (1)")`, a template `DELETE FROM …
  WHERE`, `"UPDATE … SET"` and `"EXEC dbo.Proc @p"` emit only `CALLS "query"`.
- **Python:** `cursor.execute("INSERT INTO …")`, an f-string `DELETE`, `"EXEC dbo.Insert_Order ?"`
  emit only `CALLS "execute"`.

So `find_references` on a table, and `find_callers` on a proc, cover PHP and SQL callers only in a
repo whose Node or Python layer talks to the same database.

## Scope

1. Each adapter ports the **recogniser's shape**, not its code (R1.1/R2): its own string-literal
   visitor, the same keyword → kind map, the same required-clause guard against prose. Template /
   f-string heads count only when the object name closes inside the literal part, as PHP's `$closed`.
2. Python's parameter markers (`?`, `%s`, `:name`) and TS's (`?`, `$1`, `@p`) satisfy the `exec`
   guard. Which dialects the guard reads is declared, never assumed (playbook §6, 228).
3. Measure first, as 281 did: a pinned TS and Python sample, the count of literals that match,
   and how many of them are prose. A sample with no hits is a finding, not a pass.

## Acceptance criteria

- **AC1:** On a TS fixture, `find_references dbo.Items` lists the `INSERT` literal's site.
- **AC2:** On a Python fixture, `find_callers dbo.Insert_Order` lists the `EXEC` literal's site.
- **AC3:** `"Update settings"` / `"delete this?"` emit nothing in either adapter.
- **AC4:** ADAPTER_PLAYBOOK §1.1's host-string row reads `371` for both adapters.
