---
id: 352
slug: string-arg-names-a-symbol-rule
title: 'A call whose string argument names a class or a proc links to nothing, so its callers read as zero'
phase: 2
milestone: Coverage
status: todo
depends_on: [040, 062, 335]
---

## Why this exists

A field retro (2026-09-30, 19 PRs on an anchor PHP + SQL Server project) scored code-atlas 7.2/10.
The two most-repeated misses were one shape: the target of a call is a string argument.

- **Class by string (4 PRs):** `Widget::make('SaveButton')` builds the class `SaveButton`.
  `find_callers SaveButton::render` answered `relation_unmodelled_for_language`; Grep found them.
- **Proc by string (2 PRs):** `$db->runProc('Insert_Order_v1', $params)` calls the SQL proc of that
  name. `find_callers Insert_Order_v1` answered `no_matches` over 7 PHP call sites.

(Names are stand-ins, R2.4.) 335 already links a literal that *is* T-SQL (`'EXEC X @p'`). A bare
name handed to a wrapper is not language grammar, so R2.2 keeps it out of the adapter.

## Scope

1. A new `CA_INDIRECTION_RULES` entry kind: calls to `<callee>` whose argument `<n>` is a string
   literal emit a HEURISTIC edge (`NEW` or `CALLS`, as the rule says) to the symbol that literal
   names. It extends PLAN §11's rule files (040/062/063); v1 `calls` takes exact qname pairs only,
   while `view_data` setters already extract one-line string args, so the extraction exists.
2. The target resolves through the normal resolver, across languages (PHP → SQL `Function`).
   No match stays unlinked and counted, never invented.
3. Edges carry `rule: true` like every rule edge (068). No rules ⇒ graph unchanged.

## Acceptance criteria

- **AC1:** With a rule for a `make(<class>)` callee, `find_callers <Class>::<method>` reaches the
  sites that build `<Class>` through it, at HEURISTIC, each hit `rule: true`.
- **AC2:** With a rule for a `runProc(<proc>)` callee, `find_callers <proc>` on a SQL proc lists the
  PHP call sites, at HEURISTIC.
- **AC3:** A literal naming no indexed symbol emits no edge and is counted in the build report.
- **AC4:** A non-literal argument (`$name`, concatenation) contributes nothing.
- **AC5:** No rule file ⇒ byte-identical graph (R4.2); an invalid rule fails loud before parse (R5.3).
- **AC6:** Zero repo or framework names under `adapters/` or `code_atlas/` (R1.1, R2.2 gates).
