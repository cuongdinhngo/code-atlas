---
id: 121
slug: onboarding-question-class-never-measured
title: Phase 3 shipped without its own cost gate — the onboarding question-class was never added to the harness
phase: 3
milestone: Measure
status: done
depends_on: [034, 045, 055, 086, 087, 088]
---

## Why this exists

[`ROADMAP.md`](../phase3-onboarding/ROADMAP.md) §5 named the gate for the whole
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

---
<!-- working doc (work_doc_mode: embed) — everything above this line is the ticket -->

## Session status

- **Current phase:** complete (shipped) — PR [#152](https://github.com/cuongdinhngo/code-atlas/pull/152)
- **work_doc_mode:** embed (plain local-file ticket)
- **SCOPE:** L · **TIER:** full
- **CHALLENGER:** OFF (run args) · **Review:** SKIPPED (run args)
- **Branch:** `feat/121-onboarding-question-class`
- **BASELINE:** 1756 passed (`main` at `4239ef4`, after PR #151)
- **Arena decision (maintainer, 2026-08-23):** option **(b)** — the class and the harness recipe are
  authored here; the anchor arm is a local-tier template for the maintainer to run on the private
  monorepo and paste back. The anchor is **not on this host**, so no anchor figure in this change is
  claimed as measured.

## Phase 1 — Analysis: requirements matrix

| # | Kind | Requirement | Source | Proven by |
|---|---|---|---|---|
| G1 | G | Phase 3's cost gate exists and runs, so M10–M12 stop being unmeasured | ticket §Why | AC1 |
| G2 | G | The verdict is written down whichever way it goes | ticket §AC2 | AC2 |
| R1 | R | An onboarding question-class in `tokens_to_answer_questions.json`, newcomer shapes | ticket §Scope, P3 work order | AC1 |
| R2 | R | Each question: fixture/pin, exact answer, an `atlas_path` recipe, a grep recipe or a stated exclusion, an `expected_set` for 055 | ticket §Scope | AC1, AC3 |
| R3 | R | Both arms run and report **per question**, not just the aggregate | work order STEP 2 | AC1 |
| R4 | R | Verdict into §5 and PLAN §19 in the 2026-08-08 register, including if negative | ticket §AC2 | AC2, AC5 |
| C1 | C | The onboarding tools must be bindable by the harness (they were not) | repo | AC1 |
| C2 | C | Ground truth established by hand; the map must not define its own correct answer | work order STEP 1 | AC1 |
| C3 | C | Do not fix the map while measuring it — defects are filed, not patched | work order STEP 3 | 129 · 130 · 131 |
| C4 | C | No fabricated baseline for a question grep cannot answer | ticket §AC3 | AC3 |
| C5 | C | Deterministic, re-runnable, no wall-clock in the report (R4.2) | ticket §AC4 | AC4 |
| C6 | C | Fixture names no repo, framework or region (R2.2) | rulebook | existing R2.2 grep-gate |
| AC1 | AC | Harness carries the class; a run reports both paths per question; recall scores every `expected_set` | ticket | new guard test + two committed reports |
| AC2 | AC | Result written in `docs/benchmarks/` **and** §5, negative half included | ticket | `benchmarks/121_…md`, §5, §19 |
| AC3 | AC | A question out of the ratio states its reason; no invented baseline | ticket | new guard test |
| AC4 | AC | Fixed recipes, pinned SHA, no wall-clock; ratio invariant to checkout depth | ticket | re-run at two path depths |
| AC5 | AC | §5 stops saying "unmeasured" only once the numbers exist | ticket | §5 rewritten with the numbers |

**Clarifications needed: 0** (the one open decision — which arena — was answered by the maintainer
before Phase 1; recorded above).

## Phase 2 — Design

**Approach.** Three tiers, each measuring what it honestly can, and nothing pretending to be the anchor.

1. **A purpose-built committed fixture** (`tests/fixtures/php/onboarding`, 10 modules + a
   `.code-atlas.toml` entry-point glob). The existing fixtures are 2–4 flat files, so every onboarding
   answer on them is trivially degenerate — `method: dependency-direction-fallback`, one layer, no hub,
   no declaration. The new tree yields **9 responsibility layers, 8 crossings, a 4-fan-in hub, a
   declared glob, an unreachable module and one module whose path names no responsibility**, so each
   question has a non-degenerate exact answer. Names are industry-generic (`controllers/`, `services/`,
   `repositories/`, `lib/`, `jobs/`, `reports/`, `legacy/`) — R2.2 holds.
2. **Two questions on the pinned `symfony/demo`**, because a real layout is where a reading order can
   actually be wrong — and it is.
3. **A local-tier template in the runbook** for the two shapes no committed tier can carry: a mirror
   pair (needs 25 shared relative paths) and a named business screen on a tree nobody can hold in
   their head. That is the anchor arm, and it is a recipe, not a claimed number.

**Harness changes, three, each forced by a measured failure:**

- `bind_tools` / `_TOOL_NAMES` did not carry `architecture_overview`, `guided_tour` or
  `generate_onboarding` at all — the class was unrunnable, not merely unwritten. (Token-neutral for
  existing rows: `get_index_status`'s suggestions are empty for a current index.)
- `found_expected_members` read identities from the response and its `results` list only. An
  onboarding answer keys its members on `layer` / `module` / `pattern`, under `modules` or nested in
  `summary`, so the recall gate scored **0** — or, with a shorter `expected_set`, would have gone
  green having measured nothing. Now it recurses the payload and derives the collection instead of
  naming one.
- `ratio_note` — a question out of the cost ratio now carries its reason into the report row, so the
  artifact states it and not just the question file (AC3). Backfilled onto the four pre-existing
  ineligible questions.

**Rejected alternatives.**

- *Reuse an existing fixture instead of adding one.* Rejected: a 4-file flat tree cannot produce a
  layering, a hub or a declaration, so nine of the ten questions would have had degenerate answers and
  the gate would lock in nothing.
- *Wire the failing shapes in as gated questions.* Rejected for now: the harness has no per-question
  "known wrong" state, and adding one to hold three findings is a framework for a population of one
  (R1.2 / R7.4). The findings are tickets **129 · 130 · 131** and a benchmark section instead.
- *Keep the sample floor at 78 by making the sample onboarding questions ratio-ineligible.* Rejected:
  that would protect a headline number by hiding the class from it. The aggregate now spans two
  classes and the floor moves to `0.8 × observed` = 55, said out loud in the runbook.
- *Fix `guided_tour`'s ordering in this ticket.* Rejected: a measurement taken on a tree you are
  editing measures nothing (the work order's own rule).

**Proving test (R6.5).** `tests/test_onboarding_question_class.py`, run against `HEAD` in a scratch
worktree **before** any of the above landed: **4 failed, 3 passed** — no onboarding class, the three
onboarding tools unexercised, ineligible questions stating no reason, and
`found_expected_members` returning `[]` for an onboarding-shaped answer.

## Phase 3 — Execute summary

- **Red run recorded** (above): 4/7 failing at `4239ef4`. Green after: 7/7.
- **Fixture tier:** 24 questions, 24 correct, recall 1.0, `confidently_wrong` 0, aggregate
  **0.789** (was 0.29). The three ratio-eligible onboarding questions: **1.58 / 1.34 / 1.01**.
- **Sample tier:** 7 questions, 7 correct, aggregate **69.06** (was 98.2 — two classes now).
  `onb_sample_feature_files` **4.66**.
- **Determinism:** the identical run at `/tmp/…/scratchpad` and 60 characters deeper both give
  2,733 / 2,155 / **0.789** — the counted payload's path normalisation holds, so the new floor is not
  a function of checkout depth (the runbook's own warning, checked rather than assumed).
- **Floors recalibrated** (`0.8 × observed`): `gate.sh` + `ci.yml` **0.27 → 0.63**, the scheduled
  sample workflow **78 → 55**.
- **Three defects filed, none fixed:** 129 (`include_graph(imports)` a silent zero for any namespaced
  file — the INCLUDES edge is anchored on the namespace node), 130 (`web_entry` counts 4 test
  controllers among 8 "web surface" files), 131 (`guided_tour`'s first five stops are lint and
  bootstrap config; front controller fifth — **1 of 5** against the hand answer).
- **One pre-existing test corrected, not weakened:** `test_questions_file_is_well_formed` demanded
  `grep_evidence` from every sample row, which a ratio-ineligible sample question cannot have; it now
  demands `grep_evidence` when a `grep` baseline exists and a `ratio_note` when it does not.
- **Delta-green:** 1756 → **1769** (+13 = 7 guard tests + 6 from three new task files);
  `scripts/gate.sh` GATE GREEN.

## Decision log

- **Arena = option (b)** (maintainer, 2026-08-23). The anchor is not on this host; no figure here is
  attributed to it, and the anchor arm ships as a runbook template rather than as a number.
- **A new fixture was authored** rather than stretching an existing one — the degenerate-answer
  argument above. It is a fixture, so R2 ("standard over sample") is untouched: it drives tests, never
  adapter semantics.
- **Nine of twelve questions are deliberately out of the cost ratio**, each with a written reason. A
  layering, a reading order, a blast radius and a whole-graph negative have no fair grep baseline, and
  inventing one is the single easiest way to make this measurement lie in our favour.
- **The negative half is the headline.** §5 said *"if the tools do not beat hand-mapping on this
  class, say so in writing and narrow the scope."* The reading-order shape lost, so §5 and §19 now
  narrow the phase to a navigation-and-provenance claim and `guided_tour`'s ordering is a ticket
  rather than a foundation.
- **Recall scoring was widened, not relaxed.** Identity matching stays exact (a child still cannot
  satisfy a parent); only the region searched grew from `results` to the whole payload. Every existing
  recall row was already 1.0, so the change cannot flatter an old number.
- **Precision is out of scope and recorded as a gap.** Finding 130 passes every mechanical check in
  this harness while being a wrong answer. Naming that in the benchmark doc is the deliverable; a
  precision metric is not this ticket.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| — | *no subagent dispatched this run* | — | — |

`LEDGER: 0 dispatch rows | main-loop spend unmeasured (host does not surface usage) | complete`
