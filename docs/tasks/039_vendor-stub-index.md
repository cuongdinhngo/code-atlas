---
id: 039
slug: vendor-stub-index
title: Vendor stub index (declarations only)
phase: 1.5
milestone: Framework
status: todo
depends_on: [009, 011]
---

## Goal
Stop framework and library base classes from dangling. `vendor/` is ignored by default
(`code_atlas/ignore.py:18`), so `class Foo extends Illuminate\…\Model` resolves to nothing and
framework apps are half-blind. Indexing **declarations only** from dependencies — no bodies, no call
edges — is cheap and makes `extends`/`implements`/type references into vendor RESOLVED. This is the
single biggest resolution gap and the cheapest to close (§19 agent-first pivot; PLAN §1 enrichment
layer).

## Scope / Deliverables
- An opt-in pass that ingests **declarations** from `vendor/` (or a configured dependency root):
  class/interface/trait/enum/method/property/constant signatures + `extends`/`implements`, with
  **no** function bodies and **no** call/NEW edges.
- A stub node marker (or a declaration-only flag) so stubs are distinguishable from first-class
  indexed nodes.
- Wire resolution so EXTENDS/IMPLEMENTS/type references into stubs become RESOLVED.

## Constraints
- **Standard over sample (R2):** this is a generic "index dependency declarations" capability, not
  framework-specific — no repo/framework names in the adapter.
- No language branches in the core (R1.1); adapter parses, store persists (R1.4); deterministic (R4).
- **Off by default** to keep normal builds cheap; document the cost when enabled. Bodies are never
  indexed (that is what keeps it cheap and avoids polluting the call graph with vendor internals).

## Acceptance criteria
- A repo whose class extends a vendor base class: after stub indexing, the EXTENDS edge is RESOLVED to
  the vendor declaration (asserted on a planted vendor tree).
- Vendor method bodies produce no call/NEW edges (stubs are declarations only).
- With stubs off (default), the graph is byte-identical to today's build for the same repo.

## References
`code_atlas/ignore.py:17-24` (built-in `vendor/` ignore); `code_atlas/indexer.py` (collect/walk);
`code_atlas/resolver.py` (edge linking); adapters/php declaration emission. PLAN §1 (optional
enrichment layer), §4 (contract). `R1.1`, `R1.4`, `R2`, `R4`. Feedback origin:
[`FEEDBACK.md`](../FEEDBACK.md) rounds 1 & 2 ("vendor stub index — the biggest single fix, and the
cheapest").
