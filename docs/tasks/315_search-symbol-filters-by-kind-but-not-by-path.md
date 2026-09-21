---
id: 315
slug: search-symbol-filters-by-kind-but-not-by-path
title: "search_symbol can filter by kind and namespace but not by file path, so a common token buries the one src/ hit under hundreds of test and mirror rows and the agent filters by eye"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [056]
---

## Why this exists (field-retro batch 2026-09-20/21)

Every retro in the batch hit the same friction on a common token: `Database` → `total_count: 506`,
`Member_Site` → 645 (`truncated: true`), the canonical hit buried under test doubles, compat mirrors
and FK-constraint rows. The agent's own words: *"I mentally filter out tests/ on every common-name
query."* The `kind:` filter shipped (056, `search_symbol.py:97-100`) and the default ranking is
already tier-first (265/297), but neither lets the agent say **"only under `src/`"** — and a
mental filter over a 50-row page is exactly the manual, error-prone step the index is meant to remove.

`search_symbol` accepts `kind` and `namespace` (a qname-prefix filter), but **nothing keyed on file
path**: `store.search_nodes` narrows only by kind and namespace (`store.py:2530-2571`, `_narrow`
`:3949-3976`); there is no `path`/`path_prefix` param on the tool (`search_symbol.py:97-105`) and a
grep of the repo for `path_prefix` finds none. `find_references` compounds it: it pages at 50 and
gives an exact `total_count` but no way to enumerate within a subtree (`find_references.py:452-458`),
so "list every consumer under `src/`" is unanswerable.

## Goal

Let an agent scope a symbol search (and a reference enumeration) to a file-path prefix, so a common
token returns the handful under the tree it cares about instead of a truncated page it must eyeball.

## Scope / Deliverables

1. **A `path_prefix` param on `search_symbol`** (file-path, distinct from the qname `namespace`
   filter), threaded into `store.search_nodes` as a path clause beside `_narrow`, fail-loud on a
   malformed value in the 056 style.
2. **The same filter on `find_references`** so a consumer enumeration can be scoped to a subtree —
   turning the 50-row sample into an enumerable answer within that scope.
3. **Disclosure when the filter hides an otherwise-exact hit** — mirror the existing `kind_excluded`
   pattern (`search_symbol.py:353-363`) so a path filter that excludes the match says so, rather than
   reading as absence.

## Constraints

- 056: an invalid `path_prefix` fails loud naming the expectation; it is published in the schema.
- The filter narrows, it does not re-rank — the tier-first order (265) is unchanged within the
  filtered set.
- R4.2: identical query + filter → identical rows.
- Path matching is on the stored, normalized path form (POSIX, index-root-relative) — one spelling,
  documented, not OS-dependent.

## Acceptance criteria

- **AC1** `search_symbol("Database", path_prefix="src/")` returns only rows whose file is under
  `src/`, in the same tier order, with `total_count` reflecting the filtered population.
- **AC2** A `path_prefix` that excludes an exact-name hit returns a `path_excluded`-style disclosure,
  not a bare `no_matches`.
- **AC3** `find_references(..., path_prefix=...)` enumerates consumers within the subtree; the page /
  `truncated` semantics stay honest for the filtered count.
- **AC4** An invalid `path_prefix` fails loud (056); the param appears in the published schema.

## Out of scope

- A path filter on `find_orphans` — its own scope question is [316]-adjacent and separately ticketed
  if wanted; not folded here.
- Re-ranking or changing the default order.
- Glob/regex path matching — a plain prefix only; anything richer is a later, evidence-backed ticket.

## References
`code_atlas/tools/search_symbol.py:97-105`, `:353-363`, `code_atlas/store.py:2530-2571`, `:3949-3976`,
`code_atlas/tools/find_references.py:452-458`, [056](056_filter-values-fail-loud.md),
ENGINEERING_RULES R4.2.
