"""Deterministic onboarding markdown + manifest from graph facts (task 088, M11).

Enrichment stays in 083–087 (metrics, layers, summaries, tour). This module is presentation:
headings, lists, and a JSON manifest. No SQL, no LLM, no language branch (R1.1/R1.4/R4).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from code_atlas.onboarding.dataset import OnboardingDataset
from code_atlas.onboarding.flows import COVERAGE_NOTE as FLOW_COVERAGE_NOTE
from code_atlas.onboarding.flows import TRUNCATED_NOTE as FLOW_TRUNCATED_NOTE
from code_atlas.onboarding.layer_diagram import (
    RESOLVED,
    DiagramEdge,
    diagram_edges,
    module_edge_tiers,
    render_layer_flowchart,
    validate_mermaid_flowchart,
)
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
from code_atlas.onboarding.metrics import GraphMetrics, NodeMetric, compute_metrics, module_edges
from code_atlas.onboarding.mirrors import find_mirror_subtrees
from code_atlas.onboarding.module_facts import module_facts
from code_atlas.onboarding.modules import COVERAGE_NOTE, find_business_modules
from code_atlas.onboarding.prose import ProseRun
from code_atlas.onboarding.reachability import classify_reachability
from code_atlas.onboarding.scope import scoped_paths
from code_atlas.onboarding.steps import TourStep, build_steps
from code_atlas.onboarding.summary import NodeFacts, Summarizer, summarize_modules
from code_atlas.onboarding.tour import TourStop, ordered_stops
from code_atlas.store import Row

H_OVERVIEW = "# Architecture overview"
H_SUMMARY = "## Summary"
H_MIRRORS = "## Mirror subtrees"
H_MODULES = "## Business modules"
H_REACHABILITY = "## Zero-inbound modules, by population"
H_LAYERS = "## Layers"
H_DIAGRAM = "## Layer graph"
H_CROSSINGS = "## Cross-layer edges"
H_TOUR = "# Guided tour"
H_ORDER = "## Reading order"
OUTPUT_DIR = "docs/onboarding"
OVERVIEW_NAME = "overview.md"
TOUR_NAME = "tour.md"
FLOWS_NAME = "flows.md"
MANIFEST_NAME = "manifest.json"
VIEWER_NAME = "index.html"
PAGES_DIR = "modules"
CACHE_DIR = ".code-atlas/onboarding"
CACHE_NAME = "artifact.json"
# Shape of artifact.json (145). Not contract_version and not DATASET_VERSION: this file is the
# tour/steps object graph a second renderer would read. Bump when as_dict keys change;
# tests/test_artifact_contract.py fails a shape change that leaves the number behind.
# 1 -> 2 (205): the `pages` and `isolated` keys are gone with the module-page tree.
# 2 -> 3 (208): every reachability bucket gains `caveat` and `declaration`.
ARTIFACT_VERSION = 3

__all__ = [
    "ARTIFACT_VERSION",
    "CACHE_DIR",
    "CACHE_NAME",
    "MANIFEST_NAME",
    "OVERVIEW_NAME",
    "PAGES_DIR",
    "TOUR_NAME",
    "VIEWER_NAME",
    "H_CROSSINGS",
    "H_DIAGRAM",
    "H_LAYERS",
    "H_MIRRORS",
    "H_MODULES",
    "H_ORDER",
    "H_OVERVIEW",
    "H_REACHABILITY",
    "H_SUMMARY",
    "H_TOUR",
    "LayerRow",
    "OnboardingArtifact",
    "OUTPUT_DIR",
    "build_artifact",
    "FLOWS_NAME",
    "manifest_dict",
    "render_flows",
    "recorded_pages",
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
class OnboardingArtifact:
    """The structured onboarding document set: overview, tour, pages, manifest."""

    method: str
    truncated: bool
    summary: dict[str, object]
    layers: tuple[LayerRow, ...]
    crossings: tuple[tuple[str, str, int], ...]
    stops: tuple[TourStop, ...]
    steps: tuple[TourStep, ...] = ()
    """The narrative reading order: 5–15 grouped steps over the stops (task 111)."""
    diagram_edges: tuple[DiagramEdge, ...] = ()
    omitted_dynamic: int = 0

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict for the versioned ``artifact.json`` contract (R4.2 / 145)."""
        return {
            "crossings": [
                {"count": count, "source": source, "target": target}
                for source, target, count in self.crossings
            ],
            "diagram_edges": [
                {
                    "count": edge.count,
                    "heuristic_only": edge.heuristic_only,
                    "source": edge.source,
                    "target": edge.target,
                }
                for edge in self.diagram_edges
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
            "method": self.method,
            "omitted_dynamic": self.omitted_dynamic,
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
            "version": ARTIFACT_VERSION,
        }


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
    """The page paths a **pre-205** ``manifest.json`` claims this tool wrote (112's ``pages`` key).

    205 stopped writing per-module pages, and this is how a tree written before it is cleaned: the
    next write removes exactly the pages the previous manifest recorded, and nothing else (R5.7).
    Anything unparseable, foreign-shaped, or outside ``modules/*.md`` yields nothing.
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


def _module_facts(
    root: Path | None,
    file_nodes: Mapping[str, Sequence[Row]] | None,
    path: str,
    metric: NodeMetric,
) -> NodeFacts:
    """Read-through when ``root`` and ``file_nodes`` are set; else the pre-118 empty stub."""
    if root is not None and file_nodes is not None:
        return module_facts(root, path, metric, file_nodes.get(path, ()))
    return NodeFacts("", "", metric)


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
    working_roots: Sequence[str] | None = None,
    file_paths: Sequence[str] = (),
    file_class_counts: Sequence[tuple[str, int]] = (),
    prose: ProseRun | None = None,
    root: Path | None = None,
    file_nodes: Mapping[str, Sequence[Row]] | None = None,
    edge_tiers: Sequence[tuple[str, str, str]] | None = None,
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
    facts = [
        _module_facts(root, file_nodes, stop.file, by_key[stop.file])
        for stop in stops
        if stop.file in by_key
    ]
    summaries = {summary.key: summary for summary in summarize_modules(facts, summarizer)}
    crossings = cross_layer_edges(module_edges(nodes, edges), assignment)
    if edge_tiers is None:
        tiers = tuple((source, target, RESOLVED) for source, target in module_edges(nodes, edges))
    else:
        tiers = module_edge_tiers(nodes, edge_tiers)
    drawn, omitted_dynamic = diagram_edges(tiers, assignment)
    artifact = OnboardingArtifact(
        method=assignment.method,
        truncated=truncated,
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
                working_roots=working_roots,
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
        diagram_edges=drawn,
        omitted_dynamic=omitted_dynamic,
    )
    # The gate refuses a filler artifact rather than write a bad tree (task 109, 050).
    from code_atlas.onboarding.quality_gate import check_artifact

    check_artifact(artifact)
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
        # 198: the label is what a reader sees; the directory stays beside it, because a renamed
        # capability a reader cannot grep for would be worse than the bare path it replaced.
        label = row.get("label") or row["module"]
        named = (
            f"**{label}** (`{row['module']}`)" if label != row["module"]
            else f"`{row['module']}`"
        )
        lines.append(
            f"- {named}: {row['files']} files, {row['classes']} classes, "
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
    could not fill renders in a ``dropped`` list with its reason, not as a zero (AC5). An empty
    bucket whose own declaration was never given carries the classifier's caveat beside its count,
    because that 0 answers a question nobody asked (208).
    """
    if not isinstance(split, dict):
        return []
    total = split.get("total", 0)
    lines = [H_REACHABILITY, "", f"- zero-inbound modules (raw total): {total}", ""]
    buckets = split.get("buckets")
    for bucket in buckets if isinstance(buckets, list) else []:
        cut = " (sample capped)" if bucket.get("sample_truncated") else ""
        lines.append(f"- **{bucket['label']}**: {bucket['count']}{cut}")
        # 208: where the count is, so a 0 nobody asked for cannot read as a measured absence. The
        # words are the classifier's; this renderer adds none of its own (R1.8).
        unasked = bucket.get("caveat")
        if isinstance(unasked, str) and unasked:
            lines.append(f"  - **{unasked}**")
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


def render_overview(
    artifact: OnboardingArtifact,
    node_cap: int | None = None,
    *,
    file_paths: Sequence[str] = (),
    working_roots: Sequence[str] | None = None,
) -> str:
    """Committed overview markdown: summary, layers, layer graph, crossings. Trailing newline."""
    cap = node_cap if node_cap is not None else max(len(artifact.layers), 1)
    diagram = render_layer_flowchart(
        [row.layer for row in artifact.layers],
        artifact.diagram_edges,
        node_cap=cap,
        omitted_dynamic=artifact.omitted_dynamic,
    )
    lines = [
        H_OVERVIEW,
        "",
        H_SUMMARY,
        "",
        *_scope_bullets(file_paths, working_roots),
        f"- method: {artifact.method}",
        f"- layers: {artifact.summary['layers']}",
        f"- modules: {artifact.summary['modules']}",
        f"- symbols: {artifact.summary['symbols']}",
        f"- cross-layer edges: {artifact.summary['cross_layer_edges']}",
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
    lines.extend(["", H_DIAGRAM, ""])
    lines.append(
        f"- layers: {diagram.shown_layers} shown of {diagram.total_layers}"
        + ("; the graph is capped" if diagram.truncated else "")
    )
    lines.append(
        "- HEURISTIC-only arrows are dashed; "
        f"DYNAMIC-only crossings omitted: {diagram.omitted_dynamic}"
    )
    if diagram.omitted_capped:
        lines.append(
            f"- crossings with no arrow because their layer is outside the cap: "
            f"{diagram.omitted_capped} — the table below still lists them"
        )
    # AC5's check guards the committed artifact, not only the benchmark script.
    validate_mermaid_flowchart(diagram.mermaid)
    lines.extend(["", "```mermaid", diagram.mermaid.rstrip(), "```"])
    lines.extend(["", H_CROSSINGS, ""])
    if artifact.crossings:
        for source, target, count in artifact.crossings:
            lines.append(f"- `{source}` → `{target}` ({count})")
    else:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"


def render_tour(
    artifact: OnboardingArtifact,
    max_results: int,
    *,
    file_paths: Sequence[str] = (),
    working_roots: Sequence[str] | None = None,
) -> str:
    """Committed tour markdown: 5–15 narrative steps (task 111). Every number is interpolated (AC6).

    A step names up to five modules and states how many it covers, so a cycle is one line stating
    its size rather than one line per member (the pre-111 500-stop dump). Trailing newline (R4.2).
    """
    lines = [
        H_TOUR,
        "",
        *_scope_bullets(file_paths, working_roots),
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


def _scope_bullets(file_paths: Sequence[str], roots: Sequence[str] | None) -> list[str]:
    """Empty when unset, so today's markdown stays byte-identical (AC4)."""
    if not roots:
        return []
    named = ", ".join(str(root) for root in roots)
    return [
        f"- scope: working_roots={named} "
        f"({len(scoped_paths(file_paths, roots))} of {len(file_paths)} indexed files)",
        "",
    ]


def _shown_suffix(shown: int, total: int) -> str:
    """Name a cut list with both numbers so it is never read as the whole truth (033/057/107)."""
    return f" ({shown} shown of {total})" if total > shown else ""


def _rationale_line(rationale: str, scc: tuple[str, ...], max_results: int) -> str:
    """Cap the SCC list a cycle rationale repeats on every member; identical per member (R4.2)."""
    if len(scc) <= 1:
        return rationale
    shown = scc[:max_results]
    return "cycle with " + ", ".join(shown) + _shown_suffix(len(shown), len(scc))


def render_flows(
    dataset: OnboardingDataset,
    *,
    file_paths: Sequence[str] = (),
    working_roots: Sequence[str] | None = None,
) -> str:
    """``flows.md`` — one capability trace per section, each with its own mermaid diagram (197).

    One diagram PER FLOW rather than one aggregate: merging disjoint traces into a single graph
    would lose the one-request framing this page exists for. Node ids are positional, so a qname
    never becomes a mermaid identifier (the rule 144 already holds).
    """
    flows = dataset.flows
    lines = ["# Capability flows", "", *_scope_bullets(file_paths, working_roots)]
    if flows is None:
        lines += ["This index carries no flows — it was built before they existed.", ""]
        return "\n".join(lines)
    if flows.refused is not None:
        lines += [f"**Refused.** {flows.refused}", ""]
        return "\n".join(lines)
    lines += [
        f"{flows.flows_found} flow(s) found from {flows.seeds_traced} of {flows.seeds_found} "
        f"seed(s); {len(flows.flows)} shown, {flows.flows_cut} cut.",
        "",
        f"> {FLOW_COVERAGE_NOTE}",
        "",
    ]
    if flows.walk_truncated:
        lines += [f"> **{FLOW_TRUNCATED_NOTE}**", ""]
    for index, flow in enumerate(flows.flows, start=1):
        ended = flow.ended if flow.sink is None else f"{flow.ended} -> `{flow.sink}`"
        lines += [
            f"## {index}. `{flow.seed}`",
            "",
            f"- module: {flow.module or '_unattributed_'}",
            f"- layers crossed: {' -> '.join(flow.layers) or '_none_'}",
            f"- ended: {ended}",
            "",
            "```mermaid",
            "flowchart LR",
        ]
        for position, step in enumerate(flow.steps):
            lines.append(f'  n{position}["{_mermaid_label(step.qname)}"]')
        for position in range(1, len(flow.steps)):
            edge = "-->" if flow.steps[position].tier == "RESOLVED" else "-.->"
            label = f"|{flow.steps[position].kind}|" if flow.steps[position].kind else ""
            lines.append(f"  n{position - 1} {edge}{label} n{position}")
        lines += ["```", ""]
    return "\n".join(lines)


def _mermaid_label(qname: str) -> str:
    """Quotes and brackets would end the node label early; the qname is data, not syntax."""
    return qname.replace('"', "'").replace("[", "(").replace("]", ")")


def manifest_dict(
    artifact: OnboardingArtifact,
    dataset: OnboardingDataset,
    *,
    index_root: str = "",
    last_ref: str = "",
) -> dict[str, object]:
    """The one committed machine-readable artifact: the aggregate dataset (task 112) plus this
    run's operational record — the doc pointers. ``index_root`` / ``last_ref`` name the tree and
    revision so 139 can refuse a cross-tree or cross-schema diff (071 / 077). No wall-clock
    (R4.2/AC2). 205 removed the ``pages`` key with the per-module tree it recorded."""
    return {
        **dataset.as_dict(),
        "index_root": index_root,
        "last_ref": last_ref,
        "flows_doc": FLOWS_NAME,
        "overview": OVERVIEW_NAME,
        "tour": TOUR_NAME,
        "truncated": artifact.truncated,
        "viewer": VIEWER_NAME,
    }


def manifest_json(
    artifact: OnboardingArtifact,
    dataset: OnboardingDataset,
    *,
    index_root: str = "",
    last_ref: str = "",
) -> str:
    """Deterministic JSON for ``manifest.json``."""
    return (
        json.dumps(
            manifest_dict(artifact, dataset, index_root=index_root, last_ref=last_ref),
            sort_keys=True,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def cache_json(artifact: OnboardingArtifact) -> str:
    """Deterministic JSON for ``.code-atlas/onboarding/artifact.json`` (versioned, 145)."""
    return json.dumps(artifact.as_dict(), sort_keys=True, ensure_ascii=False, indent=2) + "\n"
