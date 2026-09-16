---
id: 298
slug: the-sql-adapter-answers-false-to-a-question-it-never-asked
title: '262 made `is_test` a read field with the path convention as its fallback, and wrote the fallback to yield to any adapter that emits the flag — but the T-SQL adapter writes `is_test: false` on every node it builds, which is not a decision, so the fallback never runs for SQL and a procedure whose only callers are test scripts is counted as production in the one census 262 exists to provide'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [262, 130, 231]
---

## Why this exists (cross-adapter audit of the 272-292 window, 2026-09-16)

262 chose the precedence deliberately: *"the adapter's `is_test` where an adapter emits it; the
existing path convention (130) where it does not"*, implemented as an early `continue` on a present
key (`code_atlas/symbol_role.py:32-36`). That is correct precedence and it assumes a present key means
a decided value.

The SQL adapter hardcodes the field on every node it constructs — `is_test: false` at
`adapters/sql/src/scan.js:327`, `:385`, `:435`, `:660`, `:694`, `:785`. It never reads a path, never
looks for a test convention, and never sets it true. So the key is always present and always false.
Measured against the shipped helper:

```
apply_test_role([{'file_path': 'tests/foo.sql', 'is_test': 0},
                 {'file_path': 'tests/foo.php'}])
-> [{'file_path': 'tests/foo.sql', 'is_test': 0},   # adapter "wins" — stays production
    {'file_path': 'tests/foo.php', 'is_test': 1}]   # path convention fills
```

php, python and typescript emit no `is_test` at all, so all three get 130's path convention and a
`test_role_source` of `path_convention`. SQL is the only adapter that opts out of the fallback, and
it opts out by accident. The consequence is the exact answer 262 was filed to stop: a procedure
called three times, all from test scripts, reports `production_count: 3` — *dead* presented as
*load-bearing*, which is the direction that blocks a deletion rather than permitting a wrong one.

This is the defect class [231](231_params-and-args-are-emitted-by-one-adapter-each-so-a-signature-is-a-php-feature.md)
removed for the capability handshake — declaring a field the adapter does not fill — arriving through
the node payload instead of the handshake.

## Scope / Deliverables

- **The SQL adapter stops emitting `is_test`** on nodes it does not classify, so 130's path convention
  fills it exactly as it does for the other three adapters. Six sites, one construct.
- **`ADAPTER_PLAYBOOK.md` §3's `is_test` row is corrected** in the same commit: it reads *"skip —
  nothing reads it; `class_diagram.py:253` derives the role from the path"*, which 262 made false.
  The row must say what the field now decides and that emitting a constant is worse than omitting it.
- **A test that pins the rule for any adapter**: a node with no `is_test` under a test path is
  classified; the fallback is not silently defeated by a constant.

## Constraints

- **Do not invert the precedence.** An adapter that genuinely decides the flag must still win; the fix
  is to stop pretending, not to stop trusting (262 / R5.6).
- R2 / R2.2: no test-directory name list enters the SQL adapter. The path convention stays the only
  fallback and stays in the core.
- 061: a schema with no test-path files produces byte-identical payloads and counts.
- `class_diagram.py:279`'s comment ("`is_test` is unused by adapters today") is the same stale claim;
  correct it or point it at `symbol_role`.

## Acceptance criteria

- A SQL fixture under a test path reports `is_test` true with `test_role_source: path_convention`, and
  `find_callers` on a procedure called only from it returns `production_count: 0`.
- No `is_test:` literal remains in `adapters/sql/src/scan.js`.
- The playbook row and the `class_diagram.py` comment no longer state that nothing reads the field.
- 262's existing tests pass unchanged.

## References
`adapters/sql/src/scan.js:327`, `:385`, `:435`, `:660`, `:694`, `:785`,
`code_atlas/symbol_role.py:24-40`, `code_atlas/tools/class_diagram.py:279`,
[`ADAPTER_PLAYBOOK.md`](../ADAPTER_PLAYBOOK.md) §3,
[262](262_the-contract-marks-test-code-and-no-tool-reads-it.md),
[130](130_web-entry-bucket-counts-test-controllers.md).
