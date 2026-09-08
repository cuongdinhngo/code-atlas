#!/usr/bin/env python3
"""Print + CHECK the onboarding map's size and shape — task 116's AC2 evidence.

AC2 asks for the page measured "on the anchor repo and two pinned public repos, with and without
the path index". Two of those three cannot be measured here, and one of them cannot be measured
usefully anywhere, so this script says which is which rather than reporting a green tick:

* **The pinned public repos are a smoke run, not a test.** They hold 26-51 files, two orders of
  magnitude under both thresholds — they cannot fail AC2, so a pass there proves nothing about it.
* **The synthetic row is the real measurement.** It reproduces the anchor's measured cardinality
  (18,929 paths in 5,399 directories, whose front-coded index encodes to 843,439 bytes = 96.9 % of
  that repo's whole dataset) and asserts both budgets against it.
* **The anchor itself is the operator's run.** Point ``CA_ANCHOR`` at an indexed monorepo and its
  row is measured too.

Not part of per-PR CI — run locally or in Docker (needs php for the pins):

    scripts/docker-test.sh python scripts/viewer_report.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.onboarding.dataset import build_dataset  # noqa: E402
from code_atlas.onboarding.viewer import SECTION_IDS, render_viewer  # noqa: E402
from code_atlas.store import LAST_COMMIT_KEY, GraphStore  # noqa: E402
from scripts.cross_repo_validate import (  # noqa: E402
    checkout_pinned,
    index_root,
    load_manifest,
)

BUDGET_WITH_INDEX = 1024 * 1024
BUDGET_WITHOUT_INDEX = 150 * 1024
MAX_RESULTS = 50
PATH_INDEX_MAX = 20000

# The anchor monorepo, measured (task 116 analysis): 18,929 indexed paths in 5,399 directories
# across 12 responsibility layers, whose front-coded path index encodes to 843,439 bytes — 96.9 %
# of that repo's whole dataset. The generator below reproduces all four, at 1.020x the index size,
# so a page that fits the budget here fits it there too.
ANCHOR_PATHS = 18929
ANCHOR_DIRS = 5399
ANCHOR_INDEX_BYTES = 843439
# 110's ratified responsibility vocabulary, one word per layer. Using the vocabulary is what gives
# the synthetic the anchor's ~12 layers; a path naming no responsibility falls back to structural
# grouping, which produced 102 layers and a 10,404-cell matrix — not any real repo's shape.
_ROLES = (
    "controller", "service", "model", "view", "middleware", "job",
    "report", "lib", "test", "config", "vendor",
)


def dataset_of(root: Path, *, path_index_max: int):
    """Build the 112 dataset for an indexed repo, exactly as ``generate_onboarding`` does."""
    with GraphStore(root / ".code-atlas" / "graph.db") as store:
        counts = store.counts()
        return build_dataset(
            store.node_universe(),
            store.dependency_edges(),
            files=counts["files"],
            parsed=counts["parsed"],
            node_kind_counts=store.node_kind_counts(),
            edge_kind_counts=store.edge_kind_counts(),
            confidence=store.edge_health()["by_tier"],  # type: ignore[arg-type]
            hubs=store.module_hubs(limit=MAX_RESULTS),
            classes=store.largest_classes(limit=MAX_RESULTS),
            file_symbol_counts=store.file_symbol_counts(),
            file_paths=store.file_paths(),
            path_index_max=path_index_max,
            reachability_sample_max=MAX_RESULTS,
            file_class_counts=store.file_class_counts(),
            module_max=MAX_RESULTS,
            mirror_sample_max=MAX_RESULTS,
            file_kind_counts=store.file_kind_counts(),
            commit=store.get_meta(LAST_COMMIT_KEY) or "",
        )


def anchor_scale_paths(count: int = ANCHOR_PATHS, dirs: int = ANCHOR_DIRS) -> list[str]:
    """Path strings at the anchor's measured cardinality, layer count and byte length."""
    return sorted(
        {
            f"tree{(i % dirs) % 6}/branch{(i % dirs) % 97:03d}"
            f"/{_ROLES[(i % dirs) % len(_ROLES)]}/component{i % dirs:05d}"
            f"/CompiledModule{i:05d}.aa"
            for i in range(count)
        }
    )


