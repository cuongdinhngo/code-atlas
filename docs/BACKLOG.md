# Backlog — code-atlas

Task tracker. One file per task in [`docs/tasks/`](tasks/) (`NNN_slug.md`). Source of truth for scope
is [`PLAN.md`](PLAN.md).

**Status legend:** `todo` · `in-progress` · `blocked` · `deferred` · `done`
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
| 008 | [PHP runtime invocation (host / Docker)](tasks/008_php-runtime-modes.md) | M1 | done | 005, 007 |
| 009 | [Full build indexer + workers](tasks/009_full-build-indexer.md) | M1 | done | 004, 005, 007 |
| 010 | [MCP server + status/build tools](tasks/010_index-status-and-build-tools.md) | M1 | done | 009 |
| 011 | [Cross-file edge resolver](tasks/011_resolver.md) | M2 | done | 009 |
| 012 | [Contract-conformance & PHP coverage tests](tasks/012_contract-conformance-tests.md) | M2 | done | 025, 002 |
| 013 | [Nav tools — callers / refs / impls](tasks/013_nav-tools.md) | M2 | done | 011, 010 |
| 014 | [Search / read / outline + FTS **(ship)**](tasks/014_search-read-outline.md) | M3 | done | 010, 004 |
| 015 | [Full PHP coverage + scale to 112k](tasks/015_php-full-coverage-and-scale.md) | M4 | done | 013, 014, 008 |
| 016 | [Incremental update via git diff](tasks/016_incremental-git.md) | M5 | done | 011, 009 |
| 017 | [Impact engine + tool + prompts](tasks/017_impact-engine.md) | M6 | done | 013, 016 |
| 018 | [Cross-repo validation](tasks/018_cross-repo-validation.md) | M4 | done | 015 |
| 027 | [Batch resolver candidate lookups](tasks/027_resolver-batched-lookups.md) | M4 | done | 011, 015 |
| 024 | [CI hardening](tasks/024_ci-hardening.md) | Setup | done | 001 |
| 025 | [PHP adapter — full 8.5 grammar coverage](tasks/025_php-adapter-grammar.md) | M0 | done | 007 |
| 028 | [Index-health metrics in get_index_status](tasks/028_index-health-metrics.md) | M4 | done | 010, 011 |
| 029 | [PHP adapter — $this/self/static/parent receiver resolution](tasks/029_php-receiver-resolution.md) | M2 | done | 011, 025 |
| 030 | [Alias & literal-indirection edges](tasks/030_alias-indirection-edges.md) | M2 | done | 002, 011, 025 |
| 031 | [Reachability / orphan detection](tasks/031_reachability-orphans.md) | M6 | done | 003, 011, 013 |

## Phase 1.5 — Agent-first PHP depth (active — §19 pivot, 2026-08-04)

The current priority. Consumer = an AI agent in a terminal; baseline = grep+`Read`. Planned, **not
yet ticketed** (no `tasks/NNN` files yet — each is scaffolded via the mango lifecycle when picked
up). Source: [`FEEDBACK.md`](FEEDBACK.md).

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 032 | Resolve license (`LICENSE` + README) | Adoption | done | — |
| 033 | Reason codes + `total_count` on `find_*`/`search` (empty ≠ unknown) | Agent-trust | done | 013, 014 |
| 034 | Tokens-to-answer benchmark harness (vs grep+`Read`) | Measure | done | 014, 018 |
| 035 | Read-through freshness — inline reparse on hash drift | Freshness | done | 009, 011 |
| 036 | Claude Code Edit/Write index-poke hook | Distribution | done | 016, 035 |
| 037 | Compound nav responses (call-site line) + consolidation A/B | Agent-fit | todo | 013, 034 |
| 038 | `explain_path(from, to)` control-flow path tool | Task-level | done | 017, 031 |
| 039 | Vendor stub index (declarations-only) | Framework | todo | 009, 011 |
| 040 | Framework indirection as data (rules file outside `adapters/`) | Framework | todo | 039, 030 |
| 041 | Legacy/framework hardening — encoding, `.blade.php` ignore, extra extensions | Robustness | todo | 009 |
| 042 | Tokens-to-answer sample tier — populate pinned public repos (ratio ≫ 1) | Measure | todo | 034, 018 |

