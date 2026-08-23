"""Deterministic onboarding markdown + manifest from graph facts (task 088, M11).

Enrichment stays in 083–087 (metrics, layers, summaries, tour). This module is presentation:
headings, lists, and a JSON manifest. No SQL, no LLM, no language branch (R1.1/R1.4/R4).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from code_atlas.onboarding.dataset import OnboardingDataset
from code_atlas.onboarding.layers import (
    IdentityLayerRefiner,
    LayerAssignment,
    LayerRefiner,
    assign_layers,
    cross_layer_edges,
    layer_description,
    layer_descriptions,
    refine_layers,
)
from code_atlas.onboarding.metrics import GraphMetrics, compute_metrics, module_edges
from code_atlas.onboarding.mirrors import find_mirror_subtrees
from code_atlas.onboarding.modules import COVERAGE_NOTE, find_business_modules
from code_atlas.onboarding.prose import ProseRun
from code_atlas.onboarding.reachability import classify_reachability
from code_atlas.onboarding.steps import TourStep, build_steps
from code_atlas.onboarding.summary import NodeFacts, Summarizer, summarize_modules
from code_atlas.onboarding.tour import TourStop, ordered_stops

H_OVERVIEW = "# Architecture overview"
H_SUMMARY = "## Summary"
H_MIRRORS = "## Mirror subtrees"
H_MODULES = "## Business modules"
H_REACHABILITY = "## Zero-inbound modules, by population"
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
VIEWER_NAME = "index.html"
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
    "VIEWER_NAME",
    "H_CROSSINGS",
    "H_IN_TOUR",
    "H_LAYER",
    "H_LAYERS",
    "H_MIRRORS",
    "H_MODULES",
    "H_MODULE_SUMMARY",
    "H_NEIGHBOURS",
    "H_ORDER",
    "H_OVERVIEW",
    "H_REACHABILITY",
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
    """One overview layer: name, description, rank, size, and aggregated degrees."""

    layer: str
    rank: int
    modules: int
    fan_in: int
    fan_out: int
    entry_points: int
    description: str


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
    fan_in: int
    fan_out: int


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
    steps: tuple[TourStep, ...] = ()
    """The narrative reading order: 5–15 grouped steps over the stops (task 111)."""
    isolated: tuple[str, ...] = ()
    """Modules a page would say nothing about: no edge either way, no summary (task 107)."""

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict for the regenerable cache (R4.2)."""
        return {
            "crossings": [
                {"count": count, "source": source, "target": target}
                for source, target, count in self.crossings
            ],
            "layers": [
                {
                    "description": row.description,
                    "entry_points": row.entry_points,
                    "fan_in": row.fan_in,
                    "fan_out": row.fan_out,
                    "layer": row.layer,
                    "modules": row.modules,
                    "rank": row.rank,
                }
                for row in self.layers
            ],
            "isolated": list(self.isolated),
            "method": self.method,
            "pages": [
                {
                    "docline": page.docline,
                    "fan_in": page.fan_in,
                    "fan_out": page.fan_out,
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
            "steps": [
                {
                    "covers": step.covers,
                    "cycle_size": step.cycle_size,
                    "modules": list(step.modules),
                    "order": step.order,
                    "title": step.title,
                    "why": step.why,
                }
                for step in self.steps
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
    """The page paths a previous ``manifest.json`` claims this tool wrote (task 112 ``pages`` key).

    Anything unparseable, foreign-shaped, or outside ``modules/*.md`` yields nothing: the
    writer deletes only what it can prove it wrote (050 — never destroy another's file).
    """
    try:
        data = json.loads(manifest_text)
    except ValueError:
        return ()
    pages = data.get("pages") if isinstance(data, dict) else None
    if not isinstance(pages, list):
        return ()
    kept = {page for page in pages if isinstance(page, str) and _is_page_path(page)}
    return tuple(sorted(kept))


def _layer_rows(
    metrics: GraphMetrics,
    assignment: LayerAssignment,
    described: Mapping[str, str] | None = None,
) -> tuple[LayerRow, ...]:
    """One row per layer, in the assignment's dependency order (rank 0 = most source-like).

    ``described`` is 117's already-resolved prose; a missing entry keeps 110's structural default,
    so a partially-enriched map is still a complete one.
    """
    prose = dict(described or {})
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
            description=prose.get(layer) or layer_description(layer),
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
    layer_refiner: LayerRefiner | None = None,
    *,
    max_results: int,
    declared_entry_points: Sequence[str] | None = None,
    declared_stub_roots: Sequence[str] | None = None,
    file_paths: Sequence[str] = (),
    file_class_counts: Sequence[tuple[str, int]] = (),
    prose: ProseRun | None = None,
) -> OnboardingArtifact | None:
    """Compose 083–087 into one artifact. ``None`` when the index has no module.

    ``declared_*`` are the operator's own ``entry_points``/``stub_roots`` — 113's highest-trust
    signal for the reachability split. Unset simply leaves those buckets to the path signal.

    ``prose`` is the 117 seam over the layer descriptions and the step narratives. Unset, both keep
    their structural defaults and this is byte-identical to the deterministic build (AC1).
    """
    metrics = compute_metrics(nodes, edges)
    if not metrics.modules:
        return None
    refiner: LayerRefiner = IdentityLayerRefiner() if layer_refiner is None else layer_refiner
    assignment = refine_layers(assign_layers(metrics), metrics, refiner)
    described = layer_descriptions(assignment, metrics, prose)
    stops = ordered_stops(tour_files, tour_edges, entry_points)
    by_key = {metric.key: metric for metric in metrics.modules}
    placed = {module.module: module for module in assignment.modules}
    facts = [NodeFacts("", "", by_key[stop.file]) for stop in stops if stop.file in by_key]
    summaries = {summary.key: summary for summary in summarize_modules(facts, summarizer)}
    outgoing, incoming = _neighbours(tour_edges)
    pages: list[ModulePage] = []
    isolated: list[str] = []
    for index, stop in enumerate(stops, start=1):
        metric_row = placed.get(stop.file)
        summary = summaries.get(stop.file)
        if metric_row is None or summary is None:
            continue
        degrees = by_key[stop.file]
        # No edge either way in the WHOLE graph and no summary: a page could only repeat the
        # path. Budget-cut neighbours are a different fact — that page stays and says so (107).
        if not summary.docline and not degrees.fan_in and not degrees.fan_out:
            isolated.append(stop.file)
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
                fan_in=degrees.fan_in,
                fan_out=degrees.fan_out,
            )
        )
    crossings = cross_layer_edges(module_edges(nodes, edges), assignment)
    # A capped neighbour or SCC list is a cut just like the walk budget's — one flag says so (108).
    list_truncated = any(
        len(page.outgoing) > max_results
        or len(page.incoming) > max_results
        or len(page.scc) > max_results
        for page in pages
    )
    artifact = OnboardingArtifact(
        method=assignment.method,
        truncated=truncated or list_truncated,
        summary={
            "cross_layer_edges": len(crossings),
            "layers": len(assignment.layers),
            "method": assignment.method,
            "module_entry_points": len(metrics.module_entry_points),
            "modules": len(metrics.modules),
            "mirrors": find_mirror_subtrees(
                file_paths or [metric.key for metric in metrics.modules],
                stub_roots=declared_stub_roots,
                sample_limit=max_results,
            ).as_dict(),
            "business_modules": find_business_modules(
                file_paths or [metric.key for metric in metrics.modules],
                class_counts=dict(file_class_counts),
                fan_in={metric.key: metric.fan_in for metric in metrics.modules},
                stub_roots=declared_stub_roots,
                limit=max_results,
            ).as_dict(),
            "reachability": classify_reachability(
                metrics,
                entry_points=declared_entry_points,
                stub_roots=declared_stub_roots,
                sample_limit=max_results,
            ).as_dict(),
            "symbols": len(metrics.symbols),
        },
        layers=_layer_rows(metrics, assignment, described),
        crossings=tuple((edge.source, edge.target, edge.count) for edge in crossings),
        stops=stops,
        pages=tuple(pages),
        steps=build_steps(
            stops,
            assignment,
            metrics,
            tour_edges,
            entry_points,
            prose=prose,
            docline_of={key: value.docline for key, value in summaries.items()},
            descriptions=described,
        ),
        isolated=tuple(sorted(isolated)),
    )
    # The gate refuses a filler or oversized artifact rather than write a bad tree (task 109, 050).
    from code_atlas.onboarding.quality_gate import check_artifact

    check_artifact(artifact, max_results=max_results)
    return artifact


def _mirror_lines(mirrors: object) -> list[str]:
    """Mirrored sibling subtrees, caveat first (task 115).

    The caveat leads, because the counts are about PATHS and a reader must not take them for proof
    that the files are copies. No pair renders an explicit "none detected" rather than an empty gap.
    """
    if not isinstance(mirrors, dict):
        return []
    lines = [H_MIRRORS, "", f"- {mirrors.get('caveat', '')}"]
    pairs = mirrors.get("pairs")
    for pair in pairs if isinstance(pairs, list) else []:
        lines.append(
            f"- `{pair['left']}` <-> `{pair['right']}`: {pair['shared']} shared paths "
            f"({pair['overlap']:.0%} overlap), {pair['left_only']} / {pair['right_only']} "
            "on one side only"
        )
    if not pairs:
        lines.append("- (no mirrored sibling subtrees detected)")
    lines.append("")
    return lines


def _module_lines(modules: object) -> list[str]:
    """The capability table with the coverage it does NOT claim (task 114).

    Coverage is printed before the rows, so a reader cannot take the table for the whole repo; a
    container refused for grouping by role is named with its reason instead of vanishing (AC5).
    """
    if not isinstance(modules, dict):
        return []
    cover = modules.get("coverage", {})
    lines = [
        H_MODULES,
        "",
        f"- coverage: {cover.get('covered', 0)} of {cover.get('total', 0)} indexed files "
        f"({cover.get('percent', 0.0)} %); {cover.get('excluded', 0)} excluded "
        "as vendored or test code",
        f"  - {COVERAGE_NOTE}",
    ]
    rows = modules.get("modules")
    for row in rows if isinstance(rows, list) else []:
        flag = " — **only tree**" if row.get("single_tree") else ""
        lines.append(
            f"- `{row['module']}`: {row['files']} files, {row['classes']} classes, "
            f"trees {', '.join(row['trees'])}{flag}"
        )
        if row.get("hub"):
            lines.append(f"  - busiest file: `{row['hub']}` (fan_in {row['hub_fan_in']})")
    if not rows:
        lines.append("- (no capability layout found)")
    refused = modules.get("refused")
    for entry in refused if isinstance(refused, list) else []:
        lines.append(f"- refused `{entry['container']}`: {entry['reason']}")
    lines.append("")
    return lines


def _reachability_lines(split: object) -> list[str]:
    """The zero-inbound split as its own section — never one number (task 113).

    Every bucket renders, including an empty one (an honest zero — AC4); a bucket the classifier
    could not fill renders in a ``dropped`` list with its reason, not as a zero (AC5).
    """
    if not isinstance(split, dict):
        return []
    total = split.get("total", 0)
    lines = [H_REACHABILITY, "", f"- zero-inbound modules (raw total): {total}", ""]
    buckets = split.get("buckets")
    for bucket in buckets if isinstance(buckets, list) else []:
        cut = " (sample capped)" if bucket.get("sample_truncated") else ""
        lines.append(f"- **{bucket['label']}**: {bucket['count']}{cut}")
        lines.append(f"  - {bucket['note']}")
        lines.append(f"  - signal: {bucket['signal']}")
        tally = bucket.get("signals")
        if isinstance(tally, dict) and any(tally.values()):
            named = ", ".join(f"{count} {name}" for name, count in tally.items() if count)
            lines.append(f"  - by signal: {named}")
    dropped = split.get("dropped")
    for row in dropped if isinstance(dropped, list) else []:
        lines.append(f"- **{row['bucket']}**: not reported — {row['reason']}")
    # 119: what each declaration matched, beside what it claimed. The caveat rides with them.
    caveat = split.get("caveat")
    if isinstance(caveat, str) and caveat:
        lines.extend(["", f"- {caveat}"])
    patterns = split.get("patterns")
    for claim in patterns if isinstance(patterns, list) else []:
        lines.append(
            f"  - `{claim['pattern']}` ({claim['kind']}): matches {claim['files_matched']} "
            f"indexed files, claims {claim['zero_inbound_claimed']} of the modules above"
        )
    lines.append("")
    return lines


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
        f"- cross-layer edges: {artifact.summary['cross_layer_edges']}",
        f"- module pages: {len(artifact.pages)}",
        f"- modules with no page (isolated, no summary): {len(artifact.isolated)}",
        f"- truncated: {'true' if artifact.truncated else 'false'}",
        "",
    ]
    lines.extend(_mirror_lines(artifact.summary.get("mirrors")))
    lines.extend(_module_lines(artifact.summary.get("business_modules")))
    lines.extend(_reachability_lines(artifact.summary.get("reachability")))
    lines.extend([H_LAYERS, ""])
    for row in artifact.layers:
        lines.append(
            f"- rank {row.rank}: `{row.layer}` ({row.modules} modules, "
            f"fan_in {row.fan_in}, fan_out {row.fan_out}, "
            f"{row.entry_points} entry points)"
        )
        lines.append(f"  - {row.description}")
    lines.extend(["", H_CROSSINGS, ""])
    if artifact.crossings:
        for source, target, count in artifact.crossings:
            lines.append(f"- `{source}` → `{target}` ({count})")
    else:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"


