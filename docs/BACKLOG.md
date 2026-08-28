# Backlog — code-atlas

Task tracker. One file per task in [`docs/tasks/`](tasks/) (`NNN_slug.md`). Source of truth for scope
is [`PLAN.md`](PLAN.md); the durable decision log is [PLAN §19](PLAN.md#19-project-context--decision-log)
and per-task lessons are in [`LESSONS.md`](LESSONS.md). This file tracks *what is open and what
landed*; each ticket's cost is one row in [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) (R7.2) — narrative
rationale lives in those three.

**Status legend:** `todo` · `in-progress` · `blocked` · `deferred` · `done`
**Shipped for daily use at task 014** (search/read/outline).

## Open work — Pillar 1 · Graph

Resolved relationships for the agent, and the honesty of the payload that carries them
([PLAN §1](PLAN.md#1-goals--non-goals)). The `Theme` column is unchanged.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 074 | [Does the index harm mechanism questions? — no verdict](tasks/074_does-the-index-harm-mechanism-questions.md) | Measure | deferred | 055, 067, 045 |
| 098 | [Should the graph hold "this file is a copy/port of that one"? — evidence-gated](tasks/098_correspondence-relation-seam.md) | Coverage | deferred | 030, 011, 003 |
| 100 | [Nine kinds of evidence in the PR, zero graph payloads](tasks/100_claim-signing-output-mode.md) | Agent-fit | done | 017, 057, 061 |
| 101 | [A ten-name sweep is ten calls, so the agent used a shell loop](tasks/101_nav-tools-take-one-subject-at-a-time.md) | Agent-fit | done | 014, 013, 066 |
| 102 | [`impact` reports `seeds_dropped: 0` for a subject it never found](tasks/102_impact-cannot-tell-an-absent-subject-from-a-zero.md) | Agent-fit | done | 017, 100 |
| 120 | ["Can this subtree be deleted?" — subtree dependency with duplicate-declaration attribution](tasks/120_subtree-dependency-attribution.md) | Coverage | done | 017, 043, 078, 115 |
| 122 | [075 normalised the leading backslash for three tools; four `find_*` tools still decline over it](tasks/122_exact-miss-shaping-discards-a-resolved-subject.md) | Agent-trust | done | 075, 076, 065, 093 |
| 123 | [`file_outline` omitted the symbol under repair, reported `total_count: 10` for a 12-symbol file, and has no page 2](tasks/123_file-outline-total-count-is-the-page-length.md) | Agent-trust | done | 014, 057, 066, 067 |
| 124 | [`find_orphans` blew the transport limit at 19k files, on the one ticket whose root cause *was* an orphan](tasks/124_find-orphans-cannot-answer-at-scale.md) | Agent-fit | done | 031, 057, 066, 119 |
| 125 | [No payload names the server build — every field retro is told its own subject by an operator](tasks/125_no-payload-names-the-server-build.md) | Measure | done | 082, 095, 100 |
| 128 | [TypeScript/JavaScript — M0 spike only, to answer §4.4 with evidence](tasks/128_typescript-adapter-m0-spike.md) | Phase 2 / M7 | done | 012, 147, 149 |
| 129 | [`include_graph(imports)` is a silent zero for any namespaced file — the INCLUDES edge is anchored on the namespace](tasks/129_include_graph_imports-is-a-silent-zero-for-a-namespaced-file.md) | Agent-trust | done | 121 |
| 132 | [The doc set costs an agent ~66k tokens before it knows what binds it — give every standing doc a boundary](tasks/132_docs-restructure.md) | Docs | done | — |
| 133 | [The always-binding read is ~66.5k tokens and most of it is reference — tier the agent chain and gate the tier](tasks/133_agent-chain-is-one-tier.md) | Docs | done | 132 |
| 134 | [The standing docs grew to 66k tokens of mostly retold narrative — prune them and gate the size](tasks/134_standing-docs-grow-and-nothing-prunes-them.md) | Docs | done | 132 |
| 135 | [The recall gate cannot see a wrong answer — an answer with every expected row plus four wrong ones scores 1.0](tasks/135_harness-scores-recall-but-never-precision.md) | Measure | done | 055, 121, 130 |
| 136 | [Two thirds of the graph's edges are HEURISTIC, the plan promises the fix, and no ticket ever carried it](tasks/136_heuristic-share-has-no-owner.md) | Coverage | done | 025, 029, 011 |
| 137 | [A PHP local type table — the cause of ≥99% of the HEURISTIC share, with a measured target per pin](tasks/137_php-local-type-table.md) | Coverage | done | 136, 039 |
| 140 | [`impact` answers in symbols, and the decision is module-shaped — 500 rows at ~160 KB is the only answer today](tasks/140_impact-answers-in-symbols-not-modules.md) | Agent-fit | done | 017, 112, 114, 124 |
| 141 | ["Can this module be split out?" — the cut edges and the cycles that block it — evidence-gated](tasks/141_extractability-cut-edges-and-the-cycles-that-block-it.md) | Coverage | deferred | 120, 087, 140 |
| 142 | [The supervision question class was never put through the harness — 121's lesson, one phase later](tasks/142_supervision-question-class-has-no-baseline.md) | Measure | done | 034, 055, 121, 135 |
| 158 | [The mandated caller sweep is a habit, not a trigger — routing suggestions fire on index state, never on the question](tasks/158_routing-suggestions-fire-on-index-state-not-on-the-question.md) | Agent-fit | done | 081, 099, 069 |
| 159 | [An adapter ships in-repo but is invisible until an env var is set — nothing in any payload says it exists](tasks/159_get-index-status-does-not-name-available-but-unconfigured-adapters.md) | Adoption | done | 064, 028, 095 |
| 160 | [A zero answer never names the index language coverage — a false negative wears a modelled zero's clothes](tasks/160_a-zero-answer-never-names-the-index-language-coverage.md) | Agent-trust | done | 065, 129, 093, 159 |
| 161 | [`impact` binds a shared qname to one arbitrary twin at tier RESOLVED, and carries no freshness field](tasks/161_impact-resolves-a-shared-qname-to-one-twin-and-carries-no-freshness.md) | Agent-trust | done | 017, 070, 078, 077 |
| 162 | [A build swap is invisible on every payload but `get_index_status` — carry a cheap `server_build` stamp](tasks/162_a-build-swap-is-invisible-on-every-payload-but-get-index-status.md) | Agent-trust | done | 125, 077, 100 |
| 163 | [`read_symbol` `detail_level: "minimal"` is byte-identical to `standard` — a documented knob that does nothing](tasks/163_read-symbol-minimal-is-byte-identical-to-standard.md) | Agent-trust | done | 014, 066 |
| 164 | [`server_build` names the repo HEAD, not the code the process loaded](tasks/164_server-build-names-the-repo-not-the-running-process.md) | Agent-trust | done | 162, 125, 100 |
| 165 | [`find_callers` on a qualified twin silently omits callers bound to its sibling, and says `reason: "ok"`](tasks/165_find-callers-splits-across-twins-and-says-reason-ok.md) | Agent-trust | done | 013, 054, 161, 122 |
| 166 | [`read_symbol` answers from the pre-repair state and calls it `no_such_symbol`](tasks/166_read-symbol-answers-from-pre-repair-state-and-calls-it-no-such-symbol.md) | Agent-trust | done | 035, 014, 065 |
| 167 | [A substring near-miss is returned at `reason: "ok"`](tasks/167_a-substring-near-miss-is-reported-as-reason-ok.md) | Agent-trust | done | 014, 160, 093 |
| 168 | [`find_references` under-reports an alias-backed class by 4.7× and still says `reason: "ok"`](tasks/168_find-references-never-got-165s-twin-disclosure.md) | Agent-trust | done | 165, 013, 122 |
| 169 | [An `impact` path seed expands to every symbol in the file and reports 29× the qname](tasks/169_impact-path-seed-walks-every-symbol-and-its-twins.md) | Agent-trust | done | 161, 017, 078 |
| 170 | [`server_identity` is cached, so a later build swap is unreportable](tasks/170_server-identity-is-cached-so-a-later-build-swap-is-unreportable.md) | Agent-trust | todo | 164, 162, 125 |
| 171 | [`sibling_definitions` fires on 83 % of calls and lists nine sites unranked](tasks/171_sibling-definitions-fires-on-most-calls-and-is-unranked.md) | Agent-trust | done | 165, 168, 013 |
| 172 | [An incremental build is blind to a scope change — 3,244 files in scope, `wrote.files: 0`](tasks/172_incremental-is-blind-to-a-scope-change.md) | Freshness | done | 016, 060, 053 |
| 173 | [Coverage claims key on what is *configured*, not on what is *indexed*](tasks/173_coverage-claims-key-on-configured-not-indexed.md) | Agent-trust | done | 160, 159, 082 |
| 174 | [`unconfigured_adapters` names the switch but not the cost](tasks/174_unconfigured-adapters-names-the-switch-not-the-cost.md) | Agent-trust | done | 159, 082 |
| 175 | [Config is read once at spawn and no payload says so](tasks/175_config-is-loaded-at-spawn-and-nothing-says-so.md) | Agent-trust | todo | 164, 170 |
| 176 | [No full build from a shell — `refresh` is incremental-only](tasks/176_no-full-build-from-a-shell.md) | Freshness | done | 010, 053 |
| 177 | [A valid long build is indistinguishable from a hang — 30 min of silence, no progress](tasks/177_a-long-build-is-indistinguishable-from-a-hang.md) | Agent-trust | done | 072, 010, 052, 176 |
| 178 | [`get_index_status` reads `staleness: "current"` while a build is still linking](tasks/178_status-reads-current-while-a-build-is-still-linking.md) | Agent-trust | done | 072, 077, 010, 177 |
| 179 | [`impact_modules` inherits 169's seed classification but not its twin refusal](tasks/179_impact-modules-inherits-half-the-seed-fix.md) | Agent-trust | done | 169, 161, 140 |
| 180 | [`search_symbol` ranks a substring near-miss above six exact matches](tasks/180_search-ranks-a-near-miss-above-exact-matches.md) | Agent-trust | done | 167, 014, 057 |
| 181 | [`sibling_definitions` at `ranked_by: "path"` is a 93-row dump wearing a ranking's shape](tasks/181_sibling-definitions-fallback-is-a-dump-not-a-ranking.md) | Agent-trust | todo | 171, 168, 169 |
| 182 | [`find_orphans` returns 215,177 rows it has already flagged unreliable](tasks/182_find-orphans-answers-with-rows-it-has-flagged-unreliable.md) | Agent-fit | todo | 124, 031, 119 |
| 183 | [`edge_health` is whole-graph only, so no adapter can be evaluated on the repo it was added for](tasks/183_edge-health-has-no-per-language-breakdown.md) | Measure | done | 136, 082, 173 |
| 185 | [No tool is ever asked a question over a second language's graph — the multi-language claim stops at the adapter boundary](tasks/185_no-tool-is-ever-asked-a-question-over-a-second-languages-graph.md) | Coverage | done | 147, 012, 019 |
| 186 | [A zero answer still cannot say "this relation is not modelled for this file's language" — 160's carve-out, now a false negative](tasks/186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md) | Agent-trust | done | 160, 183, 185 |
| 187 | [`find_orphans` crashes when `CA_ENTRY_POINTS` matches no indexed file](tasks/187_find-orphans-crashes-on-an-entry-point-glob-that-matches-nothing.md) | Agent-trust | todo | 185, 031, 124 |
| 188 | [`IMPORTS` is never linked, so no tool can walk a module graph](tasks/188_imports-edges-are-never-linked-so-no-tool-can-walk-a-module-graph.md) | Agent-fit | todo | 186, 019, 155 |

## Open work — Pillar 2 · Onboarding

The rendering of what the code actually is, for a human supervising an agent or presenting the
project ([PLAN §1](PLAN.md#1-goals--non-goals)). Same graph, no second pipeline.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 083 | [Onboarding — deterministic graph-metrics foundation](tasks/083_onboarding-graph-metrics.md) | Phase 3 / M10 | done | 014, 031, 017 |
| 084 | [Onboarding — architectural layer assignment](tasks/084_onboarding-layer-assignment.md) | Phase 3 / M10 | done | 083 |
| 103 | [Onboarding — layer granularity: strip common prefix, group by top segment](tasks/103_onboarding-layer-granularity.md) | Phase 3 / M10 | done | 084 |
| 104 | [Onboarding — fix the layer collapse (F1): group beneath the dominant subtree](tasks/104_onboarding-layer-signal.md) | Phase 3 / M10 | done | 103 |
| 105 | [Onboarding — the dominant subtree is decided by file count, and a config dir can win it](tasks/105_dominant-subtree-loses-to-a-config-dir.md) | Phase 3 / M10 | done | 104, 086 |
| 085 | [Onboarding — Summarizer Protocol seam + deterministic default](tasks/085_onboarding-summarizer-seam.md) | Phase 3 / M10 | done | 083 |
| 086 | [Onboarding — architecture_overview tool](tasks/086_architecture-overview-tool.md) | Phase 3 / M10 | done | 084, 085, 104 |
| 087 | [Onboarding — guided_tour tool](tasks/087_guided-tour-tool.md) | Phase 3 / M11 | done | 083, 086 |
| 088 | [Onboarding — generate_onboarding markdown + manifest](tasks/088_generate-onboarding-markdown.md) | Phase 3 / M11 | done | 084, 086, 087 |
| 089 | [Onboarding — static HTML viewer](tasks/089_onboarding-viewer.md) | Phase 3 / M11 | done | 088 |
| 090 | [Onboarding — LLM summarizer behind the seam (opt-in)](tasks/090_llm-summarizer-impl.md) | Phase 3 / M12 | done | 085, 088 |
| 091 | [Onboarding — LLM layer-name refinement (opt-in)](tasks/091_llm-layer-refinement.md) | Phase 3 / M12 | done | 084, 090 |
| 106 | [Onboarding — the tour budget buys the 500 alphabetically-first isolated files](tasks/106_tour-budget-buys-500-alphabetical-isolated-files.md) | Phase 3 / M11 | done | 087, 088 |
| 107 | [Onboarding — a page with no neighbours and no summary is filler](tasks/107_a-page-with-no-neighbours-and-no-summary-is-filler.md) | Phase 3 / M11 | done | 088, 106 |
| 108 | [Onboarding — a module page prints every neighbour, so the median page is 82 KB](tasks/108_module-page-neighbour-list-is-unbounded.md) | Phase 3 / M11 | done | 088, 107 |
| 109 | [Onboarding — a quality gate on the emitted artifact, so filler cannot ship again](tasks/109_onboarding-artifact-quality-gate.md) | Phase 3 / M11 | done | 088, 108 |
| 110 | [Onboarding — layers are directory names, not architecture; name them by responsibility](tasks/110_layers-named-by-responsibility.md) | Phase 3 / M10 | done | 084, 105, 109 |
| 111 | [Onboarding — the tour is one stop per module, so 500 modules is a 500-stop "tour"](tasks/111_tour-is-narrative-steps.md) | Phase 3 / M11 | done | 087, 110 |
| 112 | [Onboarding — one compact dataset as the contract behind every renderer](tasks/112_onboarding-dataset-contract.md) | Phase 3 / M11 | done | 083, 086, 110 |
| 113 | [Onboarding — "zero inbound" is four populations, and one number misleads](tasks/113_reachability-split.md) | Phase 3 / M11 | done | 083, 112 |
| 114 | [Onboarding — nothing bridges "fix screen X" to a file path](tasks/114_business-module-table.md) | Phase 3 / M11 | done | 112 |
| 115 | [Onboarding — sibling subtrees duplicating 62% of their paths, and nothing says so](tasks/115_mirror-subtree-detection.md) | Phase 3 / M11 | done | 112 (feeds 098) |
| 116 | [Onboarding — replace the 31 MB page dump with a navigable system map](tasks/116_dashboard-viewer.md) | Phase 3 / M11 | done | 112, 114, 115 |
| 117 | [Onboarding — the map's structure is derivable, its prose is not; route prose through the seams](tasks/117_llm-prose-for-map.md) | Phase 3 / M12 | done | 110, 111, 090, 091 |
| 118 | [Onboarding — every module page says `Summary: (none)`, and the cause is the seam, not the repo](tasks/118_module-summary-seam-gets-empty-facts.md) | Phase 3 / M11 | done | 085, 090, 107, 117 |
| 119 | [Onboarding — the reachability split never says which signal produced each count](tasks/119_reachability-signal-provenance.md) | Phase 3 / M11 | done | 113, 116 |
| 121 | [Phase 3 shipped without its own cost gate — the onboarding question-class was never added to the harness](tasks/121_onboarding-question-class-never-measured.md) | Measure | done | 034, 045, 055, 086, 087, 088 |
| 126 | [Onboarding — the map's search palette clusters into one subtree](tasks/126_search-palette-clusters-into-one-subtree.md) | Phase 3 / M11 | done | 067, 115, 116 |
| 127 | [Onboarding — a caveat the dataset carries can vanish in the rendered map](tasks/127_caveats-drop-at-the-artifact-layer.md) | Phase 3 / M11 | done | 100, 112, 113, 116, 119 |
| 130 | [The `web_entry` bucket counts test controllers as web surface — half the count on a canonical repo](tasks/130_web-entry-bucket-counts-test-controllers.md) | Phase 3 / M11 | done | 113, 119, 121 |
| 131 | [`guided_tour`'s first five stops are lint and bootstrap config, not the front controller](tasks/131_tour-ranks-configuration-ahead-of-the-front-controller.md) | Phase 3 / M11 | done | 111, 121 |
| 138 | [The architecture rules are prose plus a regex sweep — nothing asks the graph whether they hold](tasks/138_architecture-rules-are-never-asked-of-the-graph.md) | Supervision | done | 040, 110, 112, 136 |
| 139 | [The map is a snapshot, so nothing tells a reviewer what the agent changed about the architecture](tasks/139_map-is-a-snapshot-so-nothing-shows-architectural-drift.md) | Supervision | done | 112, 077, 127 |
| 143 | [The system map has no diagram — every relation is a table, and PILLAR 2 promised diagrams](tasks/143_the-system-map-has-no-diagram.md) | Presentation | done | 112, 116, 110, 130 |
| 144 | [A class diagram is a projection of rows the graph already holds — except the return type](tasks/144_class-diagram-is-a-projection-minus-the-return-type.md) | Presentation | done | 002, 112, 116 |
| 145 | [`artifact.json` is a gitignored cache — a second renderer turns it into a published contract](tasks/145_artifact-json-is-a-cache-that-a-second-renderer-turns-into-a-contract.md) | Presentation | done | 088, 112, 116, 118 |
| 146 | [`scripts/gate.sh` can report GREEN against bytecode that is not the source on disk](tasks/146_gate-can-pass-on-stale-bytecode.md) | Measure | done | — |


**Round ordering, and what each round left open.** One line each; the narratives live in
[`FEEDBACK.md`](FEEDBACK.md), [PLAN §19](PLAN.md#19-project-context--decision-log),
[`LESSONS.md`](LESSONS.md) and `benchmarks/`.

| Round | Tickets | State |
|---|---|---|
| 4–7 (2026-08-10…23) | 075–082 · 092–097 · 099–102 · 122–125 · 126 · 127 | closed — 081 `NOT OBSERVED`; 127 closed **119** in the same change |
| 8–9 (2026-08-25/26) | 158–163 · 022 | closed — SQL deferred (022) |
| 10 (2026-08-26) | 164–167 | closed — the verification round: no prior fix reached a long-lived process until **164** (#187); then 165–167 (#188–#190) |
| 11 (2026-08-27) | 168–179 | closed — **first round a fix reached the field**; adapter #2's fourth zero was an absent `CA_<LANG>_CMD`, not capability. 170 · 174 · 175 · 179 stayed open |
| 12 (2026-08-28) | 180–186 | open — first **two-language** index. Decisive fact: the T-SQL the index does not read → **184**; adapter #2's fifth zero is now **applicability**, not roll-out. **Roll-out unmoved for a fifth round** — `.mcp.json` 0, CI 0 |
| Architecture review (2026-08-23) | 138–142 · 143–145 | 138 · 139 · 142 · 143 · 144 · **145A** done; 141 gated at n = 0; 145B deferred (stack not chosen) |

**What still governs open work:**

- **Every `deferred` ticket holds its own gate** — 074, 098, 141 and 022 each state theirs, and 141 is
  at n = 0; do not queue one without reading it. Auto *reading orders* stay unscheduled
  ([121](benchmarks/121_onboarding-question-class.md)).
- **M10–M12 are complete** — 22 tools on the MCP surface, plus four shell entry points; the 108–117
  reshape renders the map from 112's dataset alone ([`ROADMAP.md`](phase3-onboarding/ROADMAP.md)).
- **Roll-out is the binding constraint and deliberately not a ticket here** — five rounds standing. The
  backlog accepts only code, which is the mechanism that defers it, so it goes to the consumer as a PR.
- **The anchor repo is the test subject, not the product** — 185/186 keep the language-agnostic claim
  checked at the tool surface, where 147 only checks it at the adapter's.

## Phase 2 — More languages (deferred — §19 pivot, 2026-08-04)

**Deferred, not cancelled** for adapters #3–#4 (human-ratified 2026-08-04, §19); the language *order*
is unchanged (§18.2). **019 was reopened 2026-08-25**, its remaining scope filed as **150–157**, all
landed. Adapter #2 parses the anchor's front end but is unwired there, so its **zero** contribution is
a roll-out finding, not an adapter one.

| # | Task | Milestone | Status | Depends on |
|---|---|---|---|---|
| 019 | [TypeScript/JavaScript adapter, no contract bump needed](tasks/019_typescript-adapter.md) | M7 | done | 012, 011, 128 |
| 020 | [Python adapter](tasks/020_python-adapter.md) | M8 | deferred | 019 |
| 021 | [C#/.NET adapter](tasks/021_csharp-adapter.md) | M9 | deferred | 019 |
| 022 | [SQL / DB-schema awareness — a fifth capability, distinct in kind](tasks/022_sql-schema-adapter.md) | M9+ | deferred | 019, 020, 021 |
| 184 | [T-SQL source adapter, tier 1a — procs, functions and `EXEC` cost zero contract vocabulary](tasks/184_tsql-source-adapter-tier-1a.md) | M9+ | deferred | 019, 147, 183 |
| 026 | [Inverse Docker path rebase (adapter #2)](tasks/026_docker-inverse-path-rebase.md) | M7 | deferred | 008, 019 |
| 147 | [The R3.4 conformance harness is PHP-shaped — `tests/contract/` cannot admit a second adapter](tasks/147_contract-harness-is-php-shaped.md) | M7 | done | 012, 025 |
| 148 | [The R2.2 framework sweep lists only PHP frameworks — it cannot fail for adapter #2](tasks/148_r22-framework-sweep-cannot-fail-for-adapter-2.md) | M7 | done | 012, 146 |
| 149 | [Name the TS/JS construct inventory before any parsing exists](tasks/149_tsjs-construct-inventory.md) | M7 | done | 147 |
| 150 | [No static analyser (R6.6) and no cross-repo run (R6.3) for the TS adapter](tasks/150_ts-adapter-has-no-gate-but-its-own-fixtures.md) | M7 | done | 019, 018, 148 |
| 151 | [`obj.method()` emits no edge at all](tasks/151_ts-member-calls-emit-no-edge.md) | M7 | done | 019, 128, 137 |
| 152 | [TS call edges carry no `args`/`arg_keys`](tasks/152_ts-call-args-and-arg-keys.md) | M7 | done | 019, 151 |
| 153 | [No `semantic_types` — inferred receivers want 137's type table](tasks/153_ts-declared-and-inferred-types.md) | M7 | done | 019, 151, 137 |
| 154 | [`allowJs` breadth and JSDoc as a type source](tasks/154_ts-allowjs-and-jsdoc-types.md) | M7 | done | 019, 153 |
| 155 | [An aliased specifier and an `export *` both resolve to nothing](tasks/155_ts-tsconfig-paths-and-export-star.md) | M7 | done | 019 |
| 156 | [R1.2's condition is met — write the registry verdict down](tasks/156_r12-registry-verdict-now-adapter-2-exists.md) | M7 | done | 019 |
| 157 | [R6.2's TS inventory has no named-`export default` case](tasks/157_r62-inventory-has-no-named-default-export-case.md) | M7 | done | 019, 149 |

## Phase 1 — Core + PHP (done)

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
| 024 | [CI hardening](tasks/024_ci-hardening.md) | Setup | done | 001 |
| 025 | [PHP adapter — full 8.5 grammar coverage](tasks/025_php-adapter-grammar.md) | M0 | done | 007 |
| 027 | [Batch resolver candidate lookups](tasks/027_resolver-batched-lookups.md) | M4 | done | 011, 015 |
| 028 | [Index-health metrics in get_index_status](tasks/028_index-health-metrics.md) | M4 | done | 010, 011 |
| 029 | [PHP adapter — $this/self/static/parent receiver resolution](tasks/029_php-receiver-resolution.md) | M2 | done | 011, 025 |
| 030 | [Alias & literal-indirection edges](tasks/030_alias-indirection-edges.md) | M2 | done | 002, 011, 025 |
| 031 | [Reachability / orphan detection](tasks/031_reachability-orphans.md) | M6 | done | 003, 011, 013 |

## Phase 1.5 — Agent-first PHP depth (done — §19 pivot, 2026-08-04)

Consumer = an AI agent in a terminal; baseline = grep+`Read`. **Editing tools are permanently out**
and tool *consolidation* was measured and rejected — both §19.

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

## Phase 1.5b — Large-monorepo validation hardening

Surfaced by full-build validation against the anchor monorepo and the field-retro rounds run on it.
Open tickets are in [Pillar 1](#open-work--pillar-1--graph) / [Pillar 2](#open-work--pillar-2--onboarding);
everything below has landed.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 043 | [Duplicate-declaration resilience — repeated `qualified_name` must not abort the build](tasks/043_duplicate-decl-resilience.md) | Robustness | done | 004, 009 |
| 044 | [Onboarding runbook — installing code-atlas on a large legacy repo](tasks/044_onboarding-runbook.md) | Adoption | done | 014, 039, 043 |
| 045 | [Tokens-to-answer — measure against a local repo with a pre-built index](tasks/045_tokens-to-answer-local-repo.md) | Measure | done | 034, 042 |
| 046 | [Resolver — dedupe candidates by `qualified_name`](tasks/046_resolver-qname-candidate-dedupe.md) | Robustness | done | 011, 027, 043 |
| 047 | [Staleness must reflect the index, not the working tree](tasks/047_staleness-scoped-to-indexed-files.md) | Freshness | done | 028, 035, 016 |
| 048 | [`edge_health` returns two different fields both meaning "resolved"](tasks/048_edge-health-resolved-ambiguity.md) | Agent-trust | done | 028 |
| 049 | [Select call sites by argument shape (design-first)](tasks/049_call-site-argument-selectivity.md) | Agent-fit | done | 013, 037, 002 |
| 050 | [A schema-version mismatch is direction-blind](tasks/050_schema-version-mismatch-recovery.md) | Robustness | done | 010, 016 |
| 051 | [`BuildReport.edges` counts what the adapters emitted, not what the build wrote](tasks/051_build-report-edge-undercount.md) | Agent-trust | done | 009, 011, 028 |
| 052 | [Where does a no-op incremental build spend 62 seconds?](tasks/052_incremental-noop-cost.md) | Freshness | done | 016, 047 |
| 053 | [Nothing refreshes the index when the repo changes outside the agent's editor](tasks/053_refresh-on-checkout-hook.md) | Freshness | done | 052, 036, 016 |
| 054 | [`find_callers` reports `total_count: 0` for a method that has callers](tasks/054_bare-name-callers-silent-drop.md) | Agent-trust | done | 011, 013, 046 |
| 055 | [Nothing measures what the tools fail to find — a recall gate above the cost metric](tasks/055_recall-benchmark.md) | Measure | done | 034, 045 |
| 056 | [An unknown filter value returns an empty result instead of an error](tasks/056_filter-values-fail-loud.md) | Agent-trust | done | 014, 033 |
| 057 | [A large answer cannot be enumerated, so `total_count` cannot be audited](tasks/057_answer-pagination.md) | Agent-trust | done | 013, 014, 033 |
| 058 | [`parse_failures: 29` — nobody can find out which 29 files](tasks/058_list-parse-failures.md) | Agent-trust | done | 009, 028 |
| 059 | [The handler → template data-bag edge is unmodelled](tasks/059_view-databag-edge.md) | Coverage | done | 030, 040 |
| 060 | [An incremental run reports deltas under the field names a full build uses for totals](tasks/060_build-report-scale-naming.md) | Agent-trust | done | 051 |
| 061 | [Every response carries fields that earn nothing](tasks/061_payload-weight.md) | Cost | done | 010, 014, 033 |
| 062 | [Producer-side view data-bag edges — rules + enrichment](tasks/062_view-databag-producer.md) | Coverage | done | 030, 040, 059 |
| 063 | [The data-bag setter takes an array, not a key](tasks/063_view-databag-array-keys.md) | Coverage | done | 062, 002, 049 |
| 064 | [A build with no adapter configured reports success over an empty index](tasks/064_build-without-adapter-silent.md) | Agent-trust | done | 009, 028, 056 |
| 065 | [An empty answer cannot say why it is empty](tasks/065_empty-answer-cannot-explain-itself.md) | Agent-trust | done | 033, 054, 056 |
| 066 | [`limit: 30` returns 10 rows and nothing says it was clamped](tasks/066_limit-clamped-silently.md) | Agent-trust | done | 057, 033 |
| 067 | [Page 1 of `find_callers` was 100% of the tree the agent must not touch](tasks/067_first-page-not-representative.md) | Agent-trust | done | 057, 013 |
| 068 | [The rules bookmark is counted as an indexed source file](tasks/068_rules-bookmark-counted-as-source-file.md) | Agent-trust | done | 040, 062, 064 |
| 069 | [`find_view_data` went uncalled in the exact session it was built for](tasks/069_tool-names-do-not-say-what-they-answer.md) | Agent-fit | done | 062, 063, 038 |
| 070 | [One qname, five definitions, 23 callers merged](tasks/070_ambiguous-qname-no-scoping.md) | Agent-fit | done | 043, 013, 011 |
| 071 | [A worktree agent gets the main checkout's symbols with `reason: "ok"`](tasks/071_answers-do-not-name-their-tree.md) | Agent-trust | done | 033, 061, 065 |
| 072 | [`mode: "busy"` returns in 0.0 s and reads like success](tasks/072_busy-build-hides-staleness.md) | Agent-trust | done | 053, 033 |
| 073 | [Read-through freshness repairs only rows it already found](tasks/073_freshness-cannot-find-what-is-not-indexed.md) | Agent-trust | done | 035, 065, 033 |
| 075 | [`read_symbol` answers `found: false` with `reason: "ok"` for a class the index holds](tasks/075_read-symbol-confident-zero-on-unnormalised-qname.md) | Agent-trust | done | 065, 070, 014 |
| 076 | [A bare method name answers `no_such_symbol` while its qualified form has 82 callers](tasks/076_bare-name-subject-reads-as-absence.md) | Agent-trust | done | 054, 011, 013 |
| 077 | [The index cannot name the revision it describes](tasks/077_index-cannot-name-the-revision-it-describes.md) | Agent-trust | done | 071, 047, 072 |
| 078 | [`ambiguous_definitions` warns while `source` silently ships one](tasks/078_ambiguous-payload-still-picks-one-definition.md) | Agent-trust | done | 070, 043, 049 |
| 079 | [`build_or_update_index` is the one payload with no `index_root`](tasks/079_build-payload-does-not-name-its-tree.md) | Agent-trust | done | 071, 060 |
| 080 | [No-op incremental costs ~56 s and reports 6,071 edges for 0 files](tasks/080_noop-incremental-cost-and-uninterpretable-writes.md) | Cost | done | 052, 051, 060 |
| 081 | [The four routing prompts have never been reachable by an agent](tasks/081_routing-prompts-are-not-in-the-agents-surface.md) | Agent-fit | done | 069, 017, 038 |
| 082 | [Two claims nobody outside can check](tasks/082_claims-nobody-outside-can-check.md) | Agent-trust | done | 068, 072, 028 |
| 092 | [An untracked file is skipped silently, then answers `no_such_symbol`](tasks/092_untracked-files-are-invisible-and-answer-no-such-symbol.md) | Agent-trust | done | 073, 082, 065 |
| 093 | [`try_instead` returns a string that is not a callable tool name](tasks/093_try-instead-is-not-a-callable-tool-name.md) | Agent-fit | done | 065, 076, 069 |
| 095 | [`collection.ignore: 9541` excludes indexable PHP by an unnamed rule](tasks/095_ignore-bucket-does-not-name-its-rule.md) | Agent-trust | done | 082, 003, 068 |
| 097 | [The recognition probe measures names, not descriptions or recall](tasks/097_recognition-probe-measures-names-not-recall.md) | Measure | done | 081, 069, 074 |
| 094 | [A `::class` constant in a routing array is `relationship_not_modelled`](tasks/094_class-constant-in-array-literal-is-not-an-edge.md) | Coverage | done | 030, 011, 002 |
| 096 | [A 2-file incremental costs 59 s while a no-op costs 2 s](tasks/096_edit-then-ask-tax-two-files-cost-a-minute.md) | Cost | done | 080, 052, 016 |
| 099 | [Every decision made without the graph wanted a line inside a file read](tasks/099_write-time-signal-seam.md) | Agent-fit | done | 097, 069, 036 |

### Where these tickets came from

Provenance is in the three docs the preamble names, not retold here (R7.6). One note still governs
open work: the anchor repo's `CLAUDE.md` asserts `grep` "times out" and costs "~650× the tokens" — an
**un-evidenced claim, not a code-atlas defect**; round 3 observed neither, so it needs evidence or
removal.

## Follow-ups (not yet ticketed)

One line each, with the pointer that holds the detail. Nothing here is scheduled.

- **Resolver: link `IMPORTS`** so `find_references` sees `use` — docstring note in `code_atlas/tools/find_references.py`.
- **PSR-4 / autoload-aware include resolution**, with PSR-0 duplicate-name disambiguation — [042](tasks/042_tokens-to-answer-sample-tier.md).
- **`max_results` does two unrelated jobs** — returned rows *and* resolver candidate fan-out, so a query knob sets index size — [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4.
- **Tokens-to-answer measures cost, not information** — 046 moved the ratio 0.02 % while doubling the distinct answers. Wants a second axis before it judges a retrieval change.
- **`reachable_from` payload size at `standard`** — bounded by `impact_max_nodes` (500), ~160 KB of JSON. Worth a lower default or `minimal`-by-default; workaround in [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4.
- **Parser-OOM size cap (optional)** — multi-MB generated files exhaust the PHP parser (already soft-failed/restarted in `indexer.py`); a byte-cap pre-skip (`CA_MAX_FILE_BYTES`) would avoid ~30 restart cycles. Log skips; no silent truncation.
- **Adapter-subprocess test harness on Windows (bug)** — `CA_*_CMD` uses POSIX quoting but splits with `posix=False`, so quoted paths reach `CreateProcess` verbatim → `WinError 2`. Fails ~56 adapter tests on Windows, green on Linux. Surfaced by [043](tasks/043_duplicate-decl-resilience.md).
- **043 AC1 end-to-end `full_build` dup test** — blocked by the Windows bug above; the surface is proven at the `_write`+store layer.
- **PHP-adapter duplicate-declaration fixture (optional)** — the adapter already emits per-declaration, so this only pins it.
- **015 AC2 operator run** — a scale-timing artifact folded into [018](tasks/018_cross-repo-validation.md) as optional A4. Needs an operator machine.
- **018 construct gaps** — cross-repo misses feed the (still empty) gap log in [`runbooks/cross-repo-validation.md`](runbooks/cross-repo-validation.md) and tasks 007 / 025.
- **`test_ac4_a_same_second_same_size_edit_is_a_stale_import` is flaky under load** — its premise is that both writes land in one second; when they straddle the boundary CPython invalidates correctly and the negative control fails claiming *"CPython changed"*. Seen once in a full run, green alone. The test should pin the mtime instead of racing for it.
- **Four CI tightenings deferred from the drift audit** — the audit's own doc was never committed, so the list is lost; re-derive from `ci.yml` vs `scripts/gate.sh` if it is wanted.
- **Docker images are never built by CI** — `docker/Dockerfile` can rot (`Dockerfile.runtime` is built inside `pytest`). Honest shape: one job building both. Survives the unbillable-Actions arrangement AGENTS.md records, which also means every gate is a human step.

## Conventions
- Keep task `status` in this table **and** in each task file's frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
- A task reaching `done` also gets its spend row in [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) (R7.2).
- Landed narrative belongs in [PLAN §19](PLAN.md#19-project-context--decision-log) or
  [`LESSONS.md`](LESSONS.md), not here; a ticketed follow-up leaves the
  [Follow-ups](#follow-ups-not-yet-ticketed) list. This is R7.6, with a ceiling in
  `tests/test_doc_size_budget.py`.
