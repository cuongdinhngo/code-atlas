---
id: 034
slug: tokens-to-answer-benchmark
title: Tokens-to-answer benchmark harness (vs grep+Read)
phase: 1.5
milestone: Measure
status: todo
depends_on: [014, 018]
---

## Goal
Make the product thesis falsifiable. Nothing in the repo measures the claim the whole project rests
on — cross-repo validation asserts "no crash / sane counts", which is a smoke test, not an accuracy
or value test. The right metric for an agent consumer is **tokens-to-correct-answer against a
grep+`Read` baseline**, not precision-vs-LSP. Build the harness first, because it is what tells you
whether every later change (033/037/039/040) actually earned its cost (§19 agent-first pivot).

## Scope / Deliverables
- A committed ground-truth set: ~40 realistic agent questions across the pinned sample matrix
  (`scripts/cross_repo_samples.json`), each with a known correct answer.
- A harness that, per question, measures: (a) tokens to answer using code-atlas tools, (b) tokens to
  answer with grep+`Read` only, (c) whether the answer was correct. Reports per-question rows and an
  aggregate ratio.
- A regression gate: fail if the aggregate ratio degrades beyond a set threshold.

## Constraints
- The harness is **dev tooling, not core** — it lives under `scripts/` or `tests/`, never under
  `code_atlas/` (SRP; the core stays deterministic and consumer-agnostic).
- No network/LLM inside the core (R4); any model calls the harness makes are confined to the harness.
- Ground truth is hand-labelled and version-controlled; the harness must be re-runnable and its
  per-question correctness check must be falsifiable (exact expected answers), not "looks plausible".

## Acceptance criteria
- The harness runs on the pinned samples and emits, per question, token counts for both paths plus a
  correct/incorrect verdict, and an aggregate tokens-to-answer ratio.
- The regression gate fails on a deliberately degraded fixture and passes on the baseline.
- The ground-truth set is committed and documented (how to add a question).

## References
`tests/test_cross_repo_validation.py` (`assert_plausible_counts` / `assert_parse_isolation` — the
smoke tests this replaces as the accuracy story); `scripts/cross_repo_samples.json` (sample matrix);
PLAN §15 (ship discipline), §19. Feedback origin: [`FEEDBACK.md`](../FEEDBACK.md) rounds 1 & 3 — the
metric to build the project around; "a guard that cannot fail is not evidence".
