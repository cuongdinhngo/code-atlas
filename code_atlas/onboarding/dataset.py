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

from code_atlas.onboarding.flows import (
    FlowSet,
    build_flows,
    seed_files,
    seed_symbols,
)
from code_atlas.onboarding.headlines import Headline, headline_candidates
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
from code_atlas.onboarding.mirrors import MirrorReport, find_mirror_subtrees
from code_atlas.onboarding.modules import (
    COVERAGE_NOTE,
    ModuleMap,
    directory_owners,
    find_business_modules,
)
from code_atlas.onboarding.prose import ProseRun
from code_atlas.onboarding.reachability import ReachabilitySplit, classify_reachability

# 2: the zero-inbound total became the ``reachability`` split (113). 3: the ``modules``
# capability table (114). 4: the ``mirrors`` pair table (115). 5: ``commit``, per-layer ``kinds``
# and ``dir_symbol_threshold``, so the map renders from the dataset ALONE and states the threshold
# it was pruned at (116). 6: ``headlines`` — the facts a newcomer needs first, derived here and
# worded through the 117 seam. 7: caveats and declaration provenance — ``path_index.caveat``,
# ``reachability.caveat``/``patterns``, per-bucket ``signals`` (119/127), so a caveat and a
# declared count travel together. This is NOT ``contract_version``; the contract is untouched.
DATASET_VERSION = 8
# A directory is kept in the tree only when its subtree holds at least this many symbols — the
# mockup's prune, so a 40k-file repo yields a map of a few dozen rows, not thousands (AC3).
DIR_SYMBOL_THRESHOLD = 400

