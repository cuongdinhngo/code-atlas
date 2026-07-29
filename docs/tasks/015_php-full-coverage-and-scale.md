---
id: 015
slug: php-full-coverage-and-scale
title: Full PHP coverage + scale to 112k files (M4)
phase: 1
milestone: M4
status: todo
depends_on: [013, 014, 008]
---

## Goal
Prove global-namespace/PSR-0 resolution and large-repo performance (§6, §8).

## Scope / Deliverables
- Global-namespace & PSR-0 (`Foo_Bar_Baz` ↔ `Foo/Bar/Baz.php`) resolution end-to-end.
- `include_graph(path, direction)` tool over `include`/`require` edges.
- Run the ~112k-file validation sample (a large PHP monorepo) end-to-end; capture full-build timing as the perf target.

## Acceptance criteria
- Underscore/global symbols resolve correctly (not dropped).
- Full build over the large sample completes and stays within memory caps; timing recorded.

## References
Plan §6, §6.1, §8, §12, §15 (M4), §17 (scale risk).
