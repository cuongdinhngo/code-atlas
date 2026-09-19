---
id: 307
slug: human-authored-architecture-drift-budgets
title: "Architecture checks report facts, but no human-authored budget says which confirmed drift should block a change"
phase: 3
milestone: Change-Assurance
status: todo
depends_on: [138, 139, 303]
---

## Parent epic

[304 — Change Assurance](304_change-assurance-makes-every-important-change-carry-evidence.md).

## Goal

Let a project declare review policy over facts already produced by architecture-rule checks and
architecture diffs, while keeping default Change Assurance informational.

## Scope / Deliverables

1. A generic, committed policy file whose rules can bound confirmed dependency violations and
   measured drift categories such as new layer pairs, module additions or reachability movement.
2. A pure evaluator over 138/139 result objects. It does not query the graph or duplicate their
   matching/diff logic.
3. Per-policy outcomes: passed, confirmed breach, candidate-only, not measured or invalid policy.
4. 303 includes the outcomes. Report mode stays green; an explicit policy-gate option fails only
   confirmed breaches that the project marked blocking.
5. Candidate, truncated, stale or incompatible evidence can never satisfy a policy or fail as a
   confirmed breach; it yields an honest non-authoritative outcome.

## Constraints

- Projects choose budgets and blocking status. The core ships vocabulary and validation, never
  project thresholds or framework rules.
- A policy cannot weaken operational failures or turn a missing baseline into “within budget”.
- Identical policy plus evidence yields identical ordered outcomes.
- The policy file is data, not executable code, and performs no network/provider action.

## Acceptance criteria

- A red-first fixture introduces a confirmed forbidden dependency and exceeds a blocking budget;
  report mode renders it and explicit policy-gate mode fails.
- The same relation at `HEURISTIC` is candidate-only and never fails the gate.
- Missing source matches, missing snapshot, truncated walk and schema mismatch each produce distinct
  non-authoritative outcomes.
- A zero budget, a numeric budget and a non-blocking observation policy are all validated and tested.
- Direct 138/139 outputs and the evaluator's cited evidence agree row-for-row.
- No repository, language or framework name appears in the evaluator or default vocabulary.

## Out of scope

- Inventing architecture rules, recommending thresholds or fixing violations.
- Replacing source-text grep gates; this policy operates on graph and snapshot facts only.

## References

[138](138_architecture-rules-are-never-asked-of-the-graph.md),
[139](139_map-is-a-snapshot-so-nothing-shows-architectural-drift.md),
[303](303_pre-pr-evidence-is-scattered-across-tools.md),
`code_atlas/architecture_rules.py`, `code_atlas/onboarding/architecture_diff.py`,
ENGINEERING_RULES R2, R4.2, R5.2, R5.3, R5.5 and R5.6.
