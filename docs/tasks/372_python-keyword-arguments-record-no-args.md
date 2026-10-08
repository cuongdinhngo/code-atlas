---
id: 372
slug: python-keyword-arguments-record-no-args
title: 'A Python keyword argument records no args entry, so arg_is and keyed_calls rules cannot read it'
phase: 2
milestone: Coverage
status: todo
depends_on: [049, 352, 364]
---

## Why this exists

Split from 367. Measured with `adapters/python/index.py --file` on 2026-10-08: `Foo(a=1, b='b')`
emits `args: []`. `contract.py`'s `args` is positional, so a keyword argument is invisible to
`arg_is` (049), to a `keyed_calls` rule's `key_arg` (352/364), and to 367's construction sites.
Keyword arguments are the common Python call shape, so this caps every argument-reading tool there.

## Scope

1. Design settles the shape against `contract.py` before code: a parallel keyword map, or named
   entries in `args`. Either may move the contract — then R3 applies (version bump, conformance
   tests, release), decided in design, not assumed.
2. A `keyed_calls` rule can name a keyword (`key_arg` by name) only if design adds it; `arg_is`
   gains the same reach.
3. Python only: TS has no keyword arguments; PHP 8 named arguments are a follow-up if design keeps
   the shape language-neutral.

## Acceptance criteria

- **AC1:** `Foo(a=1, b='b')` records both arguments with their shapes.
- **AC2:** `arg_is` narrows `find_callers` by a keyword argument's shape.
- **AC3:** A positional-only call's `args` are byte-identical to today's.
- **AC4:** If the contract moves, `contract_version` is bumped and the conformance suite covers it.
