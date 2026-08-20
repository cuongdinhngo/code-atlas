---
id: 112
slug: onboarding-dataset-contract
title: Onboarding — one compact dataset as the contract behind every renderer (M11)
phase: 3
milestone: M11
status: todo
depends_on: [083, 086, 110]
---

## Why this exists (measured, anchor monorepo)

Today each onboarding renderer walks the artifact object graph and re-derives what it needs, and the
machine-readable output is a **6,507,331-byte `manifest.json`** that no machine reads. The mockup showed
the whole map needs only an **aggregate dataset of ~50 KB**: counts by node kind and edge kind, edge
confidence, the layer table, the layer×layer matrix, the top hubs, the largest classes, and a
directory tree pruned to a symbol threshold carrying each node's dominant layer.

Size comparison on the same repo, same commit:

| | Bytes |
|---|---:|
| current `manifest.json` | 6,507,331 |
| mockup aggregate dataset | ~50,000 |
| mockup dataset + full path index (18,929 paths, front-coded over 5,399 dirs) | ~850,000 |

The path index is what powers search and counterpart lookup (114/115/116) and is the single reason the
mockup is 891 KB rather than ~60 KB. It should be a documented, capped, optional part of the dataset —
not an accident.

## Scope

- **All aggregation lands in `store.py`** as bounded SQL (R1.4, R4.3): per-kind counts, per-file degree,
  the layer matrix, hub ranking, the largest-class query, and the directory rollup. The prototype's
  direct `graph.db` reads are exactly what must *not* be copied into `code_atlas/`.
- A versioned dataset shape in `onboarding/` that renderers consume and nothing else re-derives.
  It is **not** the adapter contract and must not touch `contract_version` (R3).
- The path index is a separate, capped section with an explicit knob; when the cap trims it, the dataset
  says so and search states its own incompleteness.
- `manifest.json` is either replaced by this dataset or reduced to it — one machine-readable artifact,
  not two.

## Acceptance criteria

1. **AC1.** Every aggregate comes from `store.py`; a grep-gate proves no SQL and no `sqlite3` import
   under `onboarding/` or `tools/`.
2. **AC2.** Byte-stable given the same index, with sorted keys and no timestamps (R4.2) — two runs
   compare equal.
3. **AC3.** Dataset size measured on the anchor repo and two pinned public repos, with and without the
   path index; the aggregate half stays under 100 KB on the anchor repo.
4. **AC4.** Every query is bounded — no unbounded recursive walk (R4.3) — and the total added query time
   on the anchor repo is reported against today's `tour_subgraph` cost.
5. **AC5.** A renderer given only the dataset can produce the overview, the layer table, the matrix and
   the hub list with no further store access — proven by a test that builds a renderer from a fixture
   dataset with no `GraphStore` present.
6. **AC6.** When the path-index cap trims, the dataset carries both numbers and 109's C5 still passes.

## Out of scope

The renderers themselves (116) and the LLM prose fields (117). No change to the adapter contract.
