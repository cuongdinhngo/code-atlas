---
id: 040
slug: framework-indirection-data
title: Framework indirection as data (rules file outside adapters/)
phase: 1.5
milestone: Framework
status: todo
depends_on: [039, 030]
---

## Goal
Resolve the dispatch frameworks move out of static PHP — facades, container-by-string, array
callables, string-callback hooks — without teaching the adapter any framework. Encode the
indirections as **data** consumed by a core-side enrichment pass, so `find_callers` on a Laravel or
WordPress repo stops being quietly useless while adapters stay standard-only (§19 agent-first pivot;
PLAN §1 enrichment layer).

## Scope / Deliverables
- A rules/data file **outside `adapters/`** (so the R2.2 grep-gate stays clean) mapping known
  indirections to concrete edges, e.g.:
  - `Facade::method` → concrete class method (`Cache::get` → `Illuminate\Cache\Repository::get`)
  - `add_action('hook', 'fn')` / string-callback → CALLS edge
  - `[Controller::class, 'method']` array callables → CALLS edge
  - container id → class aliases
- A core enrichment pass that applies the rules to add edges, tagged with provenance and confidence
  tier (reuse task 030's alias/literal-indirection edge machinery).

## Constraints
- The mapping is **data, not code**, and lives outside `adapters/` (R2.2); the core applies generic
  rules with **no** `if framework == …` branches (R1.1).
- Added edges carry a distinguishable provenance and tier (HEURISTIC or rule-RESOLVED) — never
  silently promoted to plain RESOLVED (tier honesty, PLAN §8.2).
- Deterministic (R4); **empty/off by default** — no rules loaded ⇒ graph unchanged.

## Acceptance criteria
- With a facade rule loaded, `Cache::get` yields an edge to the concrete `Repository::get`; a
  string-callback hook yields a CALLS edge; an array callable yields a CALLS edge (planted fixtures).
- With no rules loaded, the graph is unchanged.
- Rule-added edges carry provenance/tier distinguishable from adapter-emitted edges.

## Constraints on sequence
Depends on task 039 (vendor stubs) so facade/container targets exist as nodes to link to, and on task
030 (alias & literal-indirection edges) whose contract vocabulary these edges reuse.

## References
`code_atlas/resolver.py`; task 030 (alias/literal-indirection edges, contract v2); task 039 (vendor
stubs). PLAN §1 (non-goal: framework-magic as planned optional enrichment), §8.2 (tiers). `R1.1`,
`R2.2`, `R4`. Feedback origin: [`FEEDBACK.md`](../FEEDBACK.md) rounds 1 & 2 ("framework indirection as
data, not code — a rules file outside adapters/").
