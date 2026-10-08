---
id: 369
slug: class-property-references-beyond-php
title: 'A TS static field or a Python class attribute is never referenced, so find_references on it answers a confident zero'
phase: 2
milestone: Coverage
status: todo
depends_on: [336, 232]
---

## Why this exists

336 made a PHP static property read or write (`Foo::$count`) a `REFERENCES` edge onto the property.
Neither other source adapter emits one. Measured with each adapter's `--file` mode on 2026-10-08:

- **TypeScript:** `static count = 0` is `Property Foo::count` with `modifiers: ["static"]`.
  `Foo.count`, `Foo.count = 2` and `this.count` emit no edge of any kind. The only `REFERENCES` are
  decorators and type annotations (`adapters/typescript/src/parse.js`).
- **Python:** `count = 0` in a class body is `Property Foo::count`. `Foo.count`, `Foo.count = 1`,
  `self.count` and `cls.count` emit no edge. The only `REFERENCES` are decorators and annotations.

`find_references Foo::count` therefore answers zero for a property the code reads and writes.

## Scope

1. A member access whose receiver the adapter already resolves — the class by name, or the lexical
   receiver (`this` · `self`/`cls`) — onto a **declared** property of that class emits `REFERENCES`.
   Reads and writes alike, as 336 did.
2. Only what the type table can name. An untyped receiver emits nothing (never a bare-name guess),
   and a property the class does not declare is not invented (229).
3. PHP's own residual stays where it is: `$this->x` / `$obj->x` (BACKLOG Follow-ups, 336). Whether
   this ticket's lexical-receiver rule should land in PHP too is decided in design, not assumed.

## Acceptance criteria

- **AC1:** On a TS fixture, `find_references Foo::count` lists the `Foo.count` read, the write and
  the `this.count` read.
- **AC2:** The same on a Python fixture for `Foo.count`, `self.count` and `cls.count`.
- **AC3:** A method call `this.bar()` / `self.bar()` adds no `REFERENCES` (it is already `CALLS`).
- **AC4:** The parity fixture gains the probe, and §7 regenerates with the new row.
