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
2. The edge must never bind to a same-language symbol (204). Decide at design how. Two known
   constraints: the contract has no procedure kind (a T-SQL procedure is a `Function`, the same kind
   as a PHP function, `code_atlas/contract.py` `NodeKind`), so a target-kind restriction needs a new
   kind and a `contract_version` bump (R3) — filtering by language in the core breaks R1.1. And the
   T-SQL adapter keeps a routine's qname as written (`adapters/sql/src/scan.js` `CREATE_RE`), so
   `CREATE PROCEDURE Insert_Order` is `Insert_Order`, not `dbo.Insert_Order`: an adapter that emits
   `dbo.<name>` alone misses every procedure created without a schema.
3. Unqualified `EXEC` with no clause after the name (prose like `"exec summary"`) still emits
   nothing, as today. That also leaves a parameterless `"EXEC Proc"` unlinked; whether a whole,
   closed literal `"EXEC Proc"` may link (as the qualified form does) is decided at design from the
   split measured in the first assumption.
4. `EXEC @rc = Proc @p` (return-code form) and `EXECUTE AS …` (not a call) keep their current
   handling.
5. The same guard lives in all three host adapters: `adapters/php/src/SqlLiteral.php:74-76`,
   `adapters/typescript/src/sqlLiteral.js:50` and `adapters/python/src/sql_literal.py` (371). All
   three change together, so one host never links what another drops.

## Assumptions to prove at design

- Before design, split the anchor index's 88 unqualified literals into those followed by a clause
  and those not (parameterless calls): the first number is what this ticket can link.
- `dbo` as the default schema is the T-SQL standard fallback, not a sample convention (R2.3). A repo
  whose procedures live in another schema gets `rule_keys_unresolved`-style counting of misses, not
  a wrong edge.
- No language branch enters the core (R1.1).

## Acceptance criteria

- **AC1:** `"EXEC Insert_Order @id"` and `"EXEC [Insert_Order] ?"` in a PHP fixture emit `CALLS` to
  the fixture's procedure, tier `HEURISTIC` — once created as `dbo.Insert_Order` and once as bare
  `Insert_Order`; both link.
- **AC2:** with a PHP method also named `Insert_Order` in the fixture, no edge lands on the method.
- **AC3:** `"exec summary"` (no clause) and `"EXECUTE AS USER = 'x'"` emit nothing.
- **AC4:** `find_callers` on the procedure lists the PHP caller; the count of linked call sites on
  the anchor index before and after is recorded in the task.
- **AC5:** AC1-AC3 pass on a TypeScript and a Python fixture too.
