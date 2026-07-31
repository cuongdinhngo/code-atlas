---
id: 025
slug: php-adapter-grammar
title: PHP adapter — full 8.5 grammar coverage
phase: 1
milestone: M0
status: todo
depends_on: [007]
---

## Goal
Close the construct gap the task 006 spike left, so the adapter covers the **full PHP 8.5 grammar**
(§6, R2.1) rather than the subset two fixtures happened to reach.

Split out of task 007 at its Gate 0: 007 shipped the streaming protocol, which alone unblocks 008 and
009. This card carries the language coverage, which only task 012 waits on.

## Scope / Deliverables

Task 007's analysis built a **42-construct inventory** by expanding the language spec, not the
ticket's prose; 18 were already satisfied by the 006 spike. The 23 below are what remain. Each is one
per-item row — review confirms **every** one, not a total.

**Nodes**
- Backed enums: capture `Enum_::$scalarType` (a pure enum must stay distinguishable from a backed one).
- Anonymous classes (`namespacedName` is `null`, so the spike skips them entirely).
- Property declared types (`Stmt\Property::$type` — today only params carry a type).
- Promoted constructor properties (`Node\Param::$flags != 0`).
- Property hooks (PHP 8.4, `Node\PropertyHook`).
- `ClassConst` modifiers (`final`, visibility) and typed class constants.
- Enum cases (`Stmt\EnumCase`) — **as `ClassConst`**, see the decision below.
- Closures (`Expr\Closure`) and arrow functions (`Expr\ArrowFunction`).
- Global `const` (`Stmt\Const_`) → the `Const` node kind, which the contract reserves and nothing emits.

**Edges**
- `USES_TRAIT` from `Stmt\TraitUse` — a trait used by a class currently produces **no edge, silently**.
- Trait adaptations (`insteadof` / `as` aliasing).
- `CALLS` from `Expr\NullsafeMethodCall` (`$o?->m()`) — a class distinct from `MethodCall`.
- First-class callables `f(...)` distinguished from a call (`CallLike::isFirstClassCallable()`).
- `NEW` for anonymous classes, and `new $var` as `DYNAMIC` (R5.2).
- `IMPORTS`: aliases (`UseItem::$alias`), function/const import types (`Use_::TYPE_*`), and
  `Stmt\GroupUse` including mixed-type group use.

**Other**
- Attributes captured raw on declarations, into the node `extra` field (`contract.NODE_FIELDS` has no
  `attributes` field). Raw name + args only — framework *meaning* is the Phase-2 enrichment layer (R2.3).

## Decisions inherited from task 007's Gate 0

These were ratified by the user on 2026-07-31 and are **not** re-open questions:

- **Anonymous declarations use line-anchored qualified names** — `\Ns\Class::method::{closure@42}`,
  `\Ns::{class@17}`, `path.php::{fn@8}`. The start line is a pure function of the file's own text, so
  it satisfies R4.2; unlike an ordinal, inserting one closure does not rename every later one. Add a
  `:col` suffix only if two anonymous declarations are ever found opening on the same line.
- **Enum cases reuse the `ClassConst` node kind**, with enum-ness recorded in `extra`. This avoids a
  `CONTRACT_VERSION` bump — PLAN §4.4 reserves v2 for task 019 — and matches PHP's own reflection
  hierarchy, where `ReflectionEnumUnitCase extends ReflectionClassConstant`.

## Acceptance criteria
- Each construct above is asserted over a spec-driven fixture (R6.1, R6.2) — **in this task**, not
  deferred. Task 012 owns the cross-adapter conformance matrix (R3.4), not this ticket's correctness.
- "Correct" means: for each construct, the emitted rows match an expected
  `(kind, qualified_name, [modifiers/params/extra])` tuple, `contract.validate()` returns `[]`,
  `ok` is `true`, and `nodes` is non-empty — a valid but empty result proves nothing.
- No repo/framework names in adapter source (grep-gate clean, R2.2).
- No `CONTRACT_VERSION` bump (both vocabulary decisions above were chosen to avoid one).

## References
Plan §6, §7, §2. Task 007's working doc carries the full 42-row inventory with the current state of
each row measured by running the adapter, plus the citations for why nullsafe calls, property hooks
and global `const` are in scope despite not being named in 007's original prose.
