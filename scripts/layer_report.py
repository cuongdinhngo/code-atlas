#!/usr/bin/env python3
"""Print + CHECK `assign_layers` for the pinned public PHP repos — the AC2 real-repo gate (105).

Authored fixtures have now hidden a path-shape layer defect five times (retro
`fixture-shape-begs-the-question`; 084, 103, 104, 086, 105). This makes the real-repo check
committed and re-runnable: it clones+indexes each pin from `cross_repo_samples.json` (reusing task
018's harness), prints the actual layer assignment, and **asserts** the invariant each repo must
hold — so a regression fails with a non-zero exit instead of needing a human to eyeball it. Not part
of per-PR CI — run locally or in Docker (needs php + network):

    scripts/docker-test.sh python scripts/layer_report.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.onboarding.layers import (  # noqa: E402
    LayerAssignment,
    assign_layers,
    cross_layer_edges,
)
from code_atlas.onboarding.metrics import compute_metrics, module_edges  # noqa: E402
from code_atlas.store import GraphStore  # noqa: E402
from scripts.cross_repo_validate import (  # noqa: E402
    checkout_pinned,
    index_root,
    load_manifest,
)

# The invariant each pinned repo must satisfy — robust subsets, not exact counts (PHP-version drift
# moves those). laravel: app/** must stay split (F1 fix), never one "app" layer. symfony / brick:
# the source tree's known subdirs must remain distinct layers (086's recorded, sensible split).
_EXPECT: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "laravel_app": (frozenset({"Http", "Models"}), frozenset({"app"})),
    "symfony_demo": (frozenset({"Controller", "Entity", "Repository"}), frozenset()),
    "brick_math": (frozenset({"src", "Exception", "Internal"}), frozenset()),
}


def format_report(
    assignment: LayerAssignment,
    nodes: list[tuple[str, str]],
    edges: list[tuple[str, str]],
) -> str:
    """The layer assignment for one indexed repo, in the format 086's evidence recorded."""
    per_layer: dict[str, int] = {}
    for module in assignment.modules:
        per_layer[module.layer] = per_layer.get(module.layer, 0) + 1
    chain = " → ".join(f"{layer}({per_layer[layer]})" for layer in assignment.layers)
    crossings = cross_layer_edges(module_edges(nodes, edges), assignment)
    top = " · ".join(f"{e.source}→{e.target} ×{e.count}" for e in crossings[:4])
    return (
        f"  method={assignment.method}  layers={len(assignment.layers)}\n"
        f"  {chain}\n  crossings: {top}"
    )


def check(sid: str, layers: tuple[str, ...]) -> list[str]:
    """The gate: which required layers are missing / which forbidden layers are present."""
    spec = _EXPECT.get(sid)
    if spec is None:
        return []
    require, forbid = spec
    problems: list[str] = []
    missing = sorted(require - set(layers))
    present = sorted(forbid & set(layers))
    if missing:
        problems.append(f"missing required layers {missing}")
    if present:
        problems.append(f"forbidden layers present {present}")
    return problems


def main() -> int:
    cache_root = _REPO / "artifacts" / "cross-repo-cache"
    failures = 0
    for sample in load_manifest():
        sid = str(sample["id"])
        print(f"\n### {sid} @ {str(sample['sha'])[:7]}")
        try:
            root = checkout_pinned(sample, cache_root)
            index_root(root)
            with GraphStore(root / ".code-atlas" / "graph.db") as store:
                nodes = store.node_universe()
                edges = store.dependency_edges()
            assignment = assign_layers(compute_metrics(nodes, edges))
            print(format_report(assignment, nodes, edges))
            problems = check(sid, assignment.layers)
            if problems:
                failures += 1
                print(f"  FAIL: {'; '.join(problems)}")
        except Exception as exc:  # noqa: BLE001 — report every repo even if one fails
            failures += 1
            print(f"  FAILED: {type(exc).__name__}: {exc}")
    if failures:
        print(f"\n{failures} repo(s) failed the layer check")
        return 1
    print("\nall repos pass the layer check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
