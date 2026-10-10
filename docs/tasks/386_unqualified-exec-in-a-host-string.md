---
id: 386
slug: unqualified-exec-in-a-host-string
title: 'A PHP string that runs `EXEC Proc @p` without a schema calls nothing, so a procedure lists no PHP callers'
phase: 2
milestone: Coverage
status: todo
depends_on: [335, 371]
---

## Why this exists

278/281/335 taught the PHP adapter to read a string literal that *begins* a SQL statement
(`adapters/php/src/SqlLiteral.php`). For `EXEC` it requires a **schema-qualified** name
(`SqlLiteral.php:74-76`): "a bare EXEC name would bind to a same-language method by name (204), so
EXEC is schema-qualified or nothing".

That guard is right about the risk and wrong about the population. In T-SQL an unqualified
procedure name is the ordinary form: the server resolves it against the caller's default schema,
then `dbo`. Measured on the anchor index (2026-10-10): of 94 `EXEC` literals in its PHP layer,
**88 name the procedure without a schema** (bare `Proc` or bracketed `[Proc]`) and emit nothing. Only 6 are
qualified. The procedures themselves are indexed by the T-SQL adapter, so `find_callers` on one
answers with its SQL callers only, and a capability trace stops at the PHP method that calls it.
Every PHP → procedure → table path in such a repo is cut at the first hop.

## Scope

1. An `EXEC` / `EXECUTE` literal whose name is unqualified (bare or `[bracketed]`) and that still
   meets the existing clause rule (a parameter follows: `@`, `?`, `:name`, a literal) emits a
   `CALLS` edge, tier `HEURISTIC`.
2. The edge must never bind to a same-language symbol (204). Decide at design how: the adapter emits
   the T-SQL default-resolution target (`dbo.<name>`), or emits the bare name with a target-kind
   restriction that the core resolves only against SQL procedure nodes. The contract is frozen (R3):
   if the second needs a contract field, that is a design decision with its own reason.
3. Unqualified `EXEC` with no clause after the name (prose like `"exec summary"`) still emits
   nothing, as today.
4. `EXEC @rc = Proc @p` (return-code form) and `EXECUTE AS …` (not a call) keep their current
   handling.

## Assumptions to prove at design

- `dbo` as the default schema is the T-SQL standard fallback, not a sample convention (R2.3). A repo
  whose procedures live in another schema gets `rule_keys_unresolved`-style counting of misses, not
  a wrong edge.
- The fix lives in `SqlLiteral.php` (and its TS/Python twins from 371, if they share the guard);
  no language branch enters the core (R1.1).

## Acceptance criteria

- **AC1:** `"EXEC Insert_Order @id"` and `"EXEC [Insert_Order] ?"` in a PHP fixture emit `CALLS` to
  the fixture's `dbo.Insert_Order` procedure, tier `HEURISTIC`.
- **AC2:** with a PHP method also named `Insert_Order` in the fixture, no edge lands on the method.
- **AC3:** `"exec summary"` (no clause) and `"EXECUTE AS USER = 'x'"` emit nothing.
- **AC4:** `find_callers` on the procedure lists the PHP caller; the count of linked call sites on
  the anchor index before and after is recorded in the task.
