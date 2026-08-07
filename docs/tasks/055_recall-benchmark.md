---
id: 055
slug: recall-benchmark
title: Nothing measures what the tools fail to find — a recall gate above the cost metric
phase: 1.5b
milestone: Measure
status: todo
depends_on: [034, 045]
---

## Goal
The project's metric is **tokens-to-correct-answer vs a grep+`Read` baseline** (PLAN §19, task 034).
That is a *cost* metric. It checks each question's `expected` answer, but every question in the set was
written by someone who already knew the tool could answer it — so nothing in the harness ever asks
**what the tool missed**.

That gap is not theoretical. Field retro round 2 recorded `find_callers` returning `total_count: 0` for
a method with six live call sites ([054](054_bare-name-callers-silent-drop.md)). Run through the
existing harness, that answer scores as a **cheap success**: few tokens, and the missing callers are
not in anyone's `expected` list. The metric we build the project around cannot see the worst failure
the project has had.

Task 046's outcome already recorded the same shortcoming from the other side — *"this benchmark
measures cost, never what a payload carries"* — and nothing was done about it.

**Both retros also measured the wrong shape.** Every question they timed handed the agent the symbol's
name up front (`who calls \Foo::save`). That is grep's best case, not the case the project exists for.
The founding claim — that native tools flounder on a large repo — is about starting from a *symptom*
with no name in hand, and it has never been measured once.

## Scope / Deliverables
- **A recall measure, reported next to the cost ratio.** For a question with known ground truth: what
  fraction of the true result set the tool returned, and — counted separately, because it is the one
  that destroys trust — how often it returned a confident empty or a confident wrong answer.
- **`confidently_wrong` is its own metric, not a recall miss.** "I don't know" and "there is nothing"
  are different answers; the harness must score them differently or the number hides the only failure
  mode that makes an agent stop using the tool.
- **Symptom-first questions.** A question tier whose prompt names no file, class, or method — the agent
  must find the name before it can use it. This is the only shape that can test the founding claim.
- **Session-level accounting for that tier**: tokens to the answer, files read, whether the answer was
  reached at all — not per-call cost, which is what the current harness measures.
- **A recall floor in CI, on the fixture tier**, alongside the existing `--min-ratio` gate: a change
  that halves tokens while losing results must fail, and today it passes.
- **Runbook section** in [`runbooks/tokens-to-answer.md`](../runbooks/tokens-to-answer.md) stating the
  ordering plainly: recall is a gate, cost is the win. A cheaper answer that finds less is a regression.

## Constraints
- **Correctness is a gate, cost is what is maximised.** Not a ranking — a tool that is merely as
  correct as grep and no cheaper has no reason to exist, and a tool that is cheaper and wrong loses the
  user. Both halves must be expressible in the harness.
- **Ground truth is written before the run, by hand.** Truth decided after seeing a tool's answer
  measures nothing.
- **Determinism (R4)** — no LLM in the harness; recipes stay fixed data, as they are today.
- **Nothing about a private repo enters this repository** (as [045](045_tokens-to-answer-local-repo.md)):
  the symptom-first question set for the anchor repo lives outside, and the local report is not the
  artifact CI uploads.
- **The existing fixture gate must not move** — `--min-ratio 0.24` on the fixture tier stays green and
  byte-identical unless the recall work deliberately changes it.
- **No language branch in the core (R1.1)**; this is `scripts/`-side.

## Acceptance criteria
- A question can declare a **complete** expected set, and the harness reports recall against it.
- A tool that returns an empty result where ground truth is non-empty is scored `confidently_wrong`,
  reported separately from a partial-recall miss, and a test asserts the two are not conflated.
- A symptom-first question runs end to end and reports session-level tokens and whether the answer was
  reached.
- CI gates a recall floor on the fixture tier; a deliberately-broken resolver fails that gate in a test.
- The runbook states the gate-vs-win ordering.
- Existing fixture-tier output is unchanged; `pytest`, `ruff`, `mypy` green.

## References
`scripts/tokens_to_answer.py` — `evaluate_question` `:173-191`, `run_grep_path` `:139-170`, the CLI at
`:380+`; [`runbooks/tokens-to-answer.md`](../runbooks/tokens-to-answer.md) (fixture / sample / local
tiers, and the "What this metric cannot see" section this ticket extends).
PLAN §19 (the metric, and the founding claim this ticket makes falsifiable).
[046](046_resolver-qname-candidate-dedupe.md) outcome — the same shortcoming, recorded and not acted on.
[054](054_bare-name-callers-silent-drop.md) — the failure this metric must be able to see; its Part B
is what lets a miss be reported honestly rather than as an empty answer.
Origin: field retro round 2, and the priority decision of 2026-08-07 (correctness gates, cost wins).
