---
id: 151
slug: ts-member-calls-emit-no-edge
title: '`obj.method()` emits no edge at all — the TS graph is missing the commonest call shape in the language'
phase: 2
milestone: M7
status: done
depends_on: [019, 128, 137]
---

## Why this exists

The TS adapter drops a member call on the floor. Measured on both adapters, same source shape:

```
// probe.ts                         probe.php
function run(obj) {                 function run($obj) {
  obj.method();                       $obj->method();
  helper();                           helper();
}                                   }

TS  → CALLS probe.ts::run -> helper            (one edge; obj.method() emits nothing)
PHP → CALLS \run -> method       HEURISTIC     (two edges)
      CALLS \run -> \helper      —
```

`adapters/typescript/src/parse.js` `emitBodyEdges`: a callee that is neither `this.x` nor a bare
identifier goes to `resolveExpr`, which returns `null` for any property access whose base is not a
**namespace import** — and the caller is `if (target) addEdge(...)`, so no target means **no edge**.
PHP's `Visitor.php:648` emits the bare method name at `HEURISTIC` for the same construct.

This is claim **`128-C1`** recurring — *an adapter emits every reference it sees and only declines to
**resolve**; gating edge emission on whether the target is locally known drops what the core was meant
to link*. 128 fixed it for the identifier branch and left the member branch with the same bug, and no
fixture caught it because the TS fixtures reach methods through `this.` or a namespace import.

**Why this outranks the other slices.** In idiomatic TS/JS most calls *are* `obj.method()`. Every one
of them is absent from the graph, so `impact`, `who_calls` and `find_references` under-report on TS by
a margin nothing currently measures. It is a correctness hole, not missing breadth — and unlike
[153](153_ts-declared-and-inferred-types.md) it needs no type table: the bare name is enough for the
core to link or to leave `HEURISTIC`.

## Landed 2026-08-25 — folded into 019's PR (#179) on maintainer instruction

Emitted as specified: a member call whose receiver the adapter cannot name targets the **bare method
name** at `HEURISTIC`; `this.m()` and `ns.f()` still resolve to full qnames; a computed callee
(`obj[name]()`, an IIFE) emits `(dynamic)` at `DYNAMIC`, PHP's convention rather than silence.

**`HEURISTIC` turned out to be load-bearing, not cosmetic.** `resolver.py`'s bare-member branch takes
an edge into its name-only fallback **only if the edge already claims `HEURISTIC`**; an edge that names
`greet` with no tier claim falls through and links to nothing. Both states are recorded as red runs on
`tests/test_ts_import_resolution.py`: no tier → `target_qname is None`; no edge → `0 == 1`.

**How much was missing (AC5, on real JS rather than a fixture, since 150 has not landed):** the
adapter's own unchanged sources plus `tests/viewer_dom_stub.js` — four files — go from **22 CALLS edges
to 96**. 74 of 96 call edges, **77%**, were absent from the graph.

## Scope / Deliverables

- Emit `CALLS` for a member call whose receiver the adapter cannot name, targeting the **bare method
  name**, at the tier the contract already has for "named but unproven" — PHP's choice is `HEURISTIC`
  and parity is the default; design states the tier and why.
- Keep what already resolves: `this.m()` → `<class>::m`, `ns.f()` → `<ns-file>::f`. A chained
  `a.b.c()` names `c`. `super.m()` needs its own answer (the parent qname is known from EXTENDS).
- A dynamic callee (`obj[name]()`, an immediately-invoked expression) is **not** a bare name: decide
  between PHP's `(dynamic)`/`DYNAMIC` convention and emitting nothing, and write the choice down.
- Fixture + conformance case for a member call on a plain variable, so the shape cannot regress; the
  histograms of every existing TS case move, which is the visible measure of what was missing.

## Acceptance criteria

1. `obj.method()` in a TS/JS file produces a `CALLS` edge naming `method`, with the same tier the PHP
   adapter gives `$obj->method()`; a red run is recorded (R6.5).
2. `this.m()` and `ns.f()` still resolve to their full qnames — no regression to bare.
3. The conformance case's exact edge shapes pin the new edge's `source_qname`, target and tier.
4. The adapter README's edge section says which member calls resolve, which stay bare, and which are
   dynamic — the same three-way split PHP documents.
5. The before/after edge count on one pinned cross-repo TS sample is reported, so the size of the hole
   this closes is on the record rather than asserted. (Needs [150](150_ts-adapter-has-no-gate-but-its-own-fixtures.md);
   if 150 has not landed, report it on a fixture tree and say so.)

## Out of scope

- **Resolving the receiver's type.** Turning `obj.method()` into `<Class>::method` is the inferred-type
  table — [153](153_ts-declared-and-inferred-types.md), in 137's shape. This ticket only stops the
  edge from vanishing.
- `args`/`arg_keys` on the new edges — [152](152_ts-call-args-and-arg-keys.md).

## References

PLAN §4.4, §8.2; ENGINEERING_RULES R3.3, R6.2, R6.5; LESSONS claim `128-C1`; tasks 128, 137, 019.
