#!/usr/bin/env python3
"""Measure the onboarding aggregate dataset on the pinned public repos — AC3/AC4 for task 112.

The committed ``manifest.json`` used to be a multi-megabyte per-module dump. 112 reduces it to one
aggregate dataset (counts, layer table, matrix, hubs, classes, tree) plus a capped path index. This
script clones + indexes each pin (reusing task 018's harness, like ``layer_report.py`` /
``tour_report.py``), builds the dataset from the bounded ``store.py`` aggregates, and reports:

  * the aggregate-half bytes (no path index) — must stay under 100 KB on the anchor (AC3),
  * the full bytes (aggregate + path index) — the before/after against the old manifest, and
  * the added aggregate-query time against today's ``tour_subgraph`` cost (AC4).

Not part of per-PR CI — run locally or in Docker (needs php + network):

    scripts/docker-test.sh python scripts/dataset_report.py

The anchor monorepo is absent on the dev host, so its row is an operator run (108/015 precedent).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.onboarding.dataset import build_dataset, dataset_json  # noqa: E402
from code_atlas.store import LAST_COMMIT_KEY, GraphStore  # noqa: E402
from scripts.cross_repo_validate import (  # noqa: E402
    checkout_pinned,
    index_root,
    load_manifest,
)

_MAX_RESULTS = 50
_AGGREGATE_KB_CEILING = 100  # AC3: the aggregate half must stay under 100 KB (measured on anchor).


def _dataset(store: GraphStore, *, path_index_max: int):
    """Build one dataset from the store's bounded aggregates at the given path-index cap."""
    counts = store.counts()
    confidence = store.edge_health()["by_tier"]
    return build_dataset(
        store.node_universe(),
        store.dependency_edges(),
        files=counts["files"],
        parsed=counts["parsed"],
        node_kind_counts=store.node_kind_counts(),
        edge_kind_counts=store.edge_kind_counts(),
        confidence=confidence,
        hubs=store.module_hubs(limit=_MAX_RESULTS),
        classes=store.largest_classes(limit=_MAX_RESULTS),
        file_symbol_counts=store.file_symbol_counts(),
        file_paths=store.file_paths(),
        path_index_max=path_index_max,
        file_kind_counts=store.file_kind_counts(),
        commit=store.get_meta(LAST_COMMIT_KEY) or "",
    )


def _timings(store: GraphStore) -> tuple[float, float]:
    """(aggregate-query seconds, tour_subgraph seconds) — the AC4 comparison."""
    start = time.perf_counter()
    store.node_kind_counts()
    store.edge_kind_counts()
    store.edge_health()
    store.module_hubs(limit=_MAX_RESULTS)
    store.largest_classes(limit=_MAX_RESULTS)
    store.file_symbol_counts()
    store.file_kind_counts()
    store.file_paths()
    aggregate = time.perf_counter() - start
    start = time.perf_counter()
    store.tour_subgraph(max_nodes=1000)
    tour = time.perf_counter() - start
    return aggregate, tour


def _report(sid: str) -> tuple[str, bool]:
    """One repo's line, and whether the aggregate half stayed under the byte ceiling."""
    cache_root = _REPO / "artifacts" / "cross-repo-cache"
    sample = next(s for s in load_manifest() if str(s["id"]) == sid)
    root = checkout_pinned(sample, cache_root)
    index_root(root)
    with GraphStore(root / ".code-atlas" / "graph.db") as store:
        aggregate = _dataset(store, path_index_max=0)
        full = _dataset(store, path_index_max=10**9)
        agg_time, tour_time = _timings(store)
    agg_bytes = len(dataset_json(aggregate).encode("utf-8"))
    full_bytes = len(dataset_json(full).encode("utf-8"))
    under = agg_bytes < _AGGREGATE_KB_CEILING * 1024
    paths = full.path_index.total
    line = (
        f"  files={full.files}  paths={paths}  layers={len(full.layers)}\n"
        f"  aggregate: {agg_bytes} B (under {_AGGREGATE_KB_CEILING}KB: {under})  "
        f"+path-index: {full_bytes} B\n"
        f"  query time: aggregates {agg_time * 1000:.1f} ms "
        f"vs tour_subgraph {tour_time * 1000:.1f} ms"
    )
    return line, under


def main() -> int:
    failures = 0
    for sample in load_manifest():
        sid = str(sample["id"])
        print(f"\n### {sid} @ {str(sample['sha'])[:7]}")
        try:
            line, under = _report(sid)
            print(line)
            if not under:
                failures += 1
                print(f"  FAIL: aggregate half is not under {_AGGREGATE_KB_CEILING} KB")
        except Exception as exc:  # noqa: BLE001 — report every repo even if one fails
            failures += 1
            print(f"  FAILED: {type(exc).__name__}: {exc}")
    if failures:
        print(f"\n{failures} repo(s) failed the dataset check")
        return 1
    print("\nall repos pass the dataset check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
