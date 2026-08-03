---
id: 030
slug: alias-indirection-edges
title: Alias and literal-indirection edges (class_alias, string dispatch)
phase: 1
milestone: M2
status: todo
depends_on: [002, 011, 025]
---

## Goal
See through the indirection that legacy PHP resolves at runtime but a graph currently misses:
`class_alias()` registrations and literal-string dispatch. Without them, impact under-reports blast
radius on exactly the indirection-heavy code that is riskiest to change (§8.2). These are PHP-standard
mechanisms, not a repo's convention (R2).

## Scope / Deliverables
- **Contract:** add an `ALIASES` edge kind to `contract.EDGE_KINDS`, decide its resolver treatment
  (FQN-resolved: alias name → real class), bump `contract_version`, and update the conformance
  vocabulary + tests (R3). This is a frozen-contract change — treat the bump as first-class.
- **Adapter — aliases:** when the argument shape is literal, emit `ALIASES` from the alias name to the
  target class for `class_alias('Real', 'Alias')` (and the 2-arg form). `find_callers(\Real)` should
  then also surface `\Alias` users once the resolver links both.
- **Adapter — literal dispatch:** emit a low-confidence (HEURISTIC) `CALLS`/`NEW` edge when the target
  is a **string/class-name literal** — `new $var` where `$var` is a literal, `call_user_func('A::b')`,
  `call_user_func(['A','b'])`, `A::{'b'}()` — and keep the existing `DYNAMIC` marker when the argument
  is genuinely non-literal. "Here are the N dynamic sites I cannot resolve" is a valid honest answer.
- Confirm `enterNew` already covers `new $expr` → `DYNAMIC` (it does) and extend only the literal case.

## Constraints
- Contract change gates everything: `contract.py` is the single source of truth (R3); no adapter emits
  `ALIASES` until the version bump + conformance test land together.
- Literal edges are HEURISTIC at most — a string that names a class is still a guess about intent
  (R5.2). Non-literal stays DYNAMIC and unlinked.
- Zero language branches in the core (R1.1); the resolver treats `ALIASES` generically by FQN, gated
  through `FQN_EDGE_KINDS` (new kinds opt in, never silently join — see `contract.py:48`).
- Standard only: parse the language builtins, never a repo's alias-registry file (R2).

## Acceptance criteria
- `contract_version` incremented; a conformance test asserts `ALIASES` round-trips and that an adapter
  emitting the old version is handled per the versioning rule.
- Fixture: `class_alias('\A\Real','\A\Alias')` yields an `ALIASES` edge that resolves, and
  `find_references(\A\Real)` reaches a caller written against `\A\Alias`.
- Fixture: `call_user_func('Foo::bar')` and `new $literal` produce HEURISTIC edges; `new $runtimeVar`
  and `$this->$method()` stay DYNAMIC — asserted on resolved rows.
- Full contract-conformance, resolver, impact and PHP coverage suites pass under the new version.

## References
Plan §4 (contract, versioning), §4.2 (vocabulary), §8.2 (resolver, tiers). `R3`, `R5.2`, `R1.1`, `R2`.
`code_atlas/contract.py` (`EDGE_KINDS`, `FQN_EDGE_KINDS`, `CONTRACT_VERSION`); `adapters/php/src/Visitor.php`
(`enterNew`, `enterNamedCall`); `tests/contract/`. Feedback origin: external review Top-3 #2
("alias/indirection edges — the legacy-PHP blind spot").
