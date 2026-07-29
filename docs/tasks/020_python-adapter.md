---
id: 020
slug: python-adapter
title: Python adapter (M8)
phase: 2
milestone: M8
status: todo
depends_on: [019]
---

## Goal
Third adapter — cheap once the contract is hardened (§3, §15).

## Scope / Deliverables
- `adapters/python/`: `ast` builtin for parse + `jedi` for import/name resolution.
- Map qnames as `module.Class.method`; emit the standard node/edge vocabulary.
- Runs in-process or a venv (document runtime).

## Acceptance criteria
- Passes `tests/contract/` with Python fixtures; core unchanged.
- Import/name resolution produces `RESOLVED` edges where jedi can resolve; else `HEURISTIC`.

## References
Plan §3, §15 (M8).
