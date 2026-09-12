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
| 251 | [The RESOLVED caller can be off the page: `find_callers` pages alphabetically, tier is a label](tasks/251_the-resolved-caller-can-be-off-the-page.md) | Honesty | todo | 165, 168, 057 |
| 252 | [A class-level reference question costs n+1 calls](tasks/252_a-class-reference-question-costs-n-plus-one-calls.md) | Adoption | todo | 245, 168, 065 |
| 255 | [The honesty predicate is keyed to two PHP-shaped edge kinds, so a Table's 34 unlinked WRITES read as a zero](tasks/255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md) | Honesty | todo | 221, 232, 186, 065 |
| 257 | [The index goes blind at the moment it is most wanted](tasks/257_the-index-goes-blind-at-the-moment-it-is-most-wanted.md) | Adoption | todo | 035, 182, 100 |
| 258 | [The graph stores the cartesian product of call site x same-named symbol — 48.4% of the anchor graph](tasks/258_the-graph-stores-the-cartesian-product-of-call-site-and-same-named-symbol.md) | Honesty | todo | 251, 054, 066, 182 |

## Open work — Pillar 2 · Onboarding

The rendering of what the code actually is, for a human supervising an agent or presenting the
project ([PLAN §1](PLAN.md#1-goals--non-goals)). Same graph, no second pipeline.
M10–M12 have all landed; round narratives live in [`FEEDBACK.md`](FEEDBACK.md),
[PLAN §19](PLAN.md#19-project-context--decision-log), [`LESSONS.md`](LESSONS.md) and `benchmarks/`.

Nothing open — 225 (the sequence view) landed.

**What still governs open work:**

- **24 tools** on the MCP surface (`main.TOOL_NAMES`), pinned by
  `tests/test_documented_tool_count.py`.
- **Every `deferred` ticket holds its own gate** — 074, 098 and 141 each state theirs, and 141 is at
  n = 0; do not queue one without reading it. Auto *reading orders* stay unscheduled
  ([121](benchmarks/121_onboarding-question-class.md)).
- **Roll-out is the binding constraint** — five rounds standing. 244 shipped the code-shaped face
  of it; what remains is not a ticket here and goes to the consumer as a PR. 244's own re-check
  left one instance open: a capability with no tool name (`find_mirror_subtrees`, 115).

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
hardening) are closed. Two decisions from them still bind; both are in §19, not here.
hardening) are closed. Two decisions from them still bind and are recorded in §19, not here: editing
tools are permanently out, and tool *consolidation* was measured and rejected. The round-3 open note is half closed: round 18 did
observe whole-tree `grep` timing out in the anchor repo; the "~650×" figure still has no evidence.

## Follow-ups (not yet ticketed)

One line each, with the pointer that holds the detail. Nothing here is scheduled.

- **PSR-4 / autoload-aware include resolution**, with PSR-0 duplicate-name disambiguation — [042](tasks/042_tokens-to-answer-sample-tier.md).
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
