#!/usr/bin/env python3
"""Measure the narrative tour on the pinned public repos — the AC5 evidence for task 111.

`render_tour` used to emit one line per budgeted module (500 stops / 6.3 MB on the anchor). 111
groups those stops into 5–15 steps. This script clones + indexes each pin (reusing task 018's
harness, like `layer_report.py`), builds the artifact, and prints the before/after the ticket asks
for: the stop count (the old deliverable), the step count, `tour.md` bytes new vs the old flat
render, and how many modules each step covers. Not part of per-PR CI — run locally or in Docker
(needs php + network):

    scripts/docker-test.sh python scripts/tour_report.py

The anchor monorepo is absent on the dev host, so its row is an operator run (108/015 precedent).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.onboarding.artifact import (  # noqa: E402
    H_ORDER,
    H_TOUR,
    build_artifact,
    render_tour,
)
from code_atlas.onboarding.summary import StructuralSummarizer  # noqa: E402
from code_atlas.store import GraphStore  # noqa: E402
from scripts.cross_repo_validate import (  # noqa: E402
    checkout_pinned,
    index_root,
    load_manifest,
)

_MAX_RESULTS = 50
_TOUR_KB_CEILING = 64  # AC5: tour.md must stay under 64 KB (measured against the anchor).


def _flat_bytes(stops: tuple, max_results: int) -> int:
    """Bytes the pre-111 one-line-per-stop render would have produced (the 'before')."""
    from code_atlas.onboarding.artifact import _rationale_line

    lines = [H_TOUR, "", "truncated: false", "", H_ORDER, ""]
    for index, stop in enumerate(stops, start=1):
        rationale = _rationale_line(stop.rationale, stop.scc, max_results)
        lines.append(f"{index}. `{stop.file}` — {rationale}")
    return len(("\n".join(lines) + "\n").encode("utf-8"))


def _report(sid: str) -> tuple[str, bool]:
    """One repo's line, and whether it stayed under the tour byte ceiling."""
    cache_root = _REPO / "artifacts" / "cross-repo-cache"
    sample = next(s for s in load_manifest() if str(s["id"]) == sid)
    root = checkout_pinned(sample, cache_root)
    index_root(root)
    with GraphStore(root / ".code-atlas" / "graph.db") as store:
        nodes = store.node_universe()
        edges = store.dependency_edges()
        subgraph = store.tour_subgraph(max_nodes=1000)
    artifact = build_artifact(
        nodes, edges, subgraph.files, subgraph.edges, subgraph.entry_points,
        subgraph.truncated, StructuralSummarizer(), max_results=_MAX_RESULTS,
    )
    if artifact is None:
        return "  (no module — nothing to tour)", True
    new_bytes = len(render_tour(artifact, _MAX_RESULTS).encode("utf-8"))
    old_bytes = _flat_bytes(artifact.stops, _MAX_RESULTS)
    covers = ", ".join(str(step.covers) for step in artifact.steps)
    under = new_bytes < _TOUR_KB_CEILING * 1024
    line = (
        f"  stops={len(artifact.stops)}  steps={len(artifact.steps)}\n"
        f"  tour.md bytes: {old_bytes} (flat) -> {new_bytes} (steps)  "
        f"under {_TOUR_KB_CEILING}KB: {under}\n"
        f"  covers per step: {covers}"
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
                print(f"  FAIL: tour.md is not under {_TOUR_KB_CEILING} KB")
        except Exception as exc:  # noqa: BLE001 — report every repo even if one fails
            failures += 1
            print(f"  FAILED: {type(exc).__name__}: {exc}")
    if failures:
        print(f"\n{failures} repo(s) failed the tour check")
        return 1
    print("\nall repos pass the tour check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
