---
id: 088
slug: generate-onboarding-markdown
title: Onboarding — generate_onboarding markdown + manifest (M11)
phase: 3
milestone: M11
status: todo
depends_on: [084, 086, 087]
---

## Goal
Emit committable, version-controllable onboarding docs from the graph — the human-facing side of the
same enrichment the tools serve.

## Scope / Deliverables
- New `code_atlas/tools/generate_onboarding.py`: write markdown (overview · tour · per-module pages)
  under `docs/onboarding/` **plus a `manifest.json`** the viewer (089) reads. Regenerable caches under
  `.code-atlas/onboarding/`.
- Deterministic given a fixed summarizer stub (R4.2).

## Acceptance criteria
- Generated markdown is committable; CI asserts **structure** — expected sections present, dependency
  order respected, deterministic given the stub. Coherence is a **recorded manual check** (not
  falsifiable — task-023 note).
- No PHP-specific logic.

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §4 (M11);
PLAN §14, §15 (M11).
