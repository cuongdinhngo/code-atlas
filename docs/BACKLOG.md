# Backlog — code-atlas

Task tracker for **phase 2**. One file per task in [`docs/tasks/`](tasks/) (`NNN_slug.md`). Source of
truth for scope is [`PLAN.md`](PLAN.md); the durable decision log is
[PLAN §19](PLAN.md#19-project-context--decision-log) and per-task lessons are in
[`LESSONS.md`](LESSONS.md). This file tracks *what is open*; each ticket's cost is one row in
[`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) (R7.2) — narrative rationale lives in those three.

**Phase 1 — the pre-public build, tasks 001–342 — closed 2026-09-27.** What it delivered is
[PLAN §15](PLAN.md#15-milestones--what-phase-1-delivered). Its done task files, token ledger and
lessons were archived out of the repo, so a task number cited in these docs may have no file here;
the five open tasks below carried over, and new tasks continue from **343**. What stays is what you
read to choose the next ticket: the finding, not the slug.

**Status legend:** `todo` · `in-progress` · `blocked` · `deferred` · `done`

## Open work — Pillar 1 · Graph

Resolved relationships for the agent, and the honesty of the payload that carries them
([PLAN §1](PLAN.md#1-goals--non-goals)). The `Theme` column is unchanged.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 098 | [Should the graph hold "this file is a copy/port of that one"? — evidence-gated](tasks/098_correspondence-relation-seam.md) | Coverage | deferred | 030, 011, 003 |
| 141 | ["Can this module be split out?" — the cut edges and the cycles that block it — evidence-gated](tasks/141_extractability-cut-edges-and-the-cycles-that-block-it.md) | Coverage | deferred | 120, 087, 140 |
| 200 | [The remaining recognition measurement is AC5 on today's channels](tasks/200_the-recognition-map-is-a-prompt-no-agent-can-read.md) | Adoption | blocked | 081, 097, 036, 099, 260, 266, 268 |

## Open work — Pillar 2 · Onboarding

The rendering of what the code actually is, for a human supervising an agent or presenting the
project ([PLAN §1](PLAN.md#1-goals--non-goals)). Same graph, no second pipeline.
M10–M12 have all landed; their decisions live in
[PLAN §19](PLAN.md#19-project-context--decision-log) and `benchmarks/`.

*Nothing open.*

**What still governs open work:** the surface has **24 tools** (`main.TOOL_NAMES`), count-pinned by
tests.
- **Every `deferred` ticket holds its own gate** — 098 and 141 each state theirs, and 141 is at
  n = 0; do not queue one without reading it. Auto *reading orders* stay unscheduled
  ([121](benchmarks/121_onboarding-question-class.md)).

## More languages (§19 pivot, 2026-08-04)

**Adapters #2–#4 have all landed**; which ticket carried which tier is
[`ADAPTER_PLAYBOOK.md`](ADAPTER_PLAYBOOK.md) §1. C#/.NET stays deferred (2026-08-04, §19); the
language *order* is unchanged (§18.2).

| # | Task | Milestone | Status | Depends on |
|---|---|---|---|---|
| 021 | [C#/.NET adapter](tasks/021_csharp-adapter.md) | M9 | deferred | 019 |
| 026 | [Inverse Docker path rebase (adapter #2)](tasks/026_docker-inverse-path-rebase.md) | M7 | deferred | 008, 019 |

## Follow-ups (not yet ticketed)

One line each, with the pointer that holds the detail. Nothing here is scheduled.

- **PSR-4 / autoload-aware include resolution**, with PSR-0 duplicate-name disambiguation — 042.
- **Tokens-to-answer measures cost, not information** — 046 moved the ratio 0.02 % while doubling the distinct answers. Wants a second axis before it judges a retrieval change.
- **Parser-OOM size cap (optional)** — multi-MB generated files exhaust the PHP parser (already soft-failed/restarted in `indexer.py`); a byte-cap pre-skip (`CA_MAX_FILE_BYTES`) would avoid ~30 restart cycles. Log skips; no silent truncation.
- **258's anchor-scale figures were never taken** — AC1 (the edge-count drop on the anchor index) and AC5 (the query cost of the proximity expansion at that scale) shipped E1 on fixture evidence. The ticket makes the expensive case convert to **build-time ranking**, so that measurement is the decision, not a confirmation — 258.
- **Uptake is gated by deferred delivery and whether `Grep` hurts** — 300.
- **A PHP property is referenced only by a static fetch naming its declaring class** — `$this->x`, `$obj->x` and `self::$x` on an inherited property emit no edge onto it, so `find_references` on it can still answer a confident zero — 336.
- **A separator-normalised `read_symbol` hit ignores `path_prefix`** — `\Foo\bar` re-read as `Foo::bar` returns the body from a file the filter excluded; `find_references`' prefix zero names no `path_excluded` either — 339.
- **Docker images are never built by CI** — `docker/Dockerfile` can rot, and since 323 `gate.sh --docker` runs through it (`Dockerfile.runtime` is built inside `pytest`). Honest shape: one job building both. Survives the unbillable-Actions arrangement AGENTS.md records, which also means every gate is a human step.
- **`host_root` / `container_root` from the project file are unchecked paths** — harmless today
  (`to_adapter_path` only maps repo-relative strings) but ungated, unlike 341's two knobs —
  341.
- **Two symlink residuals 342 left out of scope** — a stub root's files (`collect_stubs`, `os.walk`)
  and the index directory (`.code-atlas/` committed as a link aims SQLite writes) are not yet contained
  — 342.

## Conventions
- Keep an **open** task's `status` in this table **and** in its frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
- **A task reaching `done` gets its spend row in [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) (R7.2) and its
  row here is removed in the same commit** — the ledger row carries it from then on.
- Landed narrative belongs in [PLAN §19](PLAN.md#19-project-context--decision-log) or
  [`LESSONS.md`](LESSONS.md), not here; a ticketed follow-up leaves the
  [Follow-ups](#follow-ups-not-yet-ticketed) list. This is R7.6, with a ceiling in
  `tests/test_doc_size_budget.py`.
