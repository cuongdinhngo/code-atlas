# Backlog — code-atlas

Task tracker. One file per task in [`docs/tasks/`](tasks/) (`NNN_slug.md`). Source of truth for scope
is [`PLAN.md`](PLAN.md); the durable decision log is [PLAN §19](PLAN.md#19-project-context--decision-log)
and the per-task engineering lessons are in [`LESSONS.md`](LESSONS.md). This file tracks *what is open,
what landed, and what it cost* — narrative rationale lives in those three.

**Status legend:** `todo` · `in-progress` · `blocked` · `deferred` · `done`
**Shipped for daily use at task 014** (search/read/outline).

## Open work

| # | Task | Theme | Status | Depends on |
|---|---|---|---|---|
| 074 | [Does the index harm mechanism questions? — resolve at n ≥ 3](tasks/074_does-the-index-harm-mechanism-questions.md) | Measure | blocked | 055, 067, 045 |
| 098 | [Should the graph hold "this file is a copy/port of that one"? — evidence-gated](tasks/098_correspondence-relation-seam.md) | Coverage | deferred | 030, 011, 003 |
| 100 | [Nine kinds of evidence in the PR, zero graph payloads](tasks/100_claim-signing-output-mode.md) | Agent-fit | done | 017, 057, 061 |
| 101 | [A ten-name sweep is ten calls, so the agent used a shell loop](tasks/101_nav-tools-take-one-subject-at-a-time.md) | Agent-fit | done | 014, 013, 066 |
| 102 | [`impact` reports `seeds_dropped: 0` for a subject it never found](tasks/102_impact-cannot-tell-an-absent-subject-from-a-zero.md) | Agent-fit | done | 017, 100 |
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
| 119 | [Onboarding — the reachability split never says which signal produced each count](tasks/119_reachability-signal-provenance.md) | Phase 3 / M11 | todo | 113, 116 |
| 120 | ["Can this subtree be deleted?" — subtree dependency with duplicate-declaration attribution — evidence-gated](tasks/120_subtree-dependency-attribution.md) | Coverage | todo | 017, 043, 078, 115 |
| 121 | [Phase 3 shipped without its own cost gate — the onboarding question-class was never added to the harness](tasks/121_onboarding-question-class-never-measured.md) | Measure | todo | 034, 045, 055, 086, 087, 088 |
| 122 | [075 normalised the leading backslash for three tools; four `find_*` tools still decline over it](tasks/122_exact-miss-shaping-discards-a-resolved-subject.md) | Agent-trust | done | 075, 076, 065, 093 |
| 123 | [`file_outline` omitted the symbol under repair, reported `total_count: 10` for a 12-symbol file, and has no page 2](tasks/123_file-outline-total-count-is-the-page-length.md) | Agent-trust | done | 014, 057, 066, 067 |
| 124 | [`find_orphans` blew the transport limit at 19k files, on the one ticket whose root cause *was* an orphan](tasks/124_find-orphans-cannot-answer-at-scale.md) | Agent-fit | done | 031, 057, 066, 119 |
| 125 | [No payload names the server build — every field retro is told its own subject by an operator](tasks/125_no-payload-names-the-server-build.md) | Measure | todo | 082, 095, 100 |

**Order (round-5 tickets):** ~~**092**~~ (done — an untracked file read as a non-existent symbol)
**→ ~~093~~** (done — 092's route shape generalised to every `try_instead`) **→ ~~095~~**
(done — names the denominator 082 made auditable) **→ ~~097~~** (done — protocol now scores
descriptions separately from names, and names the recall bucket) **→ ~~094~~** (done — `::class`
mentions are DYNAMIC REFERENCES) **→ ~~096~~** (done — cost, and last for
the same reason 061 and 080 were, but it is the round's behaviour finding, not just a number).
**Round 5 closed:** 092–097 all landed. **Round 4 closed:** 075–082 all landed; round 5 verified
7 of 8 fixed and 081 `NOT OBSERVED` (§A).

**Order (round-6 tickets), 2026-08-21 — all four are payload honesty, none is a graph defect.** The
round's own closing line is the ordering argument: *"the graph knew everything I asked it; the failures
were the tool knowing and not saying how much it was not telling me, and the tool knowing and declining
over punctuation."* So ~~**122**~~ first (done — the four `find_*` tools now re-point onto the
resolved qname and disclose `resolved_qname`) — it is the round's single most expensive event (one silently-empty
answer moved the evaluator to `grep` for the remaining **four of five** tickets) and it is
[075](tasks/075_read-symbol-confident-zero-on-unnormalised-qname.md)'s own scope bullet left unfinished:
`classify_missing_subject` resolves the leading-anchor case to `resolved_unique` and three tools
(`read_symbol`, `explain_path`, `impact`) honour it while four (`find_references`, `find_callers`,
`find_implementations`, `find_view_data`) discard the resolved qname inside the shared
`shape_exact_miss`. **→ 123** (`file_outline` returned 10 of a 12-symbol file, omitted the method under
repair, and reported `total_count: 10` — the field means *page length* there and *true total* on
`search_symbol`; round 5 called this tool its most expensive **miss**, round 6 called it and it was
**wrong**). **→ 124** (`find_orphans` exceeded the transport limit at 154,004 characters and cannot be
paged; it borrows `impact_max_nodes` for a cap that decides which orphans are visible at all, and the one
ticket that round whose root cause *was* an orphan got nothing from it). **→ 125** last, and it is the
cheapest: no payload names the server build, so every retro in this series has been told its own subject
by an operator — round 6 identified the build by reading task numbers out of tool `description` prose.

123 and 124 are **recorded exclusions meeting their first field evidence**, not oversights:
[057](tasks/057_answer-pagination.md) wrote *"Reachability, `file_outline`, and `include_graph` stay
out"* and [066](tasks/066_limit-clamped-silently.md) ruled `file_outline` out of the clamp contract with
a forward clause for exactly this case. Nine tools already take `offset`; these two are the only
list-returning tools that do not. **Two things round 6 measured and no ticket claims:** `edge_health`
HEURISTIC sat at **63.81 %** against round 4's 63.8 % — unmoved to three significant figures across two
rounds and ~20 tasks, tracked by the regressions table for three rounds without a ticket aimed at it, so
it is either a non-goal that should say so or an unowned gap; and the round's most valuable result came
from a question the evaluator **never asked** (a `search_symbol` page returned a test class whose
docblock falsified a claim already shipped), which no benchmark scoring "given question Q, did the tool
return A" can see. That is also independent evidence for **121**: five bug-fix tickets generated **zero**
calls to the three onboarding tools, because onboarding answers a once-per-repo question and a ticket
asks a once-per-ticket one — so 121's question-class must measure a newcomer, not a maintainer, or it
will fail for the wrong reason.

**Order (round-5 interview tickets) — these are positioning, not defects.** The round-5 tickets fix
what the tool *says*; these decide **where it stands**. ~~**099**~~ first (done — every decision the
field made without the graph wanted a line inside a file read; the adoption finding, with 096 as its
enabler, not its substitute) **→ ~~100~~** (done — the tool held evidence-grade payloads that never
reached the artifact; smallest change with the largest positioning effect) **→ ~~101~~** (done — a
shape fix, bounded). All three generalise because **their subject is the agent, not the repository**
— see the evidence filter in [PLAN §19](PLAN.md#19-project-context--decision-log).
**Then 102**, the only open ticket on this track: measured *during* 100, it is the same evidence
argument one field in — `impact` answers an unresolvable subject with `results: []` and
`seeds_dropped: 0`, the exact pair a modelled zero returns, so the field that exists to separate
them cannot. Unblocked now that 100 has landed.
**098 is `deferred` behind that filter, not queued:** the demand is real and comes from the project's
first production user, but the relation is that repository's shape, and a general server cannot spend
schema every user inherits on **n = 1**. Its gate — a second independent repo, zero cost when
undeclared, a cheaper alternative rejected in writing — is written into the ticket.
**074's core needs the anchor repo** — the pre-registered protocol has landed and round 5 is its
**n = 1** (session type *legacy→unified port*; verdict **helped, narrowly** — downgraded by the
interview's §6.5 retraction; see the ticket).

**104 fixes 103's shipped F1 collapse** (the dominant-subtree grouping); its C1 implementation +
AC1/AC3/AC4 landed, and AC2 — the real-repo proof — was **produced by 086**, whose own AC1 asks for
the same evidence. 086 indexed the three real repos already pinned in `scripts/cross_repo_samples.json`
and found **`laravel/laravel` still collapsed `app/**`**, because that skeleton's `config/` holds 10
indexed files against `app/`'s 3 and the dominant subtree was elected by file **count**.

**105 fixes that** (`done`): `_dominant_subtree` now elects by **graph mass** (Σ fan_in+fan_out), so a
flat, disconnected settings directory can no longer out-vote a small but connected source tree — no
directory stop-list (R2.2), no language branch (R1.1), still deterministic (R4.2). Proven on the same
three pinned repos via the new committed `scripts/layer_report.py`: **`laravel/laravel` now splits
`app/**` into Http/Models/Providers**, and **`symfony/demo` / `brick/math` are byte-identical to 086's
recorded assignments** (no regression). 104 stays **`blocked`** — its AC2 names the **anchor
monorepo**, and three public repos are stronger than fixtures but are not that repo; the maintainer
holds that judgement.

**M10 is complete** (083 · 084 · 085 · 103 · 104 · 086) — `architecture_overview` is the 15th tool on
the surface. **087 shipped** (`guided_tour`, 16th tool). **088 shipped** (`generate_onboarding`,
17th tool). **089 shipped** (static HTML viewer). **090 shipped** (LLM summarizer behind the 085
seam — the `onboarding_llm/` package + `code-atlas-llm` entry point, opt-in, the core still imports no
LLM). **091 shipped** (LLM layer-name refinement behind a new 091 `LayerRefiner` seam — renames the
weak dependency-direction bands 084 falls back to on flat namespaces; opt-in via
`CA_ONBOARDING_LAYER_REFINER`, off by default, core still imports no LLM). **117 shipped** (one
`ProseWriter` seam for the map's three prose slots — layer descriptions, tour-step narratives, and
the wording of the headline facts; opt-in via `CA_ONBOARDING_PROSE`, off by default, core still
imports no LLM). **M12 is complete** (090 · 091 · 117). **105 shipped** (dominant subtree elected by graph mass, not file count — the laravel
`app/**` collapse is fixed and proven on the three pinned repos).

**Onboarding reshape (108–117), 2026-08-20.** Reviewing the emitted artifact on the anchor monorepo as a human newcomer found it unusable: 43 MB total, a median module page of 82,218 bytes that is 99.96 % flat path lists, `Summary: (none)` on 500/500 pages, and a 500-stop "tour". A reviewed mockup — one self-contained 891 KB page with a sitemap treemap, responsibility layers, a full dependency matrix, hubs, a business-module table, mirror-subtree lookup and a 12-step tour — is recorded in [`phase3-onboarding/ONBOARDING_MOCKUP.md`](phase3-onboarding/ONBOARDING_MOCKUP.md) with a reproducible prototype. It splits the audience: **the MCP tools are the product for AI, the onboarding artifact is the product for humans**. Tasks **108–117** implement it — wave 1 (108 · 109) is independently shippable, wave 2 (110–113) is the reshape — **all four landed** — and wave 3 (114–117) is the map and its prose — **all four landed, so the reshape is complete**. 116 found that **108 had already removed ~97 % of the 31 MB** by capping the page bodies, so the size half of the original complaint was largely spent before the map was built; the "data dump, not a map" half was the whole of it, and the map answers that by rendering the 112 dataset alone (`DATASET_VERSION` 5). Its size is measured, not asserted: the path index is **96.9 %** of the anchor's dataset, the page is **969 KB** with it and **109 KB** without, and the three pinned public repos are recorded as a **smoke run that cannot falsify the budget** at 26–51 files each. 115's measured absence of mirrored subtrees on three public repos is now written into 098 as the evidence keeping that ticket deferred. 117 closed it, and its own measurement is the finding worth keeping: **091's rename seam fires on nothing** now that 110 made `responsibility` the primary layer method — all three pins yield zero weak layers — so the ticket's routing bullet was falsified and the prose went through one new seam serving all three slots instead. The cost is bounded by construction rather than by a guess: 6 headline families + 110's 12 layers + 109's 15-step ceiling = **33 calls a build**, enforced per slot, and at 18,929 synthetic files the ceiling served 12 layer descriptions and refused 1,164. Both R2.2 judgments are now settled: a generic architectural vocabulary **is** a standard (110, maintainer-ratified), and **113 needed no separate vendor signal at all** — that same ratified vocabulary already carries `vendor`, so the classifier is composition of 110 + 083's degrees + the operator's own `entry_points`/`stub_roots`, with no library-name list and no `composer.json` parsing.

**Field measurement on the anchor, 2026-08-21 — what the shipped map got right and what it did not.**
Regenerating the artifact on the anchor monorepo (18,972 modules, 135,649 symbols, index at that
repo's `main`) took **17 s** and produced a **950 KB** map, **500** pages at a **median 2,943 B**
(against 82,218 B before 108), 12 responsibility layers, a 10-stop tour, and 109's gate green. Two
findings came out of reading it as a newcomer, and both are now tickets:

- **118** — `Summary: (none)` on **500 / 500** pages, and the cause is **not** the one 117 recorded.
  `artifact.py` passes `NodeFacts("", "", …)`, so the deterministic summarizer is starved on *every*
  repo, and the opt-in LLM implementer is starved with it; 107's isolation rule has a permanently-false
  clause as a side effect. The anchor does have docblocks — the graph has nowhere to carry one.
- **119** — the reachability split prints one number over two signals. The anchor had declared
  `legacy/*/web/*.php` as entry points, which no request can reach (its nginx roots at `public/`
  only); that stale declaration put **560** files in *Web entry points* and made every unreferenced
  legacy page self-justifying to `find_orphans`, and **nothing in the output could expose it** — the
  653-declared / 248-vocabulary split had to be recomputed by hand. After the operator corrected the
  knob the bucket went **901 → 341**, with 494 files moving to *not statically reachable* and 66 to
  *no edge either way*. Classification changed; no fact did.

**120** is the third, and it is **gated, not scheduled**: answering "what still depends on this subtree,
so can it be deleted?" on the anchor took hand-written SQL, and the naive attribution was wrong by
**5.7×** (23,086 vs 4,013 resolved `src → legacy` edges) because 22,282 symbols are declared in more
than one file. Real need, **n = 1** — held to 098's discipline.

**The phase's own cost gate never ran — 121.** [`PHASE3_ONBOARDING.md`](phase3-onboarding/PHASE3_ONBOARDING.md)
§5 gated the whole phase on an **onboarding question-class** in the tokens-to-answer harness (034/045)
plus the recall gate (055), baselined against `grep`+`Read`. `scripts/tokens_to_answer_questions.json`
holds **zero** onboarding questions. M10–M12 are complete; whether they beat hand-mapping on tokens is
**unmeasured**, not won — the same exposure that made the founding search-speed premise false (§19),
one phase later.

**Then:** round 6's payload-honesty tickets go first (**122 → 123 → ~~124~~ → 125**) — they are the
mechanism tools an agent uses every ticket, and 122 is a defect that already cost a field session its
tool. The two onboarding-quality tickets (118 · 119) close what the field measurement found; **121**
decides whether Phase 3 is measured at all, and round 6 sharpened how (a newcomer's question-class, not
a maintainer's). Phase 2 language breadth stays deferred per §19. 104 stays `blocked` because 105
superseded its approach (graph mass, not file count), not because it is waiting on anything.

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
this track are in [Open work](#open-work); everything below has landed.

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

One line each; full narratives in [PLAN §19](PLAN.md#19-project-context--decision-log) (round 4, the
memory run, the founding-premise benchmark), [`FEEDBACK.md`](FEEDBACK.md) (external review rounds) and
[`LESSONS.md`](LESSONS.md) (per-ticket engineering lessons).

| Source | Tickets | Headline |
|---|---|---|
| Field retro 1 (`v0.1.0`, `e117b47`) | 047–049 | **Zero graph queries in a multi-hour session** — the defect lived in string-keyed controller→template data flow, which the index does not model, so the tool had no chance to pay for itself. The retro calls itself "no evidence, not a clean bill of health" |
| Same day | 050–051 | A `schema version '3' is not '2'` error was read as a corrupt index and the session fell back to `grep`; the index was fine and the error's advice would have destroyed the newer one. Verifying that rebuild found the build reporting **949,808 edges against 1,775,812** in the table — resolver siblings inserted after the tally |
| Field retro 2 | 054–061 | First session to exercise the graph (7 of 13 tools, ~23 hand-checked results): **three ways an empty result reads as proof of absence**, one reporting no callers for a method with six live sites. Priority rule 2026-08-07 — correctness is a gate, cost is the win — put direct cost under 1% of a 250–300k session, so 061 ranked last |
| Field retro 3 (2026-08-09, contract v5) | 065–070 | Run blind to every prior finding. **5 of 14 tools, ~1.8% of session tokens**, all graph calls in the first third; what it competed for it won — `find_callers` **23/23** sites, **8/8** hand-verified against `grep`, 17/17 calls correct first try. Sharpest point: 066 + 067 made a *fully correct* tool a **net loss** on its one question |
| Memory & concurrency run (`869dcc6`) | 071–073 | **Memory is a non-finding**: n-th agent ~70 MB PSS, the 925 MB index **0 MB** (never mmapped), 5 agents = 1.3% of RAM at **4.3×** throughput, 452 drift events with zero soft-fails and zero `SQLITE_BUSY`. All three defects are about what an answer *claims* — a worktree agent got the main checkout's symbol with `reason: "ok"` (071), refuting our own `cwd`-relative-`db_path` isolation claim |
| Freshness review (not a session) | 052–053 | Of four layers that keep an index current, only `build_or_update_index(full=false)` has no trigger. **052 gates 053**: a `post-merge` hook costing the field-measured 62 s is worse than a stale index |
| Field retro 4 (2026-08-10, `e8f56d0`) | 075–082 | First **verification** round: 7 fixed and verified, 2 improved, 1 reproduced (054), 2 not exercised. Read with its own three caveats — protocol violated so the recognition test is **void**, the server changed mid-session via a client reconnect, and **4 of 6 question shapes never arose**. Both findings that mattered came from *outside* the verification section (075, 077), which is a regression harness |
| Field retro 5 (2026-08-14, `348a8a7`) | 092–097 | First round with **mechanism questions in the work** (3 of 6 shapes) and the first where **cost changed what was asked**: 16 calls, 8 at the start, 7 at the end, **1 in three hours of writing code**, because each refresh cost ~60 s. **8 of 8 checked claims exact, zero false statements** — every failure was silence or ambiguity. Sharpest point: an untracked file answered `no_such_symbol` while `dirty_indexed_files: 0` and the build payload both read green (092). Verification: 7 of 8 round-4 fixes confirmed, 081 **NOT OBSERVED** — its proxy scored 14/14 off bare names because 7 of 14 descriptions were never loaded (097) |
| Field **interview** — round-5 companion (2026-08-14) | 099–101 (+098 gated) | Six questions about the moments the agent **did not** call the tool, run on the same evaluator right after the retro. It **retracted the round's headline** (PHP method names are case-insensitive, so the "prevented a latent fatal" story is void — 074 downgraded to *helped, narrowly*), and produced the finding four rounds of routing and cost work had missed: **all three decisions made without the graph wanted one line inside a `Read` already happening, and none wanted a tool call** — while the two most valuable uncalled queries **needed no rebuild at all**. Plus the behavioural proof for the evidence-layer thesis: **nine kinds of counted evidence in the PR body, zero graph payloads**, holding `seeds_dropped: 0` the whole time |
| Measured while building 100 (2026-08-16) | 102 | Signing an `impact` answer put its caveats on one quotable line — and exposed that the line can be honest and still useless: `impact(qnames=["\App\Nope"])` returns `results=0 seeds_dropped=0` for a subject that is **not in the index at all**, the identical pair a genuine modelled zero returns. The early return in `store.py:1009-1011` fires before any counting, so the one field a reader consults to tell the two apart is the one that cannot |
| PLAN §19 threats paragraph | 074 | The founding-premise benchmark's one accidental repeat ran the mechanism question twice under the indexed arm and got **opposite verdicts**, the denied run right — the only datapoint suggesting the index costs *accuracy* |

Three notes that still govern open work:

- **074 must not claim** an answer-quality comparison against a language server — the anchor repo's
  resident LSP was uninstalled 2026-08-07 and invoked zero times in 84 calls — and its 19% adoption
  figure means the token result measures adoption, not capability.
- **Round 4's two self-corrections, verified here:** `code-atlas-refresh` *is* a reachable second
  builder, so 072's `busy` payload is exercisable and the gap is affordance (→ 082); and 069's
  descriptions half **did** work, so 081 is about the prompt *channel*, not the description content.
- **One un-evidenced claim, not a code-atlas defect:** the anchor repo's `CLAUDE.md` asserts `grep`
  "times out" and costs "~650× the tokens"; round 3 observed neither, and the `grep` alternative to its
  most expensive graph call was cheaper. Needs evidence or removal.

## Follow-ups (not yet ticketed)

- **Resolver: link `IMPORTS`** (`target_raw` is already an FQN) so `find_references` sees `use`
  statements — filed from [PR #23](https://github.com/cuongdinhngo/code-atlas/pull/23) review. **Still
  open:** `IMPORTS ∉ contract.FQN_EDGE_KINDS`, so the resolver never links it (see the docstring note
  in `code_atlas/tools/find_references.py`).
- **PSR-4 / autoload-aware include resolution** — `include_graph` is effectively empty on real
  Composer-autoloaded repos: their only `INCLUDES` edges are dynamic bootstrap `require`s with no
  resolved target. Found concretely in [042](tasks/042_tokens-to-answer-sample-tier.md). Also open from
  the external review: duplicate-name disambiguation across PSR-0 roots.
- **`max_results` does two unrelated jobs (design smell, measured).** It caps both the rows a tool
  returns *and* the resolver's per-call-site candidate fan-out (`indexer.py:118` →
  `resolve_edges(max_candidates=config.max_results)`), so a query-ergonomics knob silently sets index
  size. On the anchor monorepo: 491,741 heuristic call sites, 33,300 saturating a cap of 50; heuristic
  edges 4.76M at cap 50 vs 2.60M at cap 10 (−46%), DB 2,115 MB vs 1,133 MB. A `CA_RESOLVE_MAX_CANDIDATES`
  would separate them. **And the server never states which meaning is in force** — the field session
  learned it from a comment in the repo's own config file, yet `total_count` is only interpretable if
  you know. Origin: [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4; retro round 1 §3b/§3e/§6d.
- **Tokens-to-answer measures cost, not information — proven blind by 046.** Removing 1.06M duplicate
  edges doubled the distinct answers in a 10-row nav response (5 → 10) and moved the aggregate ratio by
  **0.02%** (178.318 → 178.356), because `max_results` fills the budget either way. Correctness is
  covered by `expected`; nothing covers *usefulness*. Worth a second axis — distinct answers per
  response, or rank-of-first-correct — before the ratio is used to judge a retrieval change.
- **Reachability payload size at `detail_level="standard"`:** `reachable_from` is still bounded by
  `impact_max_nodes` (default 500) rather than `max_results`, and a 500-row answer is ~160 KB of JSON
  against a §19 metric measured *in tokens*. `find_orphans` now pages via `limit`/`offset` and has its
  own walk budget (`CA_ORPHANS_MAX_NODES`); use `minimal` at scale (124). Worth a lower default or a
  `minimal`-by-default shape for `reachable_from`; workaround in [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4.
- **Parser-OOM size cap (optional):** multi-MB generated files (TCPDF/PHPExcel CID font tables ~1.5 MB,
  MPDF ~1.2 MB) exhaust the PHP parser and kill the adapter process. Already handled — `indexer._work`
  (`code_atlas/indexer.py:565-573`) soft-fails the file and restarts the adapter — but a pre-skip by
  byte cap (`CA_MAX_FILE_BYTES`) would avoid ~30 crash-and-restart cycles on the large monorepo. Log
  what is skipped; no silent truncation.
- **Adapter-subprocess test harness on Windows (bug):** `fake_command()`/`php_config()` build `CA_*_CMD`
  with `shlex.join` (POSIX quoting) but `load_config` splits with `shlex.split(posix=False)` on Windows,
  so quoted paths reach `CreateProcess` verbatim → `WinError 2`. Fails ~56 adapter-launching tests on
  the Windows dev host (green in CI/Linux). Surfaced by [043](tasks/043_duplicate-decl-resilience.md);
  a `fix` ticket in its own right.
- **043 AC1 end-to-end `full_build` dup test (CI-gated):** a fake-adapter path emitting two same-qname
  nodes for one file plus an `interface`/`class` same-name pair, asserting the build completes with
  `parsed_ok=1` and one node per qname. Deferred at Gate 4 (human-approved coverage-gap exclusion) —
  blocked by the Windows harness bug above. The fix's surface is already proven at the `_write`+store layer.
- **PHP-adapter duplicate-declaration fixture (optional):** a spec-shaped fixture with a
  `function_exists`-guarded double definition + `interface X`/`class X`, asserting the adapter emits two
  same-qname nodes. Optional — the adapter already emits per-declaration.
- **015 AC2 operator run:** land a real `CODE_ATLAS_SCALE_SAMPLE` timing artifact (elapsed +
  `peak_rss_*`) against the ~112k checkout — deferred from
  [PR #25](https://github.com/cuongdinhngo/code-atlas/pull/25) (D1), folded into
  [018](tasks/018_cross-repo-validation.md) as optional A4. Needs an operator machine with the private checkout.
- **018 construct gaps:** any cross-repo misses → fill the gap log in
  [`runbooks/cross-repo-validation.md`](runbooks/cross-repo-validation.md) and feed task 007 / 025.
  (Gap log is still empty — no scheduled run has recorded a miss.)
- **Three CI items deferred from the drift audit** (each a *tightening*, not a lag): (a)
  `requires-python = ">=3.12"` is open-ended while the matrix stops at 3.13 — add 3.14 or cap the claim;
  (b) `mypy` covers `code_atlas` only, so `scripts/tokens_to_answer.py` — which *is* the gate logic — is
  unchecked; (c) `actions/checkout@v4` / `setup-python@v5` are a major behind, and there is no
  `dependabot.yml` to notice.

## Token usage

Token spend per task, recorded before its PR is opened (see the "Token usage on PR" rule in
[`AGENTS.md`](../AGENTS.md)); the per-phase breakdown lives in each task's `tasks/NNN_slug.work.md`
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
| 024 | 0 dispatch; no work doc. Row added late in [#15](https://github.com/cuongdinhngo/code-atlas/pull/15), which turned the rule into a test | [#14](https://github.com/cuongdinhngo/code-atlas/pull/14) |
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
| 032 | 0 dispatch | [#36](https://github.com/cuongdinhngo/code-atlas/pull/36) |
| 034 | 0 dispatch; no work doc | [#37](https://github.com/cuongdinhngo/code-atlas/pull/37) |
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
| 044 | 0 dispatch; no work doc (two full builds, a tool-by-tool sweep, an incremental run, the write-up) | [#50](https://github.com/cuongdinhngo/code-atlas/pull/50) |
| 045 | 0 dispatch; no work doc (impl, 13 tests, the equivalence proof, first anchor measurement — ratio 178.3) | [#51](https://github.com/cuongdinhngo/code-atlas/pull/51) |
| 046 | 0 dispatch; no work doc (root cause, fix, 3 pinned tests corrected, 4 new, rebuild measurement) | [#52](https://github.com/cuongdinhngo/code-atlas/pull/52) |
| 047 | 0 dispatch; **217.7k fresh** (73.4k out) + 24.8M cache / 114 calls, time-sliced | [#56](https://github.com/cuongdinhngo/code-atlas/pull/56) |
| 048 | 0 dispatch; **93.1k fresh** (27.0k out) + 7.7M cache / 52 calls, time-sliced | [#55](https://github.com/cuongdinhngo/code-atlas/pull/55) |
| 049 | 0 dispatch; **299.6k fresh** (70.5k out) + 6.6M cache / 54 calls. **Understated** — the Option A/B measurement that decided the design falls in the pre-ticket segment | [#57](https://github.com/cuongdinhngo/code-atlas/pull/57) |
| 050 | 0 dispatch; **426.6k fresh** (108.1k out) + 9.5M cache / 122 calls, in two segments (341.1k fix + 39 tests + docs; 85.5k diagnosis + ticket). **Overstated** — the second also holds the anchor v3 rebuild | [#58](https://github.com/cuongdinhngo/code-atlas/pull/58) |
| 051 | 0 dispatch; **109.1k fresh** (42.5k out) + 13.3M cache / 72 calls | [#60](https://github.com/cuongdinhngo/code-atlas/pull/60) |
| — | Ticket-writing for 051: **39.5k fresh** (13.5k out) + 3.3M cache / 23 calls | [#59](https://github.com/cuongdinhngo/code-atlas/pull/59) |
| — | Ticket-writing + the field retro that produced 047–049: **45.6k fresh** / 28 calls for the tickets, plus **1.84M fresh** (503.0k out) + 122.2M cache / 576 calls for the retro, the 049 design measurement and everything before the first commit — not attributable to one task | — |
| — | Ticket-writing for 052 + 053: **463.1k fresh** (58.7k out) + 6.7M cache / 72 calls, one inseparable pass. **Recorded late** | [#54](https://github.com/cuongdinhngo/code-atlas/pull/54) |
| — | Ticket-writing for 054: **356.0k fresh** (139.5k out) + 17.2M cache / 104 calls — **also produced the 055–061 tickets** | [#61](https://github.com/cuongdinhngo/code-atlas/pull/61) |
| — | Ticket-writing for 055–061: **30.2k fresh** (8.0k out) + 2.6M cache / 11 calls — tail only; honest total with the row above is **386.2k fresh / 115 calls** | [#62](https://github.com/cuongdinhngo/code-atlas/pull/62) |
| — | Ticket-writing for 064–070: **384.8k fresh** (117.1k out) + 11.8M cache / 136 calls — also the contract-v5 rebuild, the round-3 retro, and reproducing every claim before ticketing. **Recorded late** | [#77](https://github.com/cuongdinhngo/code-atlas/pull/77) |
| — | Ticket-writing for 071–074 + the memory/concurrency run: **222.0k fresh** (58.3k out) + 5.9M cache / 56 calls. **Understated by the tail** (074, the §19 correction, the runbook rewrite) | [#78](https://github.com/cuongdinhngo/code-atlas/pull/78) |
| — | The founding-premise benchmark + the PLAN §19 decision: **549.6k fresh** (105.4k out) + 7.6M cache / 100 calls. The benchmark runs were headless sessions outside this transcript | [#62](https://github.com/cuongdinhngo/code-atlas/pull/62) |
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
| 064 | 0 dispatch (review skipped). Post-merge review found the suffix guard unreachable → follow-up PR | [#79](https://github.com/cuongdinhngo/code-atlas/pull/79), [#80](https://github.com/cuongdinhngo/code-atlas/pull/80) |
| 065 | 2 dispatch, unmeasured. Post-PR review fixed a red `mypy` gate + the reason missing on `both` | [#81](https://github.com/cuongdinhngo/code-atlas/pull/81) |
| 073 | 2 dispatch, unmeasured. Post-PR review found miss-repair firing on an empty *page* | [#82](https://github.com/cuongdinhngo/code-atlas/pull/82) |
| — | CI drift audit (no ticket, no work doc): 0 dispatch — three workflows re-read, one benchmark re-measured, full `pytest` | [#83](https://github.com/cuongdinhngo/code-atlas/pull/83) |
| 071 | 2 dispatch, unmeasured. Post-PR review found the absolute `index_root` made the benchmark measure path depth — paths normalized, floor re-set to **0.27**, 38 re-derivations collapsed into `Config.index_root` | [#84](https://github.com/cuongdinhngo/code-atlas/pull/84) |
| 068 | 2 dispatch, unmeasured. Post-PR review removed two dead reconcile exemptions + an absence-proving test | [#85](https://github.com/cuongdinhngo/code-atlas/pull/85) |
| 067 | 0 dispatch (review skipped) | [#86](https://github.com/cuongdinhngo/code-atlas/pull/86) |
| 066 | 0 dispatch (review skipped) | [#87](https://github.com/cuongdinhngo/code-atlas/pull/87) |
| 072 | 0 dispatch (review waived); + a Docker measurement of busy-branch latency under 4-way contention | [#89](https://github.com/cuongdinhngo/code-atlas/pull/89) |
| 070 | **78.5k dispatch** — 1 analysis Explore (17 / 126 s); review waived | [#91](https://github.com/cuongdinhngo/code-atlas/pull/91) |
| 069 | **113.7k dispatch** — analysis Explore 88.3k (40 / 227 s) + an execute blind-reader routing exercise 25.3k; review waived | [#92](https://github.com/cuongdinhngo/code-atlas/pull/92) |
| 074 | 0 dispatch — prep half only; the n ≥ 3 runs need the anchor repo | [#93](https://github.com/cuongdinhngo/code-atlas/pull/93) |
| 075 | 0 dispatch (review waived); two Docker full-suite runs for delta-green (**1094 passed**) | [#94](https://github.com/cuongdinhngo/code-atlas/pull/94) |
| 076 | 0 dispatch — folded into 075's run; shared cost is the row above | [#94](https://github.com/cuongdinhngo/code-atlas/pull/94) |
| 077 | 2 dispatch, unmeasured (explore + exposure-checker); review waived | [#96](https://github.com/cuongdinhngo/code-atlas/pull/96) |
| 078 | 2 dispatch, unmeasured (explore + exposure-checker); review waived | [#97](https://github.com/cuongdinhngo/code-atlas/pull/97) |
| 079 | 0 dispatch (review waived); main-loop only. Four Docker runs for delta-green (full gate **1130 passed**) | [#98](https://github.com/cuongdinhngo/code-atlas/pull/98) |
| 082 | 1 dispatch — refine exposure-checker **50.5k** (9 tool-uses, 154 s); review waived. Docker runs for delta-green (full gate **1134 passed**) | [#99](https://github.com/cuongdinhngo/code-atlas/pull/99) |
| 081 | 1 dispatch — refine exposure-checker **60.4k** (17 tool-uses, 194 s); review waived. Docker runs for delta-green (full gate **1137 passed**) | [#100](https://github.com/cuongdinhngo/code-atlas/pull/100) |
| 080 | 1 dispatch — refine exposure-checker **57.8k** (8 tool-uses, 187 s); review waived. Docker runs for delta-green (full gate **1140 passed**); one blast-radius miss caught + absorbed | [#101](https://github.com/cuongdinhngo/code-atlas/pull/101) |
| 092 | 1 dispatch — refine exposure-checker unmeasured (blocking retrieval); review waived at solve time, then done on the PR (0 dispatch, in-session). Docker delta-green (full gate **1167 passed**; branch pre-review 1165, `main` 1160 — both re-measured, the "1162" first recorded here was a stale count) | [#102](https://github.com/cuongdinhngo/code-atlas/pull/102) |
| 093 | 1 dispatch — `/code-review` on the PR **61.7k** (20 tool-uses, 205 s); refine skipped (0 unresolved product-decisions), review waived at solve time then run on the PR. Docker delta-green (full gate **1175 passed**; `main` baseline 1167, +8 new tests, none removed — 1173 pre-review, +2 from the review fixes) | [#103](https://github.com/cuongdinhngo/code-atlas/pull/103) |
| 095 | 1 dispatch — refine exposure-checker unmeasured (host does not surface usage); review waived at solve time. Docker delta-green (full gate **1183 passed**; `main` baseline 1175, +8 new tests, none removed) | [#105](https://github.com/cuongdinhngo/code-atlas/pull/105) |
| 097 | 1 dispatch — refine exposure-checker unmeasured (host does not surface usage); review waived at solve time. Docker delta-green (full gate **1191 passed**; `main` baseline 1183, +8 new tests, none removed) | [#107](https://github.com/cuongdinhngo/code-atlas/pull/107) |
| 101 | **139.2k dispatch, all measured** — reviewer r1 139.2k (47 tool-uses, 952 s), returned CHANGES REQUESTED with 2 Important findings, both real and both fixed; verify pass **not dispatched** (conditional LGTM, done in the main loop). Challenger **waived by operator**; refine exposure-checker and analysis Explore fan-out **not dispatched** (session standing instruction), disclosed rather than silently skipped. Docker delta-green (full gate **1262 passed**; `main` baseline 1240, +22 new tests, none removed). Review finding 1: the first delta-green claim was true when measured and stale when committed — the docs commit itself armed the bookkeeping test | [#116](https://github.com/cuongdinhngo/code-atlas/pull/116) |
| 100 | **296.0k dispatch, all measured** — reviewer r1 134.9k (54 tool-uses, 649 s) + reviewer r2 verify 161.1k (16 / 272 s). Challenger **waived by operator**; refine exposure-checker and analysis Explore fan-out **not dispatched** (session standing instruction), disclosed rather than silently skipped. Docker delta-green (full gate **1238 passed**; `main` baseline 1222, +16 new tests, none removed). Review found 2 Important defects, both fixed | [#114](https://github.com/cuongdinhngo/code-atlas/pull/114) |
| 094 | 1 dispatch — refine exposure-checker unmeasured (host does not surface usage); review waived at solve time, then run on the PR (0 dispatch, in-session — caught `self`/`static`/`parent``::class` emitting `\self`). Docker delta-green (full gate **1196 passed**; `main` baseline 1191, +5 new tests, none removed — 1195 pre-review, +1 from the review fix) | [#108](https://github.com/cuongdinhngo/code-atlas/pull/108) |
| 096 | **0 dispatch — main-loop only** (challenge waived at solve time; the host does not surface subagent usage, so a dispatched row would have read `unmeasured` either way). Docker delta-green (full gate **1204 passed**; `main` baseline 1196, +8 new tests, none removed — 1202 pre-review, +2 from the second review pass). Cost dominated by the synthetic-index profiling runs (5k/20k/60k, before and after), not by the diff | [#110](https://github.com/cuongdinhngo/code-atlas/pull/110) |
| 099 | **0 dispatch — main-loop only** (challenge waived at solve time; host does not surface subagent usage). Docker delta-green (full gate **1222 passed**; `main` baseline 1204, +14 new tests and +4 parametrized cases from two new core modules, none removed) | [#111](https://github.com/cuongdinhngo/code-atlas/pull/111) |
| — | CI red on `main` after #108: profiler wall-tolerance floor. 0 dispatch, main-loop only. Docker gate **1196 passed**, plus a throttled (0.4 CPU) 40-run repro sizing the floor from the measured tail | [#109](https://github.com/cuongdinhngo/code-atlas/pull/109) |
| 100 | **296.0k dispatch, all measured** — `mango:reviewer` r1 134.9k (54 / 649 s) + r2 verify 161.1k (16 / 272 s); refine + analysis fan-out not dispatched (session standing instruction, disclosed). Main-loop unmeasured | [#114](https://github.com/cuongdinhngo/code-atlas/pull/114) |
| 101 | **139.2k dispatch, measured** — `mango:reviewer` r1 139.2k (47 / 952 s), CHANGES REQUESTED with 2 real Important findings; r2 not dispatched (conditional LGTM, verify done in the main loop); challenger waived. Main-loop unmeasured — the A1/A2 harness + 29 tests were the real spend | [#116](https://github.com/cuongdinhngo/code-atlas/pull/116) |
| 102 | **89.4k dispatch, all measured** — `mango:reviewer` r1 89.4k (27 tool-uses, 356 s), CHANGES REQUESTED / conditional LGTM with 1 Important finding: the fix's own new `paths` branch counted a *resolvable* subject as lost and labelled it `name_not_qualified` — the defect class the ticket exists to remove, reintroduced inside its fix. Confirmed by measurement before it was accepted. Verify pass **not dispatched** (fix stayed inside the approved rows, done in the main loop). Challenger **waived by `--no-challenger`**; refine exposure-checker and analysis Explore fan-out **not dispatched** (session standing instruction), disclosed rather than silently skipped. Main-loop unmeasured — the two Docker gate runs and the live probes were the real spend. Docker delta-green (full gate **1268 passed**; `main` baseline 1262, +6 new tests, none removed). First run of `/mango:autorun` in this repo | [#117](https://github.com/cuongdinhngo/code-atlas/pull/117) |
| — | Ticket-writing for 102: 0 dispatch; the defect was measured during 100, not by a separate run | [#115](https://github.com/cuongdinhngo/code-atlas/pull/115) |
| — | Field retro round 4 + ticket-writing for 075–082: 0 dispatch. **No PR** — committed straight to `main` on the maintainer's instruction for docs-only changes | — |
| 083 | **65.4k dispatch, measured** — `mango:reviewer` r1 65.4k (30 tool-uses, 233 s) → LGTM, no findings. Challenger **waived by `--no-challenger`**; refine exposure-checker (refine self-skipped, 0 unresolved) and analysis Explore fan-out (done in the main loop) **not dispatched**, disclosed. Main-loop unmeasured (host does not surface usage). Docker delta-green (`main` baseline **1268** → branch **1283**, +15: 11 authored tests + 4 from the two per-module R1.1 sweeps; none removed). Second `/mango:autorun` run in this repo | [#120](https://github.com/cuongdinhngo/code-atlas/pull/120) |
| 084 | **124.4k dispatch, measured** — `mango:reviewer` r1 **74.0k** (32 tool-uses, 297 s) → LGTM, no findings + `mango:challenger` **50.4k** (22 tool-uses, 170 s) → 9 met / 1 recorded-exclusion (AC1(b) anchor manual check). Challenger **ON** (default). refine self-skipped (0 unresolved) → exposure-checker not dispatched; analysis Explore fan-out done in the main loop; no extractor — disclosed. Main-loop unmeasured (host does not surface usage). Docker delta-green (full gate **1291 passed**, mypy 44 files, ruff clean; scoped baseline 103→111). Third `/mango:autorun` run in this repo | [#121](https://github.com/cuongdinhngo/code-atlas/pull/121) |
| 103 | **175.4k dispatch, all measured** — refine exposure-checker (ticket-blind challenger) **38.9k** (3 tool-uses, 103 s) → raised 5 items → 3 product-decisions (2 ASSUMED, delegated by the maintainer); `mango:reviewer` r1 **77.1k** (22 tool-uses, 295 s) → **LGTM**, no findings; `mango:challenger` **59.5k** (13 tool-uses, 259 s) → 8 met / 2 not-met on tested deliverables (AC1 rank assertion + AC4(c) lone-module test — both **fixed**) / 1 ambiguity (AC5 wording — **reconciled**). Challenger **ON** (default); refine did **NOT** self-skip (first autorun here where it exposed real product-decisions). Verify-only re-review in the main loop (fixes stayed in the named findings). Main-loop unmeasured (host does not surface usage). Docker delta-green (full gate **1299 passed**, mypy 44 files, ruff clean; scoped baseline 100→106). Fourth `/mango:autorun` run in this repo | [#122](https://github.com/cuongdinhngo/code-atlas/pull/122) |
| 104 | **91.8k dispatch, measured** — `mango:reviewer` r1 **91.8k** (21 tool-uses, 401 s) → **LGTM**, no Critical/Important + 1 non-blocking observation (byte-stability test could not observe order-dependence past `_grain`'s sort) **acted on** (commit `bf1bea2`: a determinism probe at the `assign_layers` boundary on a count-tie fixture). Challenger **waived by `--no-challenger`** (0); refine **self-skipped** (0 unresolved — 104 pre-decides the signal) → no exposure-checker; analysis Explore fan-out done in the main loop — disclosed. Main-loop unmeasured (host does not surface usage). Docker delta-green (full gate **1308 passed, 0 failed**; `main` was **red** — 2 bookkeeping failures from 103's unparseable status cell, fixed here; +6 onboarding tests, none removed). Fifth `/mango:autorun` run. **Ticket `blocked` on AC2** (anchor-repo proof outstanding — recorded exclusion) | [#123](https://github.com/cuongdinhngo/code-atlas/pull/123) |
| 085 | **136.5k dispatch, measured** — `mango:reviewer` r1 **88.6k** (24 tool-uses, 262 s) → **CHANGES REQUESTED → conditional LGTM**, no Critical + 2 Important (F1 docs-before-PR bookkeeping; F2 the split-guard's made-to-fail claim needed a *recorded red run* per R6.5 + a docstring framing correction) — **both landed**, verify-only re-review in the main loop (fixes stayed in the named findings). `mango:challenger` **47.9k** (10 tool-uses, 78 s) → **9 met / 0 not-met / 0 can't-tell**. Challenger **ON** (default); refine **self-skipped** (0 unresolved) → no exposure-checker; analysis Explore fan-out done in the main loop; no extractor — disclosed. Main-loop unmeasured (host does not surface usage). Docker delta-green (full gate **1317 passed, 0 failed**, mypy **45 files**, ruff clean; `main` baseline **1308** → branch **1317**, +9: 7 authored tests + 2 per-module parametrized guard cases for the new core module; none removed). Sixth `/mango:autorun` run | [#124](https://github.com/cuongdinhngo/code-atlas/pull/124) |

| 086 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 086 with skipped review and challenger`: the **review phase was waived by the operator argument** and the **challenger with it**, refine **self-skipped** (0 unresolved) so no exposure-checker ran, and the analysis fan-out was done in the main loop. Every phase ran in the main loop, which this host does not surface usage for — so the ledger is **complete with one honest marker**: dispatch **0 rows**, main-loop **unmeasured (host does not surface usage)**. Delta-green: gate **1317 → 1336 passed, 0 failed** (+19: 9 authored tool tests, 8 parametrized cases the new tool adds to the existing per-tool sweeps, 2 bookkeeping cases from ticket 105's row; none removed), ruff clean, mypy **46 files**; confirmed in Docker (`scripts/docker-test.sh`). **Self-review round on the PR** (operator asked for a direct review instead of mango reviewer+challenger, so still 0 dispatch): 6 findings, all reproduced, all fixed — the worst was `results`/`cross_layer_edges` uncapped on the default path (176 KB → 7.8 KB on a 1000-module synthetic). Three real pinned repos indexed for AC1 (evidence in the working doc) | [#125](https://github.com/cuongdinhngo/code-atlas/pull/125) |
| 087 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 087 with skipped Review + Challenger`: review waived, challenger off, refine self-skipped (0 unresolved). Main-loop **unmeasured (host does not surface usage)**. Delta-green: **1336 → 1347 passed, 0 failed** (+11: 5 authored tests in `test_guided_tour.py` + parametrized `TOOL_NAMES` cases; none removed), ruff clean, mypy **48 files**. Host `.venv/bin/pytest -q` (Linux + PHP) at `6c2475e`. **Review round on the PR** (maintainer asked for a direct review, so still 0 dispatch): PR CI is red for **four billing-blocked jobs**, not for code — gate proven in Docker. 4 findings, all reproduced then fixed; the worst was a component no entry point reaches being silently absent with `truncated: false` (a 3-file index answered with 1 stop). Delta-green **1347 → 1353**, +6 tests. | [#126](https://github.com/cuongdinhngo/code-atlas/pull/126) |
| 088 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 088 with skipped Review + Challenger`: review waived, challenger off, refine self-skipped (0 unresolved). Main-loop **unmeasured (host does not surface usage)**. Delta-green: **1353 → 1373 passed, 0 failed** (+20: 6 authored tests in `test_generate_onboarding.py` + parametrized `TOOL_NAMES`/`CALLS` cases; none removed), ruff clean, mypy **50 files**. Host `.venv/bin/pytest -q` (Linux + PHP) at `bd431a4`. **Review round on the PR** (maintainer asked for a direct review, so still 0 dispatch): PR CI red for the same **four billing-blocked jobs**, not for code — gate proven in Docker. 2 findings, both reproduced then fixed; the worst was `shutil.rmtree` on `docs/onboarding/modules`, which deleted hand-authored files the tool never wrote (050's rule). Delta-green **1373 → 1377**, +4 tests. | [#127](https://github.com/cuongdinhngo/code-atlas/pull/127) |
| 089 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 089 with skipped Review + Challenger`: review waived, challenger off, refine self-skipped (0 unresolved). Main-loop **unmeasured (host does not surface usage)**. Delta-green: **1377 → 1382 passed, 0 failed** (+5: 3 authored tests in `test_onboarding_viewer.py` + 2 count-pin cases; none removed), ruff clean, mypy **51 files**. Host `.venv/bin/pytest -q` (Linux + PHP) at `9ff28b4`. **Review round on the PR** (maintainer asked for a direct review, so still 0 dispatch): PR CI red for the same **four billing-blocked jobs**, not for code — gate proven in Docker. 3 findings: the `<`-escape that stops a script-tag breakout had **no test** (deleting it kept the suite green, and a directory `a<` + file `script>x` makes a path string carry `</script>`), a blank page with scripting off, and no `lang`. All fixed. Delta-green **1382 → 1384**, +2 tests. | [#128](https://github.com/cuongdinhngo/code-atlas/pull/128) |
| 090 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 090 with skipped review & challenger`: review waived, challenger off, refine ran (4 how-decisions resolved+cited, 0 want-decisions, 0 ASSUMED). Main-loop **unmeasured (host does not surface usage)**. Delta-green: **1384 → 1441 passed, 0 failed** (+57: 6 authored tests in `test_onboarding_llm.py` + the `no-core-module-imports-an-llm` parametrization over the 51 core modules; count-pins `core_modules() == 51` **unchanged** — the LLM code lives outside `code_atlas/`), ruff clean, mypy clean (`onboarding_llm` added to files). Docker `scripts/docker-test.sh` at `77.42s`. Self-verification sweep in the main loop (review phase waived by run arg): diff ⊆ approved change-list, every Approach bullet implemented-as-approved. **Post-PR `/code-review #129`** (main-loop review, still 0 dispatch): 5 findings, all reproduced then fixed on the generation/cache path — empty/refused result was cached permanently (now falls back, uncached), `max_tokens` shared with adaptive thinking (256 → 2048), `anthropic` floor predated `output_config` (dropped `output_config`, floor → `>=0.69`), malformed cache entry raised `KeyError` (now a miss), cache key omitted `_SYSTEM`/`max_tokens` (folded in). +2 tests. Delta-green **1441 → 1443**. | [#129](https://github.com/cuongdinhngo/code-atlas/pull/129) |
| 105 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 105 with skipped review & challenger`: review waived, challenger off, refine self-skipped (0 unresolved — the signal is a design how-decision the ticket hands to the design phase, not a want-decision). Main-loop **unmeasured (host does not surface usage)**. Core change is one function: `_dominant_subtree` elects by graph mass (Σ fan_in+fan_out), not file count — **no new file under `code_atlas/`**, so count-pins `core_modules() == 51` unchanged. Delta-green: full Docker gate **1453 passed, 0 failed** (proving test renamed/retargeted), ruff clean, mypy **51 source files**. **AC2 satisfied this session** (unlike 104): `scripts/docker-test.sh python scripts/layer_report.py` cloned+indexed the three pinned repos — laravel/laravel splits `app/**` into Http/Models/Providers (F1 fixed), symfony/demo + brick/math byte-identical to 086. New committed opt-in `scripts/layer_report.py` is the durable answer to the recurring `fixture-shape-begs-the-question` lesson. **Post-PR `/code-review #131`** (main-loop, still 0 dispatch): 4 findings, all dispositioned — F2 edgeless index elected alphabetically not most-populous (**fixed**: mass tie-break falls back to `-count`, then name; +1 edgeless test), F3 `layer_report.py` had no assertions (**fixed**: per-repo require/forbid check with non-zero exit), F4 docstring count inconsistency (**fixed**), F1 hub-dir out-mass a documented deferred trade-off. Delta-green **1453 → 1454**. | [#131](https://github.com/cuongdinhngo/code-atlas/pull/131) |
| 091 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 091 with skipped review & challenger`: review waived, challenger off, refine ran (4 how-decisions resolved+cited — new `LayerRefiner` seam, rename-map contract, names-only scope, `claude-opus-5` top tier; 0 want-decisions, 0 ASSUMED). Main-loop **unmeasured (host does not surface usage)**. Delta-green: **1443 → 1453 passed, 0 failed** (+10 authored tests in `test_onboarding_llm_layers.py`; the seam types live in the existing `layers.py`, so **no new file under `code_atlas/`** — count-pins `core_modules() == 51` **unchanged**, mypy sees 51 source files), ruff clean, mypy clean. Docker `scripts/docker-test.sh` at `130.25s`. Self-verification sweep in the main loop (review phase waived by run arg): diff ⊆ approved change-list, every Approach bullet implemented-as-approved. Extracted `onboarding_llm/client.py` (shared client Protocol + `first_text`) so 090's summarizer and 091's refiner share one shape (DRY). | [#130](https://github.com/cuongdinhngo/code-atlas/pull/130) |
| 106 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 106 with skipped review & challenger`: review waived, challenger off, refine self-resolved (4 how-decisions resolved+cited — out-degree seed rank, quarter-budget seed cap, ranked+batched refill, R3/R4 rejected; 0 want-decisions, 0 ASSUMED); analysis reading done in the main loop — disclosed. Main-loop **unmeasured (host does not surface usage)**. Delta-green: collected **1458 → 1461**, Docker full gate **1461 passed, 0 failed** in 78.18 s (+3 authored tests in `test_guided_tour.py`, none removed), ruff clean, mypy clean over **51 source files** (count-pin unchanged — no new module). **AC3 proven on the three pinned repos** (laravel/symfony/brick tours byte-identical before/after — their 23/30/9 entry points sit under the 125 cap, so the cap cannot bind). **AC5 on the anchor monorepo** (18,926 files): seed-label stops **500/500 → 125/500**, pages with both neighbour lists empty **500/500 → 0/500**, page layer coverage **4 → 6**, subgraph edges **0 → 100,853**; `tour_subgraph` **3.554 s → 5.969 s**. One recorded deviation: D1/D3 refined mid-execute to a single out-degree signal after measuring the two-sided mass table at 6.125 s of 10.096 s — same subgraph, 4.1 s cheaper. | [#132](https://github.com/cuongdinhngo/code-atlas/pull/132) |
| 107 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 107 with skipped review & challenger`: review waived, challenger off, refine ran (4 how-decisions resolved at design; 0 want-decisions, 0 ASSUMED) and **caught the ticket's own evidence as stale** — 107 was written pre-#132 and claimed 500/500 bare pages on the anchor repo, re-measured **0/500**, so **AC2 was amended at Gate 1** (maintainer-ratified) to prove the fix on `laravel/laravel` (20 of 26), `symfony/demo` (7 of 51) and a sparse fixture, with the anchor repo as a no-regression check. Main-loop **unmeasured (host does not surface usage)**. Delta-green: **1461 → 1466 passed, 0 failed** (Docker, 100.03 s; +5 authored tests, none removed, **no existing assertion rewritten**), ruff clean, mypy clean over **51 source files**. Before → after: laravel 26 → 6 pages, symfony 51 → 44, brick 32 → 32, anchor 500 → 500, **stop counts unchanged everywhere**. Payload gains `isolated_modules` on `standard` — the shape change #132 deferred here. One **scope under-run** recorded: the Gate-2-flagged test update proved unnecessary because the rule tests full-graph degree. | [#133](https://github.com/cuongdinhngo/code-atlas/pull/133) |
| 108 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 108 with skipped Review & Challenge`: review waived, challenger off, refine self-skipped (0 unresolved product-decisions; 3 how-decisions resolved at design). Main-loop **unmeasured (host does not surface usage)**. Cap both neighbour lists **and** the SCC cycle-rationale at `CA_MAX_RESULTS` **in the presentation layer only** (`artifact.py` + `viewer.py`, the same fix serves the 31 MB HTML viewer) — `tour.py` untouched so `guided_tour`'s payload is unchanged; **no new file under `code_atlas/`**, count-pins `core_modules() == 51` unchanged. Delta-green: full Docker gate **1491 passed, 0 failed** in 107.44 s (+5 authored tests, none removed, no existing assertion rewritten), ruff clean, mypy clean. **AC1 observed red** against pre-fix code (20 back-ticks / all 10 paths, no `(N shown of M)`). **AC4 amended at Gate 1** — the anchor monorepo is absent on this dev host, so the byte bound is proven on a synthetic-scale fixture reproducing the 82 KB shape: one page **40,074 B → 6,878 B** at the default cap 50; the at-scale anchor re-measure is deferred to an operator run (015/018 pattern). | [#135](https://github.com/cuongdinhngo/code-atlas/pull/135) |
| 110 | **95.3k dispatch, measured** — one Explore fan-out (layer test / byte-stability surface map) **95,257** tokens; reviewer + ticket-blind challenger **WAIVED** by run arg (0). Main-loop **unmeasured (host does not surface usage)**. Gate 0 (R2.2): the 36-word responsibility vocabulary ratified **STANDARD** by the maintainer → full ticket. `assign_layers` is responsibility-first (deepest directory-segment wins), dominant-subtree/direction kept as fallback (105/104/103 coverage intact, fixtures de-vocabularised); every layer gains a `description` derived from its name; 109's C3 moved name→description (one-line hand-off). No new core module → count-pins stay 52. Delta-green: full Docker gate **1514 passed, 0 failed** in 106.72 s (+6 net; layer suite rewritten to 40 tests, none of 105/104's regressions lost), ruff clean, mypy clean. **AC4 on pinned repos** via `scripts/layer_report.py` (anchor deferred, 108 pattern): laravel/laravel 5 layers/23% Uncategorised, symfony/demo 7/35%, brick/math 2/75% — the last a pure math library with no web/domain roles, so Uncategorised dominating is the "reported, not hidden" signal, discussed not silenced. | [#137](https://github.com/cuongdinhngo/code-atlas/pull/137) |
| 109 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 109 with skipped Review & Challenge`: review waived, challenger off, refine self-skipped (0 unresolved product-decisions; 6 how-decisions H1–H6 resolved at analysis). Main-loop **unmeasured (host does not surface usage)**. New core module `onboarding/quality_gate.py` (`check_artifact` runs C1–C7, raises `QualityGateError` from `build_artifact` before writing — 050 precedent); **count-pins bumped 51 → 52** in the two guard-the-guard tests. Three checks reference things a later ticket introduces, so each ships its pre-cursor invariant: **C3** = non-empty layer name (110 strengthens to a description), **C4** = `len(stops) ≤ 500` regression ceiling (111 tightens to `[5,15]`), **C7** = canonical-ordering invariant (its build-twice half reuses the existing byte-stable test, R7.1). Delta-green: full Docker gate **1508 passed, 0 failed** in 79.93 s (+14 authored pure tests + 2 count-pin bumps, none removed), ruff clean, mypy clean. **AC3 recorded ceilings** `MAX_PAGE_BYTES=16384`, `MAX_TOUR_STEPS=500`; **AC5** gate = 4.09 ms over a 500-page synthetic artifact. Anchor at-scale AC3/AC5 re-measure **deferred to an operator run** (108 pattern — anchor absent on this host). | [#136](https://github.com/cuongdinhngo/code-atlas/pull/136) |
| 111 | **61.6k dispatch, measured** — one Explore fan-out (test/consumer blast-radius map) **61,614** tokens (30 tool-uses, 180 s); reviewer + ticket-blind challenger **WAIVED** by run arg (0). Main-loop **unmeasured (host does not surface usage)**. refine self-skipped (0 unresolved product-decisions; 8 how-decisions H1–H8 at analysis). New core module `onboarding/steps.py` (`build_steps` groups the budgeted stops into `[5,15]` steps by layer rank × BFS depth, one contribution per SCC), `OnboardingArtifact` gains `steps`, `render_tour` emits steps not one line per file, **109's C4 repurposed** `len(stops)≤500` → `len(steps)≤15` + no-empty-step (`MAX_TOUR_STEPS` 500→15); **count-pins bumped 52 → 53**. `stops` kept (drives pages/manifest/viewer); `guided_tour` + `viewer.py` untouched (H8 scope; 116 owns the viewer). Delta-green: full Docker gate **1524 passed, 0 failed** in 99.91 s (+10 net authored, none removed), ruff clean, mypy clean over **53 source files**. **AC1 observed red** (`ordered_stops` yields 60 vs 5 steps). **AC5** via `scripts/tour_report.py` (anchor deferred, 108 pattern): laravel 26→7 steps (1729→1335 B), symfony 51→13 (4193→2844 B), brick 32→5 (5994→1205 B) — all `tour.md` <64 KB. | [#138](https://github.com/cuongdinhngo/code-atlas/pull/138) |
| 112 | **116.0k dispatch, measured** — one Explore fan-out (store/consumer/prototype blast-radius map) **115,972** tokens (24 tool-uses, 169 s); reviewer + ticket-blind challenger **WAIVED** by run arg (inline main-loop review only). Main-loop **unmeasured (host does not surface usage)**. refine self-skipped (0 unresolved product-decisions; 9 how-decisions H1–H9 at analysis). New pure core module `onboarding/dataset.py` (versioned `OnboardingDataset` + `build_dataset` + `render_dataset_overview`); **five bounded SQL aggregates in `store.py`** (`node_kind_counts`, `edge_kind_counts`, `module_hubs`, `largest_classes`, `file_symbol_counts` — the mockup's direct reads, ported); new knob `CA_PATH_INDEX_MAX` (config pins 13→14); **`manifest.json` reduced to the dataset** + a `pages` delete-record, `recorded_pages` reads the new key; **count-pins bumped 53 → 54**. Layer table/matrix stay from the pure 083/110 pipeline (H3 — assignment is graph-mass reasoning, not SQL; documented double-compute, 116 can share); renderers themselves are 116 (H8 — only the AC5 proof-renderer here). Delta-green: full Docker gate **1543 passed, 0 failed** (+19 net authored, none removed), ruff clean, mypy clean over **54 source files**. **AC1** grep-gate: no SQL/`sqlite3` under `onboarding/` or `tools/`. **H4** pinned: SQL hub fan-in == module-metric fan-in. **AC3/AC4** via `scripts/dataset_report.py` (aggregate-half <100 KB, added query time vs `tour_subgraph`; **anchor deferred to operator**, 108 pattern). | [#139](https://github.com/cuongdinhngo/code-atlas/pull/139) |
| 113 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 113 with skipped review & challenge`: review waived, challenger off, refine self-skipped (0 unresolved product-decisions; 8 how-decisions H1–H8 at analysis). Main-loop **unmeasured (host does not surface usage)**. **The R2.2 judgment the ticket held open resolved in the ticket's favour and needed no new signal:** 110's responsibility vocabulary is already recorded as a ratified R2.2 standard and already carries `vendor`, `test`/`spec`/`mock` and `controller`/`route`/`api`, so the classifier is pure composition of that vocabulary + 083's degrees + the operator's own `entry_points`/`stub_roots` — **no library-name list, no `composer.json` parsing, four buckets fillable rather than the honest three-bucket fallback.** New pure core module `onboarding/reachability.py` (five disjoint buckets summing to the raw total; role before structure, so a test file with no edges is a test, not a dead-code candidate); `layers.py` gains a public `responsibility_layer` so a **091 LLM rename cannot silently empty a bucket**; `DATASET_VERSION` 1 → 2; **count-pins bumped 54 → 55**; the R2.2 CI grep-gate now also scans `code_atlas/`, not `adapters/` alone. `nodes.is_test` was **rejected** as the test signal — the contract field exists but no adapter emits it, so it would render a false zero on a repo with 1,776 test files. Delta-green: full Docker gate **1559 passed, 0 failed** (main 1543, +16 net = 13 new + 3 from module-parametrized pins; none removed), ruff clean, mypy clean over **55 source files**. **AC5 is exercisable, not a formality**: where no indexed path names any responsibility, the three vocabulary buckets are dropped **with the reason**, never a misleading zero. **AC4** via `scripts/reachability_report.py` (**anchor deferred to operator**, 108/112 pattern). | [#140](https://github.com/cuongdinhngo/code-atlas/pull/140) |
| 114 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 114 with skipped review & challenge`: review waived, challenger off, refine self-skipped (0 unresolved product-decisions; 10 how-decisions H1–H10 at analysis). Main-loop **unmeasured (host does not surface usage)**. **The mockup prototype was not portable — four separate R2.2 violations** (a container word list, a region list, a *library* list, and hardcoded tree prefixes), so the signal is re-derived structurally: the container is the directory fanning out into >= 4 peer subtrees of >= 3 files, its children are the modules, and its own parent is their tree — which makes region and container names **structurally incapable** of becoming modules, satisfying half of AC4 with no list at all. A container whose children are >= half 110 role names is **refused with its reason**. New pure core module `onboarding/modules.py`; one bounded store aggregate `file_class_counts()`; `DATASET_VERSION` 2 -> 3; **count-pins bumped 55 -> 56**. **Real-repo measurement ran BEFORE the design** (the cached pins) and moved it twice — a file-count floor alone cannot separate a library's 10-file exception directory from a module, and the widest container on one pin is role-organised. **AC1's fixture was amended at Gate 1** (2 modules -> 4 + a boundary test): the literal 2-module fixture cannot pass the shipped gate, and lowering that gate would break AC5 on a real repo. Two gates caught real defects: `responsibility_layer` **drops the last segment**, so the role check silently returned `None` for a bare directory name (fixed with a public `responsibility_of_segment` — the one addition beyond the approved change list), and **113's widened R2.2 CI gate fired on this ticket's own draft comment** (LESSONS 003 class), earning its widening on the first ticket after it landed. Delta-green: full Docker gate **1581 passed, 0 failed** (main 1559, +22 net = 19 new + 3 from module-parametrized pins; none removed), ruff clean, mypy clean over **56 source files**. **AC5 via `scripts/module_report.py` (Docker, indexed): 0 modules on all three pins** — laravel 0/26 files, symfony 0/51 with `src` refused as role-organised, brick 0/32 — which is AC5's honest zero, not a gap. **Anchor deferred to operator** (108/112/113 pattern). | [#141](https://github.com/cuongdinhngo/code-atlas/pull/141) |
| 115 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 115 with skipped review & challenge`: review waived, challenger off, refine self-skipped (0 unresolved product-decisions; 10 how-decisions H1–H10 at analysis). Main-loop **unmeasured (host does not surface usage)**. **`depends_on` was pointing the wrong way** — 098 was listed as a dependency but 115 *feeds* 098, so the frontmatter becomes `depends_on: [112]` + `feeds: [098]` and nobody waits on a deferred ticket. New pure core module `onboarding/mirrors.py` (sibling subtrees discovered, never configured — the prototype hardcoded one tree prefix and two region names and carried the region names in its output keys); `resolve_counterpart` answers the lookup with **three** outcomes, where `no_counterpart` is the divergence marker and a negative drawn from a **capped** path index is **qualified**, because a trimmed file and a diverged file are otherwise indistinguishable; `DATASET_VERSION` 3 -> 4; **count-pins bumped 56 -> 57**. **Two gates, not one, chosen by measurement before the design:** a pinned public repo scores a **perfect 1.000 overlap on a pair sharing ONE file**, so the Jaccard fraction alone accepts noise — the shared-count gate (25) rejects it, and `scripts/mirror_report.py` prints the best *ungated* pair per repo so the constant can be re-justified whenever a pin moves. **AC3/AC4 measured (Docker, indexed): 0 accepted pairs on all three pins**; the anchor arithmetic is pinned instead by a test reproducing its 4,244 / 1,522 / 1,134 and 0.615 exactly. **AC6 — and the verdict is negative, which is the finding:** the evidence written into 098 keeps it **deferred** rather than opening it, because a structural detector found the shape in **none** of three independent repos (gate 1 unmet and now *further* from met — measured absence beats no evidence), while gates 2 and 3 are answered *against* a schema relation (near-zero cost precisely by not being in the schema; the cheaper alternative was not rejected, it works). The R2.2 unit twin caught this ticket's own docstring quoting the prototype's literals — **the same failure as 114**, so the claim now has `seen: [114, 115]` and is flagged for `/mango:promote`. Delta-green: full Docker gate **1601 passed, 0 failed** (main 1581, +20 net = 17 new + 3 from module-parametrized pins; none removed), ruff clean, mypy clean over **57 source files**. **Anchor deferred to operator** (108/112/113/114 pattern). | [#142](https://github.com/cuongdinhngo/code-atlas/pull/142) |
| 116 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 116 with skipped review & challenge`: review waived, challenger off. Main-loop **unmeasured (host does not surface usage)**. refine ran the **ticket-refine** path (1 unresolved product-decision, W1: the map drops 089's Tour tab and renders the dataset **alone** — assumed, ratified at Gate 1); 6 how-decisions H1–H6. **`viewer.py` rewritten, not duplicated** (AC7), so the core-module pin stays at **57**; `viewer_payload` deleted rather than ported — 089 kept a second hand-written payload shape and the dataset now *is* the payload. `DATASET_VERSION` 4 -> 5 for three fields, each forced by an AC: `commit` (AC3 needs the dataset to be the sole input), per-layer `kinds` (the composition bar, from a new bounded `store.file_kind_counts()`), and `dir_symbol_threshold` (AC4 forbids a template literal, and the empty-sitemap sentence must name the threshold). **The ticket's premise was partly falsified and the proving test re-chosen:** 089's viewer at anchor scale measures **921,746 B, not 31 MB** — task **108 had already removed ~97 %** by capping the page bodies — so the red is the *absence of the spatial answer*, not the size. **node is now a test dependency** (`docker/Dockerfile` + CI): the page builds its content in the browser, so AC4/AC5/AC6 have no static formulation and a grep over the HTML would be a false green; `tests/viewer_dom_stub.js` runs the page and reports what rendered, with every assertion in Python. **AC4 reformulated after it asserted something false** — "every figure moved" cannot hold for a cardinality or a ratio, so it is now a static half (no digit in the template's visible text) plus a behavioural half (every >=4-digit figure disjoint under a x1009 count scaling). **AC2 measured, and the pins named as unable to test it** (26–51 files, two orders of magnitude under both thresholds): asserted against a synthetic dataset at the anchor's *measured* cardinality — **969,009 B** with the path index (index alone 860,143 B = **1.020x** the anchor's 843,439 B, which is **96.9 %** of its whole dataset) and **108,940 B** without, vs 089's 921,746 B — **8.5x smaller without the index, while answering more**. Two of three pins map **zero** directories, so the empty sitemap names its threshold instead of drawing a blank box. Delta-green: full Docker gate **1618 passed, 0 failed** (main 1601, +17 net = 13 in the rewritten viewer suite + 4 dataset tests; none removed), ruff clean, mypy clean over **57 source files**. **Anchor deferred to operator** via `CA_ANCHOR` in `scripts/viewer_report.py` (108/112–115 pattern). | [#143](https://github.com/cuongdinhngo/code-atlas/pull/143) |
| 117 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 117 with skipped review & challenge`: review waived, challenger off. Main-loop **unmeasured (host does not surface usage)**. refine ran the **ticket-refine** path (2 unresolved decisions: the seam's routing, and AC1's reading — the latter tagged `ASSUMED` and ratified at Gate 1); 4 how-decisions H1–H4. **The ticket's routing bullet was falsified by measurement before any code was written:** it sends layer descriptions through 091's `LayerRefiner`, which is gated on the *weak* names 084 falls back to — and 110 made `responsibility` the primary method, so all three pinned repos yield **zero weak layers** and that route would have described **0 of 14** layers. Replaced by **one** `ProseWriter` Protocol with one method serving all three slots, which is also the only way the filler guard (AC6), the failure degradation (AC4) and the per-run ceiling (AC5) get one home each instead of two — a split budget is not a budget. `LayerRefiner` left untouched. New pure core modules `onboarding/prose.py` (seam + `is_filler` + `ProseRun`) and `onboarding/headlines.py` (six derived candidate families); `TYPE_KINDS`/`CALLABLE_KINDS` added to `contract.py` as **named subsets** of the existing vocabulary, so `CONTRACT_VERSION` stays 5 (R3); `DATASET_VERSION` 5 -> 6 for `headlines`; **count-pins bumped 57 -> 59**. **AC1 could not mean what it says** — the Scope requires structural-default headline sentences when the seam is off, which is new deterministic content, so the map's bytes necessarily move; read (and ratified) as the reproducibility claim, proven over all four renderers against both `None` and an explicit identity run. **The call ceiling is derived, not invented:** 6 families + 110's 12 layers + 109's 15-step C4 = **33**, pinned by a test that re-derives each from its source (R6.7) rather than trusting the copy. **AC5 measured, including the case where the ceiling actually bites** — the pins cost 12/17/25 cold calls and 0 warm, an 18,929-file synthetic with named layers costs 24, and the same synthetic with paths naming no responsibility (084 falls back to per-directory layers, unbounded) requests **1,176 layer descriptions, is served 12 and refused 1,164**: a report where the limit never triggers proves the arithmetic, not the enforcement. Tokens are printed as prompt **bytes** plus a labelled char/4 **estimate**, never as a measurement. Two gates caught real work: an AC6 test asserted that a writer returning `"Services"` is filler for every layer — it is filler only for the layer *named* Services, and C1 catches prose that restates what it was handed, not prose that is merely wrong (fixture fixed, predicate kept); and a shared `indexed_pins()` helper was written and then **deleted** on finding the three existing report scripts wrap that loop in a per-repo `try/except`, so migrating them was not mechanical and was out of scope. Delta-green: full Docker gate **1671 passed, 0 failed** (main 1618, +53 net = 47 authored + 6 from tests parametrized over the core-module list; none removed), ruff clean, mypy clean over **59 source files**. New CI grep-gate **R4.1** (no prompt, model id or LLM import under `code_atlas/` — AC7). **Anchor deferred to operator** via `scripts/prose_cost_report.py` (108/112–116 pattern). | [#144](https://github.com/cuongdinhngo/code-atlas/pull/144) |
| — | **Docs-truth sweep + four tickets authored (118 · 119 · 120 · 121).** 0 dispatch — main-loop only, **unmeasured** (the host surfaces no usage block); no mango lifecycle, so `no work doc`. The spend was reading, not writing: two onboarding regenerations on the anchor monorepo (17 s each), a hand-written attribution pass over its 1.0 GB index, and the doc audit itself. Delta-green: Docker gate **1679 passed**, ruff clean, mypy clean over 59 source files (`main` baseline 1671; the +8 is `test_backlog_bookkeeping`'s two parametrized rows per new task file — no test authored, none removed) | [#145](https://github.com/cuongdinhngo/code-atlas/pull/145) |
| — | **Round-6 retro triage + four tickets authored (122 · 123 · 124 · 125).** 0 dispatch — main-loop only, **unmeasured** (no usage block surfaced); no mango lifecycle, so `no work doc`. The spend was verification, not authoring: every one of the retro's five findings was re-derived from source before it was written down, which is what turned "one-character fix" into 075's unfinished scope bullet and turned two "defects" into 057's recorded exclusions. Docs-only, no source touched; suite unchanged except `test_backlog_bookkeeping`'s parametrized rows for the four new task files | [#146](https://github.com/cuongdinhngo/code-atlas/pull/146) |
| 122 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 122 with skipped review & Challenge`: review waived, challenger off, refine self-skipped (0 unresolved). Main-loop **unmeasured (host does not surface usage)**. `shape_exact_miss` now branches on `resolved_unique` before `candidate_count`; four `find_*` tools re-point via shared `unique_repoint` and attach `resolved_qname` when the answered qname differs from the asked one. Delta-green: **1687 → 1692 passed, 0 failed** (+5 authored tests in `test_qname_subject_honesty.py`; none removed), ruff clean, mypy clean over 5 touched source files. 075 sibling-surface bullet closed with enumerating test evidence | [#147](https://github.com/cuongdinhngo/code-atlas/pull/147) |
| 123 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 123 with skipped review & Challenge`: review waived, challenger off. Main-loop **unmeasured (host does not surface usage)**. `file_outline` now reports the store-side symbol count, pages with `limit`/`offset`, attaches `result_kinds` when truncated, and joins 066's clamp denominator (N=6). Delta-green: **1692 → 1710 passed, 0 failed** (+18: 13 new tests across three files, plus the R6.7 source-scan guard added in review; none removed), ruff clean, mypy clean. 057/066 exclusion bullets closed with field-evidence pointers | [#148](https://github.com/cuongdinhngo/code-atlas/pull/148) |
| 124 | **0 dispatch — no subagent was dispatched this run.** Run as `/mango:solve 124 with skipped review & Challenge`: review waived, challenger off. Main-loop **unmeasured (host does not surface usage)**. `find_orphans` pages with `limit`/`offset`, names orphan population in `total_count`, uses `CA_ORPHANS_MAX_NODES` for the walk (not `impact_max_nodes`), and keeps `minimal` transport-safe via `unproven_total`. Review split page truncation from walk truncation (`walk_truncated`) — folded together, a budget-bound walk kept `truncated: true` on every page and the documented pager never terminated. Delta-green: **1710 → 1725 passed, 0 failed** (+15: 8 new pagination tests, the review's pager-termination test, guard/collateral updates; none removed), ruff clean, mypy clean. Round-6 >10k carve-out retired; 057/066 exclusion bullets closed | [#149](https://github.com/cuongdinhngo/code-atlas/pull/149) |

**How 047–049 were measured.** One autonomous session, no per-task transcript: each row is the API
calls between the previous commit and that task's own commit. The approximation runs one way — work
interleaved across tasks lands in whichever segment it finished in (049 is the known case).

## Conventions
- Keep task `status` in this table **and** in each task file's frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
- Landed narrative belongs in [PLAN §19](PLAN.md#19-project-context--decision-log) or
  [`LESSONS.md`](LESSONS.md), not here; a follow-up that gets ticketed leaves this file's
  [Follow-ups](#follow-ups-not-yet-ticketed) list.
