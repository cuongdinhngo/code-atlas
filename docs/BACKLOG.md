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
| 105 | [Onboarding — the dominant subtree is decided by file count, and a config dir can win it](tasks/105_dominant-subtree-loses-to-a-config-dir.md) | Phase 3 / M10 | todo | 104, 086 |
| 085 | [Onboarding — Summarizer Protocol seam + deterministic default](tasks/085_onboarding-summarizer-seam.md) | Phase 3 / M10 | done | 083 |
| 086 | [Onboarding — architecture_overview tool](tasks/086_architecture-overview-tool.md) | Phase 3 / M10 | done | 084, 085, 104 |
| 087 | [Onboarding — guided_tour tool](tasks/087_guided-tour-tool.md) | Phase 3 / M11 | todo | 083, 086 |
| 088 | [Onboarding — generate_onboarding markdown + manifest](tasks/088_generate-onboarding-markdown.md) | Phase 3 / M11 | todo | 084, 086, 087 |
| 089 | [Onboarding — static HTML viewer](tasks/089_onboarding-viewer.md) | Phase 3 / M11 | todo | 088 |
| 090 | [Onboarding — LLM summarizer behind the seam (opt-in)](tasks/090_llm-summarizer-impl.md) | Phase 3 / M12 | todo | 085, 088 |
| 091 | [Onboarding — LLM layer-name refinement (opt-in)](tasks/091_llm-layer-refinement.md) | Phase 3 / M12 | todo | 084, 090 |

**Order (round-5 tickets):** ~~**092**~~ (done — an untracked file read as a non-existent symbol)
**→ ~~093~~** (done — 092's route shape generalised to every `try_instead`) **→ ~~095~~**
(done — names the denominator 082 made auditable) **→ ~~097~~** (done — protocol now scores
descriptions separately from names, and names the recall bucket) **→ ~~094~~** (done — `::class`
mentions are DYNAMIC REFERENCES) **→ ~~096~~** (done — cost, and last for
the same reason 061 and 080 were, but it is the round's behaviour finding, not just a number).
**Round 5 closed:** 092–097 all landed. **Round 4 closed:** 075–082 all landed; round 5 verified
7 of 8 fixed and 081 `NOT OBSERVED` (§A).

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
and recorded the actual layer assignment for each: **`symfony/demo` and `brick/math` are
architecturally sensible**; **`laravel/laravel` still collapses `app/**`**, because that skeleton's
`config/` holds 10 indexed files against `app/`'s 3 and the dominant subtree is elected by file
**count**. 104's AC3 fixture (a) hid it by authoring 8 classes under `app/**`. That narrow residual is
**105**, with a rejected-in-advance stop-list (R2.2) and an AC that forbids the question-begging
fixture shape. 104 stays **`blocked`** — its AC2 names the **anchor monorepo**, and three public repos
are stronger than fixtures but are not that repo; the maintainer holds that judgement. **086 shipped
against the measured evidence rather than waiting on it**, and its payload carries `method` so a
reader can see which grouping produced a split.

**M10 is complete** (083 · 084 · 085 · 103 · 104 · 086) — `architecture_overview` is the 15th tool on
the surface. **Next: 087** (`guided_tour`), with **105** as M10's open residual.

**Then:** Phase 3 onboarding (083 → 091; M10 → M11 → M12) or Phase 2 language breadth — both are
unblocked by Phase 1.5; breadth stays deferred per §19.

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
- **Reachability payload size at `detail_level="standard"`:** `reachable_from` / `find_orphans` are
  bounded by `impact_max_nodes` (default 500) rather than `max_results`, and a 500-row answer is
  ~160 KB of JSON against a §19 metric measured *in tokens*. Worth a lower default or a
  `minimal`-by-default shape; workaround in [`runbooks/onboarding-a-repo.md`](runbooks/onboarding-a-repo.md) §4.
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

**How 047–049 were measured.** One autonomous session, no per-task transcript: each row is the API
calls between the previous commit and that task's own commit. The approximation runs one way — work
interleaved across tasks lands in whichever segment it finished in (049 is the known case).

## Conventions
- Keep task `status` in this table **and** in each task file's frontmatter in sync.
- New task: next free `NNN`, add file + a row here. Record cross-task deps in `depends_on`.
- Landed narrative belongs in [PLAN §19](PLAN.md#19-project-context--decision-log) or
  [`LESSONS.md`](LESSONS.md), not here; a follow-up that gets ticketed leaves this file's
  [Follow-ups](#follow-ups-not-yet-ticketed) list.
