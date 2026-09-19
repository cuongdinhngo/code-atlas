---
id: 301
slug: typescript-return-types-do-not-resolve-the-next-call
title: "TypeScript reads a callable's return type but drops it before the next member call, leaving fluent and factory-result receivers HEURISTIC"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [153]
---

## Why this exists

[153](153_ts-declared-and-inferred-types.md) added the TypeScript local type table and promoted
225 calls on pinned `ky`, but measured `CALLS` HEURISTIC share still at **54.1%**. Its written
verdict names the dominant residual: the receiver is the return value of a call, so annotations,
constructor bindings and assignments cannot name its class. The adapter already records declared
function and method return types in node `extra.type`; it does not carry that fact from
`makeClient()` to `makeClient().send()` or from `const c = makeClient()` to `c.send()`.

This is a narrower claim than "use the TypeScript checker". Before buying a `ts.Program`, measure
how many residual sites have a same-file callable target with an explicit return type—the subset the
existing file-at-a-time adapter can settle without changing the protocol.

## Scope / Deliverables

1. Extend the committed edge-health reporter with a TypeScript receiver-shape census that separates
   explicit same-file return types from unknown, imported, union/ambiguous and genuinely dynamic
   receivers. The census names the maximum number this ticket can safely promote.
2. Build a same-file callable-return map from declarations the adapter already walks. A call result
   enters the local type table only when its target and single class-like return type are explicit.
3. Cover both forms: `const x = factory(); x.method()` and `factory().method()`, including a
   same-file method returning another class.
4. Promote only those member calls to `<ReturnedClass>::method` at `RESOLVED`. Every missing,
   ambiguous, union, generic-without-a-concrete-binding, external or unindexed target keeps today's
   bare `HEURISTIC` edge.
5. Record the before/after HEURISTIC share and promoted-site count on pinned `ky` using the committed
   reporter.

## Constraints

- File-at-a-time remains the contract. No `ts.Program`, type checker, project lifecycle, second pass
  or new adapter capability.
- No core language branch, contract field, qname change or `CONTRACT_VERSION` bump.
- Return annotations are evidence; inferred library types and runtime values are not.
- Flow is forgetful: assigning an unknown result after a known one must reopen the receiver rather
  than preserve a stale `RESOLVED` target.
- Sample data sets the measured ceiling and validates the result; it never changes adapter semantics
  (R2, R6.3).

## Acceptance criteria

- **AC1 — evidence gate.** Before implementation, the committed reporter classifies every
  HEURISTIC `CALLS` edge on pinned `ky` into a derived receiver-shape cause and reports a non-zero
  explicit-return, indexed-target ceiling. If the ceiling is zero, close this ticket with the
  measurement instead of adding machinery.
- **AC2 — red first.** A fixture with assigned and direct same-file return-value receivers produces
  bare `HEURISTIC` edges before the change and the expected qualified `RESOLVED` edges after it.
- **AC3 — no false promotion.** Fixtures for union, unresolved import, unknown return and reassigned
  receiver remain `HEURISTIC`; none gains a guessed `target_qname`.
- **AC4 — measured result.** The post-change promoted count equals the reporter's safely
  classifiable population, or every difference is itemised by cause. The `ky` HEURISTIC share does
  not increase.
- **AC5 — boundary stability.** `code_atlas/`, `contract.py`, `CONTRACT_VERSION` and existing
  unaffected TypeScript fixture rows remain byte-identical.

## Out of scope

- Return types available only from an imported declaration, `.d.ts`, conditional/generic
  instantiation or whole-program inference.
- Expanding `semantic_types`; task 153 already announces it.
- Deeper JavaScript/JSDoc inference beyond return declarations already captured by the adapter.

## References

[153](153_ts-declared-and-inferred-types.md), [137](137_php-local-type-table.md),
`adapters/typescript/src/types.js`, `scripts/edge_health_report.py`,
`scripts/cross_repo_samples.json`, ENGINEERING_RULES R1.1, R2, R3, R5.2, R6.3 and R6.5.
