---
id: 450
slug: inherited-constructor
title: "PHP: `Child::__construct` resolves to the inherited constructor, and `new Child` reaches it"
phase: 2
milestone: "Round-3 field gaps"
status: todo
depends_on: [362]
---

## Why this exists

The follow-up 362 left: an inherited constructor misses its subclass's `new` sites. Round-3 field
feedback hit both halves: `search_symbol` / `read_symbol` on `Child::__construct` for a class that
declares none returns nothing, and "who constructs this" on the parent misses every `new Child(...)`.
PHP inherits `__construct` like any method, so this is the language rule (R2).

## Scope

1. `read_symbol Child::__construct`, when `Child` declares no constructor, walks the linked
   ancestry (the resolver's existing inherited-member walk) and answers the nearest ancestor's
   constructor, marked `inherited_from: <Parent>`.
2. A `NEW` edge onto a class that declares no constructor also counts as a caller of the inherited
   constructor: `find_callers Parent::__construct` lists `new Child(...)` sites, each marked
   `via_subclass: Child`, at the tier of the `NEW` edge.
3. An unlinked ancestor (a class in an unindexed path) answers `no_such_symbol` with
   `ancestry_unresolved`, never a confident absence.

## Acceptance

- Fixture: `class Child extends Base {}` + `new Child()` → `read_symbol Child::__construct` returns
  `Base::__construct` with `inherited_from`, and `find_callers Base::__construct` includes the site.
- Fixture: a `Child` that declares its own constructor is unchanged.
