# Backlog — code-atlas

Task tracker. One file per task in [`docs/tasks/`](tasks/) (`NNN_slug.md`). Source of truth for scope
is [`PLAN.md`](PLAN.md); the durable decision log is [PLAN §19](PLAN.md#19-project-context--decision-log)
and the per-task engineering lessons are in [`LESSONS.md`](LESSONS.md). This file tracks *what is open,
what landed, and what it cost* — narrative rationale lives in those three.

**Status legend:** `todo` · `in-progress` · `blocked` · `deferred` · `done`
**Shipped for daily use at task 014** (search/read/outline).

## Open work — Pillar 1 · Graph

Resolved relationships for the agent, and the honesty of the payload that carries them
([PLAN §1](PLAN.md#1-goals--non-goals)). The `Theme` column is unchanged.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 074 | [Does the index harm mechanism questions? — resolve at n ≥ 3](tasks/074_does-the-index-harm-mechanism-questions.md) | Measure | blocked | 055, 067, 045 |
| 098 | [Should the graph hold "this file is a copy/port of that one"? — evidence-gated](tasks/098_correspondence-relation-seam.md) | Coverage | deferred | 030, 011, 003 |
| 100 | [Nine kinds of evidence in the PR, zero graph payloads](tasks/100_claim-signing-output-mode.md) | Agent-fit | done | 017, 057, 061 |
| 101 | [A ten-name sweep is ten calls, so the agent used a shell loop](tasks/101_nav-tools-take-one-subject-at-a-time.md) | Agent-fit | done | 014, 013, 066 |
| 102 | [`impact` reports `seeds_dropped: 0` for a subject it never found](tasks/102_impact-cannot-tell-an-absent-subject-from-a-zero.md) | Agent-fit | done | 017, 100 |
| 120 | ["Can this subtree be deleted?" — subtree dependency with duplicate-declaration attribution — evidence-gated](tasks/120_subtree-dependency-attribution.md) | Coverage | todo | 017, 043, 078, 115 |
| 122 | [075 normalised the leading backslash for three tools; four `find_*` tools still decline over it](tasks/122_exact-miss-shaping-discards-a-resolved-subject.md) | Agent-trust | done | 075, 076, 065, 093 |
| 123 | [`file_outline` omitted the symbol under repair, reported `total_count: 10` for a 12-symbol file, and has no page 2](tasks/123_file-outline-total-count-is-the-page-length.md) | Agent-trust | done | 014, 057, 066, 067 |
| 124 | [`find_orphans` blew the transport limit at 19k files, on the one ticket whose root cause *was* an orphan](tasks/124_find-orphans-cannot-answer-at-scale.md) | Agent-fit | done | 031, 057, 066, 119 |
| 125 | [No payload names the server build — every field retro is told its own subject by an operator](tasks/125_no-payload-names-the-server-build.md) | Measure | done | 082, 095, 100 |
| 128 | [TypeScript/JavaScript — M0 spike only, to answer §4.4 with evidence](tasks/128_typescript-adapter-m0-spike.md) | Phase 2 / M7 | todo | 012, 019 |
| 129 | [`include_graph(imports)` is a silent zero for any namespaced file — the INCLUDES edge is anchored on the namespace](tasks/129_include_graph_imports-is-a-silent-zero-for-a-namespaced-file.md) | Agent-trust | done | 121 |
| 132 | [The doc set costs an agent ~66k tokens before it knows what binds it — give every standing doc a boundary](tasks/132_docs-restructure.md) | Docs | done | — |
| 133 | [The always-binding read is ~66.5k tokens and most of it is reference — tier the agent chain and gate the tier](tasks/133_agent-chain-is-one-tier.md) | Docs | in-progress | 132 |
| 134 | [The standing docs grew to 66k tokens of mostly retold narrative — prune them and gate the size](tasks/134_standing-docs-grow-and-nothing-prunes-them.md) | Docs | done | 132 |
| 135 | [The recall gate cannot see a wrong answer — an answer with every expected row plus four wrong ones scores 1.0](tasks/135_harness-scores-recall-but-never-precision.md) | Measure | done | 055, 121, 130 |
| 136 | [Two thirds of the graph's edges are HEURISTIC, the plan promises the fix, and no ticket ever carried it](tasks/136_heuristic-share-has-no-owner.md) | Coverage | todo | 025, 029, 011 |

## Open work — Pillar 2 · Onboarding

The rendering of what the code actually is, for a human supervising an agent or presenting the
project ([PLAN §1](PLAN.md#1-goals--non-goals)). Same graph, no second pipeline.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 083 | [Onboarding — deterministic graph-metrics foundation](tasks/083_onboarding-graph-metrics.md) | Phase 3 / M10 | done | 014, 031, 017 |
| 084 | [Onboarding — architectural layer assignment](tasks/084_onboarding-layer-assignment.md) | Phase 3 / M10 | done | 083 |
| 103 | [Onboarding — layer granularity: strip common prefix, group by top segment](tasks/103_onboarding-layer-granularity.md) | Phase 3 / M10 | done | 084 |
| 104 | [Onboarding — fix the layer collapse (F1): group beneath the dominant subtree](tasks/104_onboarding-layer-signal.md) | Phase 3 / M10 | blocked | 103 |
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
| 118 | [Onboarding — every module page says `Summary: (none)`, and the cause is the seam, not the repo](tasks/118_module-summary-seam-gets-empty-facts.md) | Phase 3 / M11 | todo | 085, 090, 107, 117 |
| 119 | [Onboarding — the reachability split never says which signal produced each count](tasks/119_reachability-signal-provenance.md) | Phase 3 / M11 | done | 113, 116 |
| 121 | [Phase 3 shipped without its own cost gate — the onboarding question-class was never added to the harness](tasks/121_onboarding-question-class-never-measured.md) | Measure | done | 034, 045, 055, 086, 087, 088 |
| 126 | [Onboarding — the map's search palette clusters into one subtree](tasks/126_search-palette-clusters-into-one-subtree.md) | Phase 3 / M11 | done | 067, 115, 116 |
| 127 | [Onboarding — a caveat the dataset carries can vanish in the rendered map](tasks/127_caveats-drop-at-the-artifact-layer.md) | Phase 3 / M11 | done | 100, 112, 113, 116, 119 |
| 130 | [The `web_entry` bucket counts test controllers as web surface — half the count on a canonical repo](tasks/130_web-entry-bucket-counts-test-controllers.md) | Phase 3 / M11 | todo | 113, 119, 121 |
| 131 | [`guided_tour`'s first five stops are lint and bootstrap config, not the front controller](tasks/131_tour-ranks-configuration-ahead-of-the-front-controller.md) | Phase 3 / M11 | todo | 111, 121 |


**Round ordering, and what each round left open.** One line each; the narratives live in
[`FEEDBACK.md`](FEEDBACK.md) (external review rounds), [PLAN §19](PLAN.md#19-project-context--decision-log)
(decisions), [`LESSONS.md`](LESSONS.md) (per-ticket lessons) and `benchmarks/` (numbers).

| Round | Tickets | State |
|---|---|---|
| 4 (2026-08-10) | 075–082 | closed — round 5 verified 7 of 8 fixed, 081 `NOT OBSERVED` |
| 5 (2026-08-14) | 092–097 | closed — first round with mechanism questions |
| 5 interview | 099–102 | closed — the subject is the agent, not the repository (§19) |
| 6 (2026-08-21) | 122–125 | closed — all four payload honesty, none a graph defect |
| 7 (2026-08-23) | 126 · 127 | closed — 127 closed **119** in the same change |
| Phase 3 cost gate | 121 → 129 · 130 · 131 | 121 done; 130 · 131 open |

**What still governs open work:**

- **098 is `deferred` behind an evidence gate, not queued.** The demand is real and comes from the
  first production user, but the relation is that repository's shape, and a general server cannot
  spend schema every user inherits on **n = 1**. The gate is written into the ticket: a second
  independent repo, zero cost when undeclared, a cheaper alternative rejected in writing. **120** is
  held to the same discipline — its naive attribution was wrong by 5.7× and its need is still n = 1.
- **104 stays `blocked` because 105 superseded its approach** (dominant subtree elected by graph mass,
  not file count — proven on the three pinned repos), not because it waits on anything. Its AC2 names
  the anchor monorepo, and three public repos are not that repo.
- **118 is the hard prerequisite for auto-generated docs.** The contract carries no doc field, so a
  docblock cannot reach a summarizer: a `contract_version` bump plus a conformance test in one change
  (R3.1).
- **121's verdict is split, and it narrows the phase.** Cheap and correct where the question is a
  lookup (12/12, recall 1.0, fixture aggregate 0.29 → 0.789), **wrong where it is a reading order** —
  `guided_tour` opened `symfony/demo` with a lint config and put the front controller fifth. Numbers:
  [`benchmarks/121_onboarding-question-class.md`](benchmarks/121_onboarding-question-class.md).
  Auto-generated docs and diagrams stay unscheduled: that verdict licenses neither.
- **128 (TS/JS M0 spike) is independent** of the open Pillar-2 work and may run in parallel — as a
  *proposal* about §19's ordering, not a decision. Phase 2 breadth stays deferred.
- **The two things round 6 measured now have tickets.** `edge_health` HEURISTIC, unmoved at 63.8 %
  across two rounds and ~20 tasks, is **136**. Round 6's most valuable result came from a question the
  evaluator **never asked**, which no benchmark scoring "given question Q, did the tool return A" can
  see — the reachable half of that is **135**, the precision the recall gate cannot see.
- **074 must not claim** an answer-quality comparison against a language server: the anchor's resident
  LSP was uninstalled 2026-08-07 and invoked zero times in 84 calls, so its 19 % adoption figure
  measures adoption, not capability. Its core still needs the anchor repo; round 5 is its n = 1
  (verdict *helped, narrowly*).
- **M10–M12 are complete** — 17 tools on the surface — and the 108–117 reshape is complete: the map
  renders from 112's dataset alone. Detail: [`ROADMAP.md`](phase3-onboarding/ROADMAP.md).

## Phase 2 — More languages (deferred — §19 pivot, 2026-08-04)

**Deferred, not cancelled** (human-ratified 2026-08-04). Breadth waits until the PHP agent-loop is
complete — depth before breadth, because a large private PHP monorepo is the anchor for testing *and*
evaluation (§19). The language *order* is unchanged (§18.2).

| # | Task | Milestone | Status | Depends on |
|---|---|---|---|---|
| 019 | [TypeScript/JavaScript adapter + contract v2](tasks/019_typescript-adapter.md) | M7 | deferred | 012, 011 |
| 020 | [Python adapter](tasks/020_python-adapter.md) | M8 | deferred | 019 |
| 021 | [C#/.NET adapter](tasks/021_csharp-adapter.md) | M9 | deferred | 019 |
| 026 | [Inverse Docker path rebase (adapter #2)](tasks/026_docker-inverse-path-rebase.md) | M7 | deferred | 008, 019 |

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

Consumer = an AI agent in a terminal; baseline = grep+`Read`. **All of 032–042 landed**; source
[`FEEDBACK.md`](FEEDBACK.md). **Editing tools are permanently out** (ceded to native `Edit`, §1/§19),
and tool *consolidation* (`find_relations`) was measured behind 034 and rejected (§19).

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

Surfaced by a full-build validation against a **large private PHP monorepo** (~40k PHP files, PHP 8.5,
Docker adapter) and then by four field-retro rounds run on that same anchor repo. Open tickets from
this track are in [Open work — Pillar 1](#open-work--pillar-1--graph) and
[Pillar 2](#open-work--pillar-2--onboarding); everything below has landed.

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

One line each. Full narratives in [PLAN §19](PLAN.md#19-project-context--decision-log) (round 4, the
memory run, the founding-premise benchmark), [`FEEDBACK.md`](FEEDBACK.md) (external review rounds) and
[`LESSONS.md`](LESSONS.md) (per-ticket engineering lessons).

| Source | Tickets | Headline |
|---|---|---|
| Field retro 1 (`v0.1.0`, `e117b47`) | 047–049 | Zero graph queries in a multi-hour session — the defect lived in string-keyed controller→template data flow, which the index does not model |
| Same day | 050–051 | A schema-version error was read as a corrupt index and the session fell back to `grep`; verifying the rebuild found the build reporting 949,808 edges against 1,775,812 |
| Field retro 2 | 054–061 | First session to exercise the graph: **three ways an empty result reads as proof of absence**, one reporting no callers for a method with six live sites |
| Field retro 3 (2026-08-09) | 065–070 | Blind to prior findings; what the graph competed for it won (`find_callers` 23/23, 8/8 hand-verified). Sharpest point: 066 + 067 made a *fully correct* tool a net loss |
| Memory & concurrency run (`869dcc6`) | 071–073 | **Memory is a non-finding** (n-th agent ~70 MB PSS, the 925 MB index 0 MB). All three defects are about what an answer *claims* — a worktree agent got the main checkout's symbol with `reason: "ok"` |
| Freshness review (not a session) | 052–053 | Of four layers keeping an index current, only `build_or_update_index(full=false)` has no trigger; 052 gates 053 |
| Field retro 4 (2026-08-10) | 075–082 | First verification round: 7 fixed, 2 improved, 1 reproduced, 2 not exercised. Both findings that mattered came from *outside* the verification section, which is a regression harness |
| Field retro 5 (2026-08-14) | 092–097 | First round where **cost changed what was asked** (1 call in three hours of writing code, each refresh ~60 s). 8/8 checked claims exact — every failure was silence or ambiguity |
| Field **interview** (2026-08-14) | 099–101 (+098 gated) | Retracted the round's headline, and found what four rounds of routing work had missed: **all three decisions made without the graph wanted one line inside a `Read` already happening** |
| Measured while building 100 | 102 | `impact` returns `results=0 seeds_dropped=0` for a subject not in the index — the identical pair a genuine modelled zero returns |
| PLAN §19 threats paragraph | 074 | The founding-premise benchmark ran one mechanism question twice and got opposite verdicts, the denied run right — the only datapoint suggesting the index costs *accuracy* |

Two notes that still govern open work, beyond the constraints listed above:

- **Round 4's two self-corrections:** `code-atlas-refresh` *is* a reachable second builder, so 072's
  `busy` payload is exercisable and the gap is affordance (→ 082); and 069's descriptions half **did**
  work, so 081 is about the prompt *channel*, not the description content.
- **One un-evidenced claim, not a code-atlas defect:** the anchor repo's `CLAUDE.md` asserts `grep`
  "times out" and costs "~650× the tokens"; round 3 observed neither. Needs evidence or removal.

## Follow-ups (not yet ticketed)

One line each, with the pointer that holds the detail. Nothing here is scheduled.

- **Resolver: link `IMPORTS`** so `find_references` sees `use` statements — `IMPORTS ∉ contract.FQN_EDGE_KINDS`, so the resolver never links it. Filed from [PR #23](https://github.com/cuongdinhngo/code-atlas/pull/23); docstring note in `code_atlas/tools/find_references.py`.
- **PSR-4 / autoload-aware include resolution** — `include_graph` is near-empty on Composer-autoloaded repos, whose only `INCLUDES` edges are dynamic bootstrap `require`s. Found in [042](tasks/042_tokens-to-answer-sample-tier.md); duplicate-name disambiguation across PSR-0 roots is open with it.
- **`max_results` does two unrelated jobs** — it caps both returned rows and the resolver's per-call-site candidate fan-out, so a query knob silently sets index size (anchor: 4.76M heuristic edges at cap 50 vs 2.60M at cap 10). A `CA_RESOLVE_MAX_CANDIDATES` would separate them, and no payload states which meaning is in force. [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4.
- **Tokens-to-answer measures cost, not information** — proven blind by 046: removing 1.06M duplicate edges doubled the distinct answers in a 10-row response and moved the ratio by 0.02 %. Worth a second axis (distinct answers per response, or rank-of-first-correct) before the ratio judges a retrieval change.
- **`reachable_from` payload size at `standard`** — bounded by `impact_max_nodes` (500), so ~160 KB of JSON against a metric measured in tokens. Worth a lower default or a `minimal`-by-default shape; workaround in [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4.
- **Parser-OOM size cap (optional)** — multi-MB generated files exhaust the PHP parser; already soft-failed and restarted (`indexer.py`), but a byte-cap pre-skip (`CA_MAX_FILE_BYTES`) would avoid ~30 crash-and-restart cycles on the anchor. Log what is skipped; no silent truncation.
- **Adapter-subprocess test harness on Windows (bug)** — `CA_*_CMD` is built with POSIX quoting and split with `posix=False`, so quoted paths reach `CreateProcess` verbatim → `WinError 2`. Fails ~56 adapter-launching tests on the Windows dev host, green on Linux. Surfaced by [043](tasks/043_duplicate-decl-resilience.md).
- **043 AC1 end-to-end `full_build` dup test** — deferred at Gate 4 as an approved coverage-gap exclusion, blocked by the Windows harness bug above; the surface is already proven at the `_write`+store layer.
- **PHP-adapter duplicate-declaration fixture (optional)** — the adapter already emits per-declaration, so this only pins it.
- **015 AC2 operator run** — a real `CODE_ATLAS_SCALE_SAMPLE` timing artifact against the ~112k checkout, folded into [018](tasks/018_cross-repo-validation.md) as optional A4. Needs an operator machine with the private checkout.
- **018 construct gaps** — cross-repo misses feed the (still empty) gap log in [`runbooks/cross-repo-validation.md`](runbooks/cross-repo-validation.md) and tasks 007 / 025.
- **CI tightenings deferred from the drift audit** — `requires-python = ">=3.12"` is open-ended while the matrix stops at 3.13; `scripts/` is outside `[tool.mypy] files`, so the gate logic in `scripts/tokens_to_answer.py` is unchecked; `checkout@v4` / `setup-python@v5` are a major behind with no `dependabot.yml`.
- **Docker images are never built by CI** — `docker/Dockerfile` (the test image AGENTS.md points agents at) is built by nothing and can rot silently, while `Dockerfile.runtime` *is* built inside `pytest`. The honest shape is one docker job building both. Moot while Actions is unbillable, but it survives that.
- **GitHub Actions has not run since 2026-08-22** — private repo, no Actions budget, every job fails in seconds with no logs. `scripts/gate.sh` reproduced locally is the standing arrangement, not a lapse — but it is a human step, so a CI-only gate is currently off.

## Token usage

Token spend per task, recorded before its PR is opened
([`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) R7.2); the per-phase breakdown lives in each
task's `tasks/NNN_slug.work.md`
ledger. mango measures **subagent dispatch only**: `unmeasured` = the host surfaced no usage block, and
**main-loop spend is unmeasured unless a fresh/cache figure is given** (`rtk gain` is global and cannot
be attributed to one task, so nothing is invented). `no work doc` = the task skipped the mango
lifecycle. Fresh = input + output + cache-creation; cache reads are billed differently and listed apart.

| # | Tokens | PR |
|---|---|---|
| 001 | 113.6k dispatch (reviewer 70.9k + challenger 42.7k) | [#2](https://github.com/cuongdinhngo/code-atlas/pull/2) |
| 002 | **689.2k fresh** (239.8k out) + 27.12M cache / 164 calls; 0 dispatch | [#4](https://github.com/cuongdinhngo/code-atlas/pull/4) |
| 003 | **638.3k fresh** (223.3k out) + 24.4M cache / 167 calls; + 52.4k dispatch (7.6% — the main loop is the driver) | [#5](https://github.com/cuongdinhngo/code-atlas/pull/5) |
| 004 | 78.1k dispatch (challenger, 27 / 313 s) | [#7](https://github.com/cuongdinhngo/code-atlas/pull/7) |
| 005 | 181.6k dispatch — reviewer 108.9k (38 / 426 s) + challenger 72.7k (27 / 286 s) | [#10](https://github.com/cuongdinhngo/code-atlas/pull/10) |
| 006 | 73.9k dispatch (challenger, 34 / 228 s) | [#13](https://github.com/cuongdinhngo/code-atlas/pull/13) |
| 024 | 0 dispatch; main-loop unmeasured; no work doc | [#14](https://github.com/cuongdinhngo/code-atlas/pull/14) |
| 007 | 111.4k dispatch (challenger, 41 / 380 s) | [#16](https://github.com/cuongdinhngo/code-atlas/pull/16) |
| 009 | 96.3k dispatch (challenger, 30 / 380 s) | [#17](https://github.com/cuongdinhngo/code-atlas/pull/17) |
| 010 | 64.6k dispatch (challenger, 31 / 284 s) | [#18](https://github.com/cuongdinhngo/code-atlas/pull/18) |
| 011 | 2 dispatch, unmeasured | [#19](https://github.com/cuongdinhngo/code-atlas/pull/19) |
| 008 | 4 dispatch, unmeasured | [#20](https://github.com/cuongdinhngo/code-atlas/pull/20) |
| 025 | 4 dispatch unmeasured, + a round-3 ticket-blind challenger **112.6k** (32 / 489 s) — the cell that found the `:col` drift | [#21](https://github.com/cuongdinhngo/code-atlas/pull/21) |
| 012 | 4 dispatch, unmeasured | [#22](https://github.com/cuongdinhngo/code-atlas/pull/22) |
| 013 | 3 dispatch, unmeasured | [#23](https://github.com/cuongdinhngo/code-atlas/pull/23) |
| 014 | 3 dispatch, unmeasured | [#24](https://github.com/cuongdinhngo/code-atlas/pull/24) |
| 015 | 3 dispatch, unmeasured | [#25](https://github.com/cuongdinhngo/code-atlas/pull/25) |
| 016 | 4 dispatch, unmeasured | [#26](https://github.com/cuongdinhngo/code-atlas/pull/26) |
| 017 | 6 dispatch (reviewer ×3 + challenger ×2 + refine), unmeasured | [#27](https://github.com/cuongdinhngo/code-atlas/pull/27) |
| 018 | 3 dispatch, unmeasured | [#28](https://github.com/cuongdinhngo/code-atlas/pull/28) |
| 027 | 4 dispatch, unmeasured | [#30](https://github.com/cuongdinhngo/code-atlas/pull/30) |
| 028 | 2 dispatch, unmeasured | [#31](https://github.com/cuongdinhngo/code-atlas/pull/31) |
| 029 | 5 dispatch, unmeasured | [#32](https://github.com/cuongdinhngo/code-atlas/pull/32) |
| 030 | 5 dispatch, unmeasured | [#33](https://github.com/cuongdinhngo/code-atlas/pull/33) |
| 031 | 3 dispatch, unmeasured | [#34](https://github.com/cuongdinhngo/code-atlas/pull/34) |
| 032 | 0 dispatch; main-loop unmeasured | [#36](https://github.com/cuongdinhngo/code-atlas/pull/36) |
| 034 | 0 dispatch; main-loop unmeasured; no work doc | [#37](https://github.com/cuongdinhngo/code-atlas/pull/37) |
| 033 | 3 dispatch, unmeasured | [#40](https://github.com/cuongdinhngo/code-atlas/pull/40) |
| 035 | 4 dispatch, unmeasured | [#41](https://github.com/cuongdinhngo/code-atlas/pull/41) |
| 036 | 4 dispatch, unmeasured | [#42](https://github.com/cuongdinhngo/code-atlas/pull/42) |
| 037 | **242.7k dispatch, all measured** — challenger 61.9k (32 / 336 s) + reviewer 106.5k (42 / 595 s) + reviewer r2 74.2k (39 / 433 s) | [#43](https://github.com/cuongdinhngo/code-atlas/pull/43) |
| 038 | 4 dispatch, unmeasured | [#44](https://github.com/cuongdinhngo/code-atlas/pull/44) |
| 039 | 5 dispatch, unmeasured | [#45](https://github.com/cuongdinhngo/code-atlas/pull/45) |
| 040 | 4 dispatch, unmeasured | [#46](https://github.com/cuongdinhngo/code-atlas/pull/46) |
| 041 | 4 dispatch, unmeasured | [#47](https://github.com/cuongdinhngo/code-atlas/pull/47) |
| 042 | **134.4k dispatch, measured** — reviewer 85.6k (22 / 266 s) + challenger 48.8k (25 / 234 s) | [#48](https://github.com/cuongdinhngo/code-atlas/pull/48) |
| 043 | **150.7k dispatch, measured** — reviewer 86.4k (28 / 326 s) + challenger 64.3k (28 / 285 s) | [#49](https://github.com/cuongdinhngo/code-atlas/pull/49) |
| 044 | 0 dispatch; main-loop unmeasured; no work doc | [#50](https://github.com/cuongdinhngo/code-atlas/pull/50) |
| 045 | 0 dispatch; main-loop unmeasured; no work doc | [#51](https://github.com/cuongdinhngo/code-atlas/pull/51) |
| 046 | 0 dispatch; main-loop unmeasured; no work doc | [#52](https://github.com/cuongdinhngo/code-atlas/pull/52) |
| 047 | 0 dispatch; main-loop unmeasured | [#56](https://github.com/cuongdinhngo/code-atlas/pull/56) |
| 048 | 0 dispatch; main-loop unmeasured | [#55](https://github.com/cuongdinhngo/code-atlas/pull/55) |
| 049 | 0 dispatch; main-loop unmeasured | [#57](https://github.com/cuongdinhngo/code-atlas/pull/57) |
| 050 | 0 dispatch; main-loop unmeasured | [#58](https://github.com/cuongdinhngo/code-atlas/pull/58) |
| 051 | 0 dispatch; main-loop unmeasured | [#60](https://github.com/cuongdinhngo/code-atlas/pull/60) |
| — | Ticket-writing for 051: **39.5k fresh** (13.5k out) + 3.3M cache / 23 calls | [#59](https://github.com/cuongdinhngo/code-atlas/pull/59) |
| — | Ticket-writing + the field retro that produced 047–049: **45.6k fresh** / 28 calls for the tickets, plus **1.84M fresh** (503.0k out) + 122.2M cache / 576 calls for the retro, the 049 design measurement and everything before the first commit — not attributable to one task. | — |
| — | Ticket-writing for 052 + 053: **463.1k fresh** (58.7k out) + 6.7M cache / 72 calls, one inseparable pass. **Recorded late** | [#54](https://github.com/cuongdinhngo/code-atlas/pull/54) |
| — | Ticket-writing for 054: **356.0k fresh** (139.5k out) + 17.2M cache / 104 calls — **also produced the 055–061 tickets** | [#61](https://github.com/cuongdinhngo/code-atlas/pull/61) |
| — | Ticket-writing for 055–061: **30.2k fresh** (8.0k out) + 2.6M cache / 11 calls — tail only; honest total with the row above is **386.2k fresh / 115 calls**. | [#62](https://github.com/cuongdinhngo/code-atlas/pull/62) |
| — | Ticket-writing for 064–070: **384.8k fresh** (117.1k out) + 11.8M cache / 136 calls — also the contract-v5 rebuild, the round-3 retro, and reproducing every claim before ticketing. | [#77](https://github.com/cuongdinhngo/code-atlas/pull/77) |
| — | Ticket-writing for 071–074 + the memory/concurrency run: **222.0k fresh** (58.3k out) + 5.9M cache / 56 calls. | [#78](https://github.com/cuongdinhngo/code-atlas/pull/78) |
| — | The founding-premise benchmark + the PLAN §19 decision: **549.6k fresh** (105.4k out) + 7.6M cache / 100 calls. | [#62](https://github.com/cuongdinhngo/code-atlas/pull/62) |
| 059 | 2 dispatch, unmeasured | [#63](https://github.com/cuongdinhngo/code-atlas/pull/63) |
| 055 | 5 dispatch, unmeasured | [#64](https://github.com/cuongdinhngo/code-atlas/pull/64) |
| 054 | 4 dispatch, unmeasured | [#65](https://github.com/cuongdinhngo/code-atlas/pull/65) |
| 056 | 3 dispatch, unmeasured | [#66](https://github.com/cuongdinhngo/code-atlas/pull/66) |
| 057 | 4 dispatch, unmeasured | [#67](https://github.com/cuongdinhngo/code-atlas/pull/67) |
| 058 | 3 dispatch, unmeasured | [#68](https://github.com/cuongdinhngo/code-atlas/pull/68) |
| 060 | 3 dispatch, unmeasured | [#69](https://github.com/cuongdinhngo/code-atlas/pull/69) |
| 052 | 5 dispatch (review rounds 1–2), unmeasured | [#70](https://github.com/cuongdinhngo/code-atlas/pull/70) |
| 053 | 5 dispatch (review rounds 1–2), unmeasured | [#71](https://github.com/cuongdinhngo/code-atlas/pull/71) |
| 061 | 5 dispatch (review rounds 1–2), unmeasured | [#72](https://github.com/cuongdinhngo/code-atlas/pull/72) |
| 062 | 6 dispatch, unmeasured | [#73](https://github.com/cuongdinhngo/code-atlas/pull/73) |
| 063 | 6 dispatch, unmeasured | [#75](https://github.com/cuongdinhngo/code-atlas/pull/75) |
| 064 | 0 dispatch (review waived); main-loop unmeasured | [#79](https://github.com/cuongdinhngo/code-atlas/pull/79), [#80](https://github.com/cuongdinhngo/code-atlas/pull/80) |
| 065 | 2 dispatch, unmeasured. Post-PR review fixed a red `mypy` gate + the reason missing on `both` | [#81](https://github.com/cuongdinhngo/code-atlas/pull/81) |
| 073 | 2 dispatch, unmeasured. Post-PR review found miss-repair firing on an empty *page* | [#82](https://github.com/cuongdinhngo/code-atlas/pull/82) |
| — | CI drift audit (no ticket, no work doc): 0 dispatch — three workflows re-read, one benchmark re-measured, full `pytest` | [#83](https://github.com/cuongdinhngo/code-atlas/pull/83) |
| 071 | 2 dispatch, unmeasured. | [#84](https://github.com/cuongdinhngo/code-atlas/pull/84) |
| 068 | 2 dispatch, unmeasured. Post-PR review removed two dead reconcile exemptions + an absence-proving test | [#85](https://github.com/cuongdinhngo/code-atlas/pull/85) |
| 067 | 0 dispatch (review waived); main-loop unmeasured | [#86](https://github.com/cuongdinhngo/code-atlas/pull/86) |
| 066 | 0 dispatch (review waived); main-loop unmeasured | [#87](https://github.com/cuongdinhngo/code-atlas/pull/87) |
| 072 | 0 dispatch (review waived); main-loop unmeasured | [#89](https://github.com/cuongdinhngo/code-atlas/pull/89) |
| 070 | **78.5k dispatch** — 1 analysis Explore (17 / 126 s); review waived | [#91](https://github.com/cuongdinhngo/code-atlas/pull/91) |
| 069 | **113.7k dispatch** — analysis Explore 88.3k (40 / 227 s) + an execute blind-reader routing exercise 25.3k; review waived | [#92](https://github.com/cuongdinhngo/code-atlas/pull/92) |
| 074 | 0 dispatch; main-loop unmeasured | [#93](https://github.com/cuongdinhngo/code-atlas/pull/93) |
| 075 | 0 dispatch (review waived); main-loop unmeasured | [#94](https://github.com/cuongdinhngo/code-atlas/pull/94) |
| 076 | 0 dispatch; main-loop unmeasured | [#94](https://github.com/cuongdinhngo/code-atlas/pull/94) |
| 077 | 2 dispatch, unmeasured (explore + exposure-checker); review waived | [#96](https://github.com/cuongdinhngo/code-atlas/pull/96) |
| 078 | 2 dispatch, unmeasured (explore + exposure-checker); review waived | [#97](https://github.com/cuongdinhngo/code-atlas/pull/97) |
| 079 | 0 dispatch (review waived); main-loop unmeasured | [#98](https://github.com/cuongdinhngo/code-atlas/pull/98) |
| 082 | 1 dispatch — refine exposure-checker **50.5k** (9 tool-uses, 154 s); review waived. Docker runs for delta-green (full gate **1134 passed**) | [#99](https://github.com/cuongdinhngo/code-atlas/pull/99) |
| 081 | 1 dispatch — refine exposure-checker **60.4k** (17 tool-uses, 194 s); review waived. Docker runs for delta-green (full gate **1137 passed**) | [#100](https://github.com/cuongdinhngo/code-atlas/pull/100) |
| 080 | 1 dispatch — refine exposure-checker **57.8k** (8 tool-uses, 187 s); review waived. | [#101](https://github.com/cuongdinhngo/code-atlas/pull/101) |
| 092 | 1 dispatch — refine exposure-checker unmeasured (blocking retrieval); review waived at solve time, then done on the PR (0 dispatch, in-session). | [#102](https://github.com/cuongdinhngo/code-atlas/pull/102) |
| 093 | 1 dispatch — `/code-review` on the PR **61.7k** (20 tool-uses, 205 s); refine skipped (0 unresolved product-decisions), review waived at solve time then run on the PR. | [#103](https://github.com/cuongdinhngo/code-atlas/pull/103) |
| 095 | 1 dispatch — refine exposure-checker unmeasured (host does not surface usage); review waived at solve time. | [#105](https://github.com/cuongdinhngo/code-atlas/pull/105) |
| 097 | 1 dispatch — refine exposure-checker unmeasured (host does not surface usage); review waived at solve time. | [#107](https://github.com/cuongdinhngo/code-atlas/pull/107) |
| 094 | 1 dispatch — refine exposure-checker unmeasured (host does not surface usage); review waived at solve time, then run on the PR (0 dispatch, in-session — caught `self`/`static`/`parent``::class` emitting `\self`). | [#108](https://github.com/cuongdinhngo/code-atlas/pull/108) |
| 096 | 0 dispatch (review waived); main-loop unmeasured | [#110](https://github.com/cuongdinhngo/code-atlas/pull/110) |
| 099 | 0 dispatch (review waived); main-loop unmeasured | [#111](https://github.com/cuongdinhngo/code-atlas/pull/111) |
| — | CI red on `main` after #108: profiler wall-tolerance floor. | [#109](https://github.com/cuongdinhngo/code-atlas/pull/109) |
| 100 | **296.0k dispatch, all measured** — `mango:reviewer` r1 134.9k (54 tool-uses, 649 s) + r2 verify 161.1k (16 / 272 s); main-loop unmeasured. | [#114](https://github.com/cuongdinhngo/code-atlas/pull/114) |
| 101 | **139.2k dispatch, all measured**; main-loop unmeasured. | [#116](https://github.com/cuongdinhngo/code-atlas/pull/116) |
| 102 | **89.4k dispatch, all measured**; main-loop unmeasured. | [#117](https://github.com/cuongdinhngo/code-atlas/pull/117) |
| — | Ticket-writing for 102: 0 dispatch; the defect was measured during 100, not by a separate run | [#115](https://github.com/cuongdinhngo/code-atlas/pull/115) |
| — | Field retro round 4 + ticket-writing for 075–082: 0 dispatch. | — |
| 083 | **65.4k dispatch, measured** — `mango:reviewer` r1 65.4k (30 tool-uses, 233 s) → LGTM, no findings; main-loop unmeasured. | [#120](https://github.com/cuongdinhngo/code-atlas/pull/120) |
| 084 | **124.4k dispatch, measured**; main-loop unmeasured. | [#121](https://github.com/cuongdinhngo/code-atlas/pull/121) |
| 103 | **175.4k dispatch, all measured**; main-loop unmeasured. | [#122](https://github.com/cuongdinhngo/code-atlas/pull/122) |
| 104 | **91.8k dispatch, measured**; main-loop unmeasured. | [#123](https://github.com/cuongdinhngo/code-atlas/pull/123) |
| 085 | **136.5k dispatch, measured**; main-loop unmeasured. | [#124](https://github.com/cuongdinhngo/code-atlas/pull/124) |
| 086 | 0 dispatch (review waived); main-loop unmeasured | [#125](https://github.com/cuongdinhngo/code-atlas/pull/125) |
| 087 | 0 dispatch (review waived); main-loop unmeasured | [#126](https://github.com/cuongdinhngo/code-atlas/pull/126) |
| 088 | 0 dispatch (review waived); main-loop unmeasured | [#127](https://github.com/cuongdinhngo/code-atlas/pull/127) |
| 089 | 0 dispatch (review waived); main-loop unmeasured | [#128](https://github.com/cuongdinhngo/code-atlas/pull/128) |
| 090 | 0 dispatch (review waived); main-loop unmeasured | [#129](https://github.com/cuongdinhngo/code-atlas/pull/129) |
| 105 | 0 dispatch (review waived); main-loop unmeasured | [#131](https://github.com/cuongdinhngo/code-atlas/pull/131) |
| 091 | 0 dispatch (review waived); main-loop unmeasured | [#130](https://github.com/cuongdinhngo/code-atlas/pull/130) |
| 106 | 0 dispatch (review waived); main-loop unmeasured | [#132](https://github.com/cuongdinhngo/code-atlas/pull/132) |
| 107 | 0 dispatch (review waived); main-loop unmeasured | [#133](https://github.com/cuongdinhngo/code-atlas/pull/133) |
| 108 | 0 dispatch (review waived); main-loop unmeasured | [#135](https://github.com/cuongdinhngo/code-atlas/pull/135) |
| 110 | **95.3k dispatch, measured**; main-loop unmeasured. | [#137](https://github.com/cuongdinhngo/code-atlas/pull/137) |
| 109 | 0 dispatch (review waived); main-loop unmeasured | [#136](https://github.com/cuongdinhngo/code-atlas/pull/136) |
| 111 | **61.6k dispatch, measured**; main-loop unmeasured. | [#138](https://github.com/cuongdinhngo/code-atlas/pull/138) |
| 112 | **116.0k dispatch, measured**; main-loop unmeasured. | [#139](https://github.com/cuongdinhngo/code-atlas/pull/139) |
| 113 | 0 dispatch (review waived); main-loop unmeasured | [#140](https://github.com/cuongdinhngo/code-atlas/pull/140) |
| 114 | 0 dispatch (review waived); main-loop unmeasured | [#141](https://github.com/cuongdinhngo/code-atlas/pull/141) |
| 115 | 0 dispatch (review waived); main-loop unmeasured | [#142](https://github.com/cuongdinhngo/code-atlas/pull/142) |
| 116 | 0 dispatch (review waived); main-loop unmeasured | [#143](https://github.com/cuongdinhngo/code-atlas/pull/143) |
| 117 | 0 dispatch (review waived); main-loop unmeasured | [#144](https://github.com/cuongdinhngo/code-atlas/pull/144) |
| — | **Docs-truth sweep + four tickets authored (118 · 119 · 120 · 121).** 0 dispatch — main-loop only, **unmeasured** (the host surfaces no usage block); no mango lifecycle, so `no work doc`. | [#145](https://github.com/cuongdinhngo/code-atlas/pull/145) |
| — | **Round-6 retro triage + four tickets authored (122 · 123 · 124 · 125).** 0 dispatch — main-loop only, **unmeasured** (no usage block surfaced); no mango lifecycle, so `no work doc`. | [#146](https://github.com/cuongdinhngo/code-atlas/pull/146) |
| 122 | 0 dispatch (review waived); main-loop unmeasured | [#147](https://github.com/cuongdinhngo/code-atlas/pull/147) |
| 123 | 0 dispatch (review waived); main-loop unmeasured | [#148](https://github.com/cuongdinhngo/code-atlas/pull/148) |
| 124 | 0 dispatch (review waived); main-loop unmeasured | [#149](https://github.com/cuongdinhngo/code-atlas/pull/149) |
| 125 | 0 dispatch (review waived); main-loop unmeasured | [#150](https://github.com/cuongdinhngo/code-atlas/pull/150) |
| 126 | 0 dispatch (review waived); main-loop unmeasured | [#151](https://github.com/cuongdinhngo/code-atlas/pull/151) |
| 127 | 0 dispatch (review waived); main-loop unmeasured | [#151](https://github.com/cuongdinhngo/code-atlas/pull/151) |
| 121 | 0 dispatch; main-loop unmeasured | [#152](https://github.com/cuongdinhngo/code-atlas/pull/152) |
| 119 | 0 dispatch; main-loop unmeasured | [#151](https://github.com/cuongdinhngo/code-atlas/pull/151) |
| 132 | 0 dispatch; main-loop unmeasured | [#153](https://github.com/cuongdinhngo/code-atlas/pull/153) |
| 129 | 0 dispatch; main-loop unmeasured | [#154](https://github.com/cuongdinhngo/code-atlas/pull/154) |
| 134 | 0 dispatch; main-loop unmeasured | [#155](https://github.com/cuongdinhngo/code-atlas/pull/155) |
| 135 | 0 dispatch (no work doc); main-loop unmeasured. Two sample-tier clones (`symfony/demo`) and one pre-change re-run produced the before/after pair | [#156](https://github.com/cuongdinhngo/code-atlas/pull/156) |

**How 047–049 were measured.** One autonomous session, no per-task transcript: each row is the API
calls between the previous commit and that task's own commit. The approximation runs one way — work
interleaved across tasks lands in whichever segment it finished in (049 is the known case).

## Conventions
- Keep task `status` in this table **and** in each task file's frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
- Landed narrative belongs in [PLAN §19](PLAN.md#19-project-context--decision-log) or
  [`LESSONS.md`](LESSONS.md), not here; a follow-up that gets ticketed leaves this file's
  [Follow-ups](#follow-ups-not-yet-ticketed) list. This rule was written down and then ignored for
  ~180 lines of round narrative — it is now R7.6, with a ceiling in
  `tests/test_doc_size_budget.py`.
