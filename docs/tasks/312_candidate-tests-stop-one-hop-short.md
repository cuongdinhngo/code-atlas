---
id: 312
slug: candidate-tests-stop-one-hop-short
title: "Every miss 309 measured was one hop away — the candidate walk stops at direct callers, so a façade hides the test"
phase: 1.5b
milestone: Change-Assurance
status: todo
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
