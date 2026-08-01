# Backlog — code-atlas

Task tracker. One file per task in [`docs/tasks/`](tasks/) (`NNN_slug.md`). Source of truth for scope
is [`PLAN.md`](PLAN.md).

**Status legend:** `todo` · `in-progress` · `blocked` · `done`
**Ship point:** task 014 (search/read/outline) = first daily-usable release.

## Phase 1 — Core + PHP (make it work)

| # | Task | Milestone | Status | Depends on |
|---|---|---|---|---|
| 001 | [Project scaffold & tooling](tasks/001_project-scaffold.md) | Setup | done | — |
| 002 | [Contract — schema, version, validation](tasks/002_contract-schema.md) | Contract | done | 001 |
| 003 | [Config (CA_*) & ignore rules](tasks/003_config-and-ignore.md) | Setup | done | 001 |
| 004 | [SQLite store & schema](tasks/004_sqlite-store.md) | Core | done | 001, 002 |
| 005 | [Adapter protocol & subprocess driver](tasks/005_adapter-protocol.md) | Core | done | 002 |
| 006 | [PHP adapter spike](tasks/006_php-adapter-spike.md) | M0 | done | 002 |
| 007 | [PHP adapter — server mode & streaming](tasks/007_php-adapter-visitor.md) | M0 | done | 006, 005 |
| 008 | [PHP runtime invocation (host / Docker)](tasks/008_php-runtime-modes.md) | M1 | in-progress | 005, 007 |
| 009 | [Full build indexer + workers](tasks/009_full-build-indexer.md) | M1 | done | 004, 005, 007 |
| 010 | [MCP server + status/build tools](tasks/010_index-status-and-build-tools.md) | M1 | done | 009 |
| 011 | [Cross-file edge resolver](tasks/011_resolver.md) | M2 | done | 009 |
| 012 | [Contract-conformance & PHP coverage tests](tasks/012_contract-conformance-tests.md) | M2 | todo | 025, 002 |
| 013 | [Nav tools — callers / refs / impls](tasks/013_nav-tools.md) | M2 | todo | 011, 010 |
| 014 | [Search / read / outline + FTS **(ship)**](tasks/014_search-read-outline.md) | M3 | todo | 010, 004 |
| 015 | [Full PHP coverage + scale to 112k](tasks/015_php-full-coverage-and-scale.md) | M4 | todo | 013, 014, 008 |
| 016 | [Incremental update via git diff](tasks/016_incremental-git.md) | M5 | todo | 011, 009 |
| 017 | [Impact engine + tool + prompts](tasks/017_impact-engine.md) | M6 | todo | 013, 016 |
| 018 | [Cross-repo validation](tasks/018_cross-repo-validation.md) | M4 | todo | 015 |
| 024 | [CI hardening](tasks/024_ci-hardening.md) | Setup | done | 001 |
| 025 | [PHP adapter — full 8.5 grammar coverage](tasks/025_php-adapter-grammar.md) | M0 | todo | 007 |

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
[`AGENTS.md`](../AGENTS.md)). The authoritative per-dispatch breakdown lives in each task's working-doc
cost ledger (`tasks/NNN_slug.work.md`); this table is the roll-up. mango measures **subagent dispatch
only** — when a task dispatches no subagent, its main-loop spend is read from the Claude Code session
transcript and labelled as such, so a `0 dispatch` row is never left standing as if it were the total.

