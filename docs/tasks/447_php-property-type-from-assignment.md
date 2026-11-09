---
id: 447
slug: php-property-type-from-assignment
title: "PHP: an untyped property assigned `new X` types its receiver"
phase: 2
milestone: "Round-3 field gaps"
status: todo
depends_on: [393]
---

## Why this exists

Round-3 field feedback (20 Sep – 7 Nov): untyped receivers are the cause in ~8% of scored PRs, and
the "infer receiver types" idea came up in 17. The commonest shape is still open in the last week:
`find_callers` on a model method lists only the tests, because the production call goes through
`$this->model->m()` where `$this->model` is assigned in the constructor and declared without a type.

What the PHP adapter already types (`adapters/php/src/TypeTable.php`, `MemberTypes.php`): a local
`$x = new X`, a typed property, a constructor-promoted parameter, a return hint, and a `@return`
docblock (393). It does **not** type a property from its assignment, or from a `@var` docblock.

## Scope

1. `MemberTypes` records a property's class when it has no declared type and either:
   - a `@var X` docblock on the property names one class-like (the existing `docClass` rules,
     `NOT_A_CLASS` excluded), or
   - every `$this->p = new X(...)` in the class's own methods assigns the **same** class `X`.
     Two different classes, or any other assignment to `$this->p`, leaves it untyped.
2. A call through such a property links at **`HEURISTIC`** (a declared type stays `RESOLVED`): the
   assignment is a claim about one file, not a guarantee across subclasses.
3. File-local only (R3.3): a property assigned in a parent class declared in another file stays
   untyped; `unresolved_receivers` keeps counting it.

## Out of scope

Parameters with no type hint, factory returns past `@return`, `$var` set in an including file.

## Acceptance

- Fixture: a controller whose constructor sets `$this->model = new Model()`; `find_callers
  Model::m` names the controller's call at `HEURISTIC`, and `unresolved_receivers` drops by one.
- Fixture: two different `new` assignments to one property → no edge, still counted.
- Fixture: `/** @var Model */ private $model;` → the call links.
- Conformance suite green; the anchor's `unresolved_receivers` count before and after is reported.
