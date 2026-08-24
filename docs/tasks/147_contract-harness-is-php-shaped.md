---
id: 147
slug: contract-harness-is-php-shaped
title: The R3.4 conformance harness is PHP-shaped — `tests/contract/` cannot admit a second adapter
phase: 2
milestone: M7
status: todo
depends_on: [012, 025]
---

## Why this exists

R3.4 says every adapter must pass `tests/contract/` and that "that test *is* the substitutability
guarantee". The test cannot keep that promise today: it is written for one adapter.

- `tests/contract/test_adapter_conformance.py:14` imports `tests.php_adapter_cli`, and `CASES`
  hardcodes `.php` fixture filenames with frozen per-file kind histograms.
- `tests/php_adapter_cli.py:19-21` hardcodes `adapters/php/index.php` and `tests/fixtures/php`.

The intent was already recorded — `php_adapter_cli.py`'s own docstring says "keep that contract here
so adapter #2 does not invent a fourth copy". The intent is there; the shape is not. So the first
thing adapter #2 meets is a harness it cannot enter, and the cheapest way past it is a fourth copy —
exactly what that docstring was written to prevent.

This is a defect in the gate as it stands, not preparation for a language. It is worth fixing whether
or not [019](019_typescript-adapter.md) is ever taken off `deferred`.

## Scope

- Split the harness into a **per-adapter matrix**: one `adapter_cli` helper parametrized by
  (adapter directory, one-shot entry argv, fixtures directory, availability marker), and a
  conformance module parametrized over the registered adapters.
- Registration is **data** — a table in the test package keyed by adapter directory name — never a
  branch on a language name.
- PHP becomes one entry in that table. Its case list and histograms move across unchanged.

## Acceptance criteria

1. **AC1.** Every PHP case survives with a byte-identical frozen histogram; no case dropped, no
   count edited.
2. **AC2.** Adding a second entry requires no edit inside the conformance module body — only a row
   in the registration table and its fixtures.
3. **AC3 — guards the guard (R6.5).** With zero adapters registered the module **fails**; it must
   never pass over an empty matrix, which is how a skipped check reads as a pass.
4. **AC4.** Exactly one place in `tests/` spawns an adapter in one-shot `--file` mode. The "fourth
   copy" the existing docstring forbids is still impossible after the split.

## Not in scope

Any TypeScript parsing. Any fixture for a second language — [149](149_tsjs-construct-inventory.md)
names that inventory and this ticket does not invent it. The second CI runtime and the `npm ci` step,
which are [019](019_typescript-adapter.md)'s.

## References
R3.4, R6.1, R6.5, R6.7; PLAN §4.2, §4.3.
