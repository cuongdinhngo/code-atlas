---
id: 017
slug: impact-engine
title: Impact engine + tool + prompts (M6)
phase: 1
milestone: M6
status: todo
depends_on: [013, 016]
---

## Goal
Bounded blast-radius analysis in SQL (§12 impact engine).

## Scope / Deliverables
- Bounded best-score relaxation in SQLite: seed = changed qnames; per-edge-kind weight/direction policy (`CALLS/NEW`→callers, `EXTENDS/IMPLEMENTS`→subtypes, `INCLUDES` follows requires, `CONTAINS` not traversed); one best score/node, decay per hop, floor, bounded by `CA_IMPACT_DEPTH`/`CA_IMPACT_MAX_NODES`; exclude `DYNAMIC` by default.
- `impact(paths|qnames, depth?)` tool; `impact_of_change` prompt.

## Acceptance criteria
- Traversal happens in SQL (never loads the whole graph); respects depth/max-node caps.
- Blast radius for a known change matches a hand-traced expectation.

## References
Plan §12 (impact engine), §15 (M6).
