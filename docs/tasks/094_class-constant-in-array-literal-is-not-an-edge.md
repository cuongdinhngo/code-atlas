---
id: 094
slug: class-constant-in-array-literal-is-not-an-edge
title: 'A `::class` constant in a routing array is `relationship_not_modelled`, while a DYNAMIC tier sits unused'
phase: 1.5b
milestone: Coverage
status: todo
depends_on: [030, 011, 002]
---

## Goal
The anchor repo's front controller builds a routing table whose values are `Foo::class` constants in
an array literal, then dispatches through a variable method name. Asked *who consumes this new
controller*, `find_references` answered `relationship_not_modelled`; asked on the method,
`no_matches`. Both are honest, and both leave the single most common "who wires this up" question in
a legacy PHP monolith unanswerable by the graph.

The model already has somewhere to put this. `edge_health` reports a `DYNAMIC` confidence tier
carrying **2,956 edges** on that index. A `Foo::class` constant in a literal array is a *textual,
unambiguous* mention of a class — strictly more information than nothing, and exactly what a
low-confidence tier is for. A `DYNAMIC`-tier hit with an honest tier label is better than a refusal.

## Evidence (field retro round 5, 2026-08-14, **real work**)
- 5 `find_references` calls across two new controllers produced three flavours of nothing;
  the question was answered by `grep` on one file (§7.1, §8 "lost" row).
- After commit + rebuild: `reason: "relationship_not_modelled"` for a class whose consumer references
  it as a `::class` constant in an array literal (§4 row 2).
- Retro's own verdict: **"partly wrong to be silent"** — `edge_health.by_tier.DYNAMIC` = 2,956 on the
  same payload, so the tier exists and is populated by other rules.
- Cost recorded: 5 calls and a wrong belief about *why* the answer was empty (§7.1).
- The evaluator's regression test asserts on the front controller's **source text** for the same
  reason — the repo's own test had to do by regex what the graph declined to model.
- Carve-out (a) in §10 exists because of this: *"not for routing tables built from `::class`
  constants plus variable-method dispatch — grep the front controller"*.

## Scope / Deliverables
- **Emit an edge for a `::class` constant used as a value**, at `DYNAMIC` confidence, from the
  enclosing declaration (file/function/method) to the named class. Start with the array-literal case
  that the field met; decide in design whether a bare `Foo::class` argument or assignment is in the
  same rule or a follow-up.
- **Name the edge kind honestly.** It is a *mention*, not a call and not an instantiation. Decide
  whether the existing indirection vocabulary (030) covers it or a new `edge_kind` is needed — a new
  kind is a contract change (R3) and must be justified against reusing one.
- **Make the tier legible at the answer.** A `find_references` result whose only hits are `DYNAMIC`
  must say so in a way an agent reads as *candidate list, not answer* — round 4's all-`HEURISTIC`
  hazard (§A carry-over) applies with more force at a lower tier.
- **Do not model the dispatch.** The variable-method invocation stays unmodelled; this ticket answers
  *which classes does this table name*, not *does control flow reach this action*. Say so in the
  ticket's resolution so the carve-out in §10 can be narrowed precisely, not deleted.
- **Re-measure the carve-out.** After the fix, the §7.1 question must be re-asked against the anchor
  index and the answer recorded here.

## Constraints
- R1.1 — the rule belongs in the **PHP adapter**; `::class` is PHP syntax and the core must not learn
  it. The core sees an edge with a tier, nothing more.
- R2 — encode the language construct, never the anchor repo's front controller or its route names.
  The fixture must be a generic array-of-`::class` table, not a copy of the repo's.
- R3 — a new `edge_kind` bumps `contract_version` and extends the conformance suite; reusing an
  existing kind does not.
- R4 — deterministic ordering of the new edges.
- Scale: the anchor index holds 1.79 M edges, 64 % already `HEURISTIC`. Measure the edge-count delta
  this rule adds before merging; a rule that inflates a low-confidence tier by a large factor makes
  every answer noisier and needs a cost verdict, not just a correctness one.

## Acceptance criteria
- A fixture with `['a' => Foo::class, 'b' => Bar::class]` produces `DYNAMIC`-tier edges to both
  classes, pinned by an adapter conformance test and a store-level test.
- `find_references` on `Foo` returns the mention with its tier, and the payload makes the tier's
  meaning legible without reading source.
- The edge-count delta on a full anchor build is recorded in this ticket (before/after totals and the
  `by_tier` breakdown).
- The `no_matches` answer for the variable-method dispatch is unchanged, and a test says so.
- §10's carve-out (a) is rewritten in the retro-derived docs to cover only the dispatch half.

## References
Field retro round 5 §7.1, §4 row 2, §8 ("Does the front controller reach `displayAction`?" — lost),
§10 carve-out (a); candidate 3.
Related: [030](030_alias-indirection-edges.md) (alias & literal-indirection edges — the precedent
rule), [011](011_resolver.md), [059](059_view-databag-edge.md) and
[062](062_view-databag-producer.md) (the last time a string-keyed seam was modelled),
[067](067_first-page-not-representative.md) (low-tier results read as answers).
