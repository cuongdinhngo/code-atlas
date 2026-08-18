"""Deterministic architectural-layer assignment for Phase-3 onboarding (task 084, M10; revised 103).

Pure functions over 083's ``GraphMetrics`` — no SQL, no LLM, no language branches (R1.1/R1.4/R4).
The heuristic is **common-root segment refined by dependency direction**: strip the longest
directory prefix shared by every module, then group by the first remaining path segment, with a
**pure dependency-direction fallback** when the tree does not split into >= 2 named groups (flat
legacy, or files in the common-root dir). Identical input yields byte-identical output (R4.2); layer
names are the repo's own path segments (or direction labels), never a per-language taxonomy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from code_atlas.onboarding.metrics import GraphMetrics, NodeMetric

# Derived-from-source: a pin test cross-checks this tuple against the methods assign_layers() emits,
# rather than re-typing a copy (R6.7 / derived-not-listed-invariant).
LAYER_METHODS: tuple[str, ...] = ("common-root-segment", "dependency-direction-fallback")

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


def _group_key(module: str, common: list[str]) -> str | None:
    """The module's architectural group: the first directory segment past the common prefix. A file
    sitting directly in the common-prefix dir (no deeper segment) has no group."""
    dirs = _dirs(module)
    return dirs[len(common)] if len(dirs) > len(common) else None


def _by_prefix(modules: tuple[NodeMetric, ...], groups: dict[str, str]) -> tuple[ModuleLayer, ...]:
    """Primary path: group by common-root segment, order groups by net dependency direction (R2)."""
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
    """Assign modules to ordered architectural layers over 083's metrics (tasks 084, 103).

    Common-root segment refined by dependency direction; a pure dependency-direction fallback when
    the tree does not split into >= 2 named groups (flat legacy, or files in the common-root dir).
    Deterministic regardless of input order (R4.2). Module unit = ``file_path`` (locked 2026-08-11).
    """
    modules = metrics.modules
    common = _common_dir_prefix(modules)
    grouped = {metric.key: _group_key(metric.key, common) for metric in modules}
    distinct = {group for group in grouped.values() if group is not None}
    if None not in grouped.values() and len(distinct) >= 2:
        keyed = {module: group for module, group in grouped.items() if group is not None}
        assigned = _by_prefix(modules, keyed)
        method = "common-root-segment"
    else:
        assigned = _by_direction(modules)
        method = "dependency-direction-fallback"
    layers: list[str] = []
    for module_layer in sorted(assigned, key=lambda m: m.rank):
        if module_layer.layer not in layers:
            layers.append(module_layer.layer)
    return LayerAssignment(layers=tuple(layers), modules=assigned, method=method)
