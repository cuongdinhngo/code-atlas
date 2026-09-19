---
id: 302
slug: python-return-annotations-do-not-resolve-the-next-call
title: "Python records a callable's return annotation but drops it before the next member call, leaving factory-result receivers HEURISTIC"
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [226, 227]
---

## Why this exists

[226](226_an-imported-type-name-is-never-qualified-so-no-cross-file-base-or-annotation-links.md)
qualified imported Python types, and [227](227_python-has-no-local-type-table-so-every-member-call-is-heuristic.md)
used explicit parameter, attribute and constructor bindings to promote 199 calls on pinned `flask`.
The resulting `CALLS` HEURISTIC share is still **82.2%**. Task 227 deliberately excluded receivers
whose type comes from a function's return annotation.

Python already states that fact in source:

```python
def repository() -> UserRepository: ...
repository().save()
```

The adapter reads the annotation and records declared function/method return types, but its local
type table does not carry the returned class onto the call result. This ticket measures and closes
the same-file, explicit-annotation subset without introducing runtime inference or Jedi.

## Scope / Deliverables

1. Extend the committed edge-health reporter with a Python receiver-shape census. Separate
   same-file explicit return annotations from imported callables, unresolved/ambiguous annotations,
   unions, `Any`, unannotated calls and dynamic attribute access.
2. Build a same-file callable-return map from declarations the adapter already walks, using the
   import/FQN rules shipped by 226 for the annotation itself.
3. Cover `x = factory(); x.method()`, `factory().method()` and a same-file method whose declared
   return class is concrete.
4. Promote only calls whose callable target and class-like return annotation are unique and
   indexable. Everything else retains today's bare `HEURISTIC` edge.
5. Measure the before/after HEURISTIC share and promoted-site count on pinned `flask`.

## Constraints

- Standard-library `ast` only: no Jedi, runtime imports, execution, network or third-party
  dependency.
- File-at-a-time remains the adapter contract. Imported callable bodies and whole-program return
  inference are not reconstructed in the core.
- No core language branch, schema change, contract field or `CONTRACT_VERSION` bump.
- `Any`, unions with more than one concrete class, unresolved forward references and unknown
  reassignments are never upgraded to `RESOLVED`.
- Identical input yields identical rows; sample-specific names influence tests and measurement only.

## Acceptance criteria

- **AC1 — evidence gate.** Before implementation, the committed reporter classifies every
  HEURISTIC `CALLS` edge on pinned `flask` and reports a non-zero explicit-return, indexed-target
  ceiling. A zero ceiling closes the ticket with evidence rather than code.
- **AC2 — red first.** A fixture with assigned and direct same-file annotated return receivers is
  bare `HEURISTIC` before the change and qualified `RESOLVED` after it.
- **AC3 — honesty.** Unannotated, `Any`, ambiguous union, external callable and unknown reassignment
  fixtures remain `HEURISTIC`; no guessed qname is emitted.
- **AC4 — measured result.** The promoted count equals the safely classifiable reporter population,
  or every difference is itemised by cause. The pinned `flask` HEURISTIC share does not increase.
- **AC5 — determinism and compatibility.** Two builds produce byte-identical stable rows;
  `code_atlas/`, `contract.py`, `CONTRACT_VERSION` and unaffected Python fixtures remain unchanged.

## Out of scope

- Return annotations that can only be discovered by opening an imported callable's declaration.
- Runtime protocols, duck typing, data-flow inference, generic substitution and library stubs.
- Constructor/parameter/property bindings already owned by task 227.

## References

[226](226_an-imported-type-name-is-never-qualified-so-no-cross-file-base-or-annotation-links.md),
[227](227_python-has-no-local-type-table-so-every-member-call-is-heuristic.md),
`adapters/python/src/types.py`, `adapters/python/src/parse.py`,
`scripts/edge_health_report.py`, `scripts/cross_repo_samples.json`,
ENGINEERING_RULES R1.1, R2, R3, R4.2, R5.2, R6.3 and R6.5.
