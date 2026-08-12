---
id: 087
slug: guided-tour-tool
title: Onboarding — guided_tour tool (M11)
phase: 3
milestone: M11
status: todo
depends_on: [083, 086]
---

## Goal
A dependency-ordered walk through the codebase — the reading order a newcomer (human or agent) should
follow.

## Scope / Deliverables
- New `code_atlas/tools/guided_tour.py`: topological order over the include/call graph, seeded from
  entry points, **cycle-safe via SCC condensation**. Returns ordered stops each with a one-line
  rationale.
- **SCC lands here** (deferred from 083) and is **node-budgeted**, the pattern `impact`/`reach` already
  use (R4.3 — never load the whole graph).

## Acceptance criteria
- Tour order respects the dependency structure; a graph with a cycle is handled without a loop.
- Bounded memory (R4.3); deterministic (R4.2).
- Fixture test with a cycle asserts the order and that the node budget is honoured.

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §4 (M11);
PLAN §14, §15 (M11).
