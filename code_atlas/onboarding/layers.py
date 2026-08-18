"""Deterministic architectural-layer assignment for Phase-3 onboarding (task 084, M10).

Pure functions over 083's ``GraphMetrics`` — no SQL, no LLM, no language branches (R1.1/R1.4/R4).
The heuristic is **namespace/dir prefix refined by dependency direction**, with a **pure
dependency-direction fallback** when namespaces are uninformative (flat PSR-0/global legacy) —
locked 2026-08-11. Identical input yields byte-identical output (R4.2); layer names are the repo's
own dir prefixes (or direction labels in the fallback), never a per-language taxonomy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from code_atlas.onboarding.metrics import GraphMetrics, NodeMetric

# Derived-from-source: a pin test cross-checks this tuple against the methods assign_layers() emits,
# rather than re-typing a copy (R6.7 / derived-not-listed-invariant).
LAYER_METHODS: tuple[str, ...] = ("namespace-prefix", "dependency-direction-fallback")

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


def _prefix(module: str) -> str:
    """The module's directory prefix — its parent dir. Paths are POSIX-normalised at index time, so
    splitting on ``/`` is language-agnostic (R1.1); a root-level file has the empty prefix."""
    head, sep, _ = module.rpartition("/")
    return head if sep else ""


def _by_prefix(modules: tuple[NodeMetric, ...]) -> tuple[ModuleLayer, ...]:
    """Primary path: group by dir prefix, order the groups by net dependency direction (R2)."""
    net: dict[str, int] = {}
    for metric in modules:
        prefix = _prefix(metric.key)
        net[prefix] = net.get(prefix, 0) + metric.fan_out - metric.fan_in
    # Source-like (net-outward) groups lead; ties broken by name for determinism (R4.2).
    order = sorted(net, key=lambda prefix: (-net[prefix], prefix))
    rank_of = {prefix: rank for rank, prefix in enumerate(order)}
    assigned = [
        ModuleLayer(metric.key, _prefix(metric.key), rank_of[_prefix(metric.key)])
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
    """Assign modules to ordered architectural layers over 083's metrics (task 084).

    Namespace/dir prefix refined by dependency direction; a pure dependency-direction fallback when
    the prefixes are uninformative (≤ 1 distinct prefix — flat PSR-0/global legacy). Deterministic
    regardless of input module order (R4.2). Module unit = ``file_path`` (locked 2026-08-11).
    """
    modules = metrics.modules
    prefixes = {_prefix(metric.key) for metric in modules}
    if len(prefixes) <= 1:
        assigned = _by_direction(modules)
        method = "dependency-direction-fallback"
    else:
        assigned = _by_prefix(modules)
        method = "namespace-prefix"
    layers: list[str] = []
    for module_layer in sorted(assigned, key=lambda m: m.rank):
        if module_layer.layer not in layers:
            layers.append(module_layer.layer)
    return LayerAssignment(layers=tuple(layers), modules=assigned, method=method)
