#!/usr/bin/env python3
"""Emit committed layer-graph mermaid for the pinned public repos (task 143 AC6).

Not part of per-PR CI — clones + indexes each pin. Writes
``docs/benchmarks/143_layer_diagrams.md``:

    scripts/docker-test.sh python scripts/layer_diagram_report.py
    python scripts/layer_diagram_report.py --cached   # reuse artifacts/cross-repo-cache indexes
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.onboarding.layer_diagram import (  # noqa: E402
    diagram_edges,
    module_edge_tiers,
    render_layer_flowchart,
    validate_mermaid_flowchart,
)
from code_atlas.onboarding.layers import assign_layers  # noqa: E402
from code_atlas.onboarding.metrics import compute_metrics  # noqa: E402
from code_atlas.store import GraphStore  # noqa: E402
from scripts.cross_repo_validate import checkout_pinned, index_root, load_manifest  # noqa: E402

_OUT = _REPO / "docs" / "benchmarks" / "143_layer_diagrams.md"


def main() -> int:
    cached = "--cached" in sys.argv
    cache_root = _REPO / "artifacts" / "cross-repo-cache"
    chunks: list[str] = [
        "# 143 — layer graphs of the pinned public repos",
        "",
        "Generated from `scripts/layer_diagram_report.py` against "
        "`scripts/cross_repo_samples.json`. HEURISTIC-only arrows are dashed.",
        "",
    ]
    failures = 0
    for sample in load_manifest():
        sid = str(sample["id"])
        sha = str(sample["sha"])[:7]
        owner = sample["owner"]
        repo = sample["repo"]
        heading = f"## `{owner}/{repo}` @ `{sha}`"
        print(f"\n### {sid} @ {sha}")
        try:
            root = cache_root / sid
            if not cached:
                root = checkout_pinned(sample, cache_root)
                index_root(root)
            db = root / ".code-atlas" / "graph.db"
            if not db.is_file():
                raise FileNotFoundError(f"no index at {db}")
            with GraphStore(db) as store:
                nodes = store.node_universe()
                tiers = store.dependency_edges_with_tier()
            edges = [(source, target) for source, target, _tier in tiers]
            assignment = assign_layers(compute_metrics(nodes, edges))
            drawn, omitted = diagram_edges(module_edge_tiers(nodes, tiers), assignment)
            diagram = render_layer_flowchart(
                assignment.layers, drawn, node_cap=50, omitted_dynamic=omitted
            )
            validate_mermaid_flowchart(diagram.mermaid)
            print(
                f"  layers={diagram.shown_layers}/{diagram.total_layers} "
                f"arrows={len(drawn)} omitted_dynamic={omitted}"
            )
            chunks.extend(
                [
                    heading,
                    "",
                    f"- layers: {diagram.shown_layers} shown of {diagram.total_layers}",
                    f"- DYNAMIC-only crossings omitted: {diagram.omitted_dynamic}",
                    "",
                    "```mermaid",
                    diagram.mermaid.rstrip(),
                    "```",
                    "",
                ]
            )
        except Exception as exc:  # noqa: BLE001 — report every repo even if one fails
            failures += 1
            print(f"  FAILED: {type(exc).__name__}: {exc}")
    if failures:
        print(f"\n{failures} repo(s) failed the layer-diagram emit")
        return 1
    _OUT.write_text("\n".join(chunks), encoding="utf-8")
    print(f"\nwrote {_OUT.relative_to(_REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
