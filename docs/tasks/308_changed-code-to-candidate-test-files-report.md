---
id: 308
slug: changed-code-to-candidate-test-files-report
title: "The graph knows which test callers reach changed symbols, but exposes no honest candidate-test report"
phase: 1.5b
milestone: Change-Assurance
status: done
depends_on: [262, 273, 303]
---

## Parent epic

[304 — Change Assurance](304_change-assurance-makes-every-important-change-carry-evidence.md).

## Goal

Report test files connected to changed production symbols by graph evidence, without implying that
unlisted tests are safe to skip.

## Scope / Deliverables

1. Use 303's changed paths and the existing qname/file lookups to seed production symbols.
2. Compose inbound callers/references and imported-by relationships whose source nodes are classified
   as tests. Preserve edge kind, confidence tier, source qname/file and test-role source.
3. Emit deterministic candidate test paths in text and JSON, ranked by strongest direct evidence.
4. Carry coverage, staleness, unresolved sites, truncation and “no runner mapping” as explicit
   unmeasured reasons.
5. Add the report to Change Assurance as `mode: report_only`, with a mandatory statement that the
   project's normal full suite remains authoritative.

## Constraints

- No selective test execution, skip list, pytest/PHPUnit argv, failing gate or replacement of the
  configured test command.
- A path convention is a classification source, not proof that a runner will collect the file.
- Direct `RESOLVED` callers rank above imports and HEURISTIC evidence; lower evidence remains
  labelled.
- No framework-specific test directory or naming list enters the core.

## Acceptance criteria

- A fixture with a planted test caller to a changed production symbol lists that test path with its
  exact edge evidence.
- A production caller is not mislabeled as a test; adapter/path-convention role sources remain
  distinguishable.
- Import-only and HEURISTIC candidates are labelled and cannot read as direct resolved coverage.
- Forced paging, stale index, unindexed change and unlinked same-name sites each emit an unmeasured
  reason.
- Every output says candidates only and run the full suite; a guard fails if skip/gate/selected-test
  language appears.
- Identical graph and change set produce byte-identical ordering.

## Out of scope

- Measuring recall or precision—that is 309.
- Mapping files to test-runner selectors, reducing CI work or claiming complete coverage.
- A new MCP tool; this is a Change Assurance report section.

## References

[262](262_the-contract-marks-test-code-and-no-tool-reads-it.md), [273](273_the-partition-counts-edges-and-the-total-counts-callers.md),
[303](303_pre-pr-evidence-is-scattered-across-tools.md),
`code_atlas/symbol_role.py`, `code_atlas/tools/find_callers.py`,
`code_atlas/store.py` (`qnames_in_files`, `file_paths_targeting`, `inbound_test_rows`),
ENGINEERING_RULES R2, R4.2, R5.2, R5.5, R5.6 and R6.9.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 308 — Candidate test files report (working doc)
- **TIER:** full · **TRACK:** backend · **SCOPE:** S · **BASELINE:** green
- **Depends on:** 262, 273, 303 (merged). Branched from main; independent of open #411 (307).
- **reviewer:** off · **challenger:** on

## Phase 0
`PREMISE: 4 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 1 unresolved surfaced | 0 want-decision asked | 1 how-decision resolved+cited | 0 ASSUMED | skip: no`
**INPUT KIND:** ticket.
| H1 | Surface | `candidate_tests` section on 303 check result; no MCP tool | ticket Out of scope; 306 brief pattern |
`CLARIFICATION: 1 raised | 1 self-resolved (cited) | 0 for human decision`

## Analysis / Design
`SECTIONS: 5 found (Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 5 decomposed | ROWS: C=4 R=5 G=1 AC=6`
`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — R2 (change-type) ✅ · R4.2 (change-type) ✅ · R5.5 (change-type) ✅ · R6.9 (change-type) ✅ · R7.2 (change-type) ✅`
`BASELINE: green`
`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
**APPROVED CHANGE LIST:**
1. `code_atlas/candidate_tests.py`
2. `code_atlas/check.py` attach + render
3. `tests/test_candidate_tests.py`
4. module-count pins
5. working doc / BACKLOG / TOKEN_LEDGER
**PROVING TEST:** `.venv/bin/python -m pytest tests/test_candidate_tests.py -q`

## Phase 3–5
Execute: candidate_tests module + check section + proving tests.
`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — VERDICT CLEAN round2 (agent d8efc148). Gate 4: challenger CLEAN; reviewer waived.
`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop`
