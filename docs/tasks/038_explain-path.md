---
id: 038
slug: explain-path
title: explain_path(from, to) — control-flow path tool
phase: 1.5
milestone: Task-level
status: todo
depends_on: [017, 031]
---

## Goal
Answer a task-level question grep structurally cannot: **how does control reach B from A?** Agents
rarely ask "who calls X" — they ask "what happens when a user submits this form", "what breaks if I
change this". `explain_path` returns the path through the call/include graph between two symbols,
making the graph a reasoning tool, not just a lookup (§19 agent-first pivot).

## Scope / Deliverables
- `explain_path(from_qname, to_qname)`: a bounded, in-SQL traversal over the call/include graph that
  returns a path (sequence of edges) from A to B, reusing the impact/reachability traversal style.
- Distinguish "no path" from an empty/unknown result; mark a path that crosses non-RESOLVED hops as
  unproven (tier discipline consistent with 031/impact).
- Register in `main.build_server` + `TOOL_NAMES`.

## Constraints
- Bounded traversal **in SQL** — never `SELECT` the whole edge table, never load the graph into
  memory (R4.3), same guard as the impact/reachability suites.
- RESOLVED-first: a path that exists only via HEURISTIC/DYNAMIC edges is returned as **unproven**,
  never conflated with a proven path or with "no path".
- No language branches (R1.1); no new abstraction seam (R1.2).

## Acceptance criteria
- Planted graph with a known A→…→B chain: `explain_path` returns exactly that path (asserted, not
  counted).
- An unreachable pair returns a distinct "no path" result, not an empty-as-proof.
- A path crossing only HEURISTIC edges is marked unproven.
- Tool registered and listed via MCP; traversal never selects the whole edge table; suite passes.

## References
`code_atlas/store.py` (`impact_radius`, `reachable_from` — traversal patterns to reuse); tasks 017
(impact), 031 (reachability). PLAN §12 (impact/reachability), §8.2 (tiers). `R1.1`, `R1.2`, `R4.3`.
Feedback origin: [`FEEDBACK.md`](../FEEDBACK.md) round 3 ("add explain_path — the next new tool after
031, ahead of everything else").
