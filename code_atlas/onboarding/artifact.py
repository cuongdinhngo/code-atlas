"""Deterministic onboarding markdown + manifest from graph facts (task 088, M11).

Enrichment stays in 083–087 (metrics, layers, summaries, tour). This module is presentation:
headings, lists, and a JSON manifest. No SQL, no LLM, no language branch (R1.1/R1.4/R4).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from code_atlas.onboarding.layers import LayerAssignment, assign_layers, cross_layer_edges
from code_atlas.onboarding.metrics import GraphMetrics, compute_metrics, module_edges
from code_atlas.onboarding.summary import NodeFacts, Summarizer, summarize_modules
from code_atlas.onboarding.tour import TourStop, ordered_stops

H_OVERVIEW = "# Architecture overview"
H_SUMMARY = "## Summary"
H_LAYERS = "## Layers"
H_CROSSINGS = "## Cross-layer edges"
H_TOUR = "# Guided tour"
H_ORDER = "## Reading order"
H_ROLE = "## Role"
H_LAYER = "## Layer"
H_MODULE_SUMMARY = "## Summary"
H_IN_TOUR = "## In the tour"
H_NEIGHBOURS = "## Neighbours"

OUTPUT_DIR = "docs/onboarding"
OVERVIEW_NAME = "overview.md"
TOUR_NAME = "tour.md"
MANIFEST_NAME = "manifest.json"
PAGES_DIR = "modules"
CACHE_DIR = ".code-atlas/onboarding"
CACHE_NAME = "artifact.json"

__all__ = [
    "CACHE_DIR",
    "CACHE_NAME",
    "MANIFEST_NAME",
    "OVERVIEW_NAME",
    "PAGES_DIR",
    "TOUR_NAME",
    "H_CROSSINGS",
    "H_IN_TOUR",
    "H_LAYER",
    "H_LAYERS",
    "H_MODULE_SUMMARY",
    "H_NEIGHBOURS",
    "H_ORDER",
    "H_OVERVIEW",
    "H_ROLE",
    "H_SUMMARY",
    "H_TOUR",
    "LayerRow",
    "ModulePage",
    "OnboardingArtifact",
    "OUTPUT_DIR",
    "build_artifact",
    "manifest_dict",
    "page_relpath",
    "recorded_pages",
    "render_module",
    "render_overview",
    "render_tour",
]


@dataclass(frozen=True)
class LayerRow:
    """One overview layer: name, rank, size, and aggregated degrees."""

    layer: str
    rank: int
    modules: int
    fan_in: int
    fan_out: int
    entry_points: int


@dataclass(frozen=True)
class ModulePage:
    """One per-module markdown page, keyed by the module's file path."""

    file: str
    relpath: str
    layer: str
    rank: int
    role: str
    docline: str
    rationale: str
    scc: tuple[str, ...]
    index: int
    of: int
    outgoing: tuple[str, ...]
    incoming: tuple[str, ...]


