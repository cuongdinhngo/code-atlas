---
id: 042
slug: tokens-to-answer-sample-tier
title: Tokens-to-answer sample tier — populate pinned public repos (ratio ≫ 1)
phase: 1.5
milestone: Measure
status: todo
depends_on: [034, 018]
---

## Goal
Prove the value claim the fixtures cannot. Task 034 shipped the harness and a per-PR gate, but the
committed questions run against 4-file toy fixtures where `get_index_status` overhead makes
code-atlas *cost more* than reading one tiny file — observed ratio ≈ **0.302** (1409 vs 425 tokens,
9/9 correct). That is a behaviour-lock, not evidence code-atlas saves tokens. The token win
(ratio ≫ 1) only appears on realistic repos, where a grep pattern matches many files an agent must
read whole while code-atlas returns the one resolved answer. This ticket populates the **sample
tier** so we have a real, defensible number (§19 agent-first pivot; "a guard that cannot fail is
not evidence").

## Scope / Deliverables
- Add `source: sample` questions to `scripts/tokens_to_answer_questions.json` against the pinned
  public repos in `scripts/cross_repo_samples.json` (laravel/laravel, symfony/demo, brick/math) —
  a spread of the query kinds where grep over-reads: callers of a widely-used method, references to
  a class, implementations of an interface, "who includes X".
- Verify each answer **by running the harness in a PHP+clone environment** (not by eyeballing) — the
  `expected` must be the real resolved answer, `grep_evidence` the real raw-text hit.
- Wire the sample tier so it runs on schedule / `workflow_dispatch` (like cross-repo validation),
  not per-PR — it needs a clone and is slower. Record the observed aggregate ratio.
- Report the real ratio (expected ≫ 1) in the runbook, replacing "measured on schedule, not yet
  populated".

## Constraints
- Sample questions' answers must be **verified by execution**, never committed unverified — the
  whole point of 034 is falsifiability.
- Harness stays dev tooling under `scripts/` (SRP); no core change; deterministic recipes, no LLM
  (R4). Framework/repo names stay out of `adapters/` (R2.2) — sample pins live in the manifest.
- The per-PR fixture gate (`--min-ratio 0.24`) is unaffected; the sample tier is a separate,
  scheduled run with its own floor.

## Acceptance criteria
- `scripts/tokens_to_answer_questions.json` carries `source: sample` questions whose answers were
  produced (not guessed) by the harness against the pinned checkouts.
- A scheduled / dispatch job runs the sample tier and reports an aggregate ratio; the observed
  number is ≫ 1 (or, if not, that surprising result is investigated and written up — the metric is
  falsifiable both ways).
- The runbook states the real sample-tier ratio and how to reproduce it.

## References
`scripts/tokens_to_answer.py` (harness; `source: sample` path already wired via
`cross_repo_validate`), `scripts/tokens_to_answer_questions.json`,
`scripts/cross_repo_samples.json` (pins), `docs/runbooks/tokens-to-answer.md`,
`docs/runbooks/cross-repo-validation.md` (schedule/dispatch pattern to mirror). Origin: task 034
observed fixture ratio 0.302 — fixtures favour grep; the win is only visible on real repos.
