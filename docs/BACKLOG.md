# Backlog — code-atlas

Task tracker for **phase 2**. One file per task in [`docs/tasks/`](tasks/) (`NNN_slug.md`). Source of
truth for scope is [`PLAN.md`](PLAN.md); the durable decision log is
[PLAN §19](PLAN.md#19-project-context--decision-log) and per-task lessons are in
[`LESSONS.md`](LESSONS.md). This file tracks *what is open*; each ticket's cost is one row in
[`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) (R7.2) — narrative rationale lives in those three.

**Phase 1 — the pre-public build, tasks 001–342 — closed 2026-09-27.** What it delivered is
[PLAN §15](PLAN.md#15-milestones--what-phase-1-delivered). Its done task files, token ledger and
lessons were archived out of the repo, so a task number cited in these docs may have no file here;
the five open tasks below carried over, and new tasks continue from **352**. What stays is what you
read to choose the next ticket: the finding, not the slug.

**Status legend:** `todo` · `in-progress` · `blocked` · `deferred` · `done`

## Open work — Pillar 1 · Graph

Resolved relationships for the agent, and the honesty of the payload that carries them
([PLAN §1](PLAN.md#1-goals--non-goals)). The `Theme` column is unchanged.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 098 | [Should the graph hold "this file is a copy/port of that one"? — evidence-gated](tasks/098_correspondence-relation-seam.md) | Coverage | deferred | 030, 011, 003 |
| 141 | ["Can this module be split out?" — the cut edges and the cycles that block it — evidence-gated](tasks/141_extractability-cut-edges-and-the-cycles-that-block-it.md) | Coverage | deferred | 120, 087, 140 |
| 380 | [BM25 column weights — evidence-gated](tasks/380_search-bm25-column-weights.md) | Retrieval | deferred | 180 |

## Open work — Trust (security)

423 first: later tickets fill its rows.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 423 | [Security standard, conformance-tested](tasks/423_security-standard.md) | Standard | todo | 422 |
| 424 | [CI hardening](tasks/424_ci-hardening.md) | Supply chain | todo | 423 |
| 425 | [Locked, hashed, audited dependencies](tasks/425_dependency-lock-and-audit.md) | Supply chain | todo | 423 |
| 426 | [Non-root, digest-pinned runtime image](tasks/426_container-hardening.md) | Container | todo | 425 |
| 427 | [Pinned installs, hook activation](tasks/427_distribution-pinning.md) | Distribution | todo | 423 |
| 428 | [Tool annotations, closed schemas, surface manifest](tasks/428_tool-surface-manifest.md) | MCP surface | todo | 423 |
| 429 | [Repo text in answers marked as data](tasks/429_untrusted-output-framing.md) | Output | todo | 428 |
| 430 | [Limits, containment, scrubbed env](tasks/430_limits-and-containment.md) | Input | todo | 423 |
| 431 | [Release pipeline with provenance](tasks/431_release-pipeline.md) | Release | todo | 424, 425 |

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
- **258's anchor-scale figures were never taken** — AC1 (the edge-count drop on the anchor index) and AC5 (the query cost of the proximity expansion at that scale) shipped E1 on fixture evidence. The ticket makes the expensive case convert to **build-time ranking**, so that measurement is the decision, not a confirmation — 258.
- **Whether the grep-time nudge changes what an agent does is unmeasured** — 344 and 345 shipped the delivery and the hook; no field run has counted grep-then-index against grep-only since — 300.
- **A PHP property is referenced only by a static fetch naming its declaring class** — `$this->x`, `$obj->x` and `self::$x` on an inherited property emit no edge onto it, so `find_references` on it can still answer a confident zero — 336.
- **A separator-normalised `read_symbol` hit ignores `path_prefix`** — `\Foo\bar` re-read as `Foo::bar` returns the body from a file the filter excluded; `find_references`' prefix zero names no `path_excluded` either — 339.
- **Two field reports 365 did not reproduce** — `read_symbol` on a table answered `subject_ambiguous`
  mid-rebuild, and `find_references` answered `index_stale` during a full rebuild, whose shadowed
  live DB still repairs in 365's tests — 365.
- **`read_symbol`'s held-index parse starts every configured adapter** — a stored suffix→adapter
  map would start one; AC2's 1 s bar is proven on PHP alone — 365.
- **PHP members are case-insensitive, the resolver is not** (`validate()` onto `Validate()` stays
  unlinked — a fixture cause, not matched to the field); an inherited constructor misses its
  subclass's `new` sites — 362.
- **A Python `def` nested in a method is emitted as a class Method**, sharing a member's qname — 367.
- **Onboarding's module facts do not order or count a `View`** (`module_facts._KIND_ORDER`), so a
  view-only SQL module summarises as empty — 402.
- **A host-string `EXEC` matches case-sensitively and never counts its misses** — `exec insert_order`
  misses `Insert_Order` (the casefold pass links writes and column reads, not `EXEC`), a `dbo.py`
  module's function is an exact match, and a procedure in another schema leaves an uncounted
  unresolved edge — 386.
- **`impact_modules` reads as the PR blast-radius tool** — a name-only probe picked it for
  *"a blast-radius sentence I can paste on the PR"*; `impact` and `find_callers` are the answer — 200.
- **The consumer brief names no contract-change occasion** — its first occasion is a rename; a widened
  return contract under the same name is the field 16–30 miss (probe O6) — 200.
- **A column read under `MERGE … USING` or `UPDATE … FROM` is not credited**, and the anchor's column
  questions await a contract-19 rebuild (E1) — 410.
- **`impact` walks no `READS`/`WRITES`**, so a table's blast radius is its seed alone; its readers and
  writers are `find_references`' answer — 414.
- **The PreCompact state line reaches no one** — Claude Code adds no PreCompact stdout to context and
  discards its `systemMessage` (`hooks.md`, read 2026-10-10); the hook still runs there — 381.

## Conventions
- Keep an **open** task's `status` in this table **and** in its frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
- **A task reaching `done` gets its spend row in [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) (R7.2) and its
  row here is removed in the same commit** — the ledger row carries it from then on.
- Landed narrative belongs in [PLAN §19](PLAN.md#19-project-context--decision-log) or
  [`LESSONS.md`](LESSONS.md), not here; a ticketed follow-up leaves the
  [Follow-ups](#follow-ups-not-yet-ticketed) list. This is R7.6, with a ceiling in
  `tests/test_doc_size_budget.py`.
