---
id: 136
slug: heuristic-share-has-no-owner
title: Two thirds of the graph's edges are HEURISTIC, the plan promises the fix, and no ticket ever carried it
phase: 1.5b
milestone: Coverage
status: done
depends_on: [025, 029, 011]
---

## Why this exists

`edge_health` HEURISTIC sat at **63.8 %** in round 4 and **63.81 %** in round 6 — unmoved to three
significant figures across two field rounds and ~20 shipped tasks. Nothing is wrong with the number
being reported; what is wrong is that **nobody owns it**, and the position on it is currently
contradictory:

- [PLAN §1](../PLAN.md#1-goals--non-goals) non-goals says no type inference *in the core*, "adapters
  may supply it where free — e.g. … **a planned PHP local type table** / opt-in PHPStan
  `semantic_types`". So the plan **promises** the mechanism.
- [PLAN §17](../PLAN.md#17-risks--mitigations) says the mitigation is *"name-match HEURISTIC; defer
  precise cases to an LSP"*. So the plan also says **don't build it**.
- [`FEEDBACK.md`](../FEEDBACK.md) round 4 put it second in its priority stack — *"freshness → type
  inference → finish 031 → …"* — describing it as recovering **most** HEURISTIC "from the spec alone
  (`new X`, typed properties, promoted params, hints, return types, `@var`)". Freshness shipped
  (035). Type inference never got a ticket.

`HEURISTIC` is not a wrong answer — R5.2 makes it an honest tier, and round 5 measured **8 of 8**
checked claims exact. But it is the tier a caller cannot act on without re-reading the file, so it is
the ceiling on what PILLAR 1 sells: *resolved* relationships. Two thirds is a large ceiling to carry
without a decision.

**This ticket's deliverable is the decision, backed by a measurement — not necessarily an
implementation.**

## Scope

1. **Measure it where it can be re-run** (R6.3). A committed reporter — the shape of
   `scripts/layer_report.py` — prints, for each pinned repo in `scripts/cross_repo_samples.json`,
   the tier mix **and the breakdown of *why* each HEURISTIC edge is one**: no receiver type, an
   untyped property, a `vendor/` target with no stub, a bare method name, a multi-candidate qname.
   Right now the 63.8 % is one aggregate from a retro and nothing says which population it is.
2. **Decide, in writing, against that breakdown.** Either:
   - the share is dominated by causes the language spec can settle (`new X`, typed properties,
     promoted params, parameter/return hints, `@var`) → §17's row is wrong, and the local type table
     §1 already promises becomes a real ticket with a target share; or
   - it is dominated by causes no adapter can settle without a semantic model (dynamic receivers,
     framework indirection, `vendor/` gaps) → §1's promise is wrong, and the number becomes a
     **stated non-goal with its floor**, so it stops reading as an unowned regression every round.
3. **Reconcile §1 and §17 either way**, and say which population the tracked figure names.

## Acceptance criteria

- **AC1** A committed, re-runnable reporter prints tier mix + HEURISTIC cause breakdown per pinned
  repo. Two runs on one tree byte-identical (R4.2).
- **AC2** The breakdown is recorded in `benchmarks/`, with the spec-settleable share separated from
  the semantic-model-only share and each number traceable to a cause.
- **AC3** PLAN §1 and §17 no longer disagree, and the surviving position names the number and
  whether it is a target or a floor.
- **AC4** If the verdict is *build it*, the follow-up ticket exists with a **measured target share**
  taken from AC2 — never a round figure chosen because it sounds like progress.
- **AC5** No adapter change in this ticket. It measures and decides; R2 is not at risk because
  nothing new is encoded.

## Out of scope

- **Implementing the type table.** That is AC4's follow-up, and doing it here would pick a target
  from whatever the first implementation happened to reach.
- **PHPStan `semantic_types`.** Already the opt-in half of §1's sentence and gated by the capability
  flag (R1.6); it cannot be the answer to a default-path share.
- **`vendor/` coverage.** [039](039_vendor-stub-index.md) already ships stub roots, off by default —
  if the breakdown says missing stubs are a large cause, that is a *configuration* finding for the
  runbook, not a new mechanism.

---

## Outcome

**Done — and the ticket's own premise was one of the things it corrected.** Numbers, the per-cause
table and the reconciliation are in
[`../benchmarks/136_heuristic-causes.md`](../benchmarks/136_heuristic-causes.md); not repeated here.

- **AC1** `scripts/edge_health_report.py` — clones and indexes each pin, prints the tier mix and the
  HEURISTIC breakdown by cause, and **fails** when a cause it cannot explain appears. Byte-identical
  across two consecutive runs (R4.2). The scanned kind set comes from the store's own kind census,
  so a new HEURISTIC-emitting kind surfaces as a cause instead of vanishing (R6.7).
- **AC2** Recorded in `benchmarks/`, spec-settleable separated from semantic-model-only, each number
  traceable to one adapter emission site.
- **AC3** PLAN §1 and §17 no longer disagree: §17 keeps the LSP defer for the **≤0.6 %** late-binding
  residual and states the measured cause and cap for the rest; §1's "planned" type table now names
  its owner, [137](137_php-local-type-table.md).
- **AC4** 137 exists with **measured** targets per pin (`brick_math` 1 659 → ≤ 200; `symfony_demo`
  568 → ≤ 450; `laravel_app` deliberately no HEURISTIC target).
- **AC5** No adapter change. R2 is untouched — nothing new is encoded.

**Two findings the ticket did not ask for, and one of them contradicts it.**

1. **The tracked 63.8 % has no committed population.** It is a field-round measurement of the
   maintainer's private anchor repo. The pins measure **19.2 % / 36.1 % / 36.3 %** — so "two thirds
   of the graph's edges" is true of one repository, not of code-atlas. The ticket's own title claimed
   otherwise and the benchmark corrects it. This is why the number "never moved": nothing that ships
   is measured against it.
2. **The cause is not the cap, and only the cause had been argued.** An edge is HEURISTIC because the
   resolver's lookup **missed**; inferring the receiver's type rewrites the target but does not
   create the node it needs. So the movable share is *settleable **and** already linked*: **0 %** on
   `laravel/laravel` (every HEURISTIC edge points into unindexed `vendor/`), **22.5 %** on
   `symfony/demo`, **92.5 %** on `brick/math`. The share needs **two** mechanisms — local types and
   `vendor/` stubs ([039](039_vendor-stub-index.md), off by default) — and only one was ever
   promised. Recorded as the reason a single global target would have been meaningless.

**Red run recorded (R6.5).** The drift guard is asserted failing, not assumed: a HEURISTIC
`REFERENCES` edge — a kind the taxonomy does not explain — yields cause `other_references` and
`check()` returns *"unexplained cause(s) ['other_references'] — a new emission site is unaccounted
for"* (`tests/test_edge_health_report.py`). Without that, a future adapter change would fold a new
emission site into whichever bucket happened to match and the decision on this page would rot
silently.

**Delta-green:** `pytest` **1818 passed, 0 failed** on Linux with PHP 8.3.6 — 1806 before this
ticket, +10 in `tests/test_edge_health_report.py` and +2 from the bookkeeping suite
parametrising over the new ticket files; `scripts/gate.sh` **GATE GREEN — 12 passed · 0 failed · 0
skipped**. The reporter itself needs network + php and is **not** in per-PR CI, like
`scripts/layer_report.py`.