| # | Task | Tokens | PR |
|---|---|---|---|
| 001 | Project scaffold & tooling | 113.6k dispatch (reviewer 70.9k + challenger 42.7k); main-loop unmeasured (see `rtk gain`) | [#2](https://github.com/cuongdinhngo/code-atlas/pull/2) |
| 002 | Contract — schema, version, validation | **689.2k fresh** (239.8k output + 449.3k input) + **27.12M cache reads** over 164 calls; **0 dispatch** (no subagent ran — no fan-out, and review was skipped by user decision). Top output driver: Phase 3 execute (79.6k). Main-loop figures read from the session transcript, not mango's dispatch ledger | [#4](https://github.com/cuongdinhngo/code-atlas/pull/4) |
| 003 | Config (CA_*) & ignore rules | **638.3k fresh** (223.3k output + 415.0k input) + **24.4M cache reads** over 167 calls, from the session transcript; plus **52.4k dispatch** — 1 subagent (ticket-blind challenger; the reviewer was skipped by user decision). The dispatch is 7.6% of fresh spend, so the main loop is the cost driver | [#5](https://github.com/cuongdinhngo/code-atlas/pull/5) |
| 004 | SQLite store & schema | **78.1k dispatch** — 1 subagent (ticket-blind challenger; reviewer skipped by user decision), 27 tool uses / 313 s. **Main-loop spend unmeasured for this task**: mango measures dispatch only, and `rtk gain` reports a global all-time figure (22.8M saved over 4,774 commands) that cannot be attributed to one task — so unlike 002/003 there is no session-transcript figure here, and none is invented | [#7](https://github.com/cuongdinhngo/code-atlas/pull/7) |
| 005 | Adapter protocol & subprocess driver | **181.6k dispatch** — 2 subagents, both in review round 1: `mango:reviewer` 108.9k (38 tool uses / 426 s) + `mango:challenger` 72.7k (27 tool uses / 286 s). Phases 1–3 dispatched **nothing** (no Explore fan-out; 12 read-only spikes did the de-risking on the main model), and review round 2 was verify-only in the main loop, so it dispatched nothing either. **Main-loop spend is unmeasured for this task**, as for 004: mango measures dispatch only, and `rtk gain` reports a global all-time figure that cannot be attributed to one task — so no session-transcript number is invented here | [#10](https://github.com/cuongdinhngo/code-atlas/pull/10) |
| 006 | PHP adapter spike | **73.9k dispatch** — 1 subagent (`mango:challenger`, 34 tool uses / 228 s). The `mango:reviewer` pass was skipped by user instruction, and phases 1–3 dispatched nothing: five read-only spikes on the main model did the de-risking, and the post-review round was verify-only in the main loop. **Main-loop spend is unmeasured**, as for 004 and 005 — mango measures dispatch only, and `rtk gain` reports a global all-time figure that cannot be attributed to one task, so none is invented here | [#13](https://github.com/cuongdinhngo/code-atlas/pull/13) |
| 024 | CI hardening | **0 dispatch** — no subagent ran at any point: the work was an audit of `ci.yml` plus twelve task files, done entirely on the main model, and it did not go through the mango lifecycle, so no working-doc cost ledger exists for it. **Main-loop spend is unmeasured**, as for 004–006. That missing lifecycle is why this row itself was omitted at PR time and added in [#15](https://github.com/cuongdinhngo/code-atlas/pull/15), which also turns the rule into a test | [#14](https://github.com/cuongdinhngo/code-atlas/pull/14) |

| 007 | PHP adapter — server mode & streaming | **111.4k dispatch** — 1 subagent (`mango:challenger`, 41 tool uses / 380 s). The `mango:reviewer` pass was skipped by user instruction. Phases 1–3 and 5 dispatched **nothing**: the analysis inventory, four runtime spikes against the real `SubprocessAdapter`, and five negative-control mutations all ran on the main model. **Main-loop spend is unmeasured**, as for 004–006 and 024 — mango measures dispatch only, and `rtk gain` reports a global all-time figure that cannot be attributed to one task, so none is invented here | [#16](https://github.com/cuongdinhngo/code-atlas/pull/16) |
| 009 | Full build indexer + workers | **96.3k dispatch** — 1 subagent (`mango:challenger`, 30 tool uses / 380 s). The `mango:reviewer` pass was skipped by user instruction, and review round 2 was verify-only in the main loop, so it dispatched nothing. Phases 1–3 and 5 dispatched **nothing**: five runtime spikes against the real store, driver and git, and six negative-control mutation runs, all on the main model. **Main-loop spend is unmeasured**, as for 004–007 and 024 — mango measures dispatch only, and `rtk gain` reports a global all-time figure that cannot be attributed to one task, so none is invented here | [#17](https://github.com/cuongdinhngo/code-atlas/pull/17) |

| 010 | MCP server + status/build tools | **64.6k dispatch** — 1 subagent (`mango:challenger`, 31 tool uses / 284 s), which returned 8/8 requirements met and no code finding. The `mango:reviewer` pass was skipped by user instruction. Phases 1–3 and 5 dispatched **nothing**: four spikes against the real FastMCP runtime (one of which came back false and reshaped the design) and six negative-control mutations all ran on the main model. **Main-loop spend is unmeasured**, as for 004–007, 009 and 024 — mango measures dispatch only, and `rtk gain` reports a global all-time figure that cannot be attributed to one task, so none is invented here | [#18](https://github.com/cuongdinhngo/code-atlas/pull/18) |
| 011 | Cross-file edge resolver | **2 dispatch** — `mango:reviewer` + `mango:challenger` in review round 1; both token cells **`unmeasured (blocking retrieval)`** (Cursor Task returns did not surface a usage block). Round 2 was verify-only in the main loop (Co-authored-by strip). Phases 1–3 and 5 dispatched **nothing**. **Main-loop spend is unmeasured**, as for 004–007, 009 and 010 | [#19](https://github.com/cuongdinhngo/code-atlas/pull/19) |

## Suggested order

Critical path to first release: **001 → 002 → 004/005 → 006 → 007 → 009 → 010 → 011 → 013 → 014 (ship)**.
010 landed the MCP server itself, so every later tool is a registration in `main.build_server` plus one
module under `code_atlas/tools/` — 011 and 014 no longer carry any server work.
003 (config) landed before 009. **008 (runtime) did not, and did not need to** — 009 drives a host
adapter through `CA_<LANG>_CMD`, so 008 is now only the Docker path-mapping mode and blocks nothing
on the path to 014. **025 (grammar coverage) is off the critical path** — it was split out of 007 so
the protocol could unblock 008/009 first — and 012 (tests) waits on 025. 024 (CI) is independent and
can land any time. Then 015–018 harden PHP, 019–021 add languages, 022–023 add onboarding.

## Conventions
- Keep task `status` in this table **and** in each task file's frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
