---
id: 112
slug: onboarding-dataset-contract
title: Onboarding — one compact dataset as the contract behind every renderer (M11)
phase: 3
milestone: M11
status: done
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

<!-- ===================== mango working doc (embed) — raw ticket above ===================== -->

# mango working doc — 112

## Session status
- **Phase:** finalise (execute green · inline review clean · outward actions on standing approval)
- **work_doc_mode:** embed · **Branch:** `feat/112-onboarding-dataset-contract`
- **CHALLENGER:** OFF (--no-challenger) · **REVIEW (subagent):** WAIVED — inline main-loop review only
- **TIER:** full · **SCOPE:** L (new pure module + 5 store aggregates + config knob + manifest reduce + report script + test churn)
- **change type:** feat

## Phase 0 — refine
`refine skipped: 0 unresolved product-decisions`. The ticket is specific (8 named dataset sections +
capped path index; all aggregation as bounded SQL in `store.py`; manifest reduced to the dataset). No
premise falsified — `store.py` aggregates (`counts`/`edge_health`/`edge_subtrees_by_target`),
`node_universe`/`dependency_edges` (083), `compute_metrics`/`assign_layers`/`cross_layer_edges`
(083/086/110), `build_artifact`/`manifest_dict`/`recorded_pages`, `check_artifact` C5 all resolve.
The mockup (`docs/phase3-onboarding/mockup/extract.py`) exists as the direct-read prototype the ticket
says must be ported, not copied. Remaining choices are HOW-decisions (below).

## Phase 1 — analysis

### Measured problem (ticket)
`manifest.json` on the anchor is 6,507,331 bytes and no machine reads it; each renderer re-walks the
artifact object graph. The mockup shows an aggregate dataset of ~50 KB suffices (counts by node/edge
kind, confidence, layer table, layer×layer matrix, top hubs, largest classes, directory tree with
dominant layer), + an optional capped path index (~800 KB uncapped). The dataset must be a versioned
shape renderers consume, with all aggregation as bounded SQL in `store.py`.

### HOW-decisions (resolved on standing approval)
- **H1 — new pure module `code_atlas/onboarding/dataset.py` (54th core module).** Holds the versioned
  `OnboardingDataset` shape, `build_dataset` (pure assembly), `dataset_json` (byte-stable), and
  `render_dataset_overview` (the AC5 proof-renderer). No SQL (AC1). Bumps the `== 53` core-module pin
  to 54 in `test_sql_confinement.py` and `test_core_is_language_agnostic.py`.
- **H2 — new bounded SQL aggregates in `store.py`, ported from the mockup's direct reads:**
  `node_kind_counts()`, `edge_kind_counts()` (GROUP BY kind, ≤11 rows); `largest_classes(*, limit)`
  (Class + Method LEFT JOIN, `ORDER BY count DESC LIMIT ?`); `module_hubs(*, limit)` (distinct
  source-file fan-in/out per target file, `ORDER BY fan_in DESC LIMIT ?`); `file_symbol_counts()`
  (per-file symbol count, single GROUP BY pass — feeds the directory tree). Confidence reuses
  `edge_health()`; the path-index file list reuses `file_paths()`. Every one is parametrized, stable
  `ORDER BY`, bounded (LIMIT or single aggregate pass) — no recursive walk (AC4).
- **H3 — layer table + matrix stay from the existing pure 083/110 pipeline.** Layer *assignment* is
  110's graph-mass reasoning and cannot be SQL; the layer table is `artifact.LayerRow`, the matrix is
  `cross_layer_edges` (crossings). `build_dataset` recomputes `compute_metrics`+`refine_layers` purely
  from the same `nodes`/`edges` pulls (identical numbers to `build_artifact`). This is a known
  double-compute (CPU, not query); a shared pipeline is a 116 follow-up. Recorded, not hidden.
- **H4 — `module_hubs` in SQL, consistent-by-construction with the layer table.** Hub fan-in uses the
  identical distinct-`(src_file, tgt_file)` resolved-pair definition `compute_metrics` uses, so a hub's
  fan-in equals its module metric fan-in; a test pins the equality. The layer label on each hub/class
  comes from the assignment map (pure), not SQL.
- **H5 — path index is a capped, front-coded, optional section with a knob.** New config knob
  `path_index_max` (`CA_PATH_INDEX_MAX`, default 20000). Front-coded `dirs` + `(dir_index, tail)`
  entries, sorted by path, first-N kept; the section carries `total`, `shown`, `truncated` so a trim
  states both numbers (AC6). Aggregate half excludes the path index (AC3).
- **H6 — manifest.json is reduced to the dataset.** `manifest.json` becomes
  `{**dataset.as_dict(), "pages": [...relpaths...], "overview"/"tour"/"viewer": pointers}` — one
  artifact, bulk is the compact aggregate. The operational `pages` list preserves the 050 delete-record;
  `recorded_pages` reads the new `pages` key. Byte-stable (sorted keys, no timestamps — AC2).
