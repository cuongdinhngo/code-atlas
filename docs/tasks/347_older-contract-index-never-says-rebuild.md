---
id: 347
slug: older-contract-index-never-says-rebuild
title: 'An index from an older contract reads as behind or current, never as rebuild-required'
phase: 2
milestone: Adoption
status: todo
depends_on: [201, 316, 322]
---

## Why this exists

After a contract bump, every existing index needs a full rebuild. The status payload knows it:
`get_index_status` sets `full_rebuild_required` (`code_atlas/tools/get_index_status.py:238`).

The one sentence every channel lifts does not say so. `_compose_summary`
(`code_atlas/tools/get_index_status.py:311`) reads `staleness` and never reads
`full_rebuild_required`. That summary is the MCP `instructions` state line (`instructions._state`)
and the `code-atlas-state` hook line (`code_atlas/hooks/state.py`). So an anchor project that
upgrades code-atlas is never told its index is from another era.

## Evidence (this repo, 2026-09-29, server at contract v13)

- `graph.db` meta: `contract_version = 10`, `schema_version = 6`.
- `get_index_status()["summary"]` returns
  `behind @ bfb1e74 · 622 files · 8,456 symbols (read tools still serve) — run build_or_update_index`.
- The same payload holds `full_rebuild_required = {'reason': 'contract_rebuild_required', 'route':
  'code-atlas-build --full', 'in_band_option': 'allow_full_rebuild=true'}`.
- Following the summary's route (`build_or_update_index`, `full=false`) is refused
  (`contract_rebuild_required`). The advice points at a call that cannot succeed.
- When HEAD has not moved, the summary reads `current … · healthy`. The state hook is then silent
  (`state.py`: silent when `staleness == current`). The grep nudge (345) is silent too, because an
  older index stamps no `symbol_shapes`. Nothing tells the user why.

## Scope

1. When `full_rebuild_required` is set, the summary names it, whatever the staleness: the stored and
   current contract versions, and the route that works (`code-atlas-build --full`, or
   `allow_full_rebuild=true` in band). It stays one sentence, lifted (316, R6.7).
2. The state hook speaks for such an index even when it is `current`.
3. Nothing else changes: no auto-rebuild (202: a hook never starts a full build).

## Acceptance criteria

- **AC1:** On an index whose stored `contract_version` is below `CONTRACT_VERSION`, the summary
  names both versions and the full-rebuild route. It does not tell the user to run
  `build_or_update_index` without the opt-in. This holds for `behind` and for `current`.
- **AC2:** On that index at an unmoved HEAD, `code-atlas-state` prints the line on `SessionStart`.
- **AC3:** The server `instructions` carry the same line and still fit `CLIENT_CAP` (343).
- **AC4:** A same-era index's summary is byte-identical to today's.
