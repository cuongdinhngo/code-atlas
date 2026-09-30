---
id: 353
slug: include-path-concatenation
title: 'An include built as a constant plus a literal path reads as dynamic, so imported_by is empty'
phase: 2
milestone: Coverage
status: todo
depends_on: [065, 279]
---

## Why this exists

The PHP adapter keeps an include's target only when the whole expression is one string literal
(`adapters/php/src/Visitor.php:958`). Anything else becomes `(dynamic)` and the literal is lost.
That covers the two commonest include shapes in PHP:

- `require_once __DIR__ . '/partials/select.php';` (magic constant — language spec)
- `require_once ROOT_DIR . '/src/partials/select.php';` (a `define()`d root)

In the field retro (2026-09-30) `include_graph imported_by` on a partial answered
`relationship_not_modelled` for exactly the second shape, the dominant pattern in that tree.
Grep on the basename found the includers.

## Scope

1. The adapter emits the literal tail of a `Concat` include as the target, still tier `DYNAMIC`
   when the head is not a literal. `__DIR__` / `dirname(__DIR__)` heads are spec, so they resolve
   exactly (includer-relative, `contract.py` `INCLUDES`).
2. The core links a tail to a file when exactly one indexed path ends with it, at HEURISTIC.
   Several matches stay unlinked and counted (R5.6), never a pick.
3. Whether the target_raw shape change needs a `contract_version` bump is settled in design (R3).

## Acceptance criteria

- **AC1:** `__DIR__ . '/x.php'` links RESOLVED to the file beside the includer.
- **AC2:** `CONST . '/src/a/x.php'` with one indexed `…/src/a/x.php` links at HEURISTIC, and
  `include_graph imported_by` on that file lists the includer.
- **AC3:** Two indexed files ending in the tail ⇒ no edge, counted in `unresolved_includes`.
- **AC4:** A fully dynamic include (`$path`) is unchanged.
- **AC5:** Measured on the pinned PHP samples: unresolved INCLUDES before/after, recorded in the
  working doc; cross-repo floors re-set if counts move (P8).
