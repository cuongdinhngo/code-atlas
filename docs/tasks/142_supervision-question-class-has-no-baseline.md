---
id: 142
slug: supervision-question-class-has-no-baseline
title: The supervision question class was never put through the harness — 121's lesson, one phase later
phase: 3
milestone: Measure
status: todo
depends_on: [034, 055, 121, 135]
---

## Why this exists

[121](121_onboarding-question-class-never-measured.md) exists because **Phase 3 shipped without its own
cost gate**, and its split verdict is what narrowed the phase: cheap and correct where the question is a
lookup (12/12, recall 1.0), wrong where it is a reading order — `guided_tour` opened `symfony/demo` with
a lint config and put the front controller fifth
([benchmark](../benchmarks/121_onboarding-question-class.md)).

[138](138_architecture-rules-are-never-asked-of-the-graph.md),
[139](139_map-is-a-snapshot-so-nothing-shows-architectural-drift.md),
[140](140_impact-answers-in-symbols-not-modules.md) and
[141](141_extractability-cut-edges-and-the-cycles-that-block-it.md) propose four answers to a **question
class the harness has never seen**: *does this rule still hold*, *what changed architecturally*, *which
modules does this reach*, *can this be split*. 034/045/055 and 135's precision axis carry no such class.

**This ticket runs first, not last.** Done first it produces the baseline the other three are measured
against; done last it repeats 121 exactly — which is the one mistake this set already knows about.

Provenance: the architecture review of 2026-08-23, applying 121's lesson forward. **No tool is built
here.**

## Scope

- A fixture question set for the class: **≥6 questions** on the committed public pins, each with a
  hand-verified expected answer.
- The grep+`Read` baseline cost per question, recorded in a benchmark file — the same baseline 034
  defines.
- The class run under the existing harness on **both** axes: recall (055) and precision (135).
- Where no tool among the 17 can answer, that is recorded as **no tool answers this**, not scored as a
  miss — the two are different findings and 121's split verdict is what proves it.

## Acceptance criteria

- **AC1** ≥6 questions on pinned public repos, expected answers hand-verified, committed as fixtures.
- **AC2** Baseline (grep+`Read`) tokens-to-answer recorded per question in `docs/benchmarks/`.
- **AC3** The class runs on both axes; an unanswerable question is labelled unanswerable, not zero.
- **AC4** The benchmark names the host, the server build and the index revision that produced it
  (125's rule — a retro must not quote a commit that did not answer).
- **AC5** The existing question classes' numbers are unchanged, asserted — the class was added, the
  metric was not moved.

## Out of scope

- **Building any of 138–141.**
- **Changing the pins or the harness's existing classes.**
- **Deciding whether the class is worth serving.** That is what the numbers this ticket produces are
  for; 141's gate reads them.
