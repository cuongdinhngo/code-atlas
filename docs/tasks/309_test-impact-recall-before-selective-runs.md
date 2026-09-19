---
id: 309
slug: test-impact-recall-before-selective-runs
title: "No selective test mode may exist until candidate-test recall is measured on real changes"
phase: 1.5b
milestone: Change-Assurance
status: todo
depends_on: [142, 308]
---

## Parent epic

[304 — Change Assurance](304_change-assurance-makes-every-important-change-carry-evidence.md).

## Goal

Measure whether 308 finds the tests that actually exercise real changes. This ticket produces a
promotion verdict; it does not add selective execution.

## Scope / Deliverables

1. During refinement, the maintainer ratifies the qualifying public corpus, labelled-change count
   and minimum recall bar. These acceptance values are intentionally not authored by this scaffold.
2. Commit reproducible change scenarios with hand-verified relevant test files and revision
   provenance. Authored toy fixtures do not satisfy the real-corpus gate.
3. Run 308's unchanged reporter over every scenario and compute recall; compute precision only where
   the labels are exhaustive.
4. Split misses by cause: unmodelled dynamic relationship, missing test-role classification,
   traversal/page bound, stale/incomplete index, runner-only discovery or reporter defect.
5. Record one verdict: insufficient evidence, report-only retained, or eligible for a separately
   proposed opt-in selective-run ticket.

## Constraints

- The default and this ticket's implementation always run the full configured suite.
- A threshold is pre-registered before measurements; negative measurement is a valid result.
- Private repository identities and source do not enter the repo; a private field arm may contribute
  aggregate corroboration but cannot replace the public reproducible corpus.
- No result from an authored fixture can establish recall for real changes (R6.3).

## Acceptance criteria

- The ticket's refined acceptance bar is explicit, human-ratified and committed before the first
  counted run.
- Every scenario names base/head, changed paths, expected test files, collection method and
  independent ground truth.
- The committed reporter reproduces per-scenario and aggregate recall with server/index provenance.
- Every miss belongs to one named cause or `unclassified`; the cause totals reconcile with misses.
- The verdict follows the pre-registered bar even if it blocks selective execution.
- No code path, CLI flag or documentation suggests skipping unlisted tests.

## Out of scope

- Implementing selective test execution or choosing runner arguments.
- Improving graph coverage to make the metric pass; those findings become separate tickets.

## References

[142](142_supervision-question-class-has-no-baseline.md),
[308](308_changed-code-to-candidate-test-files-report.md),
`scripts/cross_repo_samples.json`, `scripts/edge_health_report.py`,
ENGINEERING_RULES R6.3, R6.5 and R6.8.
