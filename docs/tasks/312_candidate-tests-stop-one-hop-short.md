---
id: 312
slug: candidate-tests-stop-one-hop-short
title: "Every miss 309 measured was one hop away — the candidate walk stops at direct callers, so a façade hides the test"
phase: 1.5b
milestone: Change-Assurance
status: done
depends_on: [308, 309]
---

## Parent epic

[304 — Change Assurance](304_change-assurance-makes-every-important-change-carry-evidence.md).

## Why this exists

[309](309_test-impact-recall-before-selective-runs.md) measured **recall 0.824** over 15 upstream
commits and found that **all three misses share one mechanism**: the test reaches the changed symbol
at **inbound depth 2**, through a façade or a package entry point, and
[308](308_changed-code-to-candidate-test-files-report.md) walks direct inbound edges only.
`test/base-url.ts` imports `source/index.ts` rather than `source/core/Ky.ts`; `BigDecimalTest.php`
reaches `BigInteger::nthRoot()` through `BigDecimal`. Nothing truncated, nothing stale, nothing
misclassified — the bound is traversal depth and nothing else
([benchmark](../benchmarks/309_test-impact-recall.md)).

309 could not fix it: improving the metric is out of its own scope, and a ticket that moves the
number and the bar together proves nothing.

## Goal

Widen the candidate walk past direct callers so a test one hop further out is a candidate, then
re-run 309's committed reporter and read the verdict off the bar that is **already registered**.

## Scope / Deliverables

1. Walk inbound relations to a bounded depth greater than 1, carrying each candidate's hop distance
   alongside the edge kind, confidence tier and test-role source 308 already emits.
2. Keep 308's ranking contract: direct `RESOLVED` callers outrank every indirect candidate, and an
   indirect one can never read as direct resolved coverage.
3. Make the depth bound explicit and emit an honest unmeasured reason when a walk hits it.
4. Record the candidate-count growth per scenario beside the recall change, so the cost of the
   recall gained is visible rather than implied.
5. Re-run `scripts/test_impact_recall.py` **unmodified** over the **unmodified**
   `scripts/test_impact_corpus.json`, and record per-scenario and aggregate recall with provenance.

## Constraints

- Still report-only. No selective execution, skip list, runner argument, failing gate or replacement
  of the configured test command.
- **The bar is not reopened.** It was ratified blind on 2026-09-20, before any of this work existed,
  and is recorded in 309's benchmark: promote at recall ≥ 0.90, retain report-only at ≥ 0.60, corpus
  floor 12 scenarios / 3 repositories / 2 languages. This ticket reads it; it does not author one.
- **The corpus is not edited to help the metric** (R6.3). A scenario may be added only for a reason
  that would have applied before this measurement, and the addition is argued in the PR.
- No framework-specific test directory or naming list enters the core (R2); no language branch (R1.1).
- Identical graph and change set produce byte-identical ordering (R4.2).

## Acceptance criteria

- **AC1** A fixture where a test reaches a changed symbol through exactly one intermediate module
  lists that test, labelled with its hop distance, and ranked below every direct caller.
- **AC2** A test reaching the change at a depth beyond the bound is **not** listed, and the run emits
  the unmeasured reason for it — exhibited by a test that reaches the bound (R6.8).
- **AC3** Indirect candidates stay distinguishable from direct resolved coverage in every rendering:
  text, JSON and the section embedded in the 303 check result (R6.9).
- **AC4** 309's reporter re-runs unmodified over the unmodified corpus; per-scenario and aggregate
  recall are recorded with server/index provenance.
- **AC5** Candidate-count growth is recorded per scenario against the recall change; a recall gain
  bought with a large candidate-set increase is reported as that trade, not as an improvement.
- **AC6** The verdict follows the **pre-registered** bar even if recall still blocks promotion, and
  the benchmark names 0.824 as the figure it is compared against.
- **AC7** No code path, CLI flag or documentation suggests skipping unlisted tests; 308's guard
  covers the new hop-distance labels.

## Out of scope

- Implementing selective test execution or choosing runner arguments — that remains a separately
  proposed ticket, and only if AC6 clears the promotion line.
- Editing the corpus, the labels or the bar to move the number.
- Any adapter change. If a miss turns out to need new edges from a language adapter, that is a
  separate ticket and a recorded cause, not work done here.

## References

