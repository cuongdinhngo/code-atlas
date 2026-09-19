---
id: 310
slug: four-week-change-assurance-adoption-gate
title: "Capabilities do not make a must-have product — measure whether teams repeatedly use Change Assurance and miss it when removed"
phase: 3
milestone: Change-Assurance
status: todo
depends_on: [260, 300, 305, 306, 307, 309]
---

## Parent epic

[304 — Change Assurance](304_change-assurance-makes-every-important-change-carry-evidence.md).

## Goal

Decide whether Change Assurance changed real review behaviour. The answer may be “useful, not
must-have”; shipping capabilities does not pre-decide the verdict.

## Pre-registered success bar

For teams using AI on large repositories, during one four-week field window:

- at least **80% of code-changing PRs** run Change Assurance; and
- at least **50% of reviews** use at least one emitted evidence item.

Both must pass. A denominator, exclusion or evidence-use classification is defined before collection.

## Scope / Deliverables

1. A field protocol defining cohort, repository-size floor, code-changing PR, assurance run,
   evidence-used-in-review, exclusions and privacy boundaries.
2. Local-only counting or a committed tally template; no telemetry or network collection.
3. Per-week and aggregate denominators/numerators with server build, config build and repository
   revision provenance.
4. Short interviews at the end of the window: which decision changed, which evidence was ignored,
   and what users did when assurance was deliberately unavailable for a controlled comparison.
5. Apply one predeclared verdict: must-have observed, useful but optional, adoption failure, or
   measurement invalid.

## Constraints

- No repository names, source, qnames or paths enter the committed result; counts and question
  shapes only.
- A tool invocation is not automatically evidence use. The review artifact must contain or cite an
  emitted claim, finding or bundle section.
- A failed/invalid assurance run remains in the run-rate denominator and is classified; deleting it
  would reward unreliability.
- The protocol measures workflow behaviour, not server determinism, and does not coach sessions to
  call the tool.

## Acceptance criteria

- Cohort and every numerator/denominator rule are frozen before week one.
- Four weekly records reconcile exactly to the aggregate and name host/client/server/config builds.
- The verify-use rate and review-evidence rate are both reported against their separate denominators.
- At least one removal-cost comparison or interview tests whether users notice the capability's
  absence rather than merely approving it in principle.
- The final verdict mechanically follows the two thresholds and validity rules.
- Negative or invalid results update the epic status honestly; they do not trigger wording changes
  that redefine success after measurement.

## Out of scope

- Product changes during the counted window, paid telemetry, provider analytics or a claim that one
  team generalises to every repository.

## References

[260](260_the-fit-number-cannot-be-observed-only-benchmarked.md),
[300](300_the-index-is-registered-permitted-and-never-chosen.md),
[304](304_change-assurance-makes-every-important-change-carry-evidence.md),
`docs/runbooks/field-retro.md`, `docs/runbooks/tool-recognition-probe.md`,
ENGINEERING_RULES R4, R5.5, R5.6 and R6.3.
