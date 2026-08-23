# 136 — what the HEURISTIC share is actually made of

**Status:** run, three pinned public repos, 2026-08-23 (Linux, PHP 8.3.6).
**Ticket:** [`../tasks/136_heuristic-share-has-no-owner.md`](../tasks/136_heuristic-share-has-no-owner.md).
**Verdict:** **PLAN §17 was wrong about the cause and PLAN §1 was right about the mechanism — but
both missed the cap.** Local type information is the cause of **≥99 %** of the HEURISTIC share on
every pin. What a type table can actually *promote* is bounded by `vendor/` coverage, and on the
framework skeleton that bound is **zero**.

```bash
python scripts/edge_health_report.py          # clones the pins, indexes, prints the table below
```

Byte-identical across two consecutive runs (R4.2).

## The tracked 63.8 % names one repo, and it is not any of these

| repo | all edges | HEURISTIC | share |
|---|---|---|---|
| `laravel/laravel` @ `ff031db` | 452 | 87 | **19.2 %** |
| `symfony/demo` @ `03fe256` | 1 572 | 568 | **36.1 %** |
| `brick/math` @ `b61d8e6` | 4 573 | 1 659 | **36.3 %** |

The **63.8 % / 63.81 %** carried in BACKLOG and in this ticket is from a field round on the
maintainer's **anchor repo** — a large private framework app. It is not reproducible on any committed
pin, and the spread here (19 %–36 %) is wide enough that "two thirds of the graph" is a statement
about one repository, not about code-atlas. **That is the first correction this ticket owes: the
figure had no stated population, and now it has one.**

## Cause breakdown — each cause is one adapter emission site

| repo | `unknown_receiver` | `inherited_or_trait` | `late_bound_or_string` | cause is local type info | of those, target **indexed** |
|---|---|---|---|---|---|
| `laravel_app` | 87 (100 %) | — | — | **100 %** | **0 / 87 (0 %)** |
| `symfony_demo` | 563 (99.1 %) | 5 (0.9 %) | — | **100 %** | **128 / 568 (22.5 %)** |
| `brick_math` | 1 035 (62.4 %) | 614 (37.0 %) | 10 (0.6 %) | **99.4 %** | **1 535 / 1 659 (92.5 %)** |

- **`unknown_receiver`** — `$obj->m()` with no type for `$obj`. Settled by `new X`, a typed property,
  a promoted param, a param/return hint or `@var`: all of it is in the file, all of it is the
  language spec, so R2 is not at risk.
- **`inherited_or_trait_receiver`** — the method is declared by an ancestor or trait. Settled by
  walking `EXTENDS` / `IMPLEMENTS` / `USES_TRAIT`, which the graph **already holds** — no type
  inference at all. 37 % of `brick/math`'s share is this, which is the cheapest work on this page.
- **`late_bound_or_string_name`** — `static::m()`, `'C::m'` callables, string method names. The
  target depends on runtime late binding; this is the only cause an LSP defer is the right answer
  for, and it is **≤0.6 %**.

## The cap nobody had measured

An edge stays HEURISTIC because the resolver's lookup **missed**. Knowing the receiver's type
rewrites `fetch` into `\Vendor\Foo::fetch` — which still misses if `\Vendor\Foo` has no node. So the
share a type table can move is *settleable **and** already linked*:

- `laravel/laravel`: **0 of 87**. Every HEURISTIC edge points into `vendor/`, unindexed by default
  ([039](../tasks/039_vendor-stub-index.md) ships stub roots, off). A type table would make the
  claims *precise* — `\Illuminate\…::method` instead of a bare name, which is what you need to know
  what to stub — but would not move the tier by one edge.
- `symfony/demo`: **128 of 568 (22.5 %)**.
- `brick/math`: **1 535 of 1 659 (92.5 %)** — a self-contained library, so nearly all of it lands.

**This is why the number never moved.** It needs *two* mechanisms, and only one was ever promised:
local types settle the cause, `vendor/` stubs decide whether settling it changes anything.

## Reconciliation (AC3)

- **PLAN §17** claimed the mitigation was "name-match HEURISTIC; defer precise cases to an LSP". The
  defer is right for ≤0.6 % and wrong for the rest. Rewritten to say so, with the cap.
- **PLAN §1** promised "a planned PHP local type table". The promise is sound; it now names its
  owner, [137](../tasks/137_php-local-type-table.md), and its measured target instead of "planned".
- The tracked share is a **target where the repo is self-contained and a floor where it is not** —
  which is a property of the repository, not of the adapter, and cannot be one global number.

## Target handed to 137 (AC4)

From the table above, not rounded to look like progress: **`brick/math` 1 659 → ≤ 200 HEURISTIC
edges** (the 92.5 % linkable share plus the 0.6 % late-binding residual), and **`symfony/demo` 568 →
≤ 450** (22.5 % linkable). `laravel/laravel` gets **no HEURISTIC target at all** — its number is
bounded by `vendor/` coverage, so 137 asserts only that its claims become qualified names.

## What this ticket did NOT do

- **No adapter change** (AC5). Nothing new is encoded; R2 is untouched.
- **No `vendor/` decision.** 039 already ships the mechanism off by default; whether to turn it on is
  a configuration finding for the runbook, and this page is the evidence for it.
- **No claim that HEURISTIC is wrong.** R5.2 makes it an honest tier and round 5 measured 8 of 8
  checked claims exact. It is a *ceiling on what PILLAR 1 can sell as resolved*, which is a different
  complaint and the only one this ticket makes.
