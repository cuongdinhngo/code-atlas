---
id: 013
slug: nav-tools
title: Navigation tools — callers / references / implementations (M2)
phase: 1
milestone: M2
status: todo
depends_on: [011, 010]
---

## Goal
Answer relationship queries from the resolved graph (§12).

## Scope / Deliverables
- `find_callers(qname, depth?)` — who CALLS/NEW it (+ confidence tier).
- `find_references(qname)` — all edges targeting it.
- `find_implementations(qname)` — EXTENDS/IMPLEMENTS subtypes.
- Return qnames + `file:line`, not bodies.

## Acceptance criteria
- On a known class, `find_callers` matches a manual baseline (accounting for dynamic calls).
- Confidence tiers surfaced; dynamic edges flagged, not silently linked.

## References
Plan §12, §15 (M2).
