"""One compact, versioned aggregate dataset behind every onboarding renderer (task 112, M11).

The committed ``manifest.json`` used to be a multi-megabyte per-module dump no machine read, and
each renderer re-walked the artifact object graph to re-derive its view. This module is the single
contract instead: a small aggregate — kind/edge/confidence counts, the layer table, the layer×layer
matrix, the top hubs, the largest classes, a directory tree pruned to a symbol threshold — plus a
capped, front-coded path index. Every aggregate is a bounded ``store.py`` query (R1.4/R4.3, AC1);
this module only assembles the rows into the shape and labels the layers (110's pure reasoning).

No SQL, no LLM, no language branch (R1.1/R1.4/R4). Byte-stable: sorted keys, no timestamps (R4.2).
The shape is versioned by :data:`DATASET_VERSION` and is **not** the adapter contract (R3).
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from code_atlas.onboarding.layers import (
    IdentityLayerRefiner,
    LayerAssignment,
    LayerRefiner,
    assign_layers,
    cross_layer_edges,
    layer_description,
    refine_layers,
)
from code_atlas.onboarding.metrics import GraphMetrics, compute_metrics, module_edges
from code_atlas.onboarding.modules import COVERAGE_NOTE, ModuleMap, find_business_modules
from code_atlas.onboarding.reachability import ReachabilitySplit, classify_reachability

# 2: the zero-inbound total became the ``reachability`` split (113). 3: the ``modules``
# capability table (114). Each is a shape change, so the dataset's own version bumps — this is
# NOT ``contract_version``; the adapter contract is untouched.
DATASET_VERSION = 3
# A directory is kept in the tree only when its subtree holds at least this many symbols — the
# mockup's prune, so a 40k-file repo yields a map of a few dozen rows, not thousands (AC3).
DIR_SYMBOL_THRESHOLD = 400

__all__ = [
    "DATASET_VERSION",
    "DIR_SYMBOL_THRESHOLD",
    "ClassStat",
    "DirStat",
    "Hub",
    "KindCount",
    "LayerStat",
    "MatrixEdge",
    "OnboardingDataset",
    "ModuleMap",
    "PathIndex",
    "ReachabilitySplit",
    "build_dataset",
    "dataset_json",
    "render_dataset_overview",
]


@dataclass(frozen=True)
class KindCount:
    """One census row: a node kind, edge kind, or confidence tier and its total."""

    kind: str
    count: int


@dataclass(frozen=True)
class LayerStat:
    """One layer of the table: name, rank, size and aggregated degrees (mirrors the overview)."""

    layer: str
    rank: int
    modules: int
    fan_in: int
    fan_out: int
    entry_points: int
    description: str


@dataclass(frozen=True)
class MatrixEdge:
    """One cell of the layer×layer matrix: a directed crossing count between two layers."""

    source: str
    target: str
    count: int


@dataclass(frozen=True)
class Hub:
    """A high-fan-in file: the ranking is the store's, the layer label is 110's assignment."""

    file: str
    layer: str
    fan_in: int
    fan_out: int


@dataclass(frozen=True)
class ClassStat:
    """A largest-class row: qualified name, file, layer and member count."""

    name: str
    file: str
    layer: str
    members: int


@dataclass(frozen=True)
class DirStat:
    """A directory the tree kept: path, symbol/file totals and its dominant layer."""

    path: str
    symbols: int
    files: int
    layer: str


@dataclass(frozen=True)
class PathIndex:
    """The front-coded path list: ``dirs`` + ``(dir_index, filename)`` entries, capped.

    ``total`` is every indexed path; ``shown`` is how many the cap kept. When ``truncated`` a
    consumer knows search over this index is incomplete and states so (ticket / AC6).
    """

    dirs: tuple[str, ...]
    entries: tuple[tuple[int, str], ...]
    total: int
    shown: int
    truncated: bool


@dataclass(frozen=True)
class OnboardingDataset:
    """The whole aggregate map — the one shape renderers consume (task 112)."""

    version: int
    files: int
    parsed: int
    method: str
    node_counts: tuple[KindCount, ...]
    edge_counts: tuple[KindCount, ...]
    confidence: tuple[KindCount, ...]
    layers: tuple[LayerStat, ...]
    matrix: tuple[MatrixEdge, ...]
    hubs: tuple[Hub, ...]
    classes: tuple[ClassStat, ...]
    tree: tuple[DirStat, ...]
    path_index: PathIndex
    reachability: ReachabilitySplit
    modules: ModuleMap

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict view — the byte-stability surface (R4.2/AC2)."""
        return {
            "classes": [
                {"file": c.file, "layer": c.layer, "members": c.members, "name": c.name}
                for c in self.classes
            ],
            "confidence": [{"count": k.count, "tier": k.kind} for k in self.confidence],
            "edge_counts": [{"count": k.count, "kind": k.kind} for k in self.edge_counts],
            "files": self.files,
            "hubs": [
                {"fan_in": h.fan_in, "fan_out": h.fan_out, "file": h.file, "layer": h.layer}
                for h in self.hubs
            ],
            "layers": [
                {
                    "description": ly.description,
                    "entry_points": ly.entry_points,
                    "fan_in": ly.fan_in,
                    "fan_out": ly.fan_out,
                    "layer": ly.layer,
                    "modules": ly.modules,
                    "rank": ly.rank,
                }
                for ly in self.layers
            ],
            "matrix": [
                {"count": m.count, "source": m.source, "target": m.target} for m in self.matrix
            ],
            "method": self.method,
            "modules": self.modules.as_dict(),
            "node_counts": [{"count": k.count, "kind": k.kind} for k in self.node_counts],
            "parsed": self.parsed,
            "reachability": self.reachability.as_dict(),
            "path_index": {
                "dirs": list(self.path_index.dirs),
                "entries": [[index, name] for index, name in self.path_index.entries],
                "shown": self.path_index.shown,
                "total": self.path_index.total,
                "truncated": self.path_index.truncated,
            },
            "tree": [
                {"files": d.files, "layer": d.layer, "path": d.path, "symbols": d.symbols}
                for d in self.tree
            ],
            "version": self.version,
        }


