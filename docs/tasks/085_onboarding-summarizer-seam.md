---
id: 085
slug: onboarding-summarizer-seam
title: Onboarding — Summarizer Protocol seam + deterministic default (M10)
phase: 3
milestone: M10
status: todo
depends_on: [083]
---

## Goal
The single seam that keeps the LLM out of the core: a `Summarizer` Protocol with a deterministic
default, so later LLM enrichment (090/091) plugs in without the core ever importing an LLM.

## Scope / Deliverables
- `Summarizer` Protocol in `code_atlas/onboarding/`; default impl = **structural** summary (signature,
  docblock first line, role tag derived from 083 metrics). No SQL, no network, no LLM.
- One seam only (R1.2) — no registry/factory until a second summarizer exists.
- A CI test that proves the **graph → enrichment → presentation** split holds with the middle stage
  faked (R4.1 keeps the LLM out of the core; this keeps it out of CI too).

## Acceptance criteria
- Default summarizer is deterministic (R4.2) and language-agnostic (no PHP logic).
- The stubbed-seam test asserts the split and would fail if presentation read the graph directly.
- No dead abstraction (R7.4): exactly one Protocol, one default impl.

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §2–§4;
PLAN §14, §15 (M10). Precedent for optional deterministic enrichment: `code_atlas/enrichment.py`.
