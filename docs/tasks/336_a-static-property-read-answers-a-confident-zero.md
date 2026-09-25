---
id: 336
slug: a-static-property-read-answers-a-confident-zero
title: "find_references on a PHP static property answers a bare no_matches — the adapter emits no edge for Class::$prop, and the honesty check is per language, so the zero passes as measured"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [186, 232]
---

## Why this exists (field retro, 2026-09-25)

`find_references` on a config class's static property returned `no_matches` with no caveat. Grep
found the declaration and a real read. The retro called it *"the one place this session where a
zero looked authoritative and wasn't measured"*.

Probed on `main` (`927aeb9`):

```php
class Cfg { public static $flag = false; }
class Db { public function init() { if (Cfg::$flag) { return 2; } } }
class Use1 { public function f(Cfg $c) { return 1; } }
```

`find_references \App\Cfg::$flag` → `reason: no_matches`, no `authoritative` field. Two causes:

- The PHP visitor has no arm for `Expr\StaticPropertyFetch` (`Visitor.php:274-290` handles
  `StaticCall` and `ClassConstFetch` only), so the read emits nothing.
- `relation_unmodelled_for_language` (`coverage.py:41`) asks whether the *language* emits any of
  the kinds. `Use1`'s type hint emits a `REFERENCES` (232), so PHP "models" it and the zero stands.
  Without `Use1` the same subject honestly answers `relation_unmodelled_for_language`.

## Goal

A static property read or write is a reference to the property — or, until it is, the answer does
not claim a zero.

## Scope / Deliverables

1. **The PHP adapter emits `REFERENCES`** from a `StaticPropertyFetch` whose class resolves
   (`self`/`static`/`parent` through the enclosing class, as `ClassConstFetch` already does).
2. **Instance property reads (`$this->x`) are stated** — either in scope with the same shape, or
   recorded here as out of scope with the reason. Decided before code.

## Constraints

- **R3** — `REFERENCES` already exists; if a new kind is wanted instead, that is a contract bump.
- **061** — every other subject's answer is byte-identical.

## Acceptance criteria

- **AC1** The probe above: `find_references \App\Cfg::$flag` lists `\App\Db::init` at line 8; red
  on today's code.
- **AC2** `self::$flag` inside `Cfg` resolves to the same qname.
- **AC3** `$cls::$flag` (dynamic class) emits nothing, or emits `DYNAMIC` — never a guessed class.

## References
`adapters/php/src/Visitor.php:274-290`; `code_atlas/tools/coverage.py:41-54`;
`code_atlas/tools/find_references.py:564-600`; tickets 186, 232.
