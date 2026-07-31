---
id: 023
slug: guided-tour-and-docs
title: Onboarding — guided tour + markdown docs (M11)
phase: 3
milestone: M11
status: todo
depends_on: [022]
---

## Goal
Dependency-ordered guided tour and version-controllable onboarding docs (§14).

## Scope / Deliverables
- `guided_tour` tool: dependency-ordered walk through the codebase.
- `generate_onboarding`: emit markdown onboarding docs (committable) and/or a small viewer.
- **CI:** same stubbed-enrichment rule as task 022. "Generated markdown is coherent" is not falsifiable as written — CI can only assert structure (expected sections present, dependency order respected, deterministic given a fixed stub); coherence is a recorded manual check.

## Acceptance criteria
- Tour order respects dependency structure; generated markdown is coherent and committable.
- Presentation split clean: deterministic graph → LLM enrichment → presentation.

## References
Plan §14, §15 (M11).
