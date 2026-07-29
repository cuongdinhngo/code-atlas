---
id: 011
slug: resolver
title: Cross-file edge resolver (M2)
phase: 1
milestone: M2
status: todo
depends_on: [009]
---

## Goal
Link bare edges to nodes, generically — no language branches (§8.2).

## Scope / Deliverables
- After all nodes exist: resolve `EXTENDS/IMPLEMENTS/USES_TRAIT/NEW/FuncCall` FQN `target_raw` → `nodes.qualified_name`, set `target_qname`, tier `RESOLVED`; leave NULL if external/vendor.
- Instance `CALLS` with unknown receiver → name-match across index: 1 candidate = `HEURISTIC`; many = top-N `HEURISTIC`; `$x->$m()` = `DYNAMIC`, unlinked.
- `INCLUDES`: literal path resolved relative to includer; variable = `DYNAMIC`.
- Honor `semantic_types` capability when present (pre-resolved edges kept as `RESOLVED`).

## Acceptance criteria
- Resolver contains **zero** `if language == …` (grep-gate).
- Known symbol → correct resolved caller chain on fixtures.

## References
Plan §8.2, §2 (LSP litmus).
