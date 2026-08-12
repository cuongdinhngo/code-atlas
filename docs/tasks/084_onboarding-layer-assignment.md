---
id: 084
slug: onboarding-layer-assignment
title: Onboarding — architectural layer assignment (M10)
phase: 3
milestone: M10
status: todo
depends_on: [083]
---

## Goal
Assign modules (files) to architectural layers, deterministically and language-agnostically, as the
input to `architecture_overview` (086) and the tour (087).

## Scope / Deliverables
- New `code_atlas/onboarding/layers.py` consuming 083's metrics; no LLM, no SQL of its own.
- **Heuristic = namespace/dir prefix refined by dependency direction**, with a **pure
  dependency-direction fallback** when namespaces are uninformative (flat PSR-0/global legacy) — locked
  2026-08-11.
- Deterministic ordering; no per-language handling (R1.1).

## Acceptance criteria
- Layers are sensible on the anchor PHP repo (recorded manual check) and byte-stable for identical input.
- No PHP-specific logic (CI grep-gate).
- Fixture tests assert layer assignment on a namespaced graph **and** the fallback path on a
  flat-namespace fixture.

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §4 (M10);
PLAN §14, §15 (M10).
