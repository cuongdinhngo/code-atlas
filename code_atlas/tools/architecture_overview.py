"""``architecture_overview`` — the first onboarding tool: what are this repo's layers (task 086).

Presentation only. The graph computes (083's two store pulls), enrichment interprets (084 layers,
085 summaries), and this module renders — the split PHASE3 §2 names, so no SQL, no LLM and no
language branch reaches it (R1.1/R1.4/R4). An LLM summarizer (090) arrives through the 085 seam
``create`` already accepts, never through a second abstraction (R1.2).

``results`` is the LAYER list, because the layer set is the answer this tool exists for. Under
responsibility grouping (110) the set is small and named; under the dominant-subtree fallback a
layer is a *sub*directory of the dominant tree, so a monorepo can yield hundreds — hence every list
here is capped like every other tool's, and ``truncated`` describes ``results`` as convention wants.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Literal

from code_atlas.config import Config
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
from code_atlas.onboarding.modules import find_business_modules
from code_atlas.onboarding.prose import ProseRun, ProseWriter
from code_atlas.onboarding.reachability import classify_reachability
from code_atlas.onboarding.summary import (
    StructuralSummarizer,
    Summarizer,
    summarize_modules,
)
from code_atlas.store import GraphStore, Row
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
    NavReason,
)

NAME = "architecture_overview"

DetailLevel = Literal["minimal", "standard", "verbose"]

__all__ = ["NAME", "create"]


def create(
    config: Config,
    summarizer: Summarizer | None = None,
    layer_refiner: LayerRefiner | None = None,
    prose_writer: ProseWriter | None = None,
) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo and the 085/091/117 seams (deterministic defaults when unset)."""
    seam: Summarizer = StructuralSummarizer() if summarizer is None else summarizer
    refiner: LayerRefiner = IdentityLayerRefiner() if layer_refiner is None else layer_refiner

    def architecture_overview(
        detail_level: DetailLevel = "standard", offset: int = 0
    ) -> dict[str, object]:
        """What are this codebase's top-level layers, and how do they depend on each other?

        Groups every indexed file into a layer, orders the layers by net dependency direction, and
        names the entry points — the map an onboarding reader would otherwise build by hand.
        ``results`` is the layer list, capped at ``CA_MAX_RESULTS`` with ``truncated``, and
        ``total_count`` is the layer count before the cap. ``standard`` adds each layer's degrees, a
        repo-level ``summary`` — whose ``reachability`` splits the zero-inbound modules into the
        populations they are (web surface, vendored, tests, dynamic, no-edge-either-way), keeping
        the raw total beside it — and ``cross_layer_edges`` (layer → layer crossings, heaviest
        first, capped with its own flag). ``verbose`` adds one row per module in layer order with
        its degrees and role — ``modules_truncated`` says the cap bit, and ``offset`` pages further,
        so no layer's modules are unreachable. ``method`` names how the grouping was derived, so a
        caller can tell a path-derived split from the dependency-direction fallback.
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if offset > 0 and detail_level != "verbose":
            raise ValueError("offset requires detail_level='verbose'")
        if not config.db_path.is_file():
            return _unbuilt(config)
        with GraphStore(config.db_path) as store:
            nodes = store.node_universe()
            edges = store.dependency_edges()

        def load_file_nodes(paths: Sequence[str]) -> Mapping[str, Sequence[Row]]:
            """Read-through node rows for the modules on THIS page only (118).

            Eager-loading every indexed file cost one query per file and held the whole node
            table, to feed at most ``max_results`` rows — and charged it to ``minimal`` too.
            """
            if not paths:
                return {}
            with GraphStore(config.db_path) as node_store:
                return {path: node_store.nodes_by_file_all(path) for path in paths}
        metrics = compute_metrics(nodes, edges)
        if not metrics.modules:
            return _empty(config)
        assignment = refine_layers(assign_layers(metrics), metrics, refiner)
        described = layer_descriptions(assignment, metrics, ProseRun(prose_writer))
        return _overview(
            config, metrics, assignment, nodes, edges, detail_level, seam,
            offset=offset, described=described, load_file_nodes=load_file_nodes,
        )

    return architecture_overview


def _base(config: Config, *, indexed: bool, reason: NavReason) -> dict[str, object]:
    """The keys every outcome carries: 071's ``index_root``, 033/065's reason + count."""
    return {
        "indexed": indexed,
        "results": [],
        "truncated": False,
        "reason": reason,
        "total_count": 0,
        "index_root": config.index_root,
    }


def _unbuilt(config: Config) -> dict[str, object]:
    """No database yet — a read tool must not create one to answer with zeroes."""
    return _base(config, indexed=False, reason=REASON_NOT_INDEXED)


def _empty(config: Config) -> dict[str, object]:
    """An index with no module: a genuine zero, distinct from the unbuilt one above (033/065)."""
    return _base(config, indexed=True, reason=REASON_NO_MATCHES)


def _layer_rows(
    metrics: GraphMetrics,
    assignment: LayerAssignment,
    *,
    degrees: bool,
    described: Mapping[str, str],
) -> list[dict[str, object]]:
    """One row per layer, in the assignment's dependency order (rank 0 = most source-like).

    ``described`` is 117's already-resolved prose; a missing entry keeps 110's default.
    """
    by_key = {metric.key: metric for metric in metrics.modules}
    entries = set(metrics.module_entry_points)
    rank: dict[str, int] = {}
    tallies: dict[str, list[int]] = {}  # layer -> [modules, fan_in, fan_out, entry_points]
    for module in assignment.modules:
        rank.setdefault(module.layer, module.rank)
        metric = by_key[module.module]
        tally = tallies.setdefault(module.layer, [0, 0, 0, 0])
        tally[0] += 1
        tally[1] += metric.fan_in
        tally[2] += metric.fan_out
        tally[3] += 1 if module.module in entries else 0
    rows: list[dict[str, object]] = []
    for layer in assignment.layers:
        modules, fan_in, fan_out, entry_points = tallies[layer]
        row: dict[str, object] = {
            "layer": layer,
            "description": described.get(layer) or layer_description(layer),
            "rank": rank[layer],
            "modules": modules,
        }
        if degrees:
            row |= {"fan_in": fan_in, "fan_out": fan_out, "entry_points": entry_points}
        rows.append(row)
    return rows


def _module_rows(
    metrics: GraphMetrics,
    assignment: LayerAssignment,
    seam: Summarizer,
    limit: int,
    offset: int,
    *,
    root: Path,
    load_file_nodes: Callable[[Sequence[str]], Mapping[str, Sequence[Row]]],
) -> tuple[list[dict[str, object]], bool]:
    """One page of module rows in LAYER order, plus whether more remain past this page.

    Layer order, not path order: an alphabetical cap hands back one directory and silently omits
    whole layers the same payload just named. Facts come from read-through at build time (118).
    """
    by_key: dict[str, NodeMetric] = {metric.key: metric for metric in metrics.modules}
    ordered = sorted(assignment.modules, key=lambda m: (m.rank, m.layer, m.module))
    placed = ordered[offset : offset + limit]
    file_nodes = load_file_nodes([module.module for module in placed])
    facts = [
        module_facts(root, module.module, by_key[module.module], file_nodes.get(module.module, ()))
        for module in placed
    ]
    role_of = {summary.key: summary.role for summary in summarize_modules(facts, seam)}
    rows = [
        {
            "module": module.module,
            "layer": module.layer,
            "rank": module.rank,
            "fan_in": by_key[module.module].fan_in,
            "fan_out": by_key[module.module].fan_out,
            "direction": by_key[module.module].direction,
            "role": role_of[module.module],
        }
        for module in placed
    ]
    return rows, offset + len(placed) < len(ordered)


def _overview(
    config: Config,
    metrics: GraphMetrics,
    assignment: LayerAssignment,
    nodes: list[tuple[str, str]],
    edges: list[tuple[str, str]],
    detail_level: DetailLevel,
    seam: Summarizer,
    *,
    offset: int,
    described: Mapping[str, str],
    load_file_nodes: Callable[[Sequence[str]], Mapping[str, Sequence[Row]]],
) -> dict[str, object]:
    """The answer itself — cheap at ``minimal``, per-module only at ``verbose`` (061).

    Every list is capped at ``max_results``: under the dominant-subtree fallback a layer is a
    subdirectory of the dominant tree, so neither the layer list nor the crossings are small by
    construction; the cap holds regardless of grouping method.
    """
    rich = detail_level in ("standard", "verbose")
    limit = config.max_results
    layers = _layer_rows(metrics, assignment, degrees=rich, described=described)
    payload: dict[str, object] = {
        "indexed": True,
        "results": layers[:limit],
        "truncated": len(layers) > limit,
        "reason": REASON_OK,
        "total_count": len(layers),
        "index_root": config.index_root,
        "method": assignment.method,
    }
    if not rich:
        return payload
    crossings = cross_layer_edges(module_edges(nodes, edges), assignment)
    # The zero-inbound total is four unrelated populations; the split is the answer, the raw
    # total stays beside it for anyone who wants it (task 113).
    split = classify_reachability(
        metrics,
        entry_points=config.entry_points,
        stub_roots=config.stub_roots,
        sample_limit=limit,
    )
    # The capability table a newcomer actually needs: which file for "screen X" (114). Paths come
    # from the module universe; class counts are the tool's own cheap zero (the dataset carries
    # them).
    modules = find_business_modules(
        [metric.key for metric in metrics.modules],
        class_counts={},
        fan_in={metric.key: metric.fan_in for metric in metrics.modules},
        stub_roots=config.stub_roots,
        limit=limit,
    )
    # Mirrored sibling subtrees: the duplication trap, discovered rather than configured (115).
    mirrors = find_mirror_subtrees(
        [metric.key for metric in metrics.modules],
        stub_roots=config.stub_roots,
        sample_limit=limit,
    )
    payload["summary"] = {
        "layers": len(assignment.layers),
        "modules": len(metrics.modules),
        "symbols": len(metrics.symbols),
        "module_entry_points": len(metrics.module_entry_points),
        "reachability": split.as_dict(),
        "business_modules": modules.as_dict(),
        "mirrors": mirrors.as_dict(),
        "cross_layer_edges": len(crossings),
        "method": assignment.method,
    }
    # Heaviest-first, so a capped list keeps the crossings that carry the architecture.
    payload["cross_layer_edges"] = [edge.as_dict() for edge in crossings[:limit]]
    payload["cross_layer_edges_truncated"] = len(crossings) > limit
    if detail_level == "standard":
        return payload
    rows, more = _module_rows(
        metrics, assignment, seam, limit, offset,
        root=Path(config.root), load_file_nodes=load_file_nodes,
    )
    payload["modules"] = rows
    payload["modules_offset"] = offset
    payload["modules_truncated"] = more
    return payload
