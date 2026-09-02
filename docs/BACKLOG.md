# Backlog — code-atlas

Task tracker. One file per task in [`docs/tasks/`](tasks/) (`NNN_slug.md`). Source of truth for scope
is [`PLAN.md`](PLAN.md); the durable decision log is [PLAN §19](PLAN.md#19-project-context--decision-log)
and per-task lessons are in [`LESSONS.md`](LESSONS.md). This file tracks *what is open and what
landed*; each ticket's cost is one row in [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) (R7.2) — narrative
rationale lives in those three.

**A `done` row is titled by its slug, an open row by its finding.** The prose title of a closed ticket
is a second naming of what its own file already holds (R7.6), and every session pays for it; the slug
is derived from that file's name and cannot drift from it. Open rows keep the finding, because that
is what you read to choose the next ticket.

**Status legend:** `todo` · `in-progress` · `blocked` · `deferred` · `done`

## Open work — Pillar 1 · Graph

Resolved relationships for the agent, and the honesty of the payload that carries them
([PLAN §1](PLAN.md#1-goals--non-goals)). The `Theme` column is unchanged.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 074 | [Does the index harm mechanism questions? — no verdict](tasks/074_does-the-index-harm-mechanism-questions.md) | Measure | deferred | 055, 067, 045 |
| 098 | [Should the graph hold "this file is a copy/port of that one"? — evidence-gated](tasks/098_correspondence-relation-seam.md) | Coverage | deferred | 030, 011, 003 |
| 100 | [claim signing output mode](tasks/100_claim-signing-output-mode.md) | Agent-fit | done | 017, 057, 061 |
| 101 | [nav tools take one subject at a time](tasks/101_nav-tools-take-one-subject-at-a-time.md) | Agent-fit | done | 014, 013, 066 |
| 102 | [impact cannot tell an absent subject from a zero](tasks/102_impact-cannot-tell-an-absent-subject-from-a-zero.md) | Agent-fit | done | 017, 100 |
| 120 | [subtree dependency attribution](tasks/120_subtree-dependency-attribution.md) | Coverage | done | 017, 043, 078, 115 |
| 122 | [exact miss shaping discards a resolved subject](tasks/122_exact-miss-shaping-discards-a-resolved-subject.md) | Agent-trust | done | 075, 076, 065, 093 |
| 123 | [file outline total count is the page length](tasks/123_file-outline-total-count-is-the-page-length.md) | Agent-trust | done | 014, 057, 066, 067 |
| 124 | [find orphans cannot answer at scale](tasks/124_find-orphans-cannot-answer-at-scale.md) | Agent-fit | done | 031, 057, 066, 119 |
| 125 | [no payload names the server build](tasks/125_no-payload-names-the-server-build.md) | Measure | done | 082, 095, 100 |
| 128 | [typescript adapter m0 spike](tasks/128_typescript-adapter-m0-spike.md) | Phase 2 / M7 | done | 012, 147, 149 |
| 129 | [include_graph_imports is a silent zero for a namespaced file](tasks/129_include_graph_imports-is-a-silent-zero-for-a-namespaced-file.md) | Agent-trust | done | 121 |
| 132 | [docs restructure](tasks/132_docs-restructure.md) | Docs | done | — |
| 133 | [agent chain is one tier](tasks/133_agent-chain-is-one-tier.md) | Docs | done | 132 |
| 134 | [standing docs grow and nothing prunes them](tasks/134_standing-docs-grow-and-nothing-prunes-them.md) | Docs | done | 132 |
| 135 | [harness scores recall but never precision](tasks/135_harness-scores-recall-but-never-precision.md) | Measure | done | 055, 121, 130 |
| 136 | [heuristic share has no owner](tasks/136_heuristic-share-has-no-owner.md) | Coverage | done | 025, 029, 011 |
| 137 | [php local type table](tasks/137_php-local-type-table.md) | Coverage | done | 136, 039 |
| 140 | [impact answers in symbols not modules](tasks/140_impact-answers-in-symbols-not-modules.md) | Agent-fit | done | 017, 112, 114, 124 |
| 141 | ["Can this module be split out?" — the cut edges and the cycles that block it — evidence-gated](tasks/141_extractability-cut-edges-and-the-cycles-that-block-it.md) | Coverage | deferred | 120, 087, 140 |
| 142 | [supervision question class has no baseline](tasks/142_supervision-question-class-has-no-baseline.md) | Measure | done | 034, 055, 121, 135 |
| 158 | [routing suggestions fire on index state not on the question](tasks/158_routing-suggestions-fire-on-index-state-not-on-the-question.md) | Agent-fit | done | 081, 099, 069 |
| 159 | [get index status does not name available but unconfigured adapters](tasks/159_get-index-status-does-not-name-available-but-unconfigured-adapters.md) | Adoption | done | 064, 028, 095 |
| 160 | [a zero answer never names the index language coverage](tasks/160_a-zero-answer-never-names-the-index-language-coverage.md) | Agent-trust | done | 065, 129, 093, 159 |
| 161 | [impact resolves a shared qname to one twin and carries no freshness](tasks/161_impact-resolves-a-shared-qname-to-one-twin-and-carries-no-freshness.md) | Agent-trust | done | 017, 070, 078, 077 |
| 162 | [a build swap is invisible on every payload but get index status](tasks/162_a-build-swap-is-invisible-on-every-payload-but-get-index-status.md) | Agent-trust | done | 125, 077, 100 |
| 163 | [read symbol minimal is byte identical to standard](tasks/163_read-symbol-minimal-is-byte-identical-to-standard.md) | Agent-trust | done | 014, 066 |
| 164 | [server build names the repo not the running process](tasks/164_server-build-names-the-repo-not-the-running-process.md) | Agent-trust | done | 162, 125, 100 |
| 165 | [find callers splits across twins and says reason ok](tasks/165_find-callers-splits-across-twins-and-says-reason-ok.md) | Agent-trust | done | 013, 054, 161, 122 |
| 166 | [read symbol answers from pre repair state and calls it no such symbol](tasks/166_read-symbol-answers-from-pre-repair-state-and-calls-it-no-such-symbol.md) | Agent-trust | done | 035, 014, 065 |
| 167 | [a substring near miss is reported as reason ok](tasks/167_a-substring-near-miss-is-reported-as-reason-ok.md) | Agent-trust | done | 014, 160, 093 |
| 168 | [find references never got 165s twin disclosure](tasks/168_find-references-never-got-165s-twin-disclosure.md) | Agent-trust | done | 165, 013, 122 |
| 169 | [impact path seed walks every symbol and its twins](tasks/169_impact-path-seed-walks-every-symbol-and-its-twins.md) | Agent-trust | done | 161, 017, 078 |
| 170 | [server identity is cached so a later build swap is unreportable](tasks/170_server-identity-is-cached-so-a-later-build-swap-is-unreportable.md) | Agent-trust | done | 164, 162, 125 |
| 171 | [sibling definitions fires on most calls and is unranked](tasks/171_sibling-definitions-fires-on-most-calls-and-is-unranked.md) | Agent-trust | done | 165, 168, 013 |
| 172 | [incremental is blind to a scope change](tasks/172_incremental-is-blind-to-a-scope-change.md) | Freshness | done | 016, 060, 053 |
| 173 | [coverage claims key on configured not indexed](tasks/173_coverage-claims-key-on-configured-not-indexed.md) | Agent-trust | done | 160, 159, 082 |
| 174 | [unconfigured adapters names the switch not the cost](tasks/174_unconfigured-adapters-names-the-switch-not-the-cost.md) | Agent-trust | done | 159, 082 |
| 175 | [config is loaded at spawn and nothing says so](tasks/175_config-is-loaded-at-spawn-and-nothing-says-so.md) | Agent-trust | done | 164, 170 |
| 176 | [no full build from a shell](tasks/176_no-full-build-from-a-shell.md) | Freshness | done | 010, 053 |
| 177 | [a long build is indistinguishable from a hang](tasks/177_a-long-build-is-indistinguishable-from-a-hang.md) | Agent-trust | done | 072, 010, 052, 176 |
| 178 | [status reads current while a build is still linking](tasks/178_status-reads-current-while-a-build-is-still-linking.md) | Agent-trust | done | 072, 077, 010, 177 |
| 179 | [impact modules inherits half the seed fix](tasks/179_impact-modules-inherits-half-the-seed-fix.md) | Agent-trust | done | 169, 161, 140 |
| 180 | [search ranks a near miss above exact matches](tasks/180_search-ranks-a-near-miss-above-exact-matches.md) | Agent-trust | done | 167, 014, 057 |
| 181 | [sibling definitions fallback is a dump not a ranking](tasks/181_sibling-definitions-fallback-is-a-dump-not-a-ranking.md) | Agent-trust | done | 171, 168, 169 |
| 182 | [find orphans answers with rows it has flagged unreliable](tasks/182_find-orphans-answers-with-rows-it-has-flagged-unreliable.md) | Agent-fit | done | 124, 031, 119 |
| 183 | [edge health has no per language breakdown](tasks/183_edge-health-has-no-per-language-breakdown.md) | Measure | done | 136, 082, 173 |
| 185 | [no tool is ever asked a question over a second languages graph](tasks/185_no-tool-is-ever-asked-a-question-over-a-second-languages-graph.md) | Coverage | done | 147, 012, 019 |
| 186 | [a zero answer cannot say the relation is unmodelled for this language](tasks/186_a-zero-answer-cannot-say-the-relation-is-unmodelled-for-this-language.md) | Agent-trust | done | 160, 183, 185 |
| 187 | [find orphans crashes on an entry point glob that matches nothing](tasks/187_find-orphans-crashes-on-an-entry-point-glob-that-matches-nothing.md) | Agent-trust | done | 185, 031, 124 |
| 188 | [imports edges are never linked so no tool can walk a module graph](tasks/188_imports-edges-are-never-linked-so-no-tool-can-walk-a-module-graph.md) | Agent-fit | done | 186, 019, 155 |
| 189 | [a twin is a container fact not a path fact](tasks/189_a-twin-is-a-container-fact-not-a-path-fact.md) | Agent-trust | done | 181, 171, 165 |
| 190 | [a same second guard is flaky under suite load](tasks/190_a-same-second-guard-is-flaky-under-suite-load.md) | Coverage | done | 146 |
| 191 | [a conditional assertion is a test that never ran](tasks/191_a-conditional-assertion-is-a-test-that-never-ran.md) | Coverage | done | 189, 181 |
| 192 | [coverage note suppressed on a partial answer](tasks/192_coverage-note-suppressed-on-a-partial-answer.md) | Agent-trust | done | 160, 173, 186 |
| 194 | [default filled column defect class query](tasks/194_default-filled-column-defect-class-query.md) | Agent-fit | done | 022 |
| 195 | [three tools still read the whole graph blend](tasks/195_three-tools-still-read-the-whole-graph-blend.md) | Measure | done | 183 |
| 196 | [the-system-map-cannot-attribute-its-own-confidence](tasks/196_the-system-map-cannot-attribute-its-own-confidence.md) | Measure | done | 195 |
| 200 | [The recognition map is a prompt no model can read; the snippet that reaches one is PHP-only](tasks/200_the-recognition-map-is-a-prompt-no-agent-can-read.md) | Adoption | blocked | 081, 097, 036, 099 |
| 201 | [a forced full rebuild is silent and unroutable](tasks/201_a-forced-full-rebuild-is-silent-and-unroutable.md) | Freshness | done | 030, 050, 172, 176, 177 |
| 202 | [a killed build leaves an index that reports current](tasks/202_a-killed-build-leaves-an-index-that-reports-current.md) | Agent-trust | done | 072, 077, 052, 050, 035 |
| 204 | [bare-name resolution has no language predicate](tasks/204_bare-name-resolution-has-no-language-predicate.md) | Agent-trust | done | 046, 137, 183, 185, 186 |
| 203 | [a rebuild is GIL-bound and its operating knowledge is unroutable](tasks/203_a-rebuild-is-gil-bound-and-its-operating-knowledge-is-unroutable.md) | Freshness | done | 052, 096, 176, 177, 200, 201 |
| 212 | [an incremental update escalates on correctness but never on cost](tasks/212_an-incremental-update-escalates-on-correctness-but-never-on-cost.md) | Freshness | todo | 030, 052, 080, 096, 172, 202 |

## Open work — Pillar 2 · Onboarding

The rendering of what the code actually is, for a human supervising an agent or presenting the
project ([PLAN §1](PLAN.md#1-goals--non-goals)). Same graph, no second pipeline.

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 083 | [onboarding graph metrics](tasks/083_onboarding-graph-metrics.md) | Phase 3 / M10 | done | 014, 031, 017 |
| 084 | [onboarding layer assignment](tasks/084_onboarding-layer-assignment.md) | Phase 3 / M10 | done | 083 |
| 103 | [onboarding layer granularity](tasks/103_onboarding-layer-granularity.md) | Phase 3 / M10 | done | 084 |
| 104 | [onboarding layer signal](tasks/104_onboarding-layer-signal.md) | Phase 3 / M10 | done | 103 |
| 105 | [dominant subtree loses to a config dir](tasks/105_dominant-subtree-loses-to-a-config-dir.md) | Phase 3 / M10 | done | 104, 086 |
| 085 | [onboarding summarizer seam](tasks/085_onboarding-summarizer-seam.md) | Phase 3 / M10 | done | 083 |
| 086 | [architecture overview tool](tasks/086_architecture-overview-tool.md) | Phase 3 / M10 | done | 084, 085, 104 |
| 087 | [guided tour tool](tasks/087_guided-tour-tool.md) | Phase 3 / M11 | done | 083, 086 |
| 088 | [generate onboarding markdown](tasks/088_generate-onboarding-markdown.md) | Phase 3 / M11 | done | 084, 086, 087 |
| 089 | [onboarding viewer](tasks/089_onboarding-viewer.md) | Phase 3 / M11 | done | 088 |
| 090 | [llm summarizer impl](tasks/090_llm-summarizer-impl.md) | Phase 3 / M12 | done | 085, 088 |
| 091 | [llm layer refinement](tasks/091_llm-layer-refinement.md) | Phase 3 / M12 | done | 084, 090 |
| 106 | [tour budget buys 500 alphabetical isolated files](tasks/106_tour-budget-buys-500-alphabetical-isolated-files.md) | Phase 3 / M11 | done | 087, 088 |
| 107 | [a page with no neighbours and no summary is filler](tasks/107_a-page-with-no-neighbours-and-no-summary-is-filler.md) | Phase 3 / M11 | done | 088, 106 |
| 108 | [module page neighbour list is unbounded](tasks/108_module-page-neighbour-list-is-unbounded.md) | Phase 3 / M11 | done | 088, 107 |
| 109 | [onboarding artifact quality gate](tasks/109_onboarding-artifact-quality-gate.md) | Phase 3 / M11 | done | 088, 108 |
| 110 | [layers named by responsibility](tasks/110_layers-named-by-responsibility.md) | Phase 3 / M10 | done | 084, 105, 109 |
| 111 | [tour is narrative steps](tasks/111_tour-is-narrative-steps.md) | Phase 3 / M11 | done | 087, 110 |
| 112 | [onboarding dataset contract](tasks/112_onboarding-dataset-contract.md) | Phase 3 / M11 | done | 083, 086, 110 |
| 113 | [reachability split](tasks/113_reachability-split.md) | Phase 3 / M11 | done | 083, 112 |
| 114 | [business module table](tasks/114_business-module-table.md) | Phase 3 / M11 | done | 112 |
| 115 | [mirror subtree detection](tasks/115_mirror-subtree-detection.md) | Phase 3 / M11 | done | 112 (feeds 098) |
| 116 | [dashboard viewer](tasks/116_dashboard-viewer.md) | Phase 3 / M11 | done | 112, 114, 115 |
| 117 | [llm prose for map](tasks/117_llm-prose-for-map.md) | Phase 3 / M12 | done | 110, 111, 090, 091 |
| 118 | [module summary seam gets empty facts](tasks/118_module-summary-seam-gets-empty-facts.md) | Phase 3 / M11 | done | 085, 090, 107, 117 |
| 119 | [reachability signal provenance](tasks/119_reachability-signal-provenance.md) | Phase 3 / M11 | done | 113, 116 |
| 121 | [onboarding question class never measured](tasks/121_onboarding-question-class-never-measured.md) | Measure | done | 034, 045, 055, 086, 087, 088 |
| 126 | [search palette clusters into one subtree](tasks/126_search-palette-clusters-into-one-subtree.md) | Phase 3 / M11 | done | 067, 115, 116 |
| 127 | [caveats drop at the artifact layer](tasks/127_caveats-drop-at-the-artifact-layer.md) | Phase 3 / M11 | done | 100, 112, 113, 116, 119 |
| 130 | [web entry bucket counts test controllers](tasks/130_web-entry-bucket-counts-test-controllers.md) | Phase 3 / M11 | done | 113, 119, 121 |
| 131 | [tour ranks configuration ahead of the front controller](tasks/131_tour-ranks-configuration-ahead-of-the-front-controller.md) | Phase 3 / M11 | done | 111, 121 |
| 138 | [architecture rules are never asked of the graph](tasks/138_architecture-rules-are-never-asked-of-the-graph.md) | Supervision | done | 040, 110, 112, 136 |
| 139 | [map is a snapshot so nothing shows architectural drift](tasks/139_map-is-a-snapshot-so-nothing-shows-architectural-drift.md) | Supervision | done | 112, 077, 127 |
| 143 | [the system map has no diagram](tasks/143_the-system-map-has-no-diagram.md) | Presentation | done | 112, 116, 110, 130 |
| 144 | [class diagram is a projection minus the return type](tasks/144_class-diagram-is-a-projection-minus-the-return-type.md) | Presentation | done | 002, 112, 116 |
| 145 | [artifact json is a cache that a second renderer turns into a contract](tasks/145_artifact-json-is-a-cache-that-a-second-renderer-turns-into-a-contract.md) | Presentation | done | 088, 112, 116, 118 |
| 146 | [gate can pass on stale bytecode](tasks/146_gate-can-pass-on-stale-bytecode.md) | Measure | done | — |
| 197 | [no surface follows one request end to end](tasks/197_no-surface-follows-one-request-from-entry-to-the-data-it-writes.md) | Phase 3 / M11 | done | 113, 114, 111, 112, 022 |
| 198 | [a business module is labelled by its directory name](tasks/198_a-business-module-is-labelled-by-its-directory-name.md) | Phase 3 / M12 | done | 114, 117, 197 |
| 199 | [flows-have-no-tool-so-an-agent-pays-for-the-whole-overview](tasks/199_flows-have-no-tool-so-an-agent-pays-for-the-whole-overview.md) | Phase 3 / M11 | done | 197 |
| 205 | [a module page per node-budget slot](tasks/205_a-module-page-per-node-budget-slot.md) | Phase 3 / M11 | done | 106, 107, 108, 109, 111, 118 |
| 206 | [onboarding cannot be scoped to the tree the reader works in](tasks/206_onboarding-cannot-be-scoped-to-the-tree-the-reader-works-in.md) | Phase 3 / M11 | todo | 105, 111, 112, 121, 126, 131, 205 |
| 207 | [the artifact answers no question a newcomer asks first](tasks/207_the-artifact-answers-no-question-a-newcomer-asks-first.md) | Phase 3 / M12 | todo | 112, 117, 121, 206 |
| 208 | [an undeclared reachability bucket reports zero as a measurement](tasks/208_an-undeclared-reachability-bucket-reports-zero-as-a-measurement.md) | Phase 3 / M11 | todo | 113, 119, 130, 182, 186 |
| 209 | [a committed artifact cannot say which summarizer wrote it](tasks/209_a-committed-artifact-cannot-say-which-summarizer-wrote-it.md) | Phase 3 / M12 | todo | 085, 090, 117, 118, 205 |
| 210 | [the artifact has one shape for every reader](tasks/210_the-artifact-has-one-shape-for-every-reader.md) | Phase 3 / M12 | todo | 088, 112, 121, 205, 207, 209 |
| 211 | [the tour population is ranked but never grouped](tasks/211_the-tour-population-is-ranked-but-never-grouped.md) | Phase 3 / M11 | todo | 084, 105, 110, 131, 204, 206 |


**Round ordering, and what each round left open.** One line each; the narratives live in
[`FEEDBACK.md`](FEEDBACK.md), [PLAN §19](PLAN.md#19-project-context--decision-log),
[`LESSONS.md`](LESSONS.md) and `benchmarks/`.

| Round | Tickets | State |
|---|---|---|
| 4–7 (2026-08-10…23) | 075–082 · 092–097 · 099–102 · 122–125 · 126 · 127 | closed — 081 `NOT OBSERVED`; 127 closed **119** in the same change |
| 8–9 (2026-08-25/26) | 158–163 | closed |
| 10 (2026-08-26) | 164–167 | closed — the verification round: no prior fix reached a long-lived process until **164** |
| 11 (2026-08-27) | 168–179 | closed — **first round a fix reached the field** |
| 12 (2026-08-28) | 180–190 | open — first **two-language** index; the T-SQL it could not read became 184/022 and §13 became 195. Adapter #2's fifth zero is **applicability**, not roll-out. 187–190 were found by the fixes, not by the round |
| Architecture review (2026-08-23) | 138–142 · 143–145 | 138 · 139 · 142 · 143 · 144 · **145A** done; 141 gated at n = 0; 145B deferred (stack not chosen) |

**What still governs open work:**

- **Every `deferred` ticket holds its own gate** — 074, 098 and 141 each state theirs, and 141 is at
  n = 0; do not queue one without reading it. Auto *reading orders* stay unscheduled
  ([121](benchmarks/121_onboarding-question-class.md)).
- **24 tools** on the MCP surface, plus four shell entry points
  ([`ROADMAP.md`](phase3-onboarding/ROADMAP.md)).
- **Roll-out is the binding constraint and deliberately not a ticket here** — five rounds standing;
  this backlog accepts only code, so it goes to the consumer as a PR.
- **The anchor repo is the test subject, not the product** — 185/186 keep the language-agnostic claim
  checked at the tool surface, where 147 only checks it at the adapter's.

## Phase 2 — More languages (deferred — §19 pivot, 2026-08-04)

**Deferred, not cancelled** for Python and C#/.NET (human-ratified 2026-08-04, §19); the language
*order* is unchanged (§18.2). **019 was reopened 2026-08-25**, its remaining scope filed as
**150–157**, all landed.

| # | Task | Milestone | Status | Depends on |
|---|---|---|---|---|
| 019 | [typescript adapter](tasks/019_typescript-adapter.md) | M7 | done | 012, 011, 128 |
| 020 | [Python adapter](tasks/020_python-adapter.md) | M8 | deferred | 019 |
| 021 | [C#/.NET adapter](tasks/021_csharp-adapter.md) | M9 | deferred | 019 |
| 022 | [sql schema adapter](tasks/022_sql-schema-adapter.md) | M9+ | done | 184 |
| 184 | [tsql source adapter tier 1a](tasks/184_tsql-source-adapter-tier-1a.md) | M9+ | done | 019, 147, 183 |
| 026 | [Inverse Docker path rebase (adapter #2)](tasks/026_docker-inverse-path-rebase.md) | M7 | deferred | 008, 019 |
| 147 | [contract harness is php shaped](tasks/147_contract-harness-is-php-shaped.md) | M7 | done | 012, 025 |
| 148 | [r22 framework sweep cannot fail for adapter 2](tasks/148_r22-framework-sweep-cannot-fail-for-adapter-2.md) | M7 | done | 012, 146 |
| 149 | [tsjs construct inventory](tasks/149_tsjs-construct-inventory.md) | M7 | done | 147 |
| 150 | [ts adapter has no gate but its own fixtures](tasks/150_ts-adapter-has-no-gate-but-its-own-fixtures.md) | M7 | done | 019, 018, 148 |
| 151 | [ts member calls emit no edge](tasks/151_ts-member-calls-emit-no-edge.md) | M7 | done | 019, 128, 137 |
| 152 | [ts call args and arg keys](tasks/152_ts-call-args-and-arg-keys.md) | M7 | done | 019, 151 |
| 153 | [ts declared and inferred types](tasks/153_ts-declared-and-inferred-types.md) | M7 | done | 019, 151, 137 |
| 154 | [ts allowjs and jsdoc types](tasks/154_ts-allowjs-and-jsdoc-types.md) | M7 | done | 019, 153 |
| 155 | [ts tsconfig paths and export star](tasks/155_ts-tsconfig-paths-and-export-star.md) | M7 | done | 019 |
| 156 | [r12 registry verdict now adapter 2 exists](tasks/156_r12-registry-verdict-now-adapter-2-exists.md) | M7 | done | 019 |
| 157 | [r62 inventory has no named default export case](tasks/157_r62-inventory-has-no-named-default-export-case.md) | M7 | done | 019, 149 |

## Phase 1 — Core + PHP (done)

| # | Task | Milestone | Status | Depends on |
|---|---|---|---|---|
| 001 | [project scaffold](tasks/001_project-scaffold.md) | Setup | done | — |
| 002 | [contract schema](tasks/002_contract-schema.md) | Contract | done | 001 |
| 003 | [config and ignore](tasks/003_config-and-ignore.md) | Setup | done | 001 |
| 004 | [sqlite store](tasks/004_sqlite-store.md) | Core | done | 001, 002 |
| 005 | [adapter protocol](tasks/005_adapter-protocol.md) | Core | done | 002 |
| 006 | [php adapter spike](tasks/006_php-adapter-spike.md) | M0 | done | 002 |
| 007 | [php adapter visitor](tasks/007_php-adapter-visitor.md) | M0 | done | 006, 005 |
| 008 | [php runtime modes](tasks/008_php-runtime-modes.md) | M1 | done | 005, 007 |
| 009 | [full build indexer](tasks/009_full-build-indexer.md) | M1 | done | 004, 005, 007 |
| 010 | [index status and build tools](tasks/010_index-status-and-build-tools.md) | M1 | done | 009 |
| 011 | [resolver](tasks/011_resolver.md) | M2 | done | 009 |
| 012 | [contract conformance tests](tasks/012_contract-conformance-tests.md) | M2 | done | 025, 002 |
| 013 | [nav tools](tasks/013_nav-tools.md) | M2 | done | 011, 010 |
| 014 | [search read outline](tasks/014_search-read-outline.md) | M3 | done | 010, 004 |
| 015 | [php full coverage and scale](tasks/015_php-full-coverage-and-scale.md) | M4 | done | 013, 014, 008 |
| 016 | [incremental git](tasks/016_incremental-git.md) | M5 | done | 011, 009 |
| 017 | [impact engine](tasks/017_impact-engine.md) | M6 | done | 013, 016 |
| 018 | [cross repo validation](tasks/018_cross-repo-validation.md) | M4 | done | 015 |
| 024 | [ci hardening](tasks/024_ci-hardening.md) | Setup | done | 001 |
| 025 | [php adapter grammar](tasks/025_php-adapter-grammar.md) | M0 | done | 007 |
| 027 | [resolver batched lookups](tasks/027_resolver-batched-lookups.md) | M4 | done | 011, 015 |
| 028 | [index health metrics](tasks/028_index-health-metrics.md) | M4 | done | 010, 011 |
| 029 | [php receiver resolution](tasks/029_php-receiver-resolution.md) | M2 | done | 011, 025 |
| 030 | [alias indirection edges](tasks/030_alias-indirection-edges.md) | M2 | done | 002, 011, 025 |
| 031 | [reachability orphans](tasks/031_reachability-orphans.md) | M6 | done | 003, 011, 013 |

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
| 043 | [duplicate decl resilience](tasks/043_duplicate-decl-resilience.md) | Robustness | done | 004, 009 |
| 044 | [onboarding runbook](tasks/044_onboarding-runbook.md) | Adoption | done | 014, 039, 043 |
| 045 | [tokens to answer local repo](tasks/045_tokens-to-answer-local-repo.md) | Measure | done | 034, 042 |
| 046 | [resolver qname candidate dedupe](tasks/046_resolver-qname-candidate-dedupe.md) | Robustness | done | 011, 027, 043 |
| 047 | [staleness scoped to indexed files](tasks/047_staleness-scoped-to-indexed-files.md) | Freshness | done | 028, 035, 016 |
| 048 | [edge health resolved ambiguity](tasks/048_edge-health-resolved-ambiguity.md) | Agent-trust | done | 028 |
| 049 | [call site argument selectivity](tasks/049_call-site-argument-selectivity.md) | Agent-fit | done | 013, 037, 002 |
| 050 | [schema version mismatch recovery](tasks/050_schema-version-mismatch-recovery.md) | Robustness | done | 010, 016 |
| 051 | [build report edge undercount](tasks/051_build-report-edge-undercount.md) | Agent-trust | done | 009, 011, 028 |
| 052 | [incremental noop cost](tasks/052_incremental-noop-cost.md) | Freshness | done | 016, 047 |
| 053 | [refresh on checkout hook](tasks/053_refresh-on-checkout-hook.md) | Freshness | done | 052, 036, 016 |
| 054 | [bare name callers silent drop](tasks/054_bare-name-callers-silent-drop.md) | Agent-trust | done | 011, 013, 046 |
| 055 | [recall benchmark](tasks/055_recall-benchmark.md) | Measure | done | 034, 045 |
| 056 | [filter values fail loud](tasks/056_filter-values-fail-loud.md) | Agent-trust | done | 014, 033 |
| 057 | [answer pagination](tasks/057_answer-pagination.md) | Agent-trust | done | 013, 014, 033 |
| 058 | [list parse failures](tasks/058_list-parse-failures.md) | Agent-trust | done | 009, 028 |
| 059 | [view databag edge](tasks/059_view-databag-edge.md) | Coverage | done | 030, 040 |
| 060 | [build report scale naming](tasks/060_build-report-scale-naming.md) | Agent-trust | done | 051 |
| 061 | [payload weight](tasks/061_payload-weight.md) | Cost | done | 010, 014, 033 |
| 062 | [view databag producer](tasks/062_view-databag-producer.md) | Coverage | done | 030, 040, 059 |
| 063 | [view databag array keys](tasks/063_view-databag-array-keys.md) | Coverage | done | 062, 002, 049 |
| 064 | [build without adapter silent](tasks/064_build-without-adapter-silent.md) | Agent-trust | done | 009, 028, 056 |
| 065 | [empty answer cannot explain itself](tasks/065_empty-answer-cannot-explain-itself.md) | Agent-trust | done | 033, 054, 056 |
| 066 | [limit clamped silently](tasks/066_limit-clamped-silently.md) | Agent-trust | done | 057, 033 |
| 067 | [first page not representative](tasks/067_first-page-not-representative.md) | Agent-trust | done | 057, 013 |
| 068 | [rules bookmark counted as source file](tasks/068_rules-bookmark-counted-as-source-file.md) | Agent-trust | done | 040, 062, 064 |
| 069 | [tool names do not say what they answer](tasks/069_tool-names-do-not-say-what-they-answer.md) | Agent-fit | done | 062, 063, 038 |
| 070 | [ambiguous qname no scoping](tasks/070_ambiguous-qname-no-scoping.md) | Agent-fit | done | 043, 013, 011 |
| 071 | [answers do not name their tree](tasks/071_answers-do-not-name-their-tree.md) | Agent-trust | done | 033, 061, 065 |
| 072 | [busy build hides staleness](tasks/072_busy-build-hides-staleness.md) | Agent-trust | done | 053, 033 |
| 073 | [freshness cannot find what is not indexed](tasks/073_freshness-cannot-find-what-is-not-indexed.md) | Agent-trust | done | 035, 065, 033 |
| 075 | [read symbol confident zero on unnormalised qname](tasks/075_read-symbol-confident-zero-on-unnormalised-qname.md) | Agent-trust | done | 065, 070, 014 |
| 076 | [bare name subject reads as absence](tasks/076_bare-name-subject-reads-as-absence.md) | Agent-trust | done | 054, 011, 013 |
| 077 | [index cannot name the revision it describes](tasks/077_index-cannot-name-the-revision-it-describes.md) | Agent-trust | done | 071, 047, 072 |
| 078 | [ambiguous payload still picks one definition](tasks/078_ambiguous-payload-still-picks-one-definition.md) | Agent-trust | done | 070, 043, 049 |
| 079 | [build payload does not name its tree](tasks/079_build-payload-does-not-name-its-tree.md) | Agent-trust | done | 071, 060 |
| 080 | [noop incremental cost and uninterpretable writes](tasks/080_noop-incremental-cost-and-uninterpretable-writes.md) | Cost | done | 052, 051, 060 |
| 081 | [routing prompts are not in the agents surface](tasks/081_routing-prompts-are-not-in-the-agents-surface.md) | Agent-fit | done | 069, 017, 038 |
| 082 | [claims nobody outside can check](tasks/082_claims-nobody-outside-can-check.md) | Agent-trust | done | 068, 072, 028 |
| 092 | [untracked files are invisible and answer no such symbol](tasks/092_untracked-files-are-invisible-and-answer-no-such-symbol.md) | Agent-trust | done | 073, 082, 065 |
| 093 | [try instead is not a callable tool name](tasks/093_try-instead-is-not-a-callable-tool-name.md) | Agent-fit | done | 065, 076, 069 |
| 095 | [ignore bucket does not name its rule](tasks/095_ignore-bucket-does-not-name-its-rule.md) | Agent-trust | done | 082, 003, 068 |
| 097 | [recognition probe measures names not recall](tasks/097_recognition-probe-measures-names-not-recall.md) | Measure | done | 081, 069, 074 |
| 094 | [class constant in array literal is not an edge](tasks/094_class-constant-in-array-literal-is-not-an-edge.md) | Coverage | done | 030, 011, 002 |
| 096 | [edit then ask tax two files cost a minute](tasks/096_edit-then-ask-tax-two-files-cost-a-minute.md) | Cost | done | 080, 052, 016 |
| 099 | [write time signal seam](tasks/099_write-time-signal-seam.md) | Agent-fit | done | 097, 069, 036 |

### Where these tickets came from

Provenance is in the three docs the preamble names, not retold here (R7.6). One note still governs
open work: the anchor repo's `CLAUDE.md` asserts `grep` "times out" and costs "~650× the tokens" — an
**un-evidenced claim, not a code-atlas defect**; round 3 observed neither, so it needs evidence or
removal.

## Follow-ups (not yet ticketed)

One line each, with the pointer that holds the detail. Nothing here is scheduled.

- **PSR-4 / autoload-aware include resolution**, with PSR-0 duplicate-name disambiguation — [042](tasks/042_tokens-to-answer-sample-tier.md).
- **`max_results` does two unrelated jobs** — returned rows *and* resolver candidate fan-out, so a query knob sets index size — [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4.
- **Tokens-to-answer measures cost, not information** — 046 moved the ratio 0.02 % while doubling the distinct answers. Wants a second axis before it judges a retrieval change.
- **`reachable_from` payload size at `standard`** — bounded by `impact_max_nodes` (500), ~160 KB of JSON. Worth a lower default or `minimal`-by-default; workaround in [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4.
- **Parser-OOM size cap (optional)** — multi-MB generated files exhaust the PHP parser (already soft-failed/restarted in `indexer.py`); a byte-cap pre-skip (`CA_MAX_FILE_BYTES`) would avoid ~30 restart cycles. Log skips; no silent truncation.
- **Adapter-subprocess test harness on Windows (bug)** — `CA_*_CMD` uses POSIX quoting but splits with `posix=False`, so quoted paths reach `CreateProcess` verbatim → `WinError 2`. Fails ~56 adapter tests on Windows, green on Linux. Surfaced by [043](tasks/043_duplicate-decl-resilience.md).
- **043's duplicate-declaration gap** — the end-to-end `full_build` test is blocked by the Windows bug above (the surface is proven at the `_write`+store layer); a PHP-adapter fixture would only pin what the adapter already emits.
- **018 construct gaps** — cross-repo misses feed the (still empty) gap log in [`runbooks/cross-repo-validation.md`](runbooks/cross-repo-validation.md) and tasks 007 / 025.
- **The onboarding tree's bulk is outside its Markdown** — `manifest.json` + `index.html` are ~2.5 MB
  with no ceiling, and two smaller gaps sit beside it — [205](tasks/205_a-module-page-per-node-budget-slot.md).
- **Docker images are never built by CI** — `docker/Dockerfile` can rot (`Dockerfile.runtime` is built inside `pytest`). Honest shape: one job building both. Survives the unbillable-Actions arrangement AGENTS.md records, which also means every gate is a human step.

## Conventions
- Keep task `status` in this table **and** in each task file's frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
- A task reaching `done` also gets its spend row in [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) (R7.2).
- Landed narrative belongs in [PLAN §19](PLAN.md#19-project-context--decision-log) or
  [`LESSONS.md`](LESSONS.md), not here; a ticketed follow-up leaves the
  [Follow-ups](#follow-ups-not-yet-ticketed) list. This is R7.6, with a ceiling in
  `tests/test_doc_size_budget.py`.
