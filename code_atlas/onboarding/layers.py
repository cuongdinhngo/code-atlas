"""Deterministic architectural-layer assignment for Phase-3 onboarding (task 084, M10; 103, 104).

Pure functions over 083's ``GraphMetrics`` — no SQL, no LLM, no language branches (R1.1/R1.4/R4).
The heuristic is **dominant-subtree** (task 104): group modules beneath the top-level directory that
holds the most modules (strip the common prefix *within* that subtree, layer by the first remaining
segment), while every **other** top-level directory becomes its own layer. A **pure
dependency-direction fallback** takes over when the paths yield < 2 named groups (flat legacy, or a
single directory). Identical input yields byte-identical output (R4.2); layer names are the repo's
own path segments (or direction labels), never a per-language taxonomy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from code_atlas.onboarding.metrics import GraphMetrics, NodeMetric

# Derived-from-source: a pin test cross-checks this tuple against the methods assign_layers() emits,
# rather than re-typing a copy (R6.7 / derived-not-listed-invariant).
LAYER_METHODS: tuple[str, ...] = ("dominant-subtree", "dependency-direction-fallback")

# A module at the repo root (no directory) has no path segment to name a layer; it lands here
# rather than emitting the empty string (task 104 residual).
_ROOT_LAYER = "(root)"

# The fallback orders modules into direction bands (entry → foundation). The SET is derived: a pin
# test asserts it equals DIRECTION_LABELS, so a new metrics label cannot ship unplaced (R6.7). The
# ORDER is a semantic choice — sources depend on sinks, so sources lead.
_FALLBACK_ORDER: tuple[str, ...] = ("source", "mixed", "sink", "isolated")


@dataclass(frozen=True)
class ModuleLayer:
    """One module's layer name and its 0-based rank (0 = entry/source band)."""

    module: str
    layer: str
    rank: int


@dataclass(frozen=True)
class LayerAssignment:
    """Modules assigned to ordered architectural layers over the dependency graph (task 084)."""

    layers: tuple[str, ...]
    modules: tuple[ModuleLayer, ...]
    method: str

    def as_dict(self) -> dict[str, object]:
        """A plain, order-stable dict view — the serialisation consumers (086) build on."""
        return {
            "method": self.method,
            "layers": list(self.layers),
            "modules": [
                {"module": m.module, "layer": m.layer, "rank": m.rank} for m in self.modules
            ],
        }

    def to_json(self) -> str:
        """Deterministic JSON — the byte-stability surface (R4.2)."""
        return json.dumps(self.as_dict(), sort_keys=True, ensure_ascii=False)


def _dirs(module: str) -> list[str]:
    """The module's directory segments (POSIX ``/``, filename dropped). Paths are POSIX-normalised
    at index time, so splitting on ``/`` is language-agnostic (R1.1); a root file has none."""
    return module.split("/")[:-1]


def _top_dir(module: str) -> str | None:
    """The module's top-level directory segment, or ``None`` for a file sitting at the repo root."""
    dirs = _dirs(module)
    return dirs[0] if dirs else None


def _common_dir_prefix(modules: tuple[NodeMetric, ...]) -> list[str]:
    """The longest run of leading whole directory segments shared by every module (segment-wise,
    never a mid-segment character prefix — R2). Order-independent, so the result is byte-stable."""
    dir_lists = [_dirs(metric.key) for metric in modules]
    if not dir_lists:
        return []
    common = dir_lists[0]
    for dirs in dir_lists[1:]:
        matched = 0
        for left, right in zip(common, dirs, strict=False):
            if left != right:
                break
            matched += 1
        common = common[:matched]
        if not common:
            break
    return common


def _dominant_subtree(modules: tuple[NodeMetric, ...]) -> str | None:
    """The top-level directory holding the most modules; ties broken by name for determinism (R4.2).
    Root files (no top dir) do not compete; ``None`` when no module has a top-level directory."""
    counts: dict[str, int] = {}
    for metric in modules:
        top = _top_dir(metric.key)
        if top is not None:
            counts[top] = counts.get(top, 0) + 1
    if not counts:
        return None
    return sorted(counts, key=lambda name: (-counts[name], name))[0]


def _layer_of(module: str, dominant: str, sub_common: list[str]) -> str:
    """The module's layer under the dominant-subtree rule. Inside the dominant subtree: the first
    segment past its common prefix, or the top dir itself when the file sits directly in it. Else:
    that file's own top-level directory. A root file (no directory) lands in ``_ROOT_LAYER``."""
    dirs = _dirs(module)
    if not dirs:
        return _ROOT_LAYER
    if dirs[0] != dominant:
        return dirs[0]
    return dirs[len(sub_common)] if len(dirs) > len(sub_common) else dirs[0]


def _by_group(modules: tuple[NodeMetric, ...], groups: dict[str, str]) -> tuple[ModuleLayer, ...]:
    """Group by the precomputed layer map, ordering groups by net dependency direction (R2)."""
    net: dict[str, int] = {}
    for metric in modules:
        key = groups[metric.key]
        net[key] = net.get(key, 0) + metric.fan_out - metric.fan_in
    # Source-like (net-outward) groups lead; ties broken by name for determinism (R4.2).
    order = sorted(net, key=lambda key: (-net[key], key))
    rank_of = {key: rank for rank, key in enumerate(order)}
    assigned = [
        ModuleLayer(metric.key, groups[metric.key], rank_of[groups[metric.key]])
        for metric in modules
    ]
    return tuple(sorted(assigned, key=lambda m: m.module))


def _by_direction(modules: tuple[NodeMetric, ...]) -> tuple[ModuleLayer, ...]:
    """Fallback: uninformative namespaces → layer purely by dependency direction (R3)."""
    present = {metric.direction for metric in modules}
    order = [label for label in _FALLBACK_ORDER if label in present]
    rank_of = {label: rank for rank, label in enumerate(order)}
    assigned = [
        ModuleLayer(metric.key, metric.direction, rank_of[metric.direction]) for metric in modules
    ]
    return tuple(sorted(assigned, key=lambda m: m.module))


def assign_layers(metrics: GraphMetrics) -> LayerAssignment:
    """Assign modules to ordered architectural layers over 083's metrics (tasks 084, 103, 104).

    Dominant-subtree grouping refined by dependency direction; a pure dependency-direction fallback
    when the paths do not split into >= 2 named groups (flat legacy, or a single directory).
    Deterministic regardless of input order (R4.2). Module unit = ``file_path`` (locked 2026-08-11).
    """
    modules = metrics.modules
    dominant = _dominant_subtree(modules)
    subtree = tuple(m for m in modules if _top_dir(m.key) == dominant)
    sub_common = _common_dir_prefix(subtree)
    grouped = {m.key: _layer_of(m.key, dominant or "", sub_common) for m in modules}
    if dominant is not None and len(set(grouped.values())) >= 2:
        assigned = _by_group(modules, grouped)
        method = "dominant-subtree"
    else:
        assigned = _by_direction(modules)
        method = "dependency-direction-fallback"
    layers: list[str] = []
    for module_layer in sorted(assigned, key=lambda m: m.rank):
        if module_layer.layer not in layers:
            layers.append(module_layer.layer)
    return LayerAssignment(layers=tuple(layers), modules=assigned, method=method)