**Order:** 032 → 033 → 034 → (035, 036) → 037 → 038 → 039 → 040; 041 any time; **042 after 034**
(needs a PHP+clone env — proves the value claim the fixtures can't). **034 gates 037/039/040** — it
decides whether they earned their cost. **Editing tools are permanently out**
(ceded to native `Edit`, §1/§19). Tool *consolidation* (`find_relations`) is held as an A/B behind
034, not assumed.

## Phase 2 — More languages (deferred — §19 pivot, 2026-08-04)

**Deferred, not cancelled** (human-ratified 2026-08-04). Breadth waits until the PHP agent-loop
(Phase 1.5) is complete — depth before breadth. PHP is the focus because the private **anchor-repo**
monorepo is the anchor for testing and evaluation (§19). The language *order* is unchanged (§18.2).

| # | Task | Milestone | Status | Depends on |
|---|---|---|---|---|
| 019 | [TypeScript/JavaScript adapter + contract v2](tasks/019_typescript-adapter.md) | M7 | deferred | 012, 011 |
| 020 | [Python adapter](tasks/020_python-adapter.md) | M8 | deferred | 019 |
| 021 | [C#/.NET adapter](tasks/021_csharp-adapter.md) | M9 | deferred | 019 |
| 026 | [Inverse Docker path rebase (adapter #2)](tasks/026_docker-inverse-path-rebase.md) | M7 | deferred | 008, 019 |

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
| 008 | PHP runtime invocation (host / Docker) | **4 dispatch** — refine exposure-checker + analysis extractor + review `mango:reviewer` + `mango:challenger`; all token cells **`unmeasured (blocking retrieval)`**. Review round 2 verify-only in the main loop (proving-test rename). Phases 2–3 and 5 dispatched **nothing**. **Main-loop spend is unmeasured**, as for 004–007 and 009–011 | [#20](https://github.com/cuongdinhngo/code-atlas/pull/20) |
| 025 | PHP adapter — full 8.5 grammar coverage | **4 dispatch** — analysis extractor + review `mango:reviewer` + `mango:challenger` in round 1, all **`unmeasured (blocking retrieval)`**; plus a round-3 ticket-blind `mango:challenger` re-review of the open PR at **112.6k** (32 tool uses / 489 s), the only measured cell in this row. That re-review found the `:col` drift, and the PHPStan follow-up it triggered (attribute `extra` bug, R6.6, CI) ran **entirely on the main model with 0 dispatch**. Review rounds 2 and 4 were verify-only in the main loop. Phases 0/2/3/5 dispatched **nothing**. **Main-loop spend is unmeasured**, as for 004–011 and 008 | [#21](https://github.com/cuongdinhngo/code-atlas/pull/21) |
| 012 | Contract-conformance & PHP coverage tests | **4 dispatch** — refine exposure-checker + analysis extractor + review `mango:reviewer` + `mango:challenger`; all token cells **`unmeasured (blocking retrieval)`**. Phases 2–3 and 5 dispatched **nothing**. **Main-loop spend is unmeasured**, as for 004–011 and 008 | [#22](https://github.com/cuongdinhngo/code-atlas/pull/22) |
| 013 | Nav tools — callers / refs / impls | **3 dispatch** — refine exposure-checker + review `mango:reviewer` + `mango:challenger`; all token cells **`unmeasured (blocking retrieval)`**. Phases 1–3 and 5 dispatched **nothing**. **Main-loop spend is unmeasured**, as for 004–012 and 008 | [#23](https://github.com/cuongdinhngo/code-atlas/pull/23) |
| 014 | Search / read / outline + FTS **(ship)** | **3 dispatch** — refine exposure-checker + review `mango:reviewer` + `mango:challenger`; all token cells **`unmeasured (blocking retrieval)`**. Phases 1–3 dispatched **nothing** on the main model (design/execute). **Main-loop spend is unmeasured**, as for 004–013 | [#24](https://github.com/cuongdinhngo/code-atlas/pull/24) |
| 015 | Full PHP coverage + scale to 112k | **3 dispatch** — refine exposure-checker + review `mango:reviewer` + `mango:challenger`; all token cells **`unmeasured (host does not surface usage)`**. Phases 1–3 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–014 | [#25](https://github.com/cuongdinhngo/code-atlas/pull/25) |
| 016 | Incremental update via git diff | **4 dispatch** — refine exposure-checker + review `mango:reviewer` (×2) + `mango:challenger`; all token cells **`unmeasured (host does not surface usage)`**. Phases 1–3 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–015 | [#26](https://github.com/cuongdinhngo/code-atlas/pull/26) |
| 017 | Impact engine + tool + prompts | **6 dispatch** — refine exposure-checker + review reviewer (×3) + challenger (×2); all token cells **`unmeasured (host does not surface usage)`**. Phases 1–3 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–016 | [#27](https://github.com/cuongdinhngo/code-atlas/pull/27) |
| 018 | Cross-repo validation | **3 dispatch** — refine exposure-checker + review `mango:reviewer` + `mango:challenger`; all token cells **`unmeasured (host does not surface usage)`**. Phases 1–3 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–017 | [#28](https://github.com/cuongdinhngo/code-atlas/pull/28) |
| 027 | Batch resolver candidate lookups | **4 dispatch** — refine exposure-checker + review `mango:reviewer` (×2) + `mango:challenger`; all token cells **`unmeasured (host does not surface usage)`**. Phases 1–3 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–018 | [#30](https://github.com/cuongdinhngo/code-atlas/pull/30) |
| 028 | Index-health metrics in get_index_status | **2 dispatch** — review `mango:reviewer` + `mango:challenger`; both token cells **`unmeasured (host does not surface usage)`**. Refine skipped (0 unresolved); phases 1–3 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–027 | [#31](https://github.com/cuongdinhngo/code-atlas/pull/31) |
| 029 | PHP adapter — $this/self/static/parent receiver resolution | **5 dispatch** — refine exposure-checker + review `mango:reviewer` (×2) + `mango:challenger` (×2); all token cells **`unmeasured (host does not surface usage)`**. Phases 1–3 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–028 | [#32](https://github.com/cuongdinhngo/code-atlas/pull/32) |
| 030 | Alias & literal-indirection edges (contract v2) | **5 dispatch** — refine exposure-checker + review `mango:reviewer` (×2) + `mango:challenger` (×2); all token cells **`unmeasured (host does not surface usage)`**. Phases 1–3 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–029 | [#33](https://github.com/cuongdinhngo/code-atlas/pull/33) |
| 031 | Reachability / orphan detection | **3 dispatch** — refine exposure-checker + review `mango:reviewer` + `mango:challenger`; all token cells **`unmeasured (host does not surface usage)`**. Phases 1–3 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–030 | [#34](https://github.com/cuongdinhngo/code-atlas/pull/34) |
| 032 | Resolve license (`LICENSE` + README) | **0 dispatch** — no subagent ran; direct license/metadata change on the main model. Main-loop spend unmeasured (host does not surface per-task usage), as for 024 | [#36](https://github.com/cuongdinhngo/code-atlas/pull/36) |
| 033 | Reason codes + `total_count` on `find_*`/`search` (empty ≠ unknown) | **3 dispatch** — refine exposure-checker + review `mango:reviewer` + `mango:challenger`; all token cells **`unmeasured (blocking retrieval)`**. Phases 1–3 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–032 | [#40](https://github.com/cuongdinhngo/code-atlas/pull/40) |
| 034 | Tokens-to-answer benchmark harness (vs grep+`Read`) | **0 dispatch** — no subagent ran; harness + fixture questions + gate tests authored on the main model. Main-loop spend unmeasured (host does not surface per-task usage), as for 024/032 | [#37](https://github.com/cuongdinhngo/code-atlas/pull/37) |
| 035 | Read-through freshness — inline reparse on hash drift | **4 dispatch** — refine exposure-checker + review `mango:reviewer` (×2) + `mango:challenger`; all token cells **`unmeasured (blocking retrieval)`**. Phases 1–3 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–034 | [#41](https://github.com/cuongdinhngo/code-atlas/pull/41) |
| 036 | Claude Code Edit/Write index-poke hook | **4 dispatch** — refine exposure-checker + review `mango:reviewer` (×2) + `mango:challenger`; all token cells **`unmeasured (blocking retrieval)`**. Phases 1–3 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–035 | [#42](https://github.com/cuongdinhngo/code-atlas/pull/42) |
| 038 | `explain_path(from, to)` control-flow path tool | **4 dispatch** — refine exposure-checker + analysis extractor + review `mango:reviewer` + `mango:challenger`; all token cells **`unmeasured (blocking retrieval)`**. Phases 2–3 and 5 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–036 | _pending PR_ |

## Follow-ups (not yet ticketed)

- Resolver: link `IMPORTS` (`target_raw` is already an FQN) so `find_references` sees `use`
  statements — filed from [PR #23](https://github.com/cuongdinhngo/code-atlas/pull/23) review.
- **External-review batch (PHP-general, anchor-repo is only the stress test):** the Top-3 and one
  second-tier item are now ticketed — [028](tasks/028_index-health-metrics.md) (health signal),
  [029](tasks/029_php-receiver-resolution.md) (receiver resolution),
  [030](tasks/030_alias-indirection-edges.md) (alias/indirection, contract bump),
  [031](tasks/031_reachability-orphans.md) (reachability/orphans). Suggested order **028 → 029 → 030
  → 031**: 028 measures whether 029/030 help; 031 needs 029's resolved graph or it reports false
  orphans. Still un-ticketed from that review: duplicate-name disambiguation across PSR-0 roots, and
  PSR-4/autoload-aware include resolution.
- **015 AC2 operator run:** land a real `CODE_ATLAS_SCALE_SAMPLE` timing artifact (elapsed +
  `peak_rss_*`) against the ~112k checkout — deferred from [PR #25](https://github.com/cuongdinhngo/code-atlas/pull/25)
  (D1). Folded into [018](tasks/018_cross-repo-validation.md) as optional A4 (`CODE_ATLAS_SCALE_SAMPLE`
  set → `scale_full_build`; unset → skip). Still needs an operator machine with the private checkout.
- **018 construct gaps:** any cross-repo misses → fill the gap log in
  [`runbooks/cross-repo-validation.md`](runbooks/cross-repo-validation.md) and feed task 007 / 025.
- ~~**015 resolver N+1 reads**~~ — ticketed as [027](tasks/027_resolver-batched-lookups.md). Land it
  **before** the D1/018 scale baseline above, or that baseline measures the read path 027 removes.
## Suggested order

Critical path to first release: **001 → 002 → 004/005 → 006 → 007 → 009 → 010 → 011 → 013 → 014 (ship)**.
010 landed the MCP server itself, so every later tool is a registration in `main.build_server` plus one
module under `code_atlas/tools/` — 011 and 014 no longer carry any server work.
003 (config) landed before 009. **008 (runtime) did not, and did not need to** — 009 drives a host
adapter through `CA_<LANG>_CMD`, so 008 is now only the Docker path-mapping mode and blocks nothing
on the path to 014. **025 (grammar coverage) is off the critical path** — it was split out of 007 so
the protocol could unblock 008/009 first — and 012 (tests) waits on 025. 024 (CI) is independent and
can land any time. Then 015–018 harden PHP. **The active track is now Phase 1.5 (032–041, agent-first
PHP depth, §19); 019–021 language breadth and 022–023 onboarding are deferred behind it.**
**027 sits between 015 and 018**: it changes the resolver read path the 018 scale baseline would
otherwise measure, so it lands first.

## Conventions
- Keep task `status` in this table **and** in each task file's frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
