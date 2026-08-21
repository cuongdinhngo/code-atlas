---
id: 121
slug: onboarding-question-class-never-measured
title: Phase 3 shipped without its own cost gate — the onboarding question-class was never added to the harness
phase: 3
milestone: Measure
status: todo
depends_on: [034, 045, 055, 086, 087, 088]
---

## Why this exists

[`PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §5 named the gate for the whole
phase, in its own words: *"Gate the phase on the harness, not on vibes. Add an **onboarding
question-class** to the tokens-to-answer harness (034/045) and the recall gate (055). Baseline =
`grep`+`Read` with an agent building the map by hand… If the tools do not beat hand-mapping on this
class, say so in writing and narrow the scope."*

**It was never added.** `scripts/tokens_to_answer_questions.json` contains **zero** onboarding
questions. M10, M11 and M12 are all complete and the gate that was supposed to decide whether they
earned their cost has never run.

What did happen instead is real, and it is not a substitute:

- A human read the emitted artifact and found it unusable — 43 MB, an 82,218-byte median page,
  `Summary: (none)` on 500/500 pages, a 500-stop "tour". That produced **108–117**.
- Field measurement on the anchor on 2026-08-21 found two more defects, now **118** and **119**.

Both are evidence that *defects were fixed*. Neither is evidence that the onboarding question-class
**beats an agent hand-mapping the repo with `grep` + `Read`**, which is the only claim §5 set out to
test — and the same claim the project already got wrong once: PLAN §19 records search speed as a
premise "measured false", found only because a harness measured it. This is the identical exposure,
one phase later.

## Scope

- Add an **onboarding question-class** to `scripts/tokens_to_answer_questions.json`, using §5's own three
  questions: top-level layers and their dependencies · the entry point plus the first five things to read ·
  what depends on module X.
- Each question needs a fixture whose answer can be stated exactly, an `atlas_path` recipe over
  `architecture_overview` / `guided_tour` / `generate_onboarding`, a `grep` baseline recipe, and an
  `expected_set` so 055's recall scoring applies rather than a bare token count.
- Where a question has **no fair grep baseline** — "what are the layers" arguably has none — mark it
  `ratio_eligible: false` and say why in the entry, rather than inventing a baseline the comparison
  would then flatter.
- Run it on the pinned repos and record the numbers in `docs/benchmarks/`, win or lose.

## Acceptance criteria

1. **AC1.** The harness carries the onboarding class; a run reports tokens-to-answer for both paths on
   every question, and the recall gate scores those with an `expected_set`.
2. **AC2.** The result is written down **whichever way it goes**, in `docs/benchmarks/` and in §5 —
   including, if it loses, the narrowing of scope §5 promised in that case.
3. **AC3.** A question with no fair grep baseline is excluded from the ratio and states its reason;
   no baseline is fabricated to produce a favourable number.
4. **AC4.** Deterministic and re-runnable: fixed recipes, pinned repos, no wall-clock in the recorded
   output (R4.2).
5. **AC5.** §5's status line stops saying "unmeasured" only when the numbers exist.
