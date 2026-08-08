---
id: 062
slug: view-databag-producer
title: 'Producer-side view data-bag edges — rules + enrichment (implements 059 Option 1)'
phase: 1.5b
milestone: Coverage
status: todo
depends_on: [030, 040, 059]
---

## Goal
Implement the [059](059_view-databag-edge.md) decision: **Option 1 — producer side only.** When a
handler publishes values into a view/data-bag under string keys, the graph records that publish so an
agent can ask “what keys does this handler put in scope?” without grepping. Consumer-side template
reads stay out of scope (059 rejected option 2 for now).

## Scope / Deliverables
- **Contract (R3).** Add a new edge kind for “handler symbol publishes view-scope key”
  (working name `PROVIDES_VIEW_DATA` — final name chosen at design) to `EDGE_KINDS` in
  `code_atlas/contract.py`. Bump `contract_version` and update `tests/contract/` in the **same**
  change.
- **How the key is addressed.** Prefer a synthetic target (e.g. a stable qname for the string key, or
  an edge `extra` / target_raw convention documented in CONVENTION) — pick the smallest shape that
  nav tools can query without a new node kind unless a node kind is clearly cheaper.
- **Rules-file shape (R2).** Extend the 040 indirection-rules channel (or a sibling JSON rules file
  outside `adapters/`, same `CA_*` opt-in pattern) so operators declare *how* their framework’s view
  setter looks (method/qname patterns → which argument holds the key). Framework names live only in
  operator/fixture data, never under `adapters/`. Core `enrichment.py` applies rules generically —
  no `if framework == …` (R1.1).
- **Nav answer.** A tool surface (extend an existing `find_*` or add a thin helper) that, given a
  handler method qname, returns the published keys + lines at `detail_level` appropriate to §19.
- **Off by default.** No rules loaded ⇒ graph unchanged (mirror 040).
- **Deterministic (R4).** Same rules + same parse ⇒ same rows; HEURISTIC (or documented) tier — never
  silent plain RESOLVED.

## Constraints
- R2 absolute — zero framework knowledge in adapters; CI grep-gate stays green.
- R3 — vocabulary change and conformance tests land together with the version bump.
- Do **not** widen the indexed file set to Twig/Blade in this ticket (041 stands); producer edges come
  from already-indexed PHP handlers + rules.
- Nothing about a private repo enters this repository — fixtures only.

## Acceptance criteria
- With a planted fixture + rules file, a handler that publishes `items` (or equivalent) yields a
  `PROVIDES_VIEW_DATA` (or final name) edge queryable by the nav surface; without rules, no such edges.
- `contract_version` bumped; `tests/contract/` updated in the same change.
- Rule-emitted edges are distinguishable by tier/provenance from adapter CALLS/ALIASES (040 precedent).
- PLAN §19 059 decision remains the scope authority; this ticket does not silently expand to option 2.

## References
[059](059_view-databag-edge.md) (decision + occurrence counts); [040](040_framework-indirection-data.md);
`code_atlas/enrichment.py`; `code_atlas/contract.py` (`EDGE_KINDS`, `CONTRACT_VERSION`); R2, R3, R4;
PLAN §19 data-bag decision.