__all__ = [
    "DATASET_VERSION",
    "DIR_SYMBOL_THRESHOLD",
    "ClassStat",
    "DirStat",
    "Headline",
    "Hub",
    "KindCount",
    "LayerStat",
    "MatrixEdge",
    "OnboardingDataset",
    "MirrorReport",
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
    kinds: tuple[KindCount, ...] = ()
    """Node kinds declared by this layer's files — what makes a procedural layer visible (116)."""


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
    caveat: str = ""
    """What a search miss over this index does and does not prove — single-sourced here (127)."""


@dataclass(frozen=True)
class OnboardingDataset:
    """The whole aggregate map — the one shape renderers consume (task 112)."""

    version: int
    files: int
    parsed: int
    method: str
    commit: str
    dir_symbol_threshold: int
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
    mirrors: MirrorReport
    headlines: tuple[Headline, ...] = ()
    """The facts a newcomer needs first: derived here, worded through the 117 seam (task 117)."""
    flows: FlowSet | None = None
    """197's traces. ``None`` on an index built before flows existed — never a false zero."""

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict view — the byte-stability surface (R4.2/AC2)."""
        return {
            "classes": [
                {"file": c.file, "layer": c.layer, "members": c.members, "name": c.name}
                for c in self.classes
            ],
            "commit": self.commit,
            "confidence": [{"count": k.count, "tier": k.kind} for k in self.confidence],
            "dir_symbol_threshold": self.dir_symbol_threshold,
            "edge_counts": [{"count": k.count, "kind": k.kind} for k in self.edge_counts],
            "files": self.files,
            "flows": self.flows.as_dict() if self.flows is not None else None,
            "headlines": [row.as_dict() for row in self.headlines],
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
                    "kinds": [{"count": k.count, "kind": k.kind} for k in ly.kinds],
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
            "mirrors": self.mirrors.as_dict(),
            "modules": self.modules.as_dict(),
            "node_counts": [{"count": k.count, "kind": k.kind} for k in self.node_counts],
            "parsed": self.parsed,
            "reachability": self.reachability.as_dict(),
            "path_index": {
                "caveat": self.path_index.caveat,
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


def derive_caveats(payload: Mapping[str, object], _at: str = "") -> tuple[tuple[str, str], ...]:
    """Every caveat the dataset carries, DERIVED from the payload rather than listed (R6.7, 127).

    A section owns a caveat by owning a non-empty ``caveat`` key — a structural fact about the
    contract 112 froze, so caveat N+1 is covered the moment it exists. Returns ``(section, text)``
    in payload order, which is key order, which is stable (R4.2).
    """
    found: list[tuple[str, str]] = []
    text = payload.get("caveat")
    if isinstance(text, str) and text:
        found.append((_at or "dataset", text))
    for key, value in payload.items():
        where = f"{_at}.{key}" if _at else key
        if isinstance(value, Mapping):
            found.extend(derive_caveats(value, where))
        elif isinstance(value, list):
            for index, row in enumerate(value):
                if isinstance(row, Mapping):
                    found.extend(derive_caveats(row, f"{where}[{index}]"))
    return tuple(found)


def _layer_stats(
    metrics: GraphMetrics,
    assignment: LayerAssignment,
    file_kind_counts: Sequence[tuple[str, str, int]] = (),
    described: Mapping[str, str] | None = None,
) -> tuple[LayerStat, ...]:
    """The layer table in dependency order, plus each layer's node-kind composition (task 116).

    Module grain **is** file grain (``metrics.py``), so a layer's composition is the sum of the kind
    counts of the files assigned to it. Kinds are sorted by descending count then name, so the bar
    is stable and its dominant segment reads first (R4.2). ``described`` is 117's prose, already
    resolved (a missing entry falls back to 110's default, so a partial map is still complete).
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
    kinds: dict[str, Counter[str]] = {}
    layer_of = {module.module: module.layer for module in assignment.modules}
    for path, kind, count in file_kind_counts:
        layer = layer_of.get(path)
        if layer is not None:
            kinds.setdefault(layer, Counter())[kind] += count
    return tuple(
        LayerStat(
            layer=layer,
            rank=rank[layer],
            modules=tallies[layer][0],
            fan_in=tallies[layer][1],
            fan_out=tallies[layer][2],
            entry_points=tallies[layer][3],
            description=prose.get(layer) or layer_description(layer),
            kinds=tuple(
                KindCount(kind, count)
                for kind, count in sorted(
                    kinds.get(layer, Counter()).items(), key=lambda item: (-item[1], item[0])
                )
            ),
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
    truncated = len(file_paths) > cap
    caveat = (
        f"The search index holds {len(kept):,} of {len(file_paths):,} paths, so a search miss may "
        "be a cap rather than an absence."
        if truncated
        else f"The search index holds every one of the {len(file_paths):,} indexed paths, so a "
        "search miss is a real absence."
    )
    return PathIndex(
        dirs=tuple(dirs),
        entries=tuple(entries),
        total=len(file_paths),
        shown=len(kept),
        truncated=truncated,
        caveat=caveat,
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
    mirror_sample_max: int = 0,
    file_kind_counts: Sequence[tuple[str, str, int]] = (),
    commit: str = "",
    prose: ProseRun | None = None,
    flow_edges: Sequence[tuple[str, str, str, str]] | None = None,
    flow_max: int = 0,
    flow_max_nodes: int = 0,
) -> OnboardingDataset:
    """Assemble the aggregate dataset from bounded ``store.py`` rows (see module docstring).

    ``nodes``/``edges`` drive only 110's pure layer reasoning (``compute_metrics`` +
    ``refine_layers``), which labels the layer table, matrix, hubs, classes and tree; every count
    itself already came from SQL. Identical input yields an identical dataset (R4.2).

    ``prose`` is the 117 seam. Headline wording is requested BEFORE the layer descriptions, so a
    repo whose layers exhaust their own slot ceiling cannot leave the headlines unwritten (AC5). It
    touches only prose: every count, ranking and grouping below is already settled (AC2).
    """
    metrics = compute_metrics(nodes, edges)
    refiner: LayerRefiner = IdentityLayerRefiner() if layer_refiner is None else layer_refiner
    assignment = refine_layers(assign_layers(metrics), metrics, refiner)
    layer_of = {module.module: module.layer for module in assignment.modules}
    matrix = cross_layer_edges(module_edges(nodes, edges), assignment)
    reachability = classify_reachability(
        metrics,
        entry_points=declared_entry_points,
        stub_roots=declared_stub_roots,
        sample_limit=reachability_sample_max,
    )
    business = find_business_modules(
        file_paths,
        class_counts=dict(file_class_counts),
        fan_in={metric.key: metric.fan_in for metric in metrics.modules},
        stub_roots=declared_stub_roots,
        limit=module_max,
    )
    mirrors = find_mirror_subtrees(
        file_paths, stub_roots=declared_stub_roots, sample_limit=mirror_sample_max
    )
    headlines = headline_candidates(
        node_kind_counts=node_kind_counts,
        edge_kind_counts=edge_kind_counts,
        confidence=confidence,
        hubs=hubs,
        reachability=reachability,
        modules=business,
        mirrors=mirrors,
        prose=prose,
    )
    # 197 — stamped at the builder, where metrics/layers/modules already exist, so no renderer
    # re-derives a second notion of a flow. Absent rows leave `flows` None, never a false zero.
    flows: FlowSet | None = None
    if flow_edges is not None:
        file_of = dict(nodes)
        layer_of = {m.module: m.layer for m in assignment.modules}
        seeds = seed_symbols(
            metrics.entry_points,
            seed_files(
                sorted({f for _q, f in nodes if f}),
                declared_entry_points or (),
                declared_stub_roots or (),
            ),
            file_of,
        )
        flows = build_flows(
            seeds, flow_edges, file_of, layer_of, directory_owners(business.modules),
            max_flows=flow_max, max_nodes=flow_max_nodes,
        )
    dataset = OnboardingDataset(
        version=DATASET_VERSION,
        flows=flows,
        files=files,
        parsed=parsed,
        method=assignment.method,
        commit=commit,
        dir_symbol_threshold=dir_symbol_threshold,
        node_counts=tuple(KindCount(kind, count) for kind, count in node_kind_counts),
        edge_counts=tuple(KindCount(kind, count) for kind, count in edge_kind_counts),
        confidence=tuple(KindCount(tier, confidence[tier]) for tier in sorted(confidence)),
        layers=_layer_stats(
            metrics,
            assignment,
            file_kind_counts,
            layer_descriptions(assignment, metrics, prose),
        ),
        matrix=tuple(MatrixEdge(e.source, e.target, e.count) for e in matrix),
        hubs=tuple(Hub(f, layer_of.get(f, ""), fi, fo) for f, fi, fo in hubs),
        classes=tuple(
            ClassStat(name, file, layer_of.get(file, ""), members)
            for name, file, members in classes
        ),
        tree=_tree(file_symbol_counts, layer_of, dir_symbol_threshold),
        path_index=_path_index(file_paths, path_index_max),
        reachability=reachability,
        modules=business,
        mirrors=mirrors,
        headlines=headlines,
    )
    # The gate refuses filler prose rather than ship a hollow headline (task 109 C1, 117 AC6). A
    # deferred import: quality_gate reads this module's shape, so a top-level one would cycle.
    from code_atlas.onboarding.quality_gate import check_dataset

    check_dataset(dataset)
    return dataset


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
    lines.extend(["", "## Mirror subtrees", ""])
    lines.append(f"- {dataset.mirrors.caveat}")
    if dataset.mirrors.pairs:
        for mir in dataset.mirrors.pairs:
            lines.append(
                f"- `{mir.left}` <-> `{mir.right}`: {mir.shared} shared paths "
                f"({mir.overlap:.0%} overlap), {mir.left_only} / {mir.right_only} on one side only"
            )
    else:
        lines.append("- (no mirrored sibling subtrees detected)")
    lines.extend(["", "## Zero-inbound modules, by population", ""])
    split = dataset.reachability
    lines.append(f"- zero-inbound modules (raw total): {split.total}")
    for bucket in split.buckets:
        lines.append(f"- `{bucket.bucket}` — {bucket.label}: {bucket.count}")
        lines.append(f"  - {bucket.note}")
        named = ", ".join(f"{count} {name}" for name, count in bucket.signals if count)
        if named:
            lines.append(f"  - by signal: {named}")
    for bucket_id, reason in split.dropped:
        lines.append(f"- `{bucket_id}`: not reported — {reason}")
    lines.append(f"- {split.caveat}")
    for claim in split.patterns:
        lines.append(
            f"  - `{claim.pattern}` ({claim.kind}): matches {claim.files_matched} indexed files, "
            f"claims {claim.zero_inbound_claimed} of the modules above"
        )
    lines.extend(["", "## Hubs", ""])
    if dataset.hubs:
        for hub in dataset.hubs:
            lines.append(
                f"- `{hub.file}` — `{hub.layer}` (fan_in {hub.fan_in}, fan_out {hub.fan_out})"
            )
    else:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"