def _layer_stats(metrics: GraphMetrics, assignment: LayerAssignment) -> tuple[LayerStat, ...]:
    """The layer table in dependency order — the overview's ``_layer_rows``, at dataset grain."""
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
        LayerStat(
            layer=layer,
            rank=rank[layer],
            modules=tallies[layer][0],
            fan_in=tallies[layer][1],
            fan_out=tallies[layer][2],
            entry_points=tallies[layer][3],
            description=layer_description(layer),
        )
        for layer in assignment.layers
    )


def _tree(
    file_symbol_counts: Sequence[tuple[str, int]],
    layer_of: Mapping[str, str],
    threshold: int,
) -> tuple[DirStat, ...]:
    """Roll per-file symbol counts up every ancestor directory, keep those over ``threshold``.

    Symbols and files accumulate on every prefix; the dominant layer is the one covering the most
    files under the directory (ties by layer name). Sorted by path, so the tree is stable (R4.2).
    """
    symbols: Counter[str] = Counter()
    files: Counter[str] = Counter()
    layers: dict[str, Counter[str]] = {}
    for path, count in file_symbol_counts:
        segments = path.split("/")[:-1]
        layer = layer_of.get(path, "")
        prefix = ""
        for segment in segments:
            prefix = f"{prefix}/{segment}" if prefix else segment
            symbols[prefix] += count
            files[prefix] += 1
            layers.setdefault(prefix, Counter())[layer] += 1
    kept: list[DirStat] = []
    for directory in sorted(symbols):
        if symbols[directory] < threshold:
            continue
        dominant = min(layers[directory].items(), key=lambda item: (-item[1], item[0]))[0]
        kept.append(DirStat(directory, symbols[directory], files[directory], dominant))
    return tuple(kept)


def _path_index(file_paths: Sequence[str], cap: int) -> PathIndex:
    """Front-code the sorted path list, capped at ``cap`` (the one unbounded section — AC6)."""
    kept = list(file_paths[:cap])
    dir_index: dict[str, int] = {}
    dirs: list[str] = []
    entries: list[tuple[int, str]] = []
    for path in kept:
        head, _, tail = path.rpartition("/")
        if head not in dir_index:
            dir_index[head] = len(dirs)
            dirs.append(head)
        entries.append((dir_index[head], tail))
    return PathIndex(
        dirs=tuple(dirs),
        entries=tuple(entries),
        total=len(file_paths),
        shown=len(kept),
        truncated=len(file_paths) > cap,
    )


