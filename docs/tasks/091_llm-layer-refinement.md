---
id: 091
slug: llm-layer-refinement
title: Onboarding — LLM layer-name refinement (M12, opt-in)
phase: 3
milestone: M12
status: todo
depends_on: [084, 090]
---

## Goal
Improve layer names and boundaries where the deterministic heuristic (084) is weak — the flat-namespace
legacy case — using the LLM, optionally.

## Scope / Deliverables
- Behind the 085 seam and the 090 cache; consumes 084's heuristic layers and refines names/boundaries.
- Opt-in; off by default; the deterministic layering (084) remains the fallback.

## Acceptance criteria
- Opt-in and deterministic via the content-hash cache; off by default.
- Never runs in the per-PR gate (R4.1); core unaffected when off.
- With refinement off, layer output is byte-identical to 084.

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §4 (M12);
PLAN §14, §15.