- **H7 — directory tree pruned at a symbol threshold (`DIR_SYMBOL_THRESHOLD = 400`, matching the
  mockup).** Flat sorted list of `(dir, symbols, files, dominant_layer)` rows for directories whose
  subtree symbol count ≥ threshold; dominant layer = most-symbols layer under the dir (from the
  assignment). Deterministic ordering (R4.2).
- **H8 — SCOPE boundary (surface at Gate 1): the renderers themselves stay unchanged (116).** Only the
  dataset shape + one proof-renderer (`render_dataset_overview`, AC5) are built here; `viewer.py`,
  `architecture_overview.py`, and the per-module page renderer are 116's migration. `build_artifact`
  and its callers (`tour_report.py`, tests) are untouched — smallest useful change (R7.1). The mockup's
  repo-specific sections (entry-split, business-modules, alpha/beta mirror) are R2-tainted and excluded;
  the dataset is exactly the 8 sections the ticket enumerates.
- **H9 — AC1 grep-gate is an explicit, narrowed restatement.** `test_exactly_one_core_module_touches_sqlite`
  already forbids SQL outside `store.py` across all of `code_atlas/`; add a focused
  `test_onboarding_and_tools_are_sql_free` scanning `onboarding/` + `tools/` specifically (ticket-named
  AC1), plus an assertion no `sqlite3` import appears there.

### Blast radius (from analysis Explore, 115,972 tokens)
- **New:** `code_atlas/onboarding/dataset.py`; `scripts/dataset_report.py` (AC3/AC4, Docker); 5 store
  aggregate methods; `config.path_index_max` knob; `tests/test_onboarding_dataset.py`.
- **Edited:** `store.py` (+aggregates); `config.py` (+knob, +Config field, +KNOB_KEYS,
  +DEFAULT_PATH_INDEX_MAX); `onboarding/artifact.py` or `dataset.py` (`manifest_dict`/`recorded_pages`
  reshape); `tools/generate_onboarding.py` (build+write the dataset; manifest = dataset).
- **Must-fix tests:** `test_sql_confinement.py:32` + `test_core_is_language_agnostic.py:42` (`53`→`54`);
  `test_generate_onboarding.py` (manifest shape + `recorded_pages` key).
- **Verify-only green:** viewer, quality gate (C5 unaffected — AC6), cache/byte-stability, config tests.

### Acceptance-criteria matrix
| AC | Requirement | Proof | Status |
|----|-------------|-------|--------|
| AC1 | Every aggregate from `store.py`; grep-gate: no SQL / no `sqlite3` under `onboarding/` or `tools/` | `test_onboarding_and_tools_are_sql_free` + the existing one-core-module gate | ✅ |
| AC2 | Byte-stable, sorted keys, no timestamps; two runs equal | `test_ac2_...`: `dataset_json` twice byte-equal; manifest twice byte-equal | ✅ |
| AC3 | Size measured anchor + 2 pinned, with/without path index; aggregate half < 100 KB anchor | `scripts/dataset_report.py` (Docker): laravel/symfony/brick — aggregate & +path-index bytes. **Anchor deferred to operator** (absent on dev host — 108/015 precedent) | ✅ (anchor deferred) |
| AC4 | Every query bounded (no unbounded recursive walk); added query time reported vs `tour_subgraph` | store aggregates are LIMIT / single GROUP BY pass; `dataset_report.py` times them vs `tour_subgraph` | ✅ |
| AC5 | Renderer from dataset alone → overview + layer table + matrix + hub list, no `GraphStore` | `test_ac5_...`: hand-built `OnboardingDataset` fixture → `render_dataset_overview`; asserts no store import needed | ✅ |
| AC6 | Path-index cap trims → both numbers carried; 109 C5 still passes | `test_ac6_...`: tiny cap → `truncated` true, `total`>`shown`; `check_artifact` still green | ✅ |

## Cost ledger
| Phase | Dispatch | Round | Tokens |
|-------|----------|-------|--------|
| analysis | Explore — store/consumer/prototype blast radius | 1 | 115,972 (24 tool-uses, 169 s) |

**Summary:** 1 dispatch, 115,972 tokens (all measured). Top driver: the analysis Explore. Main-loop
spend unmeasured (not measured by mango). Docker: full gate **1543 passed, 0 failed** (main 1524,
+19 net); ruff clean, mypy clean over 54 source files.

## Decision log
- CHALLENGER OFF + REVIEW subagent WAIVED per run args ("skipped Review & Challenge"); inline review only.
- Standing maintainer approval to resolve HOW-decisions and pass gates; finishing steps (commit → push
  → PR) proceed on the AGENTS.md standing approval. Anchor AC re-measure deferred to operator (108).
