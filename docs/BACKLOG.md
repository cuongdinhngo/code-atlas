# Backlog — code-atlas

Task tracker. One file per task in [`docs/tasks/`](tasks/) (`NNN_slug.md`). Source of truth for scope
is [`PLAN.md`](PLAN.md); the durable decision log is [PLAN §19](PLAN.md#19-project-context--decision-log)
and per-task lessons are in [`LESSONS.md`](LESSONS.md). This file tracks *what is open and what
landed*; each ticket's cost is one row in [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) (R7.2) — narrative
rationale lives in those three.

**208 tickets closed before 2026-09-05** are not listed here — the Conventions below say why, and
`git log --follow -- docs/tasks` is the history. What stays is what you read to choose the next
ticket: the finding, not the slug.

**Status legend:** `todo` · `in-progress` · `blocked` · `deferred` · `done`

## Open work — Pillar 1 · Graph

Resolved relationships for the agent, and the honesty of the payload that carries them
([PLAN §1](PLAN.md#1-goals--non-goals)). The `Theme` column is unchanged.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 074 | [Does the index harm mechanism questions? — no verdict](tasks/074_does-the-index-harm-mechanism-questions.md) | Measure | deferred | 055, 067, 045 |
| 098 | [Should the graph hold "this file is a copy/port of that one"? — evidence-gated](tasks/098_correspondence-relation-seam.md) | Coverage | deferred | 030, 011, 003 |
| 141 | ["Can this module be split out?" — the cut edges and the cycles that block it — evidence-gated](tasks/141_extractability-cut-edges-and-the-cycles-that-block-it.md) | Coverage | deferred | 120, 087, 140 |
| 200 | [The recognition map is a prompt no model can read; the snippet that reaches one is PHP-only](tasks/200_the-recognition-map-is-a-prompt-no-agent-can-read.md) | Adoption | blocked | 081, 097, 036, 099, 260 |
| 272 | [A partition that is all tests answers `ok`](tasks/272_a-partition-that-is-all-tests-answers-ok.md) | Honesty | todo | 262, 255, 264 |
| 273 | [The partition counts edges and the total counts callers](tasks/273_the-partition-counts-edges-and-the-total-counts-callers.md) | Honesty | todo | 262, 258 |
| 275 | [Four green rows frame two red ones as absence](tasks/275_four-green-rows-frame-two-red-ones-as-absence.md) | Honesty | todo | 101, 246, 073 |
| 276 | [The caveat that fires on every answer](tasks/276_the-caveat-that-fires-on-every-answer.md) | Honesty | todo | 221, 238, 243 |
| 277 | [Page one ranks the tree that cannot run](tasks/277_page-one-ranks-the-tree-that-cannot-run.md) | Coverage | todo | 115, 180, 265 |
| 278 | [The writer set is computed for one check and addressable from nothing](tasks/278_the-writer-set-is-computed-for-one-check-and-addressable-from-nothing.md) | Coverage | todo | 022, 215, 255, 248 |
| 279 | [An autoloaded repo answers unreachable and means unmeasured](tasks/279_an-autoloaded-repo-answers-unreachable-and-means-unmeasured.md) | Honesty | todo | 031, 255, 264 |
| 280 | [A parser accepts what the runtime rejects](tasks/280_a-parser-accepts-what-the-runtime-rejects.md) | Honesty | todo | 058 |
## Open work — Pillar 2 · Onboarding

The rendering of what the code actually is, for a human supervising an agent or presenting the
project ([PLAN §1](PLAN.md#1-goals--non-goals)). Same graph, no second pipeline.
M10–M12 have all landed; round narratives live in [`FEEDBACK.md`](FEEDBACK.md),
[PLAN §19](PLAN.md#19-project-context--decision-log), [`LESSONS.md`](LESSONS.md) and `benchmarks/`.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 263 | [The question a newcomer asks most is the one table that is empty](tasks/263_the-question-a-newcomer-asks-most-is-the-one-table-that-is-empty.md) | Onboarding | todo | 114, 210 |
| 269 | [Twelve graph nouns where a reader has seven questions](tasks/269_twelve-graph-nouns-where-a-reader-has-seven-questions.md) | Onboarding | todo | 263, 121, 210, 139 |

**What still governs open work:**

- **24 tools** on the MCP surface (`main.TOOL_NAMES`), pinned by
  `tests/test_documented_tool_count.py`.
- **Every `deferred` ticket holds its own gate** — 074, 098 and 141 each state theirs, and 141 is at
  n = 0; do not queue one without reading it. Auto *reading orders* stay unscheduled
  ([121](benchmarks/121_onboarding-question-class.md)).
- **Roll-out is the binding constraint** — five rounds standing. 244 shipped the code-shaped face;
  [266](tasks/266_the-artifact-that-would-make-an-agent-ask-is-in-our-repo-not-theirs.md) now carries
  the rest, and 244 left one instance open (`find_mirror_subtrees`, 115).

## Phase 2 — More languages (§19 pivot, 2026-08-04)

**Adapters #2–#4 have all landed**; which ticket carried which tier is
[`ADAPTER_PLAYBOOK.md`](ADAPTER_PLAYBOOK.md) §1. C#/.NET stays deferred (2026-08-04, §19); the
language *order* is unchanged (§18.2).

| # | Task | Milestone | Status | Depends on |
|---|---|---|---|---|
| 021 | [C#/.NET adapter](tasks/021_csharp-adapter.md) | M9 | deferred | 019 |
| 026 | [Inverse Docker path rebase (adapter #2)](tasks/026_docker-inverse-path-rebase.md) | M7 | deferred | 008, 019 |

## Landed phases — nothing open

Phase 1 (core + PHP), Phase 1.5 (agent-first PHP depth) and Phase 1.5b (large-monorepo validation
hardening) are closed. Two decisions from them still bind and are recorded in §19, not here: editing
tools are permanently out, and tool *consolidation* was measured and rejected. The round-3 open note is half closed: round 18 did
observe whole-tree `grep` timing out in the anchor repo; the "~650×" figure still has no evidence.

## Follow-ups (not yet ticketed)

One line each, with the pointer that holds the detail. Nothing here is scheduled.

- **PSR-4 / autoload-aware include resolution**, with PSR-0 duplicate-name disambiguation — [042](tasks/042_tokens-to-answer-sample-tier.md).
- **Tokens-to-answer measures cost, not information** — 046 moved the ratio 0.02 % while doubling the distinct answers. Wants a second axis before it judges a retrieval change.
- **Parser-OOM size cap (optional)** — multi-MB generated files exhaust the PHP parser (already soft-failed/restarted in `indexer.py`); a byte-cap pre-skip (`CA_MAX_FILE_BYTES`) would avoid ~30 restart cycles. Log skips; no silent truncation.
- **258's anchor-scale figures were never taken** — AC1 (the edge-count drop on the anchor index) and AC5 (the query cost of the proximity expansion at that scale) shipped E1 on fixture evidence. The ticket makes the expensive case convert to **build-time ranking**, so that measurement is the decision, not a confirmation — [258](tasks/258_the-graph-stores-the-cartesian-product-of-call-site-and-same-named-symbol.md).
- **Docker images are never built by CI** — `docker/Dockerfile` can rot (`Dockerfile.runtime` is built inside `pytest`). Honest shape: one job building both. Survives the unbillable-Actions arrangement AGENTS.md records, which also means every gate is a human step.

## Conventions
- Keep an **open** task's `status` in this table **and** in its frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
- **A task reaching `done` gets its spend row in [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) (R7.2) and its
  row here is removed in the same commit** — the ledger row carries it from then on.
- Landed narrative belongs in [PLAN §19](PLAN.md#19-project-context--decision-log) or
  [`LESSONS.md`](LESSONS.md), not here; a ticketed follow-up leaves the
  [Follow-ups](#follow-ups-not-yet-ticketed) list. This is R7.6, with a ceiling in
  `tests/test_doc_size_budget.py`.
