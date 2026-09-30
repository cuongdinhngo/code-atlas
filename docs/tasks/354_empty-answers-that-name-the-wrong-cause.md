---
id: 354
slug: empty-answers-that-name-the-wrong-cause
title: 'Two empty answers name the wrong cause: an unconfigured trace says no_matches, a misqualified name says index_stale'
phase: 2
milestone: Honesty
status: todo
depends_on: [073, 199, 246]
---

## Why this exists

Both answers are empty, and both send the agent the wrong way. Field retro, 2026-09-30.

1. **`trace_capability` with nothing configured.** With no `capabilities.toml`, no structural
   layout and no `CA_ENTRY_POINTS`, the flow set is empty and every subject answers `no_matches`
   (`code_atlas/tools/trace_capability.py:256`). 3 PRs read that as "this route joins no flow".
   `find_view_data` and `find_orphans` refuse the same situation by name instead (069); the reason
   text already exists (`code_atlas/onboarding/capabilities.py` `EMPTY_REASON`).
2. **A qualification miss on a behind index.** `read_symbol dbo.X`, where the declaration is `[X]`
   (qname `X`), answered `index_stale`. On a miss, `ensure_miss` runs before any name-variant lookup
   (`code_atlas/tools/read_symbol.py:182` vs `:212`). With several dirty files and an unnameable
   subject it returns `stale` (073), so `_resolve_miss` never gets to suggest `X`.

## Scope

1. `trace_capability` returns a not-configured reason, with `EMPTY_REASON`'s route, when the whole
   flow set is empty. `no_matches` stays for a subject absent from a non-empty set.
2. A miss tries the name-variant resolution before it declares `index_stale`. If a variant exists
   in a clean file, that is the answer (or its `try_instead`). Check `find_callers` and
   `find_references` for the same order and fix them the same way.

## Acceptance criteria

- **AC1:** On an index with no capability sources, `trace_capability(path=…)` returns the
  not-configured reason and a route, never `no_matches`.
- **AC2:** With one flow present, a subject outside it still answers `no_matches`.
- **AC3:** On a behind index with >1 dirty file, `read_symbol dbo.X` for a clean `[X]` answers the
  `X` candidate, not `index_stale`.
- **AC4:** A true miss on that index still answers `index_stale` (073 unchanged).