def build_dataset(
    nodes: Sequence[tuple[str, str]],
    edges: Sequence[tuple[str, str]],
    *,
    files: int,
    parsed: int,
    node_kind_counts: Sequence[tuple[str, int]],
    edge_kind_counts: Sequence[tuple[str, int]],
    confidence: Mapping[str, int],
    hubs: Sequence[tuple[str, int, int]],
    classes: Sequence[tuple[str, str, int]],
    file_symbol_counts: Sequence[tuple[str, int]],
    file_paths: Sequence[str],
    path_index_max: int,
    layer_refiner: LayerRefiner | None = None,
    dir_symbol_threshold: int = DIR_SYMBOL_THRESHOLD,
    declared_entry_points: Sequence[str] | None = None,
    declared_stub_roots: Sequence[str] | None = None,
    reachability_sample_max: int = 0,
    file_class_counts: Sequence[tuple[str, int]] = (),
    module_max: int = 0,
) -> OnboardingDataset:
    """Assemble the aggregate dataset from bounded ``store.py`` rows (see module docstring).

    ``nodes``/``edges`` drive only 110's pure layer reasoning (``compute_metrics`` +
    ``refine_layers``), which labels the layer table, matrix, hubs, classes and tree; every count
    itself already came from SQL. Identical input yields an identical dataset (R4.2).
    """
    metrics = compute_metrics(nodes, edges)
    refiner: LayerRefiner = IdentityLayerRefiner() if layer_refiner is None else layer_refiner
    assignment = refine_layers(assign_layers(metrics), metrics, refiner)
    layer_of = {module.module: module.layer for module in assignment.modules}
    matrix = cross_layer_edges(module_edges(nodes, edges), assignment)
    return OnboardingDataset(
        version=DATASET_VERSION,
        files=files,
        parsed=parsed,
        method=assignment.method,
        node_counts=tuple(KindCount(kind, count) for kind, count in node_kind_counts),
        edge_counts=tuple(KindCount(kind, count) for kind, count in edge_kind_counts),
        confidence=tuple(KindCount(tier, confidence[tier]) for tier in sorted(confidence)),
        layers=_layer_stats(metrics, assignment),
        matrix=tuple(MatrixEdge(e.source, e.target, e.count) for e in matrix),
        hubs=tuple(Hub(f, layer_of.get(f, ""), fi, fo) for f, fi, fo in hubs),
        classes=tuple(
            ClassStat(name, file, layer_of.get(file, ""), members)
            for name, file, members in classes
        ),
        tree=_tree(file_symbol_counts, layer_of, dir_symbol_threshold),
        path_index=_path_index(file_paths, path_index_max),
        reachability=classify_reachability(
            metrics,
            entry_points=declared_entry_points,
            stub_roots=declared_stub_roots,
            sample_limit=reachability_sample_max,
        ),
        modules=find_business_modules(
            file_paths,
            class_counts=dict(file_class_counts),
            fan_in={metric.key: metric.fan_in for metric in metrics.modules},
            stub_roots=declared_stub_roots,
            limit=module_max,
        ),
    )


def dataset_json(dataset: OnboardingDataset) -> str:
    """Deterministic JSON for the committed dataset — sorted keys, no wall-clock (R4.2/AC2)."""
    return json.dumps(dataset.as_dict(), sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def render_dataset_overview(dataset: OnboardingDataset) -> str:
    """Overview + layer table + matrix + hub list from the dataset **alone** — no store (AC5).

    Proves the contract: a renderer needs nothing but the dataset to draw the map. The full renderer
    migration (viewer, per-module pages) is 116; this is the seam it builds on. Trailing newline.
    """
    lines = [
        "# Architecture overview",
        "",
        "## Summary",
        "",
        f"- method: {dataset.method}",
        f"- files: {dataset.files} ({dataset.parsed} parsed)",
        f"- layers: {len(dataset.layers)}",
        f"- node kinds: {len(dataset.node_counts)}",
        f"- edge kinds: {len(dataset.edge_counts)}",
        f"- indexed paths: {dataset.path_index.total} "
        f"({dataset.path_index.shown} in the index; "
        f"truncated: {'true' if dataset.path_index.truncated else 'false'})",
        "",
        "## Layers",
        "",
    ]
    for row in dataset.layers:
        lines.append(
            f"- rank {row.rank}: `{row.layer}` ({row.modules} modules, "
            f"fan_in {row.fan_in}, fan_out {row.fan_out}, {row.entry_points} entry points)"
        )
        lines.append(f"  - {row.description}")
    lines.extend(["", "## Layer matrix", ""])
    if dataset.matrix:
        for edge in dataset.matrix:
            lines.append(f"- `{edge.source}` → `{edge.target}` ({edge.count})")
    else:
        lines.append("- (none)")
    lines.extend(["", "## Business modules", ""])
    mods = dataset.modules
    lines.append(
        f"- coverage: {mods.covered} of {mods.total} indexed files ({mods.percent} %); "
        f"{mods.excluded} excluded as vendored or test code"
    )
    lines.append(f"  - {COVERAGE_NOTE}")
    if mods.modules:
        for mod in mods.modules:
            flag = " — **only tree**" if mod.single_tree else ""
            lines.append(
                f"- `{mod.module}`: {mod.files} files, {mod.classes} classes, "
                f"trees {', '.join(mod.trees)}{flag}"
            )
    else:
        lines.append("- (no capability layout found)")
    for container, reason in mods.refused:
        lines.append(f"- refused `{container}`: {reason}")
    lines.extend(["", "## Zero-inbound modules, by population", ""])
    split = dataset.reachability
    lines.append(f"- zero-inbound modules (raw total): {split.total}")
    for bucket in split.buckets:
        lines.append(f"- `{bucket.bucket}` — {bucket.label}: {bucket.count}")
        lines.append(f"  - {bucket.note}")
    for bucket_id, reason in split.dropped:
        lines.append(f"- `{bucket_id}`: not reported — {reason}")
    lines.extend(["", "## Hubs", ""])
    if dataset.hubs:
        for hub in dataset.hubs:
            lines.append(
                f"- `{hub.file}` — `{hub.layer}` (fan_in {hub.fan_in}, fan_out {hub.fan_out})"
            )
    else:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"
