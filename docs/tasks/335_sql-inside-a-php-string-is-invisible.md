---
id: 335
slug: sql-inside-a-php-string-is-invisible
title: "SQL inside a PHP string literal emits no edge — 'who writes this table' and 'who EXECs this proc' still fall back to grep, the most-repeated gap across field retros"
phase: 1.5b
milestone: Coverage
status: todo
depends_on: [222, 328]
---

## Why this exists (field retros, 2026-09-24 and 2026-09-25)

Four retros in two days asked the same question and got the same answer:

- `find_references` on a table → `no_matches` with `authoritative: false` / `writes_emitters_only`
  (`find_references.py:251-254`). Grep then found 6, 10 and 1 PHP writers in three of them.
- `find_callers` on a stored procedure missed 2 of 5 entry points: PHP call sites that `EXEC` the
  proc from a string.

328 named this as *"the retro's actual culprit and the larger win"* and set it aside as a separate
ticket. This is that ticket.

## Goal

A PHP string literal whose text is a T-SQL write or `EXEC` yields an edge onto the table or proc it
names, at a tier that says it was read from text.

## Scope / Deliverables

1. **The PHP adapter emits** `WRITES` / `DELETES` / `CALLS` from a string literal (or heredoc) whose
   text begins a T-SQL statement: `INSERT INTO`, `UPDATE`, `MERGE INTO`, `DELETE FROM`, `EXEC`.
   Tier `HEURISTIC`; interpolated segments break the match rather than being guessed.
2. **The link reuses 222's cross-language machinery** — the target is a SQL qname, the source a
   PHP symbol. No second resolver.
3. **`writes_emitters_only` narrows** to what is still unmeasured once PHP emits.

## Constraints

- **R2.2** — keyed on T-SQL statement grammar, never on a wrapper method's name (`query`,
  `querySP`, …). The retro's `querySP('<Name>'` idea is exactly what R2.2 forbids.
- **R1.4** — the PHP adapter recognises statement *shape* only; it does not parse SQL. How far the
  shape goes is a design question for this ticket, answered before code.
- **R4.2** — identical input, identical rows.

## Acceptance criteria

- **AC1** `$sql = "INSERT INTO dbo.T (a) VALUES (1)";` inside a method → `find_references dbo.T`
  lists that method, `HEURISTIC`; red on today's code.
- **AC2** `"EXEC dbo.Gen @x = 1"` → `find_callers dbo.Gen` lists the PHP method.
- **AC3** `"UPDATE {$table} SET …"` emits nothing (interpolated target).
- **AC4** A string that merely mentions a table (`"see dbo.T"`) emits nothing.

## Out of scope

- SQL built by concatenation across statements.
- Column-level `WRITES` from PHP strings, unless AC1's design makes it free.

## References
`adapters/php/src/Visitor.php`; `code_atlas/tools/find_references.py:251-254`; tickets 222, 328.
