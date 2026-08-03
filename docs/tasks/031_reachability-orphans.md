---
id: 031
slug: reachability-orphans
title: Reachability / orphan detection (find_orphans, reachable_from)
phase: 1
milestone: M6
status: todo
depends_on: [003, 011, 013]
---

## Goal
Answer the inverse of impact: given entry points, what is **unreachable**? Impact gives forward blast
radius; migration/teardown asks "can this be deleted without breaking anything?" — a reachability
query over the include + call graph from declared entry points. This turns the graph from a nav tool
into a planning tool. Generic graph traversal, entry points supplied by config — no repo specifics (R2).

## Scope / Deliverables
- **Config:** an `entry_points` knob (list of files/globs, `CA_ENTRY_POINTS` + `.code-atlas.toml`)
  naming the reachability roots. Empty/unset → the tool reports that it cannot compute reachability
  rather than guessing roots.
- **`reachable_from`:** SQL traversal (same bounded, in-store style as the impact engine — never load
  the whole graph) forward over outgoing CALLS/NEW/INCLUDES (and EXTENDS/IMPLEMENTS as configured)
  from the entry-point seed set; returns the reachable node set.
- **`find_orphans`:** the complement — indexed symbols/files with zero inbound references, and files
  no entry point can reach. Report each with why (no inbound edges vs unreachable-from-roots).
- Store owns the SQL (R1.4); tools present. Register in `main.build_server` + `TOOL_NAMES`.

## Constraints
- **Sequence after task 029.** Reachability over an under-resolved graph produces *false orphans* — a
  symbol reached only via a `$this->` edge that today collapses to HEURISTIC/name-match can look
  unreachable. Note the accuracy caveat in the tool output until 029 lands; do not present orphan
  results as authoritative on a graph with high HEURISTIC ratio (surface task 028's ratio).
- Only RESOLVED edges expand the reachability frontier by default (consistent with impact A2); a
  DYNAMIC/HEURISTIC-only path means "cannot prove reachable", reported distinctly from "proven
  unreachable" — never conflate unknown with dead.
- Traversal bounded and in SQL (R4.3); no language branches (R1.1); no new abstraction seam (R1.2).

## Acceptance criteria
- Planted graph with known entry points: `reachable_from` returns exactly the hand-traced reachable
  set; `find_orphans` returns exactly the unreachable/zero-inbound set — asserted, not counted.
- A symbol reachable only through a HEURISTIC edge is reported as "unproven", not as an orphan.
- Unset `entry_points` yields an explicit "no roots configured" result, not an empty (misleading)
  orphan list.
- Tools registered and listed via MCP; traversal never `SELECT`s the whole edge table (same guard as
  the impact suite). Full suite passes.

## References
Plan §12 (impact engine — this is its inverse), §11 (config & ignore), §8.2 (tiers / RESOLVED-only
expand). `R1.1`, `R1.2`, `R1.4`, `R4.3`, `R2`. `code_atlas/store.py` (`impact_radius` as the pattern);
`code_atlas/config.py`; `code_atlas/tools/`. Feedback origin: external review Top-3 #3
("reachability / orphan detection — the query a migration actually asks").
