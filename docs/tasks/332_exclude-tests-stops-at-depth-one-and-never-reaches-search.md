---
id: 332
slug: exclude-tests-stops-at-depth-one-and-never-reaches-search
title: "exclude_tests is refused past depth 1 on find_callers and absent from search_symbol — the two places three field sessions wanted it"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [262, 313, 315]
---

## Why this exists (field retros, 2026-09-23/24)

- **find_callers, depth 2** (FIELD-1426): `exclude_tests=true, depth=2` → hard error
  *"exclude_tests applies at depth 1 only"* (`find_callers.py:203-204`); the session dropped the
  filter and read test noise through the walk.
- **search_symbol, class-name queries** (FIELD-1449/1506/1586, FIELD-1621/1615, FIELD-1062/1634):
  66–87-row truncated pages *"dominated by `…Test::test*` methods"*, the wanted class near the top
  but the page spent on tests. `search_symbol` takes `kind`, `namespace`, `path_prefix` and no test
  filter.

262 filters **in SQL before paging** at depth 1, which is why it refuses deeper walks rather than
filter a page it already cut. 313 then made `impact` filter *inside the walk*, so the repo already
holds the second shape. The test role is one fact (`symbol_role.py`); it just is not offered here.

## Goal

The same `exclude_tests` meaning is available on a multi-hop caller walk and on symbol search.

## Scope / Deliverables

1. **find_callers depth > 1**: filter test-role sites inside the walk, as 313 does for `impact` —
   design call whether a test node is pruned (its callers unreached) or only hidden, stated in the
   payload.
2. **search_symbol `exclude_tests`**: filter in SQL before paging, 262's shape; `total_count`
   counts the filtered set.
3. **One predicate** — the test role 262 / 313 already read.

## Constraints

- **061** — `exclude_tests=false` (the default) is byte-identical on both tools.
- **R6.7** — no second test-path heuristic.
- **R1.1** — test role from the contract / adapter, never a directory-name branch.
- **313's gate** — the agent brief teaches both in the same change.

## Acceptance criteria

- **AC1** `find_callers(depth=2, exclude_tests=true)` answers, with no test-role site in the rows.
- **AC2** `search_symbol(query=<class>, exclude_tests=true)` on a fixture with the class and three
  test methods returns the class, and `total_count` excludes the tests.
- **AC3** Defaults are byte-identical (regression).

## References
`code_atlas/tools/find_callers.py:203-204`; `code_atlas/tools/search_symbol.py`;
`code_atlas/symbol_role.py`; `code_atlas/tools/impact.py`; tickets 262, 313, 315.
