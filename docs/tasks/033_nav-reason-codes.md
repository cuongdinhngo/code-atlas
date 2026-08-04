---
id: 033
slug: nav-reason-codes
title: Reason codes + total_count on find_* / search (empty ≠ unknown)
phase: 1.5
milestone: Agent-trust
status: todo
depends_on: [013, 014]
---

## Goal
Stop an empty result from reading as proof. To an LLM consumer, a bare `[]` from `find_callers`
means "nothing exists" — so it will confidently report a function is dead when the real cause was a
missing symbol, an unbuilt index, or a truncated list. Every `find_*`/`search` response must carry a
machine-readable reason so the agent can tell **"no"** from **"I don't know"** (§19 agent-first pivot).

## Scope / Deliverables
- Add a `reason` enum to `find_callers` / `find_references` / `find_implementations` / `search_symbol`
  responses covering at least: `ok` (matches returned), `no_matches` (symbol exists, zero relations),
  `no_such_symbol` (qname not in `nodes`), `not_indexed` (no DB), `index_stale` (queried file drifted).
- Add `total_count` alongside the existing `truncated` bool so a clipped list says how many existed.
- Generalise the instinct already in `get_index_status.next_tool_suggestions`
  (`code_atlas/tools/get_index_status.py:114`) and the status enum in
  `code_atlas/tools/reach_shared.py` — reuse that vocabulary, don't invent a parallel one.

## Constraints
- The reason must distinguish **not-found** (qname absent from `nodes`) from **empty** (qname present,
  zero inbound/outbound of the asked relation) — these are different answers for an agent.
- No language branches (R1.1); store owns SQL (R1.4); read-only, deterministic (R4).
- `nav_result` / `empty_nav` shaping stays in one place (`code_atlas/tools/nav_result.py:54-79`);
  extend it, don't fork per tool.

## Acceptance criteria
- Querying a non-existent qname returns `reason=no_such_symbol` (not `no_matches`, not a bare empty).
- A symbol with zero callers returns `reason=no_matches` with an empty `results` list.
- Truncation sets `truncated=true` **and** `total_count > limit`; a full result sets `total_count`
  equal to the returned length.
- An unbuilt index returns `reason=not_indexed`. All asserted on planted fixtures; full suite passes.

## References
`code_atlas/tools/nav_result.py:60-79` (current `{indexed, results, truncated}` shape);
`code_atlas/tools/read_symbol.py:38-61` (already distinguishes found / stale — mirror it);
`code_atlas/tools/reach_shared.py` (status enum); `get_index_status.py:114`. PLAN §8.2 (tiers), §12.
Feedback origin: [`FEEDBACK.md`](../FEEDBACK.md) round 3 ("empty ≠ unknown — the highest-leverage
safety property you don't have").
