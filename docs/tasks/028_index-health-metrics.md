---
id: 028
slug: index-health-metrics
title: Index-health metrics in get_index_status
phase: 1
milestone: M4
status: done
depends_on: [010, 011]
---

## Goal
Give an agent a cheap, honest trust signal for how much of the graph is resolved fact vs guess, so it
can decide how far to lean on nav/impact output (§12 `get_index_status`, §8.2 tiers).

## Scope / Deliverables
- Extend `get_index_status` (`standard` detail only — keep `minimal` at the four §12 parts) with an
  `edge_health` block derived from data already in the DB:
  - counts per `confidence_tier` (RESOLVED / HEURISTIC / DYNAMIC) via one `GROUP BY` on `edges`.
  - resolved vs unresolved split (`target_qname` NOT NULL vs NULL) — an edge can be a known kind yet
    link to nothing (external/vendor), which is distinct from DYNAMIC.
- Report `parse_failures`: files the adapter could not parse. If the build does not already persist
  this, add a `meta` counter written by `indexer.full_build` / `incremental_update`; do not infer it.
- Keep the store as the only SQL owner (R1.4); the tool presents, it does not query the raw table.
- No language branches (R1.1) — tiers and edge kinds are contract vocabulary, not PHP-specific.

## Constraints
- Must not open or create a DB when none exists — `_unbuilt` stays cheap (existing behaviour).
- Counts come from indexed rows, never re-parse or re-resolve on read (R4 determinism).
- `minimal` response shape is unchanged (it is the ~100-token first call §12 advertises).

## Acceptance criteria
- On a planted graph with a known tier mix, `standard` returns exact RESOLVED/HEURISTIC/DYNAMIC counts
  and the resolved/unresolved split, asserted against hand-counted fixtures.
- `parse_failures` reflects a fixture with at least one unparseable file (count > 0), and is 0 on a
  clean build — proven, not assumed.
- `minimal` output is byte-identical to today's.
- Existing `get_index_status` / MCP tests pass unchanged.

## References
Plan §12 (`get_index_status`, tools table), §8.2 (confidence tiers). `contract.CONFIDENCE_TIERS`;
`code_atlas/tools/get_index_status.py`; `code_atlas/store.py` (`counts`); `code_atlas/indexer.py`.
Feedback origin: external review — "index-health in get_index_status" (second-tier). This measures
whether tasks 029/030 move the needle on a real repo, so land it first.
