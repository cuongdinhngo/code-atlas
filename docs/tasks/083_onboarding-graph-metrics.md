---
id: 083
slug: onboarding-graph-metrics
title: Onboarding — deterministic graph-metrics foundation (M10)
phase: 3
milestone: M10
status: todo
depends_on: [014, 031, 017]
---

## Goal
The deterministic, read-only graph-metrics substrate Phase-3 onboarding builds on: fan-in / fan-out,
the entry-point set, and a dependency-direction summary that layering (084), the tour (087) and
summaries (085) all consume. No new tool surface here.

## Scope / Deliverables
- New `code_atlas/onboarding/metrics.py` — pure functions; **no SQL** (calls new read-only `GROUP BY`
  aggregate method(s) added to `store.py`, per R1.4 / `test_sql_confinement`).
- **Module unit = file path**, per-symbol = qname (locked 2026-08-11).
- **Entry-point = zero-inbound roots** — pure, deterministic, no config knob (locked).
- **SCC / cycle membership is out of scope** — deferred to 087 with its own node budget (locked;
  keeps 083 R4.3-clean).
- No language branches; graph shape + generic strings only (R1.1).

## Acceptance criteria
- Metrics compute over the anchor PHP index and are **byte-stable across two runs** (R4.2); anchor-repo
  run is a recorded local manual check.
- No PHP-specific logic — proven by the existing CI grep-gate (`tests/test_core_is_language_agnostic.py`).
- Unit tests over a fixture graph (including one cycle → a `mixed`-direction node) assert exact
  fan-in/out, the entry-point set, and the direction summary.

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §3–§4 (M10, locked);
PLAN §14, §15 (M10). Reuses `store.py` traversal (`reachable_from`, `impact_radius`, `find_orphans`).
