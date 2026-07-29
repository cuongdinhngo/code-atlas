---
id: 002
slug: contract-schema
title: The contract — schema, version, validation
phase: 1
milestone: Contract
status: todo
depends_on: [001]
---

## Goal
Define the single seam between core and adapters as a versioned, validated artifact (§4).

## Scope / Deliverables
- `contract.py`: node kinds (`File Namespace Class Interface Trait Enum Function Method Property ClassConst Const`) and edge kinds (`CONTAINS EXTENDS IMPLEMENTS USES_TRAIT CALLS NEW IMPORTS INCLUDES REFERENCES`).
- Node/edge field definitions; `confidence_tier ∈ {RESOLVED, HEURISTIC, DYNAMIC}`.
- Qualified-name convention documented + helpers.
- `contract_version` constant + capability-flags shape (e.g. `semantic_types`).
- A `validate(result)` function usable by both the indexer and the conformance tests.

## Acceptance criteria
- `validate()` accepts a known-good `{path, ok, nodes, edges}` and rejects malformed shapes with clear errors.
- Version constant exported; schema is the sole source of truth (no field lists duplicated in store/indexer).

## References
Plan §4 (4.1 protocol, 4.2 schema, 4.3 abstraction, 4.4 contract v2 note).
