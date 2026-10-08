---
id: 367
slug: constructor-flag-beyond-php
title: 'Only PHP flags its constructor, so find_callers on a TS constructor or a Python __init__ lists no construction site'
phase: 2
milestone: Coverage
status: todo
depends_on: [362]
---

## Why this exists

362 made `find_callers` on a flagged constructor read the construction sites of its class, with
their argument shapes (`contract.CONSTRUCTOR_FLAG`, `find_callers._constructed_class`). Only the PHP
adapter sets the flag. Measured with each adapter's `--file` mode on 2026-10-08:

- **TypeScript:** `class Foo { constructor(a: number) {} }` emits `Method Foo::__construct` with
  `params` and no `extra`. `new Foo(1)` is a `NEW` onto `Foo` with `args: ["number"]`.
- **Python:** `def __init__(self, a=0)` and `__new__` emit `Method` nodes with no `extra`.
  `Foo(1, 'a')` is a `CALLS` onto the class `m.Foo` (no `NEW` — README, by design).

So `find_callers Foo::__construct` / `Foo::__init__` answers with the direct calls only (`super()`,
explicit `__init__`), not the sites that build the object — the exact gap 362's F2 closed for PHP.

## Scope

1. Each adapter sets `extra.constructor = true` on the method its language makes the constructor:
   TS `constructor` (emitted as `__construct`), Python `__init__`. Language spec only (R2.1).
2. Confirm the core reads Python's `CALLS`-onto-class sites through `also_targets`, which matches
   on target only. If it filters on `NEW`, widen it in the core, not by changing Python's edge kind.
3. Decide `__new__` explicitly and record the decision in the Python README.
4. Declare it: a new capability flag or the existing one, settled in design (R3 if the contract moves).
5. Python records no `args` for a keyword argument: `Foo(a=1, b='b')` emits `args: []`, so neither
   `arg_is` on a construction site nor a `keyed_calls` rule (352/364) reads it. Fill keyword
   arguments, in a shape design settles against `contract.py`'s positional `args` (R3).

## Acceptance criteria

- **AC1:** `find_callers Foo::__construct` on a TS fixture lists every `new Foo(...)` site, and
  `arg_is` narrows them by a literal argument.
- **AC2:** The same for `find_callers Foo::__init__` on a Python fixture's `Foo(...)` sites.
- **AC3:** A method merely named `constructor`/`__init__` outside a class carries no flag.
- **AC4:** `Foo(a=1)` in Python records the keyword argument, and `arg_is` reads it.
- **AC5:** ADAPTER_PLAYBOOK §1.1's constructor row names this ticket for both adapters.
