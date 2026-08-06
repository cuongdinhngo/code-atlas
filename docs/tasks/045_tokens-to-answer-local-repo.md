---
id: 045
slug: tokens-to-answer-local-repo
title: Tokens-to-answer — measure against a local repo with a pre-built index
phase: 1.5
milestone: Measure
status: in-progress
depends_on: [034, 042]
---

## Goal
Make the §19 metric runnable against the repo it was adopted for. The pivot names
**tokens-to-correct-answer vs grep+`Read`** as the definition of success, and names a large private PHP
monorepo as the evaluation anchor — but the harness cannot point at it. `scripts/tokens_to_answer.py`
has exactly two sources: `fixture` (a directory committed inside this repo, copied and `git init`-ed by
`prepare_fixture_root`, `:290-298`) and `sample` (a public repo cloned at a pinned SHA by
`run_sample_questions`, `:340-373`). A private repo already on disk is neither: it cannot be committed
here, it cannot be cloned from a pin, and its questions cannot live in a public repo.

The result is that the number the pivot rests on is measured only on 4-file toy fixtures (ratio ≈ 0.29,
where grep legitimately wins) and on three public Composer libraries (ratio ≈ 98) — never on the
legacy, non-namespaced, dynamically-dispatched code that motivated the project.

## Scope / Deliverables
- **A third source, `source: "local"`.** `root` is an operator-supplied path outside this repo, used
  **in place**: no `copytree`, no `git init`, no rebuild. A `run_local_questions` alongside the two
  existing runners, grouping by root as they group by fixture/pin.
- **Bind to an existing index instead of building one.** `build_index` (`:301-308`) always runs
  `full_build`; a real repo costs ~17 minutes per run, which makes the harness unusable interactively.
  Add the reuse path — bind a `Config` to an existing `db_path` and fail loud if it is missing — and
  keep building as an explicit opt-in.
- **CLI wiring** in `main` (`:380+`): a `--local` mode flag mirroring `--samples`. `--questions`
  already accepts an external path (`:382`), so the private question set needs no new plumbing — say
  so in the runbook rather than adding a second mechanism.
- **Runbook section** in [`runbooks/tokens-to-answer.md`](../runbooks/tokens-to-answer.md): how to
  point the harness at a local repo, and the explicit warning that its question file and report stay
  outside this repository.

## Constraints
- **Default behaviour unchanged.** The per-PR gate in [`ci.yml`](../../.github/workflows/ci.yml) runs
  the fixture tier with `--min-ratio 0.24`; neither the default source selection, the report shape, nor
  the floor may move. `--local` must be inert unless passed.
- **Nothing about a private repo enters this repository.** Not the questions, not the paths, not the
  report. The repo was deliberately anonymised for public release (commit `a3879cc`), and CI uploads
  `artifacts/` — so the local mode must never be reachable from a CI path, and its default report
  destination must not be the artifact that CI publishes.
- **Determinism holds (R4).** Recipes stay fixed data; no LLM, no network. The same local index and the
  same question file must produce identical token counts.
- **No language branch in the core (R1.1)** — this is a script under `scripts/`, and the change stays
  there; nothing in `code_atlas/` learns about repos or samples.
- **`run_grep_path` is O(repo) per question and unbounded in memory** (`:139-170`): it `rglob`s every
  glob match, reads each matching file **in full** into `read_files`, and only then slices to
  `max_read_files`. On ~28k PHP files a broad pattern reads gigabytes before discarding most of it.
  Bound it before the local mode makes it routine — cap while collecting, not after — and keep the
  baseline honest: a real agent's grep does see ignored trees, so the fix is a memory bound, not a
  quiet narrowing of what grep scans.

## Acceptance criteria
- A question with `source: "local"` and an absolute `root` evaluates against that tree's existing
  `.code-atlas/graph.db` without copying the tree, without `git init`, and without rebuilding
  (asserted; a temp-dir repo + pre-built index stands in for the private one).
- A missing or unreadable index in local mode fails loud with a message naming the path (R5.3),
  rather than reporting a zero-token answer.
- Running the harness with no new flags produces byte-identical output to the current fixture run
  (asserted against the committed question set) — the CI gate is untouched.
- Two runs of the same local question set over an unchanged index produce identical token counts (R4).
- `run_grep_path` on a tree far larger than `max_read_files` holds at most that many file bodies in
  memory at once (asserted).
- The runbook documents the local mode and states that the question file and report live outside this
  repository.

## References
`scripts/tokens_to_answer.py`: `prepare_fixture_root` `:290-298`, `build_index` `:301-308`,
`run_fixture_questions` `:316-332`, `run_sample_questions` `:340-373`, `evaluate_question` `:173-191`
(already root-agnostic — it reads `config.root` and `config.db_path`, so the new runner only has to
hand it a `Config`), `run_grep_path` `:139-170`, `main` `:380+`.
PLAN §19 (the tokens-to-answer metric and the private-monorepo anchor). Gate:
[`tests/test_tokens_to_answer.py`](../../tests/test_tokens_to_answer.py).
Origin: the onboarding trial in [044](044_onboarding-runbook.md) — the index exists and every tool
works on it, but the metric that decides whether any of it is worth the tokens cannot be run there.
