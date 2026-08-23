---
id: 135
slug: harness-scores-recall-but-never-precision
title: The recall gate cannot see a wrong answer — an answer with every expected row plus four wrong ones scores 1.0
phase: 1.5b
milestone: Measure
status: todo
depends_on: [055, 121, 130]
---

## Why this exists

`score_recall` (`scripts/tokens_to_answer.py:249`) computes two things and neither is a
false-positive term:

- `recall = |found ∩ expected| / |expected|`
- `confidently_wrong = the result-bearing responses are **empty** while ground truth is non-empty`

So an answer that returns **every expected member plus wrong extras** scores `recall: 1.0`,
`confidently_wrong: False`, and passes the gate. That is not hypothetical — it is exactly
[130](130_web-entry-bucket-counts-test-controllers.md): `web_entry` reports **8** files as the web
surface on `symfony/demo` where **4** are `tests/Controller/*Test.php`. Precision is 0.5; the harness
reports a clean pass.

Two things make this the gate's most serious hole rather than a refinement:

1. **It contradicts the pillar it exists to defend.** PILLAR 1's standard is *a wrong answer is
   unacceptable, silence is* — and the gate can only see the silence.
2. **It is a recorded exclusion, not an oversight.** The round-4 review named it in one line —
   *"Measurement gap: no precision/recall harness"* ([`FEEDBACK.md`](../FEEDBACK.md)) — and
   [055](055_recall-benchmark.md) built the recall half. The precision half has been unowned since,
   and [121](121_onboarding-question-class-never-measured.md) wrote the consequence into
   [PLAN §19](../PLAN.md#19-project-context--decision-log): *"it scores recall and cost, never
   precision — finding 130 passes every mechanical check while being a wrong answer."*

## The design question this ticket must answer first

**Precision is only meaningful where the expected set is exhaustive for the question**, and today
`expected_set` is not declared to be. Several question shapes legitimately return more than the
listed rows (a ranked `search_symbol` page, a blast radius), so scoring extras as errors everywhere
would fire on correct answers and the floor would have to be set so low it means nothing.

The precedent to follow is `ratio_eligible` / `ratio_note`: a **per-question declaration** that a
metric applies here, with the reason in the row when it does not. Design decides between that and a
narrower `expected_exhaustive: true`, and states which questions carry it and why.

## Scope

1. `score_recall` (or a sibling) also returns **`precision`**, **`unexpected`** (the members
   returned that ground truth does not hold) and **`precision_eligible`**, for eligible questions
   only; ineligible rows carry a note, never a fabricated 1.0.
2. The gate takes a **`--min-precision`** floor beside `--min-recall`, and fails the same way.
3. `benchmarks/` records the first run: precision per eligible question, and every `unexpected`
   member listed rather than counted, so a drop is diagnosable.
4. Ground truth for the eligible questions is re-read **by hand** where the current `expected_set`
   was written as *"the rows that matter"* rather than *"all the rows"* — a set that was never
   exhaustive cannot become a precision denominator by relabelling it.

## Acceptance criteria

- **AC1** The scorer reports `precision` and `unexpected` for every `precision_eligible` question,
  and neither for the rest.
- **AC2** **130's shape fails the gate.** A question over the `web_entry` bucket on `symfony/demo`
  scores precision 0.5 and the four `*Test.php` files appear in `unexpected`. Red run recorded
  (R6.5) — this is the proving test, and without it the ticket has shipped a metric nobody has seen
  fire.
- **AC3** `--min-precision` fails the run when the floor is breached, and the failure names the
  question and the unexpected members.
- **AC4** Every question that is **not** eligible says why in its own row, in the
  `ratio_note` style — no silent omission and no default-true.
- **AC5** Two runs on one tree are byte-identical (R4.2), and the harness stays offline.

## Out of scope

- **Fixing 130 or 131.** This ticket builds the instrument that would have caught them; the defects
  are their own tickets and 130 is AC2's fixture, not this ticket's deliverable.
- **Differential testing against a language server**, which the same review proposed in the same
  line. [074](074_does-the-index-harm-mechanism-questions.md) already records why that comparison
  cannot be made on the anchor (its resident LSP was uninstalled and invoked zero times in 84 calls),
  and it needs a second host before it means anything.
- **A precision floor in CI.** Add the axis and record the first numbers; choosing the number the
  build dies on is a separate judgement, and picking it in the same change as the metric would set it
  to whatever today happens to score.
