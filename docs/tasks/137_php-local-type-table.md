---
id: 137
slug: php-local-type-table
title: A PHP local type table — the cause of ≥99% of the HEURISTIC share, with a measured target per pin
phase: 1.5b
milestone: Coverage
status: todo
depends_on: [136, 039]
---

## Why this exists

[136](136_heuristic-share-has-no-owner.md) measured the HEURISTIC share by cause on all three pinned
repos and found local type information behind **≥99 %** of it, with late binding — the only cause an
LSP defer answers — at **≤0.6 %**. PLAN §1 has promised "a planned PHP local type table" since round
1 of the field feedback, where it was the **second** item in the priority stack; the first (read-through
freshness) shipped as 035 and this never got a ticket.

Numbers, per-cause table and the reconciliation are in
[`../benchmarks/136_heuristic-causes.md`](../benchmarks/136_heuristic-causes.md). Not repeated here.

**The mechanism is entirely inside the language spec**, which is why it does not threaten R2: `new X`,
typed properties, constructor-promoted params, parameter and return hints, `@var`. Nothing about a
framework, a repo or a name is encoded.

## Scope

1. A per-function local type table in the PHP adapter: bind a variable to a class-like FQN from the
   sources above, then emit `$obj->m()` as `\FQN::m` at the tier the evidence earns.
2. **The cheapest half first, and it is not type inference at all:** 37 % of `brick/math`'s share is
   `inherited_or_trait_receiver` — the method is declared by an ancestor or trait the graph *already
   holds*. Settling those needs a hierarchy walk, not a type table, and it should be a separate
   commit so its share is separately measurable.
3. Re-run `scripts/edge_health_report.py` and record the move against 136's baseline.

## Acceptance criteria

- **AC1** `brick_math`: **1 659 → ≤ 200** HEURISTIC edges (92.5 % linkable + the 0.6 % residual).
- **AC2** `symfony_demo`: **568 → ≤ 450** (22.5 % linkable). No target for `laravel_app` — its share
  is capped by `vendor/` coverage at 0 %; assert instead that its claims become **qualified names**
  rather than bare method names, which is what tells an operator what to stub.
- **AC3** A tier is never promoted past its evidence: an inferred receiver makes the target *precise*,
  and only a lookup **hit** may leave HEURISTIC (the rule the resolver already enforces — R5.2).
- **AC4** No repo, framework or vendor name in the adapter (R2, CI-gated). Every rule cites the PHP
  spec or a PSR.
- **AC5** Red first (R6.5): a fixture whose `$obj->m()` is bare today and resolved after, asserted at
  the store level so the tier and the target are both pinned.
- **AC6** `contract_version` checked, not assumed — 129's precedent: the trigger is whether an index
  built before and updated after would mix eras.

## Out of scope

- **`vendor/` stub coverage.** [039](039_vendor-stub-index.md) already ships it, off by default. This
  ticket must not turn it on to flatter its own numbers — the two effects have to stay separable.
- **PHPStan `semantic_types`.** The opt-in half of §1's sentence, gated by the capability flag (R1.6);
  it cannot be the answer to a default-path share.
- **Late binding** (`static::`, `'C::m'`, string method names). ≤0.6 %, and PLAN §17's LSP defer is
  the right answer for it.
