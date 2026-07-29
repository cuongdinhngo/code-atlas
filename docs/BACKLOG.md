# Backlog — code-atlas

Task tracker. One file per task in [`docs/tasks/`](tasks/) (`NNN_slug.md`). Source of truth for scope
is [`PLAN.md`](PLAN.md).

**Status legend:** `todo` · `in-progress` · `blocked` · `done`
**Ship point:** task 014 (search/read/outline) = first daily-usable release.

## Phase 1 — Core + PHP (make it work)

| # | Task | Milestone | Status | Depends on |
|---|---|---|---|---|
| 001 | [Project scaffold & tooling](tasks/001_project-scaffold.md) | Setup | done | — |
| 002 | [Contract — schema, version, validation](tasks/002_contract-schema.md) | Contract | todo | 001 |
| 003 | [Config (CA_*) & ignore rules](tasks/003_config-and-ignore.md) | Setup | todo | 001 |
| 004 | [SQLite store & schema](tasks/004_sqlite-store.md) | Core | todo | 001, 002 |
| 005 | [Adapter protocol & subprocess driver](tasks/005_adapter-protocol.md) | Core | todo | 002 |
| 006 | [PHP adapter spike](tasks/006_php-adapter-spike.md) | M0 | todo | 002 |
| 007 | [PHP adapter — full coverage & server mode](tasks/007_php-adapter-visitor.md) | M0 | todo | 006, 005 |
| 008 | [PHP runtime invocation (host / Docker)](tasks/008_php-runtime-modes.md) | M1 | todo | 005, 007 |
| 009 | [Full build indexer + workers](tasks/009_full-build-indexer.md) | M1 | todo | 004, 005, 007 |
| 010 | [MCP server + status/build tools](tasks/010_index-status-and-build-tools.md) | M1 | todo | 009 |
| 011 | [Cross-file edge resolver](tasks/011_resolver.md) | M2 | todo | 009 |
| 012 | [Contract-conformance & PHP coverage tests](tasks/012_contract-conformance-tests.md) | M2 | todo | 007, 002 |
| 013 | [Nav tools — callers / refs / impls](tasks/013_nav-tools.md) | M2 | todo | 011, 010 |
| 014 | [Search / read / outline + FTS **(ship)**](tasks/014_search-read-outline.md) | M3 | todo | 010, 004 |
| 015 | [Full PHP coverage + scale to 112k](tasks/015_php-full-coverage-and-scale.md) | M4 | todo | 013, 014, 008 |
| 016 | [Incremental update via git diff](tasks/016_incremental-git.md) | M5 | todo | 011, 009 |
| 017 | [Impact engine + tool + prompts](tasks/017_impact-engine.md) | M6 | todo | 013, 016 |
| 018 | [Cross-repo validation](tasks/018_cross-repo-validation.md) | M4 | todo | 015 |

## Phase 2 — More languages

| # | Task | Milestone | Status | Depends on |
|---|---|---|---|---|
| 019 | [TypeScript/JavaScript adapter + contract v2](tasks/019_typescript-adapter.md) | M7 | todo | 012, 011 |
| 020 | [Python adapter](tasks/020_python-adapter.md) | M8 | todo | 019 |
| 021 | [C#/.NET adapter](tasks/021_csharp-adapter.md) | M9 | todo | 019 |

## Phase 3 — Onboarding

| # | Task | Milestone | Status | Depends on |
|---|---|---|---|---|
| 022 | [Architecture overview + layers](tasks/022_architecture-overview.md) | M10 | todo | 014 |
| 023 | [Guided tour + markdown docs](tasks/023_guided-tour-and-docs.md) | M11 | todo | 022 |

## Token usage

Token spend per task, recorded before its PR is opened (see the "Token usage on PR" rule in
[`CLAUDE.md`](../CLAUDE.md)). The authoritative per-dispatch breakdown lives in each task's working-doc
cost ledger (`tasks/NNN_slug.work.md`); this table is the roll-up.

| # | Task | Tokens | PR |
|---|---|---|---|
| 001 | Project scaffold & tooling | 113.6k dispatch (reviewer 70.9k + challenger 42.7k); main-loop unmeasured (see `rtk gain`) | [#2](https://github.com/cuongdinhngo/code-atlas/pull/2) |

## Suggested order

Critical path to first release: **001 → 002 → 004/005 → 006 → 007 → 009 → 010 → 011 → 013 → 014 (ship)**.
003 (config) and 008 (runtime) slot in before 009. 012 (tests) runs alongside 007+. Then 015–018 harden
PHP, 019–021 add languages, 022–023 add onboarding.

## Conventions
- Keep task `status` in this table **and** in each task file's frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