[308](308_changed-code-to-candidate-test-files-report.md),
[309](309_test-impact-recall-before-selective-runs.md),
[`docs/benchmarks/309_test-impact-recall.md`](../benchmarks/309_test-impact-recall.md),
`code_atlas/candidate_tests.py`, `scripts/test_impact_recall.py`,
ENGINEERING_RULES R2, R4.2, R6.3, R6.8 and R6.9.
<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 312 — Candidate walk one hop further (working doc)
- **TIER:** full · **TRACK:** backend · **SCOPE:** M · **BASELINE:** green
- **Depends on:** 308 (done), 309 (done, recall 0.824 / report_only_retained).
- **reviewer:** off · **challenger:** on
- **Branch:** `feat/312-widen-candidate-walk-one-hop` (fresh; #414 was docs-only MERGED on the slug branch)

## Session status
- **Current phase:** finalise

## Phase 0
`PREMISE: 6 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 4 claim(s) surfaced | 0 by symbol | 4 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 0 unresolved surfaced | 0 want-decision asked | 0 how-decision resolved+cited | 0 ASSUMED | skip: yes`
**INPUT KIND:** ticket.
refine skipped: 0 unresolved product-decisions — Goal already says "one hop further"; bar and corpus are locked by Constraints; ranking contract is stated in Scope.

| # | Claim (id) | Type | Matched by | Relevant? |
|---|------------|------|------------|-----------|
| 1 | `ac-failure-mode-needs-the-right-guard` → R6.8 | 2 | handle | yes — AC2 bound |
| 2 | `guard-asserts-rendered-not-shipped-bytes` → R6.9 | 2 | handle | yes — AC3 renderers |
| 3 | `assert-the-consumer-not-the-field` → R6.9 | 2 | handle | yes — AC3 |
| 4 | `bound-the-recursion-or-make-it-iterative` | 2 | handle | yes — depth walk |

`CLARIFICATION: 0 raised | 0 self-resolved (cited) | 0 for human decision`

## Phase 1 — Analysis
`SECTIONS: 5 found (Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 5 decomposed | ROWS: C=5 R=5 G=1 AC=7`
`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — R1.1 (change-type) ✅ · R2 (change-type) ✅ · R4.2 (change-type) ✅ · R6.3 (change-type) ✅ · R6.8 (change-type) ✅ · R6.9 (change-type) ✅ · R7.2 (change-type) ✅`
`BASELINE: green`

Gap: `build_candidate_test_report` walks only direct inbound (`candidate_tests.py:131-154`); hop distance is absent from `CandidateEvidence`; 309's three misses sit at inbound depth 2.

| ID | Source | Verbatim (abbrev) | Interpretation | Ph1 evidence | Ph2 | Ph3/4 | Status |
|----|--------|-------------------|----------------|--------------|-----|-------|--------|
| C1 | Constraint | report-only | no selective exec | ticket | | | ✅ |
| C2 | Constraint | bar not reopened | read 309 BAR | benchmark | | | ✅ |
| C3 | Constraint | corpus not edited to help | R6.3 | ticket | | | ✅ |
| C4 | Constraint | no framework list / no language branch | R2 / R1.1 | ticket | | | ✅ |
| C5 | Constraint | identical → identical | R4.2 | ticket | | | ✅ |
| R1 | Scope | walk inbound to bounded depth > 1 + hop | BFS depth 2 | code | | | ✅ |
| R2 | Scope | direct RESOLVED outranks indirect | hop in rank key | code | | | ✅ |
| R3 | Scope | explicit bound + unmeasured on hit | depth_bound | code | | | ✅ |
| R4 | Scope | record candidate-count growth | benchmark | | | ✅ |
| R5 | Scope | re-run 309 reporter unmodified | scripts untouched | | | ✅ |
| G1 | Goal | one-hop-further tests are candidates | depth=2 | Goal | | | ✅ |
| AC1 | AC | fixture hop=2 listed below directs | proving test | | | ✅ |
| AC2 | AC | beyond bound not listed + unmeasured | R6.8 fixture | | | ✅ |
| AC3 | AC | hop distinguishable in text/JSON/303 | R6.9 | | | ✅ |
| AC4 | AC | reporter re-run + provenance | real corpus | | | ✅ |
| AC5 | AC | candidate-count growth recorded | benchmark | | | ✅ |
| AC6 | AC | verdict from pre-registered bar; name 0.824 | benchmark | | | ✅ |
| AC7 | AC | no skip language; 308 guard covers hop labels | assert_no_selective_language | | | ✅ |

## AC validation
| AC ID | Ticket states | Independently computed | Match? | Falsifiable? |
|-------|---------------|------------------------|--------|--------------|
| AC1 | hop=2 listed, ranked below direct | hop_distance field + rank | Y | measurable |
| AC2 | beyond bound absent + unmeasured | depth_bound reason + fixture | Y | measurable |
| AC3 | distinguishable in 3 renderers | hop in text/JSON/check | Y | greppable |
| AC4 | unmodified reporter+corpus | scripts hash / no diff | Y | real-corpus |
| AC5 | growth per scenario | benchmark table | Y | real-corpus |
| AC6 | bar + 0.824 baseline named | verdict_for(BAR) | Y | real-corpus |
| AC7 | no skip suggestion | banned-phrase guard | Y | greppable |

## Phase 2 — Design
**Approach:** BFS inbound walk with `DEFAULT_MAX_DEPTH=2` (Goal "one hop further"; 309 misses at depth 2). Production intermediates expand while `hop < max_depth`; tests with `hop_distance <= max_depth` are candidates; observing an edge that would land past the bound sets `unmeasured: depth_bound`. Rank key leads with `hop_distance` so every direct outranks every indirect; RESOLVED/kind ranks unchanged inside a hop. Emit `hop_distance` on `CandidateEvidence` and in text / JSON / 303 `CANDIDATE_TEST` lines.

**Rejected alternatives:** (a) depth=3 matching diagnostic `--max-depth` — speculative beyond measured misses; (b) new MCP tool — out of 308/312 scope; (c) editing corpus — forbidden by C3/R6.3.

`HANDLES: 4 recalled | 4 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
- ac-failure-mode → AC2 fixture exhibits depth_bound
- guard-asserts-rendered / assert-the-consumer → assert hop in render_text + JSON + check.render_text
- bound-the-recursion → iterative BFS with explicit max_depth

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 3 input-shape-dependent AC(s) | 3 proven on a real corpus`

**APPROVED CHANGE LIST:**
1. `code_atlas/candidate_tests.py` — multi-hop walk, hop_distance, depth_bound, ranking
2. `code_atlas/check.py` — render hop on CANDIDATE_TEST lines
3. `tests/test_candidate_tests.py` — AC1/AC2/AC3/AC7 proving fixtures
4. `docs/benchmarks/309_test-impact-recall.md` — re-run results, growth, verdict vs 0.824 (scripts untouched)
5. working doc / BACKLOG / TOKEN_LEDGER

**PROVING TEST:** `.venv/bin/python -m pytest tests/test_candidate_tests.py -q`

**Gate 2 status:** cleared (autorun)

## Phase 3 — Execute
Implemented approved list: multi-hop BFS (`DEFAULT_MAX_DEPTH=2`), `hop_distance` on evidence,
`depth_bound` unmeasured, check render hop=, proving fixtures AC1/AC2/AC3, 309 reporter re-run
unmodified → recall_micro **0.9412** / `eligible_for_opt_in_selective_run_ticket` vs baseline 0.824.
Scripts `test_impact_recall.py` / `test_impact_corpus.json` untouched.
`PROVING TEST:` `.venv/bin/python -m pytest tests/test_candidate_tests.py -q` → 14 passed.
`tests/test_impact_recall.py` → green with updated benchmark block.

## Phase 4 — Review
`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — round1 NOT CLEAN (AC5 per-scenario growth); round2 CLEAN (agent 23067e07). Gate 4: challenger CLEAN; reviewer waived.

## Phase 5 — Finalise
`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop`

## Post-PR maintainer review (#415)
Three findings, all fixed on the branch before merge:
1. Two unreachable bound branches in `_walk_inbound` — a guard that cannot fail is not a guard (R6.5).
   Bound now decided at the single enqueue site, pinned by a `max_depth=1` parity test and a
   `max_depth=0` rejection test. Reporter re-run: aggregate byte-identical, so the verdict is unmoved.
2. The benchmark stated the number without its own `unmeasured` list — all 15 scenarios report
   `depth_bound` and 3 report `truncated_page` (309's depth-1 run truncated on none). Now disclosed
   above the verdict.
3. Provenance named a commit the figures did not come from, and the `flask@89992954ec71` residual was
   left unexplained. Both corrected; the residual is the diagnostic's file-level BFS reading shallower
   than the candidate walk's symbol-level one.