def render_tour(artifact: OnboardingArtifact, max_results: int) -> str:
    """Committed tour markdown: 5–15 narrative steps (task 111). Every number is interpolated (AC6).

    A step names up to five modules and states how many it covers, so a cycle is one line stating
    its size rather than one line per member (the pre-111 500-stop dump). Trailing newline (R4.2).
    """
    lines = [
        H_TOUR,
        "",
        f"truncated: {'true' if artifact.truncated else 'false'}",
        "",
        H_ORDER,
        "",
    ]
    if not artifact.steps:
        lines.append("- (none)")
    else:
        for step in artifact.steps:
            lines.append(f"{step.order}. **{step.title}** — {step.why}")
            named = ", ".join(f"`{module}`" for module in step.modules)
            lines.append(f"   - {named} ({len(step.modules)} of {step.covers})")
    return "\n".join(lines) + "\n"


def _absent(degree: int) -> str:
    """An empty neighbour list is either a real zero or the budget's doing — say which (102)."""
    if degree:
        return f"(none admitted in this tour; {degree} in the full graph)"
    return "(none)"


def _shown_suffix(shown: int, total: int) -> str:
    """Name a cut list with both numbers so it is never read as the whole truth (033/057/107)."""
    return f" ({shown} shown of {total})" if total > shown else ""