def synthetic_dataset(path_index_max: int):
    """The anchor-scale dataset the AC2 budget is asserted against."""
    paths = anchor_scale_paths()
    nodes = [(f"\\Sym{index}", path) for index, path in enumerate(paths)]
    edges = [
        (f"\\Sym{index}", f"\\Sym{(index * 7 + 1) % len(paths)}")
        for index in range(0, len(paths), 3)
    ]
    return build_dataset(
        nodes,
        edges,
        files=len(paths),
        parsed=len(paths),
        node_kind_counts=[("Class", 4114), ("Method", 37542), ("Property", 13631)],
        edge_kind_counts=[("CALLS", 121000), ("EXTENDS", 4300)],
        confidence={"EXACT": 40000, "HEURISTIC": 85300},
        hubs=[(paths[i], 900 - i, 40) for i in range(MAX_RESULTS)],
        classes=[(f"\\Class{i}", paths[i], 400 - i) for i in range(MAX_RESULTS)],
        file_symbol_counts=[(path, 12) for path in paths],
        file_paths=paths,
        path_index_max=path_index_max,
        reachability_sample_max=MAX_RESULTS,
        file_class_counts=[(path, 1) for path in paths],
        module_max=MAX_RESULTS,
        mirror_sample_max=MAX_RESULTS,
        file_kind_counts=[(path, kind, n) for path in paths for kind, n in (("Class", 1),)],
        commit="0" * 40,
    )


def measure(label: str, with_index, without_index, *, budgeted: bool) -> list[str]:
    """Print one row; return the problems that make it a failure rather than a note."""
    full = len(render_viewer(with_index, MAX_RESULTS).encode("utf-8"))
    bare = len(render_viewer(without_index, MAX_RESULTS).encode("utf-8"))
    index_bytes = len(
        json.dumps(with_index.as_dict()["path_index"], ensure_ascii=True).encode("utf-8")
    )
    print(
        f"  {label:<22} with index {full:>9,} B  without {bare:>8,} B"
        f"  (index alone {index_bytes:>9,} B, {len(with_index.path_index.entries):>6,} paths"
        f", {len(with_index.layers)} layers, {len(with_index.tree)} mapped dirs)"
    )
    problems: list[str] = []
    rendered = render_viewer(with_index, MAX_RESULTS)
    for section in SECTION_IDS:
        if f'id="{section}"' not in rendered:
            problems.append(f"section {section} is missing from the page")
    if rendered != render_viewer(with_index, MAX_RESULTS):
        problems.append("the same dataset rendered two different pages (AC3)")
    if not budgeted:
        print("      (smoke only: far under both budgets, so it cannot fail AC2)")
        return problems
    if full >= BUDGET_WITH_INDEX:
        problems.append(f"{full:,} B with the index is over the 1 MB budget")
    if bare >= BUDGET_WITHOUT_INDEX:
        problems.append(f"{bare:,} B without the index is over the 150 KB budget")
    if index_bytes < ANCHOR_INDEX_BYTES:
        problems.append(
            f"the index encodes to {index_bytes:,} B, under the anchor's measured "
            f"{ANCHOR_INDEX_BYTES:,} B — the budget would prove nothing"
        )
    return problems


def main() -> int:
    failures = 0
    print(
        f"budgets: with index < {BUDGET_WITH_INDEX:,} B   without index < "
        f"{BUDGET_WITHOUT_INDEX:,} B"
    )

    print("\n### synthetic, at the anchor's measured cardinality (the real AC2 measurement)")
    problems = measure(
        "synthetic-anchor", synthetic_dataset(PATH_INDEX_MAX), synthetic_dataset(0), budgeted=True
    )
    if problems:
        failures += 1
        print(f"  FAIL: {'; '.join(problems)}")

    print("\n### pinned public repos (smoke: too small to falsify AC2)")
    cache_root = _REPO / "artifacts" / "cross-repo-cache"
    for sample in load_manifest():
        sid = str(sample["id"])
        try:
            root = checkout_pinned(sample, cache_root)
            language = str(sample.get("language", "php"))
            index_root(root, language=language)
            problems = measure(
                sid,
                dataset_of(root, path_index_max=PATH_INDEX_MAX),
                dataset_of(root, path_index_max=0),
                budgeted=False,
            )
            if problems:
                failures += 1
                print(f"  FAIL: {'; '.join(problems)}")
        except Exception as exc:  # noqa: BLE001 — report every repo even if one fails
            failures += 1
            print(f"  {sid}: FAILED: {type(exc).__name__}: {exc}")

    anchor = os.environ.get("CA_ANCHOR")
    print("\n### anchor monorepo")
    if not anchor:
        print("  not measured here: set CA_ANCHOR to an indexed repo root to include it")
    else:
        root = Path(anchor)
        problems = measure(
            root.name,
            dataset_of(root, path_index_max=PATH_INDEX_MAX),
            dataset_of(root, path_index_max=0),
            budgeted=True,
        )
        if problems:
            failures += 1
            print(f"  FAIL: {'; '.join(problems)}")

    if failures:
        print(f"\n{failures} measurement(s) failed")
        return 1
    print("\nall measured pages are within budget and structurally complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
