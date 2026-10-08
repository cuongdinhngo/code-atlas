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
   and how many of them are prose. A sample with no hits is a finding, not a pass — and an edge
   links only where the repo indexes the DDL the SQL adapter reads (T-SQL). If the measurement finds
   no linkable hits, the ticket closes `wontdo` with the numbers, and no code lands.
4. One recogniser, three copies: a shared fixture table in `tests/contract/` (literal → expected
   kind and target) that the PHP, TS and Python adapters all pass, so the copies cannot drift.

## Acceptance criteria

- **AC1:** On a TS fixture, `find_references dbo.Items` lists the `INSERT` literal's site.
- **AC2:** On a Python fixture, `find_callers dbo.Insert_Order` lists the `EXEC` literal's site.
- **AC3:** `"Update settings"` / `"delete this?"` emit nothing in either adapter.
- **AC4:** The Scope 3 measurement is recorded in this file before any adapter code is written.
- **AC5:** All three adapters pass the shared literal table (Scope 4).
- **AC6:** ADAPTER_PLAYBOOK §1.1's host-string row reads `371` for both adapters.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Measurement (Scope 3 · AC4) — recorded before any adapter code

`scripts/sql_literal_report.py` (committed, re-runnable, R6.3) ports `SqlLiteral.php`'s shape and
counts, per pinned checkout, every TS/JS and Python string literal led by `INSERT INTO` · `UPDATE` ·
`MERGE INTO` · `DELETE FROM` · `EXEC`, how many the clause guard accepts (*statements*), how many it
rejects (*prose*), and how many accepted targets name a table or procedure the checkout's own
`.sql` declares (*linkable*). Host dev-host, 2026-10-08, the cache of
`scripts/cross_repo_samples.json`'s pins (`--skip-clone`):

| sample (pin) | language | literals | keyword-led | statements | prose | linkable |
|---|---|---|---|---|---|---|
| ky | TS | 3,560 | 4 | 0 | 4 | 0 |
| mqttjs | TS | 3,178 | 0 | 0 | 0 | 0 |
| socketio | TS | 13,458 | 2 | 0 | 2 | 0 |
| flask | Python | 4,405 | 8 | 5 | 3 | 5 (its tutorial's own `schema.sql`) |
| pydantic | Python | 79,501 | 14 | 0 | 14 | 0 |
| requests | Python | 3,214 | 0 | 0 | 0 | 0 |
| sql-server-samples `fd84be9` (the `adventureworks_oltp` / `wwi_dw` pin, whole checkout) | Python | 2,259 | 12 | 12 | 0 | 12 |
| same | TS/JS | 111,850 | 35 | 26 | 9 | 26 |

**Reading.** The libraries hold no statement and every keyword-led literal there is prose the guard
rejects (20 of 20 across ky, socketio and pydantic) — a finding, not a pass. The one pinned repo whose
Node and Python layers talk to the database it declares — Microsoft's samples, 757 T-SQL objects —
has 38 linkable sites the PHP-only recogniser leaves unread. **The ticket goes ahead**; it does not
close `wontdo`.
