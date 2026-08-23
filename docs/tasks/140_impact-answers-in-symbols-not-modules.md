---
id: 140
slug: impact-answers-in-symbols-not-modules
title: '`impact` answers in symbols, and the decision is module-shaped — 500 rows at ~160 KB is the only answer today'
phase: 1.5b
milestone: Agent-fit
status: todo
depends_on: [017, 112, 114, 124]
---

## Why this exists

Two halves, one measured and one not.

**Measured, and already in BACKLOG's follow-up list:** `reachable_from` at `detail_level: standard` is
bounded by `impact_max_nodes` (500) and returns *~160 KB of JSON against a metric measured in tokens*.
[`runbooks/onboarding-a-repo.md`](../runbooks/onboarding-a-repo.md) §4 carries the workaround.

**Not measured — provenance is the architecture review of 2026-08-23:** the decision that consumes an
impact answer is module-shaped. *Which modules does this change reach, how many edges into each, and
which single edge do I read first?* Today that is a 500-row symbol list the reader aggregates by hand,
and the aggregation is the whole answer.

The rollup already exists in the tree and nothing joins it to impact:
[114](114_business-module-table.md) derives business modules from the path set and
[112](112_onboarding-dataset-contract.md) publishes the assignment. Deriving a *second* module notion
here would break PLAN §1's shared constraint, so the ticket is a join, not a new model.

## Scope

- An aggregation over the **existing** impact walk: module → edge count + one exemplar `file:line`,
  using 112's assignment verbatim. No new traversal, no second module definition.
- Honest bounds: a walk that hit `impact_max_nodes` says so and labels the rollup an **under-estimate**
  — 124's `walk_truncated` vocabulary, already in CONVENTION §6.
- Tier partition per [136](136_heuristic-share-has-no-owner.md): confirmed and heuristic edge counts are
  separate numbers, because a module that appears only through heuristic edges is a different fact.
- `minimal` = module names + counts; `standard` adds exemplars. `minimal` stays a subset (CONVENTION §6).
- A file the dataset does not assign goes to an explicit `unassigned` bucket — 113's lesson: never fold
  four populations into one number, and never invent a home for a file.

## Acceptance criteria

- **AC1** A subject whose impact spans ≥3 modules; the per-module counts sum to the symbol-level
  population, asserted (127's arithmetic guard).
- **AC2** A truncated walk is stated as truncated and the rollup is labelled an under-estimate.
- **AC3** The module names are byte-identical to the ones the map prints at the same commit — one
  assertion joining tool and map, so "same graph, no second pipeline" is tested.
- **AC4** A number, not a claim: the rollup at `standard` is measurably cheaper in tokens than the
  symbol answer it summarises, recorded in the benchmark file.
- **AC5** Deterministic ordering; identical index → identical rows (R4.2).
- **AC6** Red first (R6.5), and `unassigned` is exercised by a fixture that has one.

## Out of scope

- **Changing `impact`'s own payload.** 061 pruned it once; this is an additional answer, not a reshape.
- **A new or wider traversal.** If the walk bound is wrong, that is its own ticket with its own
  measurement.
- **Guessing a module for an unassigned file.**
