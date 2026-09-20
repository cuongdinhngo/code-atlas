---
id: 307
slug: human-authored-architecture-drift-budgets
title: "Architecture checks report facts, but no human-authored budget says which confirmed drift should block a change"
phase: 3
milestone: Change-Assurance
status: done
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

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

# 307 — Architecture drift budgets (working doc)
- **TIER:** full · **TRACK:** backend · **SCOPE:** S · **BASELINE:** green
- **Depends on:** 138, 139, 303 (merged #408)
- **reviewer:** off · **challenger:** on

## Phase 0
`PREMISE: 5 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 0 claim(s) surfaced | 0 by symbol | 0 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 2 unresolved surfaced | 0 want-decision asked | 2 how-decision resolved+cited | 0 ASSUMED | skip: no`
**INPUT KIND:** ticket.
| H1 | Policy file format | JSON object `version`+`policies[]` beside 138 rules files | `architecture_rules.py` load shape; epic settled decision 2 |
| H2 | Config knob | single `architecture_policy` repo-relative path + `--policy-gate` | ticket Scope §4; `architecture_rules` list pattern in config.py |
`CLARIFICATION: 2 raised | 2 self-resolved (cited) | 0 for human decision`

## Analysis / Design
`SECTIONS: 5 found (Goal · Scope / Deliverables · Constraints · Acceptance criteria · Out of scope) | 5 decomposed | ROWS: C=4 R=5 G=1 AC=6`
`RULE SECTIONS: 5 applicable — 5 by change-type | 0 by recalled handle — R2 (change-type) ✅ · R4.2 (change-type) ✅ · R5.2 (change-type) ✅ · R5.5 (change-type) ✅ · R7.2 (change-type) ✅`
`BASELINE: green`
`HANDLES: 0 recalled | 0 traced (command + result) | 0 does not apply (reason) | 0 unanswered`
`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`
**APPROVED CHANGE LIST:**
1. `code_atlas/architecture_policy.py` — load + pure evaluate
2. `code_atlas/config.py` — `architecture_policy` knob
3. `code_atlas/check.py` — attach outcomes; `--policy-gate`
4. `tests/test_architecture_policy.py` — proving suite
5. module-count pins in language-agnostic + sql confinement
6. working doc / BACKLOG / TOKEN_LEDGER bookkeeping
**PROVING TEST:** `.venv/bin/python -m pytest tests/test_architecture_policy.py -q`

## Phase 3–5
Execute: policy module + config + check wiring + tests (312 related passed incl. check_cli).
`REVIEWER: OFF` — waived by `--no-reviewer`.
`CHALLENGER: ON` — VERDICT CLEAN (agent 4c3edfd6). Gate 4: challenger CLEAN; reviewer waived.
`CLAIMS: 0 claim(s) from 0 lesson entr(ies) | T1=0 T2=0 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 0 recurring | 0 superseded (0 retired) | 0 promotion candidate(s)`
`RECURRING-T2: 0 type-2 claim(s) with seen ≥ 2 | 0 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 0 proposed | 0 human-ratified | destinations: docs/LESSONS.md | mango files written: 0`
`FALSIFY: 0 candidate(s) checked | 0 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`LEDGER TOTAL: unmeasured · top cost driver: main-loop`
