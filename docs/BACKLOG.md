# Backlog — code-atlas

Task tracker. One file per task in [`docs/tasks/`](tasks/) (`NNN_slug.md`). Source of truth for scope
is [`PLAN.md`](PLAN.md); the durable decision log is [PLAN §19](PLAN.md#19-project-context--decision-log)
and the per-task engineering lessons are in [`LESSONS.md`](LESSONS.md). This file tracks *what is open
and what landed*; what each ticket cost is one row in [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) (R7.2) —
narrative rationale lives in those three.

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
| 120 | ["Can this subtree be deleted?" — subtree dependency with duplicate-declaration attribution](tasks/120_subtree-dependency-attribution.md) | Coverage | done | 017, 043, 078, 115 |
| 122 | [075 normalised the leading backslash for three tools; four `find_*` tools still decline over it](tasks/122_exact-miss-shaping-discards-a-resolved-subject.md) | Agent-trust | done | 075, 076, 065, 093 |
| 123 | [`file_outline` omitted the symbol under repair, reported `total_count: 10` for a 12-symbol file, and has no page 2](tasks/123_file-outline-total-count-is-the-page-length.md) | Agent-trust | done | 014, 057, 066, 067 |
| 124 | [`find_orphans` blew the transport limit at 19k files, on the one ticket whose root cause *was* an orphan](tasks/124_find-orphans-cannot-answer-at-scale.md) | Agent-fit | done | 031, 057, 066, 119 |
| 125 | [No payload names the server build — every field retro is told its own subject by an operator](tasks/125_no-payload-names-the-server-build.md) | Measure | done | 082, 095, 100 |
| 128 | [TypeScript/JavaScript — M0 spike only, to answer §4.4 with evidence](tasks/128_typescript-adapter-m0-spike.md) | Phase 2 / M7 | todo | 012, 147, 149 |
| 129 | [`include_graph(imports)` is a silent zero for any namespaced file — the INCLUDES edge is anchored on the namespace](tasks/129_include_graph_imports-is-a-silent-zero-for-a-namespaced-file.md) | Agent-trust | done | 121 |
| 132 | [The doc set costs an agent ~66k tokens before it knows what binds it — give every standing doc a boundary](tasks/132_docs-restructure.md) | Docs | done | — |
| 133 | [The always-binding read is ~66.5k tokens and most of it is reference — tier the agent chain and gate the tier](tasks/133_agent-chain-is-one-tier.md) | Docs | done | 132 |
| 134 | [The standing docs grew to 66k tokens of mostly retold narrative — prune them and gate the size](tasks/134_standing-docs-grow-and-nothing-prunes-them.md) | Docs | done | 132 |
| 135 | [The recall gate cannot see a wrong answer — an answer with every expected row plus four wrong ones scores 1.0](tasks/135_harness-scores-recall-but-never-precision.md) | Measure | done | 055, 121, 130 |
| 136 | [Two thirds of the graph's edges are HEURISTIC, the plan promises the fix, and no ticket ever carried it](tasks/136_heuristic-share-has-no-owner.md) | Coverage | done | 025, 029, 011 |
| 137 | [A PHP local type table — the cause of ≥99% of the HEURISTIC share, with a measured target per pin](tasks/137_php-local-type-table.md) | Coverage | done | 136, 039 |
| 140 | [`impact` answers in symbols, and the decision is module-shaped — 500 rows at ~160 KB is the only answer today](tasks/140_impact-answers-in-symbols-not-modules.md) | Agent-fit | done | 017, 112, 114, 124 |
| 141 | ["Can this module be split out?" — the cut edges and the cycles that block it — evidence-gated](tasks/141_extractability-cut-edges-and-the-cycles-that-block-it.md) | Coverage | deferred | 120, 087, 140 |
| 142 | [The supervision question class was never put through the harness — 121's lesson, one phase later](tasks/142_supervision-question-class-has-no-baseline.md) | Measure | todo | 034, 055, 121, 135 |

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
[`FEEDBACK.md`](FEEDBACK.md) (external review rounds), [PLAN §19](PLAN.md#19-project-context--decision-log)
(decisions), [`LESSONS.md`](LESSONS.md) (per-ticket lessons) and `benchmarks/` (numbers).

| Round | Tickets | State |
|---|---|---|
| 4 (2026-08-10) | 075–082 | closed — round 5 verified 7 of 8 fixed, 081 `NOT OBSERVED` |
| 5 (2026-08-14) | 092–097 | closed — first round with mechanism questions |
| 5 interview | 099–102 | closed — the subject is the agent, not the repository (§19) |
| 6 (2026-08-21) | 122–125 | closed — all four payload honesty, none a graph defect |
| 7 (2026-08-23) | 126 · 127 | closed — 127 closed **119** in the same change |
| Phase 3 cost gate | 121 → 129 · 130 · 131 | 121 · 129 · 130 · 131 done |
| Architecture review (2026-08-23) | 138–142 · 143–145 | 138 · 139 · 144 · **145A** done (artifact.json versioned); **143** layer mermaid; **142 still first for the class baseline**; 141 gated at n = 0; 145B deferred (stack not chosen; 118 no longer blocks) |

**What still governs open work:**

- **098 is `deferred` behind an evidence gate, not queued.** The demand is real and comes from the
  first production user, but the relation is that repository's shape, and a general server cannot
  spend schema every user inherits on **n = 1**. The gate is written into the ticket: a second
  independent repo, zero cost when undeclared, a cheaper alternative rejected in writing. **120**
  shipped after maintainer ratification of the evidence gate (anchor monorepo, n = 1).
- **104 stays `blocked` because 105 superseded its approach** (dominant subtree elected by graph mass,
  not file count — proven on the three pinned repos), not because it waits on anything. Its AC2 names
  the anchor monorepo, and three public repos are not that repo.
- **118 shipped** — module summaries now come from read-through docblocks at build time; `(none)` is
  replaced with an explicit file-attributed absence message when no doc comment exists.
- **121's verdict is split, and it narrows the phase.** Cheap and correct where the question is a
  lookup (12/12, recall 1.0, fixture aggregate 0.29 → 0.789); the lint/bootstrap tour opening is
  **closed by 131** (front controller now in the first five on `symfony/demo`). Numbers:
  [`benchmarks/121_onboarding-question-class.md`](benchmarks/121_onboarding-question-class.md).
  The **layer graph** is now a mermaid flowchart in `generate_onboarding` markdown ([143](tasks/143_the-system-map-has-no-diagram.md)) — a lookup, which 121 scored. Auto-generated *reading orders* stay unscheduled: a dependency walk is still not a curated syllabus.
- **128 (TS/JS M0 spike) now has prerequisites** — 147 and 149, not 019, whose `depends_on` it had
  backwards. It stays a *proposal* about §19's ordering, not a decision; Phase 2 breadth stays
  deferred, and 019 carries the rest of the breakdown unfiled for the same reason.
- **Both things round 6 measured are now closed, and both premises moved.** 135 gave the harness a
  precision axis; the recall gate could not see a wrong answer, and the first thing the axis does is
  fail on 130 ([benchmark](benchmarks/135_precision-axis.md)). 136 broke the HEURISTIC share down by
  cause: the tracked **63.8 %** turned out to name the private anchor repo and no committed pin
  (19–36 %), the cause is local type information (**≥99 %**, so §17's LSP defer covers ≤0.6 %), and the
  movable share is capped by `vendor/` coverage at **0 / 22.5 / 92.5 %** — hence **137**, with a
  measured target per pin ([benchmark](benchmarks/136_heuristic-causes.md)).
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

**147–149 are `todo`, not deferred, and they are not breadth work.** Two of them fix gates that
cannot fail today — `tests/contract/` admits exactly one adapter, and the R2.2 framework sweep lists
only PHP frameworks — and the third names the TS/JS construct inventory R6.2 requires. None parses a
line of TypeScript, so none of them reorders §19.

| # | Task | Milestone | Status | Depends on |
|---|---|---|---|---|
| 019 | [TypeScript/JavaScript adapter + a contract bump](tasks/019_typescript-adapter.md) | M7 | deferred | 012, 011, 128 |
| 020 | [Python adapter](tasks/020_python-adapter.md) | M8 | deferred | 019 |
| 021 | [C#/.NET adapter](tasks/021_csharp-adapter.md) | M9 | deferred | 019 |
| 026 | [Inverse Docker path rebase (adapter #2)](tasks/026_docker-inverse-path-rebase.md) | M7 | deferred | 008, 019 |
| 147 | [The R3.4 conformance harness is PHP-shaped — `tests/contract/` cannot admit a second adapter](tasks/147_contract-harness-is-php-shaped.md) | M7 | todo | 012, 025 |
| 148 | [The R2.2 framework sweep lists only PHP frameworks — it cannot fail for adapter #2](tasks/148_r22-framework-sweep-cannot-fail-for-adapter-2.md) | M7 | todo | 012, 146 |
| 149 | [Name the TS/JS construct inventory before any parsing exists](tasks/149_tsjs-construct-inventory.md) | M7 | todo | 147 |

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

## Conventions
- Keep task `status` in this table **and** in each task file's frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
- A task reaching `done` also gets its spend row in [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) (R7.2).
- Landed narrative belongs in [PLAN §19](PLAN.md#19-project-context--decision-log) or
  [`LESSONS.md`](LESSONS.md), not here; a follow-up that gets ticketed leaves this file's
  [Follow-ups](#follow-ups-not-yet-ticketed) list. This rule was written down and then ignored for
  ~180 lines of round narrative — it is now R7.6, with a ceiling in
  `tests/test_doc_size_budget.py`.
