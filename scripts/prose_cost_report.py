#!/usr/bin/env python3
"""Print + CHECK what the 117 prose seam costs — AC5's evidence.

AC5 asks for the number of calls and tokens for a cold build and for a warm cache, and for a per-run
ceiling that is enforced rather than asserted. Calls are countable **without a model**: the seam is
deterministic, so a counting writer over the real pipeline gives the exact figure. Tokens are not
countable without a tokenizer, so this prints the exact prompt **bytes** and a clearly-labelled
char/4 ESTIMATE — never a number pretending to be a measurement. Pass a live model with
``CA_PROSE_LIVE=1`` to replace the estimate with the API's own usage.

The synthetic row is the point of the report: the ceiling is structural, so an anchor-scale repo
costs the same as a small one. Not part of per-PR CI — run locally or in Docker:

    scripts/docker-test.sh python scripts/prose_cost_report.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.onboarding.artifact import build_artifact  # noqa: E402
from code_atlas.onboarding.dataset import build_dataset  # noqa: E402
from code_atlas.onboarding.prose import (  # noqa: E402
    MAX_PROSE_CALLS,
    SLOT_LIMITS,
    ProseRequest,
    ProseRun,
)
from code_atlas.onboarding.summary import StructuralSummarizer  # noqa: E402
from code_atlas.store import GraphStore  # noqa: E402
from scripts.cross_repo_validate import (  # noqa: E402
    checkout_pinned,
    index_root,
    load_manifest,
)

# The estimator's divisor. Labelled everywhere it is printed: an estimate is not a measurement.
CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class Census:
    """Everything one build needs, as the store would actually hand it over."""

    nodes: list[tuple[str, str]]
    edges: list[tuple[str, str]]
    paths: list[str]
    node_kinds: list[tuple[str, int]]
    edge_kinds: list[tuple[str, int]]
    confidence: dict[str, int]
    hubs: list[tuple[str, int, int]]


class CountingWriter:
    """A writer that answers every slot and records what a real model would have been sent."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def write(self, request: ProseRequest) -> str:
        from onboarding_llm.prose import prompt

        body = prompt(request)
        self.calls.append((request.slot, len(body.encode("utf-8"))))
        return (
            f"A written sentence for the {request.slot} slot that adds wording of its own "
            "without restating any name it was given."
        )


def measure(label: str, census: Census, subgraph, *, limits=None) -> tuple[str, int, int]:
    """Cold then warm: the same build twice through one run, so the second pays nothing.

    ``census`` carries the real store rows, not empty lists: a headline family only fires when its
    precondition holds, so a degenerate census would report a cost the seam never actually has.
    """
    nodes, edges, paths = census.nodes, census.edges, census.paths
    writer = CountingWriter()
    run = ProseRun(writer, limits=limits)
    build_artifact(
        nodes, edges, subgraph[0], subgraph[1], subgraph[2], False,
        StructuralSummarizer(), max_results=50, file_paths=paths, prose=run,
    )
    build_dataset(
        nodes, edges, files=len(paths), parsed=len(paths),
        node_kind_counts=census.node_kinds, edge_kind_counts=census.edge_kinds,
        confidence=census.confidence, hubs=census.hubs, classes=[],
        file_symbol_counts=[(path, 1) for path in paths], file_paths=paths,
        path_index_max=20000, module_max=50, mirror_sample_max=50,
        reachability_sample_max=50, prose=run,
    )
    cold = run.calls
    by_slot: dict[str, int] = {}
    prompt_bytes = 0
    for slot, size in writer.calls:
        by_slot[slot] = by_slot.get(slot, 0) + 1
        prompt_bytes += size
    # A second identical build against the SAME run is entirely memo hits — the warm case.
    build_dataset(
        nodes, edges, files=len(paths), parsed=len(paths),
        node_kind_counts=census.node_kinds, edge_kind_counts=census.edge_kinds,
        confidence=census.confidence, hubs=census.hubs, classes=[],
        file_symbol_counts=[(path, 1) for path in paths], file_paths=paths,
        path_index_max=20000, module_max=50, mirror_sample_max=50,
        reachability_sample_max=50, prose=run,
    )
    warm = run.calls - cold
    mix = ", ".join(f"{slot} {count}" for slot, count in sorted(by_slot.items()))
    print(
        f"  {label}: cold {cold} calls ({mix}); warm {warm} calls; "
        f"{prompt_bytes} prompt bytes ~ {prompt_bytes // CHARS_PER_TOKEN} tokens ESTIMATED "
        f"(char/{CHARS_PER_TOKEN}, not a measurement); declined by the ceiling: {run.declined}"
    )
    return label, cold, warm


