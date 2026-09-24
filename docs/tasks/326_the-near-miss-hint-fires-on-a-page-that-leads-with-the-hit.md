---
id: 326
slug: the-near-miss-hint-fires-on-a-page-that-leads-with-the-hit
title: "search_symbol tells a truncated page it is 'substring near-misses, not hits' even when row 1 is the exact match — so the agent learns to ignore the one hint that exists to stop it"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [167, 245, 249]
---

## Why this exists (field retro, 2026-09-24 — FIELD-1624/1626/1636 batch)

One session saw `try_instead_hint: "the page is substring near-misses, not hits — …"` **three
times on pages that led with an exact hit**: a bare method name (410 rows, exact `X::name` methods
on the page), a class-constant enum (the class itself at row 2) and a `kind=Table` query (row 1
exact). Its conclusion: *"I learned to ignore it, which is the opposite of what a hint is for."*

**The cause is one predicate carrying two findings.** `_needs_narrowing_route`
(`search_symbol.py:649-653`) is true for `reason=substring_match` **or** for any truncated page
(`hits.truncated and total_count > len(results)`). Both arms then attach the same prose,
`TRY_INSTEAD_HINT_NARROW_BY_QNAME` (`nav_result.py:166`), which asserts the page holds no hits. The
`reason` is right — `is_direct_match` (`store.py:393`) already decides `ok` vs `substring_match`
(`search_symbol.py:349-353`) — but the hint contradicts it on the truncated arm.

245 scoped the route to *`reason: substring_match` with `total_count` far above `max_results`*;
the shipped predicate dropped the `substring_match` half on its second arm. 245's own rule is that a
different finding gets a different hint (`nav_result.py:163-164`) — "near-misses" and "a flood that
still holds the hit" are two findings sharing one sentence.

## Goal

The near-miss hint rides only a page the reason calls a near-miss. A truncated page that holds a
direct hit says it is truncated, not that it is wrong.

## Scope / Deliverables

1. **Split the truncated arm from the near-miss arm** in `_needs_narrowing_route`'s two callers
   (`_single_payload`, `_batch_answer`), so the sweep and single-subject shapes cannot drift.
2. **A truncated `reason=ok` page gets its own hint** (narrow by `kind` / `path_prefix`, the two
   filters that exist) or none — the design call — but never the "not hits" prose.
3. **`substring_match` and `separator_normalised` keep today's hints** byte-for-byte.

## Constraints

- **061** — only the truncated-and-direct arm changes; every other payload is byte-identical.
- **R6.7** — the hint follows `reason`; do not add a second direct-match test beside `_direct`.
- **093** — any new hint is a `TRY_INSTEAD_HINT_*` registry entry, pinned by the invariant test.
- Comments ≤ 3 lines (R7.5).

## Acceptance criteria

- **AC1** A fixture query whose first page is truncated and leads with an exact hit carries no
  `TRY_INSTEAD_HINT_NARROW_BY_QNAME`; red-arm test fails on today's code.
- **AC2** A first page of only substring hits still carries it (regression).
- **AC3** The same two cases hold inside a `queries=[…]` sweep.

## Out of scope

- Ranking exact final-segment matches above longer prefixes (`getX` over `getXList`) — a separate
  ranking question; the retro asked for it, but the hint lie is the defect.

## References
`code_atlas/tools/search_symbol.py:349-353,506-512,549-556,649-653`;
`code_atlas/tools/nav_result.py:163-168`; `code_atlas/store.py:393`; tickets 167, 245, 249.
