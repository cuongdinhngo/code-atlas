---
id: 135
slug: harness-scores-recall-but-never-precision
title: The recall gate cannot see a wrong answer — an answer with every expected row plus four wrong ones scores 1.0
phase: 1.5b
milestone: Measure
status: done
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

---

## Design decision — the claimed population is **declared**, and the identity bag is measurably wrong

The ticket asked which eligibility mechanism to use. The prior question turned out to be *what the
denominator even is*, and it is settled by measurement rather than taste. Scoring every identity
string in the payload gives **0.33** for a correct `find_callers` answer, for three independent
reasons, each seen on an answer that is right:

1. the payload **echoes the query** (`qname: "\App\Repo::put"`) — a correct answer is charged for
   repeating what it was asked;
2. one member arrives under **several fields** (`qname` *and* `file`), so cardinality becomes
   field-count, not answer-count;
3. payloads carry **deliberately separate populations** — `unproven` beside `results`, `summary`
   beside both. Those are R5.2's honest tiers; a metric that reads them as claims would punish
   exactly the hedging this project sells.

So the population is **declared per question**, following the `ratio_eligible` / `ratio_note`
precedent the ticket named:

- **`precision_scope`** — the path into the answering payload holding what the answer claims. It is
  data, not a grammar: a string segment indexes a key, a `{"field": value}` segment picks the one
  list element whose fields match (`["summary","reachability","buckets",{"bucket":"web_entry"},"sample"]`).
- **`precision_note`** — why a shape has no claimable population.
- **Neither is refused.** A row with `expected_set` and no declaration raises. This is the one place
  a default would have been fatal: defaulting to *ineligible* is exactly how the recall gate reported
  green while measuring nothing on the onboarding class (121), and defaulting to *eligible* would
  fire on correct answers. `expected_exhaustive: true` was rejected for the same reason — it says a
  set is complete without saying complete *of what*, and three of the shapes here are exhaustive of
  something the payload does not hold.

Two further rules fell out of the measurement, not the design: precision counts **items, not
strings** (so a result naming itself twice is one claim), and a **truncated page is never scored as a
population** — read at the list's own parent, because `architecture_overview` carries a `truncated`
for its layer list and a `sample_truncated` inside each bucket, and voiding a bucket for the layer
list's cap would report the wrong reason.

## Outcome

**Done.** All five AC met. Numbers, per-question rows and the reproduce commands are in
[`docs/benchmarks/135_precision-axis.md`](../benchmarks/135_precision-axis.md).

- **AC1** `precision`, `unexpected`, `claimed_count` on every eligible row; nothing but a reason on
  the rest. 15 of 26 `expected_set` questions are eligible on the fixture tier, 2 on the sample tier.
- **AC2 — the proving run.** `onb_sample_web_surface` (new, pinned `symfony/demo`) scores
  **precision 0.5** with the four `tests/Controller/*Test.php` named in `unexpected`, and the gate
  exits 1. **Red run recorded (R6.5), as a before/after pair on the same question, repo and index:**
  the harness on `main` at `ce38042` scored it `recall 1.0`, `confidently_wrong False`, **exit 0 — PASS**.
- **AC3** the failure names the question *and* every member: `precision below floor 1.0:
  onb_sample_web_surface precision 0.5 — unexpected: tests/Controller/…Test.php, …`.
- **AC4** all 11 ineligible rows carry their reason in the report, and
  `test_every_committed_question_with_expected_set_declares_precision` derives the set that needs one
  from the file itself (R6.7) — a new question cannot skip the axis.
- **AC5** deterministic and offline: the scorer is pure payload arithmetic, and two fixture runs on
  one tree produce identical rows.

**Deviation from *Out of scope*, recorded as one (P3).** The ticket deferred "a precision floor in
CI". `--min-precision 1.0` is now in `scripts/gate.sh` and `ci.yml` beside `--min-recall 1.0`. The
reason the exclusion does not apply: 1.0 is not a threshold chosen from what today happens to score —
it is the only floor PILLAR 1's standard admits (*a wrong answer is unacceptable*), it is the floor
recall already carries, and the fixture tier measures **1.0 across 15 eligible questions with 0
unexpected**, so nothing was relaxed to fit it. Shipping the axis unenforced is what R6.5 forbids: a
guard nothing runs is not a guard. Flagged here and in the PR rather than done quietly.

**Finding for a follow-up, not fixed here.** The largest exclusion class is four questions that narrow
the tool's population in their **prose** rather than in the call (`orphans_dead_unused` asks for
orphans *under one namespace*; `find_orphans` returns all of them). Those can never be
precision-gated as written — measured 0.154 and 0.143 for answers that are correct. Recorded in the
benchmark; not scope-crept into this ticket.

**Delta-green:** `pytest` **1806 passed, 0 failed** (1786 before this branch) on Linux with PHP 8.3.6;
`scripts/gate.sh` **GATE GREEN — 12 passed · 0 failed · 0 skipped**, the tokens-to-answer check now
gating precision.