def synthetic(count: int, *, roles: tuple[str, ...] | None = None) -> Census:
    """An anchor-scale graph. With ``roles`` unset the paths name no responsibility, so 084 falls
    back to per-directory layers — the unbounded case the ceiling exists for."""
    named = roles or ()
    paths = sorted(
        (
            f"tree{index % 6}/{named[index % len(named)]}/part{index % 400:04d}/Unit{index:05d}.aa"
            if named
            else f"group{index % 400:04d}/part{index % 40:03d}/Unit{index:05d}.aa"
        )
        for index in range(count)
    )
    nodes = [(f"N{index}", path) for index, path in enumerate(paths)]
    edges = [(f"N{index}", f"N{(index * 7 + 1) % len(nodes)}") for index in range(len(nodes))]
    return Census(
        nodes=nodes,
        edges=edges,
        paths=paths,
        node_kinds=[("Class", count), ("Method", count * 6), ("Function", count)],
        edge_kinds=[("CALLS", len(edges))],
        confidence={"EXACT": len(edges) - len(edges) // 3, "HEURISTIC": len(edges) // 3},
        hubs=[(paths[0], 40, 2)],
    )


VOCABULARY = ("controller", "service", "model", "view", "middleware", "job",
              "report", "lib", "test", "config", "vendor")


def main() -> int:
    print(f"per-slot ceilings: {dict(sorted(SLOT_LIMITS.items()))}  total {MAX_PROSE_CALLS}")
    rows: list[tuple[str, int, int]] = []
    cache_root = _REPO / "artifacts" / "cross-repo-cache"
    print("\n### pinned public repos")
    for sample in load_manifest():
        label = f"{sample['id']} @ {str(sample['sha'])[:7]}"
        root = checkout_pinned(sample, cache_root)
        index_root(root)
        with GraphStore(root / ".code-atlas" / "graph.db") as store:
            census = Census(
                nodes=list(store.node_universe()),
                edges=list(store.dependency_edges()),
                paths=list(store.file_paths()),
                node_kinds=list(store.node_kind_counts()),
                edge_kinds=list(store.edge_kind_counts()),
                confidence=dict(store.edge_health()["by_tier"]),  # type: ignore[arg-type]
                hubs=list(store.module_hubs(limit=50)),
            )
            sub = store.tour_subgraph(max_nodes=2000)
        rows.append(measure(label, census, (sub.files, sub.edges, sub.entry_points)))
    print("\n### anchor-scale synthetic — the ceiling is structural, so size does not move it")
    named = synthetic(18929, roles=VOCABULARY)
    rows.append(measure(f"{len(named.paths)} files, named layers", named,
                        (named.paths[:2000], [], named.paths[:1])))
    print("\n### the unbounded case the ceiling exists for: paths that name no responsibility")
    flat = synthetic(18929)
    rows.append(measure(f"{len(flat.paths)} files, per-directory layers", flat,
                        (flat.paths[:2000], [], flat.paths[:1])))
    failures = [label for label, cold, _ in rows if cold > MAX_PROSE_CALLS]
    if failures:
        print(f"\nFAIL: {', '.join(failures)} exceeded the {MAX_PROSE_CALLS}-call ceiling")
        return 1
    print(f"\nevery build stayed inside the {MAX_PROSE_CALLS}-call ceiling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
