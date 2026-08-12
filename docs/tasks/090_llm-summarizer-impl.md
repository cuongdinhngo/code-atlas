---
id: 090
slug: llm-summarizer-impl
title: Onboarding — LLM summarizer behind the seam (M12, opt-in)
phase: 3
milestone: M12
status: todo
depends_on: [085, 088]
---

## Goal
Real prose summaries (and layer-name refinement input) via an LLM, plugged into the 085 seam — the
first and only place an LLM touches this project. Opt-in and deferred until the deterministic path is
proven and measured.

## Scope / Deliverables
- New package **outside** `code_atlas/` (proposed `onboarding_llm/`, mirroring `adapters/`); provides a
  `Summarizer` impl for the 085 Protocol. Provider = **Claude** (confirm model/pricing against the API
  reference at implementation time).
- **Content-hash cache** (keyed on symbol content) so runs replay and diffs stay stable; cached outputs
  are committable.
- Opt-in via config (e.g. `CA_ONBOARDING_SUMMARIZER`); **never imported by the core; never runs in the
  per-PR gate** (R4.1).

## Acceptance criteria
- A test asserts the LLM path **never** executes in the CI gate (stub-only there).
- The cache makes a second run deterministic against a fixed input.
- Core behaviour is unchanged when the summarizer is off (default).

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §4 (M12);
PLAN §14 (deterministic graph → LLM enrichment → presentation).
