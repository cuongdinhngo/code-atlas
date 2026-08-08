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

## Phase 1.5 — Agent-first PHP depth (complete — §19 pivot, 2026-08-04)

Consumer = an AI agent in a terminal; baseline = grep+`Read`. **All tasks 032–042 have landed** (each
was scaffolded via the mango lifecycle when picked up; source: [`FEEDBACK.md`](FEEDBACK.md)). Open
threads from this track that stayed un-ticketed are in [Follow-ups](#follow-ups-not-yet-ticketed).

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 032 | Resolve license (`LICENSE` + README) | Adoption | done | — |
| 033 | Reason codes + `total_count` on `find_*`/`search` (empty ≠ unknown) | Agent-trust | done | 013, 014 |
| 034 | Tokens-to-answer benchmark harness (vs grep+`Read`) | Measure | done | 014, 018 |
| 035 | Read-through freshness — inline reparse on hash drift | Freshness | done | 009, 011 |
| 036 | Claude Code Edit/Write index-poke hook | Distribution | done | 016, 035 |
| 037 | Compound nav responses (call-site line) + consolidation A/B | Agent-fit | done | 013, 034 |
| 038 | `explain_path(from, to)` control-flow path tool | Task-level | done | 017, 031 |
| 039 | Vendor stub index (declarations-only) | Framework | done | 009, 011 |
| 040 | Framework indirection as data (rules file outside `adapters/`) | Framework | done | 039, 030 |
| 041 | Legacy/framework hardening — encoding, `.blade.php` ignore, extra extensions | Robustness | done | 009 |
| 042 | Tokens-to-answer sample tier — populate pinned public repos (ratio ≫ 1) | Measure | done | 034, 018 |

**Order:** 032 → 033 → 034 → (035, 036) → 037 → 038 → 039 → 040; 041 any time; **042 after 034**
(needs a PHP+clone env — proves the value claim the fixtures can't). **034 gates 037/039/040** — it
decides whether they earned their cost. **Editing tools are permanently out**
(ceded to native `Edit`, §1/§19). Tool *consolidation* (`find_relations`) is held as an A/B behind
034, not assumed.

## Phase 1.5b — Large-monorepo validation hardening

Surfaced by a full-build validation against a **large private PHP monorepo** (~40k PHP files, PHP 8.5,
Docker adapter). The wiring worked (39.9k/40.1k parsed); the run exposed one build-aborting robustness
gap that fixtures never hit.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 043 | [Duplicate-declaration resilience — repeated `qualified_name` must not abort the build](tasks/043_duplicate-decl-resilience.md) | Robustness | done | 004, 009 |
| 044 | [Onboarding runbook — installing code-atlas on a large legacy repo](tasks/044_onboarding-runbook.md) | Adoption | done | 014, 039, 043 |
| 045 | [Tokens-to-answer — measure against a local repo with a pre-built index](tasks/045_tokens-to-answer-local-repo.md) | Measure | done | 034, 042 |
| 046 | [Resolver — dedupe candidates by `qualified_name` (kill duplicate edges, stop the false downgrade)](tasks/046_resolver-qname-candidate-dedupe.md) | Robustness | done | 011, 027, 043 |
| 047 | [Staleness must reflect the index, not the working tree](tasks/047_staleness-scoped-to-indexed-files.md) | Freshness | done | 028, 035, 016 |
| 048 | [`edge_health` returns two different fields both meaning "resolved"](tasks/048_edge-health-resolved-ambiguity.md) | Agent-trust | done | 028 |
| 049 | [Select call sites by argument shape (design-first)](tasks/049_call-site-argument-selectivity.md) | Agent-fit | done | 013, 037, 002 |
| 050 | [A schema-version mismatch is direction-blind — one message for two opposite situations](tasks/050_schema-version-mismatch-recovery.md) | Robustness | done | 010, 016 |
| 051 | [`BuildReport.edges` counts what the adapters emitted, not what the build wrote](tasks/051_build-report-edge-undercount.md) | Agent-trust | done | 009, 011, 028 |
| 052 | [Where does a no-op incremental build spend 62 seconds?](tasks/052_incremental-noop-cost.md) | Freshness | todo | 016, 047 |
| 053 | [Nothing refreshes the index when the repo changes outside the agent's editor](tasks/053_refresh-on-checkout-hook.md) | Freshness | todo | 052, 036, 016 |
| 054 | [`find_callers` reports `total_count: 0` for a method that has callers](tasks/054_bare-name-callers-silent-drop.md) | Agent-trust | todo | 011, 013, 046 |
| 055 | [Nothing measures what the tools fail to find — a recall gate above the cost metric](tasks/055_recall-benchmark.md) | Measure | done | 034, 045 |
| 056 | [An unknown filter value returns an empty result instead of an error](tasks/056_filter-values-fail-loud.md) | Agent-trust | todo | 014, 033 |
| 057 | [A large answer cannot be enumerated, so `total_count` cannot be audited](tasks/057_answer-pagination.md) | Agent-trust | todo | 013, 014, 033 |
| 058 | [`parse_failures: 29` — nobody can find out which 29 files the index cannot see](tasks/058_list-parse-failures.md) | Agent-trust | todo | 009, 028 |
| 059 | [The handler → template data-bag edge is unmodelled](tasks/059_view-databag-edge.md) | Coverage | done | 030, 040 |
| 060 | [An incremental run reports deltas under the field names a full build uses for totals](tasks/060_build-report-scale-naming.md) | Agent-trust | todo | 051 |
| 061 | [Every response carries fields that earn nothing](tasks/061_payload-weight.md) | Cost | todo | 010, 014, 033 |
| 062 | [Producer-side view data-bag edges — rules + enrichment](tasks/062_view-databag-producer.md) | Coverage | todo | 030, 040, 059 |

**047–049 come from the first external field session** — an agent in the anchor repo used the server for
real work and filled in a retro (`v0.1.0`, commit `e117b47`, round 1). Its headline finding was **zero
graph queries in a multi-hour session**: the defect it was fixing lived in string-keyed data flow between
controllers and templates, which the index does not model, so the tool had no opportunity to pay for
itself. Read 047–049 as what that session *could* observe, not as a verdict on the graph — §4 of the retro
labels itself "no evidence, not a clean bill of health". Order: **048 → 047 → 049** (048 is a rename with
a fixed blast radius; 047 is small and removes a false signal agents are being told to act on; 049 needs
measurement before it needs code).

**050 came out of round 2, the same day 049 merged.** A field session hit
`database schema version '3' is not '2'` — its server process predated the v3 merge — read it as a
corrupt index, and spent the rest of the session on narrow `grep`. The index was fine. The error text
told it to rebuild, which in that direction would have destroyed a newer index to write an older one.
**051 came out of verifying the same rebuild.** With the anchor repo freshly indexed under v3, the
build reported 949,808 edges and the table held 1,775,812 — the resolver's sibling rows are inserted
after the tally is taken, so the number an agent reads right after a build sits 46% below the graph it
just made. Not found by a session using the tool, but by checking a number against the thing it claims
to describe.

The first round found the graph had no opportunity to pay for itself; this one found the graph
unreachable for a reason that was never about the graph.

**054–061 come from field retro round 2**, the first session that actually exercised the graph — seven
of thirteen tools, ~23 hand-checked results. Its headline was three ways to receive an empty result that
reads as proof of absence, one of which reported no callers for a method with six live call sites.
**Read them in tiers, and the tiers are the point** (priority set 2026-08-07: *correctness is a gate,
cost is the win*):

- **Tier 1 — find the right thing.** **059 decided Option 1** (producer-side only;
  [PLAN §19](PLAN.md#19-project-context--decision-log)); **062 inherits its tier-1 head slot** — the
  founding-premise reorder's reasons (relation not location, two field sessions, unanswered by grep or
  LSP) apply to the implementation, not the decision. Then **055**, still the acceptance criterion for
  the fixes under it, since nothing *in this repo* measures what a tool missed (the benchmark was
  external, hand-graded and n=1 — evidence, not a gate). Then **054** (the false negative, and its Part
  B ships regardless of anything else), **056**, **057**, **058**.
- **Tier 2 — do not lie about the answer.** **060**; and 053's motivation rises here, since a stale
  index is a wrong answer, though it stays gated on 052 for the practical reason that a 62-second hook
  will be deleted by whoever waits for it.
- **Tier 3 — token weight.** **061**, last and deliberately so: the same retro measured code-atlas's
  direct cost at under 1% of a 250–300k-token session, and the 2026-08-08 benchmark put the indexed arm
  at **1.85× the native arm's tokens** across five questions — 0.84× with one outlier question removed.
  Token weight is where neither the loss nor the win lives. Payload size is not the leverage.

Two corrections to the retro's own reading, both found by reading the code afterwards and recorded in
the tickets: 054's cause is **not** missing type inference — the adapter emits the edge and the resolver
drops it at a cap — and 060's "not fixed" full-build disagreement reproduces 051's pre-fix figures
exactly, on a session whose server process predated the fix. The second is re-measured, not assumed, in
060.

**052–053 come from a freshness review, not a field session.** Enumerating what actually keeps an
index current gives four layers — read-through freshness repairs one file per tool call (035), the
poke hook covers files the agent itself edits (036), `build_or_update_index(full=false)` covers
everything git can name, and a full rebuild covers a contract or schema bump. Only the third has no
trigger: `git pull`, a branch switch, a rebase or an edit from another terminal never reach
`Edit`/`Write`, so nothing fires and read-through gives up after one file. Detection is not the gap —
047 made `staleness` reliable — the gap is that acting on it depends on an agent choosing to call
`get_index_status` first, which is exactly the kind of discipline round 1 showed does not hold.
**052 gates 053 deliberately**: a `post-merge` hook that costs the field-measured 62 s is worse than a
stale index, so the number comes before the automation.

## Phase 2 — More languages (deferred — §19 pivot, 2026-08-04)

**Deferred, not cancelled** (human-ratified 2026-08-04). Breadth waits until the PHP agent-loop
(Phase 1.5) is complete — depth before breadth. PHP is the focus because a large private PHP
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
| 037 | Compound nav responses (call-site line) + consolidation A/B | **3 dispatch, all measured — 242.7k total** — review `mango:challenger` **61.9k** (32 tool uses / 336 s) + `mango:reviewer` **106.5k** (42 / 595 s) + `mango:reviewer` round 2 **74.2k** (39 / 433 s), read from their returned `<usage>` blocks. Phases 0–3 dispatched **nothing** (premise check and both A/B measurements ran on the main model). **Main-loop spend is unmeasured**, as for 004–036 | [#43](https://github.com/cuongdinhngo/code-atlas/pull/43) |
| 038 | `explain_path(from, to)` control-flow path tool | **4 dispatch** — refine exposure-checker + analysis extractor + review `mango:reviewer` + `mango:challenger`; all token cells **`unmeasured (blocking retrieval)`**. Phases 2–3 and 5 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–036 | [#44](https://github.com/cuongdinhngo/code-atlas/pull/44) |
| 039 | Vendor stub index (declarations-only) | **5 dispatch** — refine exposure-checker + analysis extractor + review `mango:reviewer` (×2, incl. verify-only resume) + `mango:challenger`; all token cells **`unmeasured (blocking retrieval)`**. Phases 2–3 and 5 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–038 | [#45](https://github.com/cuongdinhngo/code-atlas/pull/45) |
| 040 | Framework indirection as data (rules file outside `adapters/`) | **4 dispatch** — refine exposure-checker + analysis extractor + review `mango:reviewer` + `mango:challenger`; all token cells **`unmeasured (blocking retrieval)`**. Review round 2 verify-only in the main loop. Phases 1–3 and 5 dispatched **nothing** on the main model. **Main-loop spend is unmeasured**, as for 004–039 | [#46](https://github.com/cuongdinhngo/code-atlas/pull/46) |
| 041 | Legacy/framework hardening — encoding, Blade ignore, extra extensions | **4 dispatch** — refine exposure-checker + analysis extractor + review `mango:reviewer` + `mango:challenger`; all token cells **`unmeasured (blocking retrieval)`**. Phases 1–3 and 5 dispatched **nothing**. **Main-loop spend is unmeasured**, as for 004–040 | [#47](https://github.com/cuongdinhngo/code-atlas/pull/47) |
| 042 | Tokens-to-answer sample tier — pinned public repos (ratio ≫ 1) | **2 dispatch, both measured — 134.4k total** — review `mango:reviewer` **85.6k** (22 tool uses / 266 s) + ticket-blind `mango:challenger` **48.8k** (25 / 234 s), read from their returned `<usage>` blocks (both landed as task-notifications). Phases 1–3 dispatched **nothing** — analysis/design/execute (incl. the PHP-env spike, index exploration, and the harness-verified sample run) all ran on the main model. Review round 2 was verify-only in the main loop (no re-dispatch). **Main-loop spend is unmeasured**, as for 004–041 | [#48](https://github.com/cuongdinhngo/code-atlas/pull/48) |
| 043 | Duplicate-declaration resilience — repeated `qualified_name` must not abort the build | **2 dispatch, both measured — 150.7k total** — review round 1 `mango:reviewer` **86.4k** (28 tool uses / 326 s) + ticket-blind `mango:challenger` **64.3k** (28 / 285 s), read from their returned `<usage>` blocks (both dispatched `run_in_background:false`). Phases 1–3 dispatched **nothing** — analysis (incl. the two `IntegrityError`/NULL spikes against the real store), design, and execute all ran on the main model; no verify-only re-review round (Gate 4 was clean on round 1 with a human-approved AC1 coverage-gap exclusion). **Main-loop spend is unmeasured**, as for 004–042 | [#49](https://github.com/cuongdinhngo/code-atlas/pull/49) |
| 044 | Onboarding runbook — installing code-atlas on a large legacy repo | **0 dispatch** — no subagent ran at any point: the work was a real onboarding trial (two full builds, a tool-by-tool verification sweep, an incremental run) plus the write-up, all on the main model, and it did not go through the mango lifecycle, so no working-doc cost ledger exists for it — as for 024, 032 and 034. **Main-loop spend is unmeasured**: mango measures dispatch only, and `rtk gain` reports a global all-time figure that cannot be attributed to one task, so none is invented here | [#50](https://github.com/cuongdinhngo/code-atlas/pull/50) |
| 045 | Tokens-to-answer — local tier against a repo on disk | **0 dispatch** — no subagent ran: the harness read, the `source: local` implementation, the `run_grep_path` memory bound, 13 tests, the stash-and-compare equivalence proof, and the first anchor-repo measurement (ratio 178.3) all ran on the main model, outside the mango lifecycle, so no working-doc cost ledger exists — as for 024, 032, 034 and 044. **Main-loop spend is unmeasured**: mango measures dispatch only, and `rtk gain` is a global all-time figure that cannot be attributed to one task, so none is invented here | [#51](https://github.com/cuongdinhngo/code-atlas/pull/51) |
| 046 | Resolver — dedupe candidates by `qualified_name` | **0 dispatch** — no subagent ran: the root-cause investigation (index queries proving the duplicate rows identical in every column but `id`, and `store.py`'s partition guarantee), the fix, the three pinned tests corrected, four new tests, and the rebuild measurement all ran on the main model, outside the mango lifecycle, so no working-doc cost ledger exists — as for 024, 032, 034, 044 and 045. **Main-loop spend is unmeasured**, for the same reason | [#52](https://github.com/cuongdinhngo/code-atlas/pull/52) |
| 047 | Staleness scoped to the files the index covers | **0 dispatch** — no subagent ran. Main-loop **217.7k fresh** (73.4k output) + 24.8M cache reads over 114 calls, time-sliced from the session transcript (see the note below the table) | [#56](https://github.com/cuongdinhngo/code-atlas/pull/56) |
| 048 | `edge_health` — rename the ambiguous `resolved` pair | **0 dispatch** — no subagent ran. Main-loop **93.1k fresh** (27.0k output) + 7.7M cache reads over 52 calls, time-sliced from the session transcript | [#55](https://github.com/cuongdinhngo/code-atlas/pull/55) |
| 049 | Select call sites by argument shape (contract v3) | **0 dispatch** — no subagent ran. Main-loop **299.6k fresh** (70.5k output) + 6.6M cache reads over 54 calls for the implementation and the three-branch integration trial. **The Option A/B measurement that decided the design is not in this figure** — it ran before the ticket commits and therefore falls in the unattributed pre-ticket segment, so 049's true cost is higher than the number shown | [#57](https://github.com/cuongdinhngo/code-atlas/pull/57) |
| 050 | Schema-version mismatch — direction and recovery | **0 dispatch** — no subagent ran. Main-loop **426.6k fresh** (108.1k output) + 9.5M cache reads over 122 calls, split into two segments read from the session transcript: **341.1k fresh** (75.1k output, 78 calls) for the fix, its 39 tests and the doc sweep, and **85.5k fresh** (33.0k output, 44 calls) for the diagnosis and the ticket. That second segment also contains the anchor-repo rebuild under v3 and its verification, which belongs to no ticket — so this row overstates 050 by that much | [#58](https://github.com/cuongdinhngo/code-atlas/pull/58) |
| 051 | `BuildReport` — count the rows the run actually wrote | **0 dispatch** — no subagent ran. Main-loop **109.1k fresh** (42.5k output) + 13.3M cache reads over 72 calls for the fix, 7 tests, the before/after cross-repo measurement (six sample builds) and the doc sweep. The ticket's own cost is the separate row below | [#60](https://github.com/cuongdinhngo/code-atlas/pull/60) |
| — | Ticket-writing for 051 | **39.5k fresh** (13.5k output) + 3.3M cache reads over 23 calls, read from the session transcript: re-verifying the counts against the anchor repo's index, tracing the ordering in `indexer.py`/`resolver.py`/`enrichment.py`, and the ticket file. Listed here rather than as a 051 row because 051 is not implemented — the row for the fix lands with its own PR | [#59](https://github.com/cuongdinhngo/code-atlas/pull/59) |
| — | Ticket-writing + the field retro that produced 047–049 | **45.6k fresh** over 28 calls for the three ticket files; a further **1.84M fresh** (503.0k output) + 122.2M cache reads over 576 calls covers the retro form, reading the filled-in retro, the 049 design measurement, and everything else before the first commit. Not attributable to one task, so it is listed here rather than split | — |
| — | Ticket-writing for 052 + 053 | **463.1k fresh** (58.7k output) + 6.7M cache reads over 72 calls, time-sliced from the session transcript between the 051 and 052/053 commits: enumerating the four freshness layers, reading `indexer.py`'s no-op path to locate the unscoped `resolve_edges` hypothesis, and the two ticket files. The two are not separable — they were written as one pass. **Recorded late:** [#54](https://github.com/cuongdinhngo/code-atlas/pull/54) shipped without this row, which the "Token usage on PR" rule requires; this is the correction, not a new measurement | [#54](https://github.com/cuongdinhngo/code-atlas/pull/54) |
| — | Ticket-writing for 054 | **356.0k fresh** (139.5k output) + 17.2M cache reads over 104 calls, time-sliced from the session transcript between the 052/053 and 054 commits: reading the round-2 retro, walking `Visitor.php` → `resolver.py` → `store.py` to establish that the adapter emits the edge and the resolver drops it at `max_candidates`, and the ticket file. **This segment also produced the 055–061 tickets** committed one minute later; the split between them is not recoverable, so the 055–061 row does not double-count it | [#61](https://github.com/cuongdinhngo/code-atlas/pull/61) |
| — | Ticket-writing for 055–061 | **30.2k fresh** (8.0k output) + 2.6M cache reads over 11 calls between the 054 and 055–061 commits — the tail only. The seven ticket files were drafted inside the 054 segment above, so **this row understates them by an unrecoverable amount** and the honest total for 054+055–061 together is the two rows summed: **386.2k fresh over 115 calls** | [#62](https://github.com/cuongdinhngo/code-atlas/pull/62) |
| — | The founding-premise benchmark and the PLAN §19 decision it forced | **549.6k fresh** (105.4k output) + 7.6M cache reads over 100 calls after the 055–061 commit: reading the three arm result files and the round's lessons file, timing broad `grep` against the anchor tree to test the "search times out" claim, and the doc changes in this PR. The benchmark runs themselves were **headless sessions outside this transcript** and are costed in the private benchmark notes, not here | [#62](https://github.com/cuongdinhngo/code-atlas/pull/62) |
| 059 | Handler → template data-bag edge — Option 1 decision | **2 dispatch** — review `mango:reviewer` + ticket-blind `mango:challenger`, both **`unmeasured (blocking retrieval)`** (Cursor Task returns did not surface a usage block). Phases 0–3 and 5 dispatched **nothing** (refine skipped; design/execute/finalise on the main model; no Explore fan-out). **Main-loop spend is unmeasured**, as for 004–051 | [#63](https://github.com/cuongdinhngo/code-atlas/pull/63) |
| 055 | Recall gate beside tokens-to-answer cost ratio | **5 dispatch** — exposure-checker `mango:challenger` + review `mango:reviewer` / `mango:challenger` + verify-only re-review of both, all **`unmeasured (blocking retrieval)`**. Phases 1–3 and 5 on the main model (no Explore fan-out). **Main-loop spend is unmeasured**, as for 004–051 | [#64](https://github.com/cuongdinhngo/code-atlas/pull/64) |

**How 047–049 were measured.** They ran back-to-back in one autonomous session, so no per-task
transcript exists. Each row is that session's assistant API calls bucketed by commit timestamp — the
calls between the previous commit and a task's own commit are attributed to it. That is an
approximation in one direction only: work interleaved across tasks lands in whichever segment it
finished in, so a row can understate a task whose thinking happened earlier (049 is the known case,
flagged in its row). "Fresh" is input + output + cache-creation; cache reads are listed separately
because they are billed differently and dwarf everything else.

## Follow-ups (not yet ticketed)

- **Resolver: link `IMPORTS`** (`target_raw` is already an FQN) so `find_references` sees `use`
  statements — filed from [PR #23](https://github.com/cuongdinhngo/code-atlas/pull/23) review. **Still
  open:** `IMPORTS ∉ contract.FQN_EDGE_KINDS`, so the resolver never links it and `use` sites never
  surface in `find_references` (see the docstring note in `code_atlas/tools/find_references.py`).
- **PSR-4 / autoload-aware include resolution** — `include_graph` is effectively empty on real
  Composer-autoloaded repos: their only `INCLUDES` edges are dynamic bootstrap `require`s with no
  resolved target. Found concretely in [042](tasks/042_tokens-to-answer-sample-tier.md) — it is why
  the tokens-to-answer sample tier cannot sample "who includes X" on laravel/symfony/brick. Teaching
  the resolver the PSR-4 autoload map would make `include_graph` useful beyond `require`-based legacy
  code. Also still un-ticketed from the external review: duplicate-name disambiguation across PSR-0
  roots.
- **External-review batch (PHP-general, the private monorepo is only the stress test) — landed.** The Top-3 and
  one second-tier item all merged: [028](tasks/028_index-health-metrics.md) (health signal, PR #31),
  [029](tasks/029_php-receiver-resolution.md) (receiver resolution, PR #32),
  [030](tasks/030_alias-indirection-edges.md) (alias/indirection + contract bump, PR #33),
  [031](tasks/031_reachability-orphans.md) (reachability/orphans, PR #34), in that order (028 measured
  whether 029/030 helped; 031 needed 029's resolved graph). Remaining un-ticketed items are the two
  above (IMPORTS linking, PSR-4/PSR-0 include & name resolution).
- **015 AC2 operator run:** land a real `CODE_ATLAS_SCALE_SAMPLE` timing artifact (elapsed +
  `peak_rss_*`) against the ~112k checkout — deferred from [PR #25](https://github.com/cuongdinhngo/code-atlas/pull/25)
  (D1). Folded into [018](tasks/018_cross-repo-validation.md) as optional A4 (`CODE_ATLAS_SCALE_SAMPLE`
  set → `scale_full_build`; unset → skip). Still needs an operator machine with the private checkout.
- **Parser-OOM size cap (optional):** multi-MB generated files (e.g. TCPDF/PHPExcel CID font tables
  ~1.5 MB, MPDF ~1.2 MB) exhaust the PHP parser's memory and kill the adapter process. This is
  **already handled** — `indexer._work` (`code_atlas/indexer.py:565-573`) soft-fails the file and
  restarts the adapter, so the build is unaffected — but a pre-skip by byte cap (`CA_MAX_FILE_BYTES`)
  would avoid ~30 crash-and-restart cycles on the large-monorepo validation. Optional `feat`; log what
  is skipped (no silent truncation). Origin: same large-monorepo full-build validation as 043.
- **043 AC1 end-to-end `full_build` dup test (CI-gated):** add a fake-adapter path prefix that emits
  two same-qname nodes for one file plus an `interface`/`class` same-name pair, and a `full_build`
  test asserting the build completes with the file `parsed_ok=1` and each qname resolving to one node.
  Deferred from [043](tasks/043_duplicate-decl-resilience.md) Gate 4 (human-approved coverage-gap
  exclusion): it cannot run on the Windows dev host, which cannot launch any adapter subprocess
  (`shlex(posix=False)`/`CreateProcess` — the same harness bug behind the 56 baseline failures). Needs
  either that harness bug fixed or the adapter-subprocess tests explicitly CI-gated. The fix's actual
  surface is already fully proven at the `_write`+real-store layer.
- **Adapter-subprocess test harness on Windows (separate bug):** `fake_command()`/`php_config()` build
  `CA_*_CMD` with `shlex.join` (POSIX quoting), but `load_config` splits with `shlex.split(posix=False)`
  on Windows, so quoted `sys.executable`/script paths reach `CreateProcess` verbatim → `WinError 2`.
  This fails all ~56 adapter-launching tests on the Windows dev host (green in CI/Linux). Surfaced by
  the [043](tasks/043_duplicate-decl-resilience.md) baseline capture; a `fix` ticket in its own right.
- **PHP-adapter duplicate-declaration fixture (optional):** a spec-shaped PHP fixture with a
  `function_exists`-guarded double definition + `interface X`/`class X`, asserting the adapter emits
  two same-qname nodes (the shape 043's store dedupe collapses). Optional; the adapter already emits
  per-declaration (that is how the duplicates were found on the monorepo).
- **Indexing-hygiene doc note (not a code bug) — captured.** The walk descends into nested worktree
  checkouts (`.claude/worktrees/…`) when `.gitignore` doesn't exclude them, ~doubling the index; and
  committed vendored libs under non-`vendor/` paths index by design. Both are `.codeatlasignore`
  guidance, not a code change — now written up in
  [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §5, together with a third variant
  found on a real repo: a host `.gitignore` **negation** (`!some/lib/vendor/`) cancels the *built-in*
  `vendor/` rule as well, so a committed dependency indexes as full source (2,580 files, 12 % of that
  index). Last-rule-wins is working as designed (`ignore.py:57-65`); the fix is a `.codeatlasignore`
  line, so this stays a doc item.
- **Nav rows are not deduplicated, and a repo with duplicate qnames halves the result budget.**
  Measured on a large private monorepo that carries two regional copies of the same legacy tree: the
  same class name is declared in two files, so `UNIQUE(qualified_name, file_path)` (`store.py:59`)
  legitimately keeps two nodes per qname, and a nav tool joining on `target_qname` matches both — so
  every hit is returned **twice** with an identical `(qname, file, line)`. `find_implementations` on an
  interface returned 10 rows carrying 5 distinct answers; `find_references` the same. That is half the
  `max_results` budget and half the response tokens spent on nothing, and it reads to an agent as a
  wrong answer rather than a duplicate. **Ticketed and fixed as [046](tasks/046_resolver-qname-candidate-dedupe.md)**,
  at the cause rather than in the row shaping: the duplicate *edges* no longer exist, so
  `total_count` never had to choose between counting answers and counting edges.
- **Tokens-to-answer measures cost, not information — proven blind by 046.** Removing 1.06M duplicate
  edges doubled the distinct answers in a 10-row nav response (5 → 10) and moved the aggregate ratio by
  **0.02 %** (178.318 → 178.356, 4,705 → 4,704 tokens), because `max_results` fills the budget either
  way. So the §19 metric cannot see a response getting twice as useful at the same price, and a tool
  returning ten duplicates scores exactly like one returning ten distinct answers. Correctness is
  covered by `expected`; nothing covers *usefulness*. Worth a second axis alongside the ratio — distinct
  answers per response, or rank-of-first-correct — before the ratio is used to judge a retrieval change.
- **`max_results` does two unrelated jobs (design smell, measured).** It caps both the rows a tool
  returns *and* the resolver's per-call-site candidate fan-out
  (`indexer.py:118` → `resolve_edges(max_candidates=config.max_results)`), so a query-ergonomics knob
  silently sets index size. Measured on a large legacy monorepo: 491,741 heuristic call sites, 33,300
  of them saturating a cap of 50; heuristic edges 4.76M at cap 50 vs 2.60M at cap 10 (−46 %), and the
  database 2,115 MB vs 1,133 MB. Splitting out a `CA_RESOLVE_MAX_CANDIDATES` would let an operator
  keep 50-row search results without paying a gigabyte for candidate noise. Origin:
  [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4.
- **Reachability payload size at `detail_level="standard"`:** `reachable_from` / `find_orphans` are
  bounded by `impact_max_nodes` (default 500) rather than `max_results`, and a 500-row answer is
  ~160 KB of JSON — tens of thousands of tokens, against a §19 metric that is measured *in tokens*.
  Worth either a lower default for these two tools or a `minimal`-by-default shape. Documented as a
  workaround in [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4.
- **A no-op incremental build costs ~62 s on a large repo.** Now ticketed as
  [052](tasks/052_incremental-noop-cost.md) — the observation stayed open here long enough to start
  blocking [053](tasks/053_refresh-on-checkout-hook.md), which is what turned it into work.
- **Controller→template data-bag edge — decided (059), not yet implemented.** Option 1 (producer side
  only) is recorded in [PLAN §19](PLAN.md#19-project-context--decision-log); shipping the edges is
  [062](tasks/062_view-databag-producer.md). Origin: field retro round 1 §6a.1, §2d / round 2 §A.6.
- **`max_results` semantics are documented locally, not by the server.** That the cap governs both
  returned rows *and* the resolver's candidate fan-out (the design smell recorded above) was learned by
  the field session only from a comment in the repo's own config file. Whatever comes of splitting the
  knob, the server should state which meaning is in force where an agent can read it — `total_count` is
  only interpretable if you know. Origin: field retro round 1 §3b, §3e, §6d.
- **018 construct gaps:** any cross-repo misses → fill the gap log in
  [`runbooks/cross-repo-validation.md`](runbooks/cross-repo-validation.md) and feed task 007 / 025.
  (Gap log is still empty — no scheduled run has recorded a miss.)
## Suggested order

Critical path to first release: **001 → 002 → 004/005 → 006 → 007 → 009 → 010 → 011 → 013 → 014 (ship)**.
010 landed the MCP server itself, so every later tool is a registration in `main.build_server` plus one
module under `code_atlas/tools/` — 011 and 014 no longer carry any server work.
003 (config) landed before 009. **008 (runtime) did not, and did not need to** — 009 drives a host
adapter through `CA_<LANG>_CMD`, so 008 is now only the Docker path-mapping mode and blocks nothing
on the path to 014. **025 (grammar coverage) is off the critical path** — it was split out of 007 so
the protocol could unblock 008/009 first — and 012 (tests) waits on 025. 024 (CI) is independent and
can land any time. Then 015–018 harden PHP. **Phase 1.5 (032–042, agent-first PHP depth, §19) is now
complete — all merged.** Next is either 019–021 language breadth or 022–023 onboarding (both still
`todo`/deferred behind Phase 1.5 per §19); no Phase 1.5 task remains open.
**027 sits between 015 and 018**: it changes the resolver read path the 018 scale baseline would
otherwise measure, so it lands first.

## Conventions
- Keep task `status` in this table **and** in each task file's frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
