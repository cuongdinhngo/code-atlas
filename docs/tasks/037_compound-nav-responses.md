---
id: 037
slug: compound-nav-responses
title: Compound nav responses (call-site line) + consolidation A/B
phase: 1.5
milestone: Agent-fit
status: todo
depends_on: [013, 034]
---

## Goal
Make a nav answer complete in one call. The agent's next call after `find_callers` is always
"show me" — so returning the call-site line with each caller removes a round-trip, and round-trips
are the real token cost, not rows. Separately, evaluate consolidating the three relation tools into
one `find_relations(qname, relation)` — but decide it with the benchmark (034), not by assertion
(§19 agent-first pivot).

## Scope / Deliverables
- `find_callers` / `find_references` optionally return each site's source line/snippet (the line range
  is already known via `nodes`/`edges` — `read_symbol.py:76-78`, `file_outline.py:71-72`).
- An A/B experiment (measured on task 034): the three tools `find_callers`/`find_references`/
  `find_implementations` as-is vs a single `find_relations(qname, relation)`. Record the result and a
  decision; keep the winner.

## Constraints
- Token-frugal by default — the snippet is opt-in or capped (a compound response must not bloat the
  common case).
- No language branches (R1.1); store owns SQL (R1.4).
- **Consolidation is held behind the benchmark.** Merging tools trades schema tokens for a muddier
  per-tool description and collides with one-module-per-tool (R1.2) — do it only if 034 shows a net
  win; otherwise keep the three tools and ship only the compound response.

## Acceptance criteria
- `find_callers` can return each caller with its call-site line; default output stays token-frugal
  (snippet opt-in/capped), asserted.
- The 034 benchmark is run comparing the 3-tool surface vs `find_relations`, and the decision is
  recorded with its numbers.
- The chosen surface passes the full suite; if tools are merged, the contract/tool docs are updated.

## References
`code_atlas/tools/find_callers.py`, `find_references.py`, `find_implementations.py`;
`nav_result.py`; `read_symbol.py:76-78` (line ranges); task 034 (benchmark). PLAN §19; R1.2.
Feedback origin: [`FEEDBACK.md`](../FEEDBACK.md) round 3 ("fewer, more compound tools; round-trips
are the real cost").