def _neighbour_line(paths: tuple[str, ...], degree: int, max_results: int) -> str:
    """A neighbour list capped at ``max_results``; an empty one keeps 107's ``_absent`` wording."""
    if not paths:
        return _absent(degree)
    shown = paths[:max_results]
    return ", ".join(f"`{path}`" for path in shown) + _shown_suffix(len(shown), len(paths))


def _rationale_line(rationale: str, scc: tuple[str, ...], max_results: int) -> str:
    """Cap the SCC list a cycle rationale repeats on every member; identical per member (R4.2)."""
    if len(scc) <= 1:
        return rationale
    shown = scc[:max_results]
    return "cycle with " + ", ".join(shown) + _shown_suffix(len(shown), len(scc))


def render_module(page: ModulePage, max_results: int) -> str:
    """One per-module page. Structure is fixed so CI can assert headings, not prose."""
    docline = page.docline if page.docline else "(none)"
    out = _neighbour_line(page.outgoing, page.fan_out, max_results)
    incoming = _neighbour_line(page.incoming, page.fan_in, max_results)
    rationale = _rationale_line(page.rationale, page.scc, max_results)
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
        f"Stop {page.index} of {page.of}. {rationale}",
        "",
        H_NEIGHBOURS,
        "",
        f"- outgoing: {out}",
        f"- incoming: {incoming}",
    ]
    return "\n".join(lines) + "\n"


def manifest_dict(
    artifact: OnboardingArtifact, dataset: OnboardingDataset
) -> dict[str, object]:
    """The one committed machine-readable artifact: the aggregate dataset (task 112) plus this
    run's operational record — the page paths written (the 050 delete-record) and the doc
    pointers. Reduced to the dataset: the per-module dump is gone. No wall-clock (R4.2/AC2)."""
    return {
        **dataset.as_dict(),
        "overview": OVERVIEW_NAME,
        "pages": sorted(page.relpath for page in artifact.pages),
        "tour": TOUR_NAME,
        "truncated": artifact.truncated,
        "viewer": VIEWER_NAME,
    }


def manifest_json(artifact: OnboardingArtifact, dataset: OnboardingDataset) -> str:
    """Deterministic JSON for ``manifest.json``."""
    return (
        json.dumps(manifest_dict(artifact, dataset), sort_keys=True, ensure_ascii=False, indent=2)
        + "\n"
    )


def cache_json(artifact: OnboardingArtifact) -> str:
    """Deterministic JSON for the gitignored regenerable cache."""
    return json.dumps(artifact.as_dict(), sort_keys=True, ensure_ascii=False, indent=2) + "\n"
