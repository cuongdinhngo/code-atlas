---
id: 308
slug: changed-code-to-candidate-test-files-report
title: "The graph knows which test callers reach changed symbols, but exposes no honest candidate-test report"
phase: 1.5b
milestone: Change-Assurance
status: todo
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