@dataclass(frozen=True)
class OnboardingArtifact:
    """The structured onboarding document set: overview, tour, pages, manifest."""

    method: str
    truncated: bool
    summary: dict[str, object]
    layers: tuple[LayerRow, ...]
    crossings: tuple[tuple[str, str, int], ...]
    stops: tuple[TourStop, ...]
    pages: tuple[ModulePage, ...]

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict for the regenerable cache (R4.2)."""
        return {
            "crossings": [
                {"count": count, "source": source, "target": target}
                for source, target, count in self.crossings
            ],
            "layers": [
                {
                    "entry_points": row.entry_points,
                    "fan_in": row.fan_in,
                    "fan_out": row.fan_out,
                    "layer": row.layer,
                    "modules": row.modules,
                    "rank": row.rank,
                }
                for row in self.layers
            ],
            "method": self.method,
            "pages": [
                {
                    "docline": page.docline,
                    "file": page.file,
                    "incoming": list(page.incoming),
                    "index": page.index,
                    "layer": page.layer,
                    "outgoing": list(page.outgoing),
                    "rank": page.rank,
                    "rationale": page.rationale,
                    "relpath": page.relpath,
                    "role": page.role,
                    "scc": list(page.scc),
                    "of": page.of,
                }
                for page in self.pages
            ],
            "stops": [
                {"file": stop.file, "rationale": stop.rationale, "scc": list(stop.scc)}
                for stop in self.stops
            ],
            "summary": self.summary,
            "truncated": self.truncated,
        }


def page_relpath(file: str) -> str:
    """POSIX path of the module page under the onboarding dir; rejects ``..`` and absolutes."""
    rel = PurePosixPath(file)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"refusing onboarding page path {file!r}")
    return str(PurePosixPath(PAGES_DIR) / rel.with_name(rel.name + ".md"))


def _is_page_path(rel: str) -> bool:
    """Could this tool have written that path? Relative, inside ``modules/``, a ``.md`` file."""
    path = PurePosixPath(rel)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and len(path.parts) > 1
        and path.parts[0] == PAGES_DIR
        and path.suffix == ".md"
    )


def recorded_pages(manifest_text: str) -> tuple[str, ...]:
    """The page paths a previous ``manifest.json`` claims this tool wrote.

    Anything unparseable, foreign-shaped, or outside ``modules/*.md`` yields nothing: the
    writer deletes only what it can prove it wrote (050 — never destroy another's file).
    """
    try:
        data = json.loads(manifest_text)
    except ValueError:
        return ()
    modules = data.get("modules") if isinstance(data, dict) else None
    if not isinstance(modules, list):
        return ()
    pages = {
        entry["page"]
        for entry in modules
        if isinstance(entry, dict)
        and isinstance(entry.get("page"), str)
        and _is_page_path(entry["page"])
    }
    return tuple(sorted(pages))


def _layer_rows(metrics: GraphMetrics, assignment: LayerAssignment) -> tuple[LayerRow, ...]:
    """One row per layer, in the assignment's dependency order (rank 0 = most source-like)."""
    by_key = {metric.key: metric for metric in metrics.modules}
    entries = set(metrics.module_entry_points)
    rank: dict[str, int] = {}
    tallies: dict[str, list[int]] = {}
    for module in assignment.modules:
        rank.setdefault(module.layer, module.rank)
        metric = by_key[module.module]
        tally = tallies.setdefault(module.layer, [0, 0, 0, 0])
        tally[0] += 1
        tally[1] += metric.fan_in
        tally[2] += metric.fan_out
        tally[3] += 1 if module.module in entries else 0
    return tuple(
        LayerRow(
            layer=layer,
            rank=rank[layer],
            modules=tallies[layer][0],
            fan_in=tallies[layer][1],
            fan_out=tallies[layer][2],
            entry_points=tallies[layer][3],
        )
        for layer in assignment.layers
    )


def _neighbours(
    tour_edges: Sequence[tuple[str, str]],
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    """Adjacency at file grain over the budgeted tour subgraph, keys and neighbours sorted."""
    outgoing: dict[str, list[str]] = {}
    incoming: dict[str, list[str]] = {}
    for source, target in tour_edges:
        outgoing.setdefault(source, []).append(target)
        incoming.setdefault(target, []).append(source)
    out_sorted = {key: tuple(sorted(set(values))) for key, values in outgoing.items()}
    in_sorted = {key: tuple(sorted(set(values))) for key, values in incoming.items()}
    return out_sorted, in_sorted


def build_artifact(
    nodes: Sequence[tuple[str, str]],
    edges: Sequence[tuple[str, str]],
    tour_files: Sequence[str],
    tour_edges: Sequence[tuple[str, str]],
    entry_points: Sequence[str],
    truncated: bool,
    summarizer: Summarizer,
) -> OnboardingArtifact | None:
    """Compose 083–087 into one artifact. ``None`` when the index has no module."""
    metrics = compute_metrics(nodes, edges)
    if not metrics.modules:
        return None
    assignment = assign_layers(metrics)
    stops = ordered_stops(tour_files, tour_edges, entry_points)
    by_key = {metric.key: metric for metric in metrics.modules}
    placed = {module.module: module for module in assignment.modules}
    facts = [NodeFacts("", "", by_key[stop.file]) for stop in stops if stop.file in by_key]
    summaries = {summary.key: summary for summary in summarize_modules(facts, summarizer)}
    outgoing, incoming = _neighbours(tour_edges)
    pages: list[ModulePage] = []
    for index, stop in enumerate(stops, start=1):
        metric_row = placed.get(stop.file)
        summary = summaries.get(stop.file)
        if metric_row is None or summary is None:
            continue
        pages.append(
            ModulePage(
                file=stop.file,
                relpath=page_relpath(stop.file),
                layer=metric_row.layer,
                rank=metric_row.rank,
                role=summary.role,
                docline=summary.docline,
                rationale=stop.rationale,
                scc=stop.scc,
                index=index,
                of=len(stops),
                outgoing=outgoing.get(stop.file, ()),
                incoming=incoming.get(stop.file, ()),
            )
        )
    crossings = cross_layer_edges(module_edges(nodes, edges), assignment)
    return OnboardingArtifact(
        method=assignment.method,
        truncated=truncated,
        summary={
            "cross_layer_edges": len(crossings),
            "layers": len(assignment.layers),
            "method": assignment.method,
            "module_entry_points": len(metrics.module_entry_points),
            "modules": len(metrics.modules),
            "symbols": len(metrics.symbols),
        },
        layers=_layer_rows(metrics, assignment),
        crossings=tuple((edge.source, edge.target, edge.count) for edge in crossings),
        stops=stops,
        pages=tuple(pages),
    )


def render_overview(artifact: OnboardingArtifact) -> str:
    """Committed overview markdown: summary, layers, crossings. Trailing newline (R4.2)."""
    lines = [
        H_OVERVIEW,
        "",
        H_SUMMARY,
        "",
        f"- method: {artifact.method}",
        f"- layers: {artifact.summary['layers']}",
        f"- modules: {artifact.summary['modules']}",
        f"- symbols: {artifact.summary['symbols']}",
        f"- module entry points: {artifact.summary['module_entry_points']}",
        f"- cross-layer edges: {artifact.summary['cross_layer_edges']}",
        f"- module pages: {len(artifact.pages)}",
        f"- truncated: {'true' if artifact.truncated else 'false'}",
        "",
        H_LAYERS,
        "",
    ]
    for row in artifact.layers:
        lines.append(
            f"- rank {row.rank}: `{row.layer}` ({row.modules} modules, "
            f"fan_in {row.fan_in}, fan_out {row.fan_out}, "
            f"{row.entry_points} entry points)"
        )
    lines.extend(["", H_CROSSINGS, ""])
    if artifact.crossings:
        for source, target, count in artifact.crossings:
            lines.append(f"- `{source}` → `{target}` ({count})")
    else:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"


def render_tour(artifact: OnboardingArtifact) -> str:
    """Committed tour markdown: the dependency-ordered reading list. Trailing newline."""
    lines = [
        H_TOUR,
        "",
        f"truncated: {'true' if artifact.truncated else 'false'}",
        "",
        H_ORDER,
        "",
    ]
    if not artifact.stops:
        lines.append("- (none)")
    else:
        for index, stop in enumerate(artifact.stops, start=1):
            lines.append(f"{index}. `{stop.file}` — {stop.rationale}")
    return "\n".join(lines) + "\n"


def render_module(page: ModulePage) -> str:
    """One per-module page. Structure is fixed so CI can assert headings, not prose."""
    docline = page.docline if page.docline else "(none)"
    out = ", ".join(f"`{path}`" for path in page.outgoing) or "(none)"
    incoming = ", ".join(f"`{path}`" for path in page.incoming) or "(none)"
    lines = [
        f"# `{page.file}`",
        "",
        H_ROLE,
        "",
        page.role or "(none)",
        "",
        H_LAYER,
        "",
        page.layer,
        "",
        H_MODULE_SUMMARY,
        "",
        docline,
        "",
        H_IN_TOUR,
        "",
        f"Stop {page.index} of {page.of}. {page.rationale}",
        "",
        H_NEIGHBOURS,
        "",
        f"- outgoing: {out}",
        f"- incoming: {incoming}",
    ]
    return "\n".join(lines) + "\n"


def manifest_dict(artifact: OnboardingArtifact) -> dict[str, object]:
    """What the viewer (089) reads: relative paths + the tour order. No wall-clock (R4.2)."""
    return {
        "layers": [
            {
                "entry_points": row.entry_points,
                "fan_in": row.fan_in,
                "fan_out": row.fan_out,
                "layer": row.layer,
                "modules": row.modules,
                "rank": row.rank,
            }
            for row in artifact.layers
        ],
        "method": artifact.method,
        "modules": [
            {"file": page.file, "layer": page.layer, "page": page.relpath}
            for page in artifact.pages
        ],
        "overview": OVERVIEW_NAME,
        "stops": [
            {
                "file": stop.file,
                "page": page_relpath(stop.file),
                "rationale": stop.rationale,
            }
            for stop in artifact.stops
        ],
        "tour": TOUR_NAME,
        "truncated": artifact.truncated,
    }


def manifest_json(artifact: OnboardingArtifact) -> str:
    """Deterministic JSON for ``manifest.json``."""
    return json.dumps(manifest_dict(artifact), sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def cache_json(artifact: OnboardingArtifact) -> str:
    """Deterministic JSON for the gitignored regenerable cache."""
    return json.dumps(artifact.as_dict(), sort_keys=True, ensure_ascii=False, indent=2) + "\n"
