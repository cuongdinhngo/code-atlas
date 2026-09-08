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
| 200 | [The recognition map is a prompt no model can read; the snippet that reaches one is PHP-only](tasks/200_the-recognition-map-is-a-prompt-no-agent-can-read.md) | Adoption | blocked | 081, 097, 036, 099 |
| 233 | [Python and SQL have no pinned public sample, so no change to either can be shown to move anything](tasks/233_python-and-sql-have-no-pinned-public-sample-so-no-change-to-either-can-be-shown-to-move-anything.md) | Measure | todo | 018, 150, 147, 228 |
| 235 | [The TS adapter has passed every gate that reads a fixture and none that reads a repo](tasks/235_the-typescript-adapter-has-never-been-asked-a-question-in-the-field.md) | Measure | todo | 019, 150, 018, 233 |

## Open work — Pillar 2 · Onboarding

The rendering of what the code actually is, for a human supervising an agent or presenting the
project ([PLAN §1](PLAN.md#1-goals--non-goals)). Same graph, no second pipeline.
M10–M12 have all landed; round narratives live in [`FEEDBACK.md`](FEEDBACK.md),
[PLAN §19](PLAN.md#19-project-context--decision-log), [`LESSONS.md`](LESSONS.md) and `benchmarks/`.

Nothing open — 225 (the sequence view) landed; its spend is one row in
[`TOKEN_LEDGER.md`](TOKEN_LEDGER.md).

**What still governs open work:**

- **24 tools** on the MCP surface (`main.TOOL_NAMES`), pinned by
  `tests/test_documented_tool_count.py` — the count is duplicated on purpose and guarded.
- **Every `deferred` ticket holds its own gate** — 074, 098 and 141 each state theirs, and 141 is at
  n = 0; do not queue one without reading it. Auto *reading orders* stay unscheduled
  ([121](benchmarks/121_onboarding-question-class.md)).
- **Roll-out is the binding constraint and deliberately not a ticket here** — five rounds standing;
  this backlog accepts only code, so it goes to the consumer as a PR.

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
tools are permanently out, and tool *consolidation* was measured and rejected. One open note, **not a code-atlas
defect**: the anchor repo's `CLAUDE.md` asserts `grep` "times out" and costs "~650×" — round 3
observed neither, so it needs evidence or removal.

## Follow-ups (not yet ticketed)

One line each, with the pointer that holds the detail. Nothing here is scheduled.

- **PSR-4 / autoload-aware include resolution**, with PSR-0 duplicate-name disambiguation — [042](tasks/042_tokens-to-answer-sample-tier.md).
- **`max_results` does two unrelated jobs** — returned rows *and* resolver candidate fan-out, so a query knob sets index size — [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4.
- **Tokens-to-answer measures cost, not information** — 046 moved the ratio 0.02 % while doubling the distinct answers. Wants a second axis before it judges a retrieval change.
- **`reachable_from` payload size at `standard`** — bounded by `impact_max_nodes` (500), ~160 KB of JSON. Worth a lower default or `minimal`-by-default; workaround in [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4.
- **Parser-OOM size cap (optional)** — multi-MB generated files exhaust the PHP parser (already soft-failed/restarted in `indexer.py`); a byte-cap pre-skip (`CA_MAX_FILE_BYTES`) would avoid ~30 restart cycles. Log skips; no silent truncation.
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
