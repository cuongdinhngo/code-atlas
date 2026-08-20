"""Deterministic architectural-layer assignment for Phase-3 onboarding (084, M10; 103, 104, 086).

Pure functions over 083's ``GraphMetrics`` — no SQL, no LLM, no language branches (R1.1/R1.4/R4).
The heuristic is **dominant-subtree** (tasks 104, 105): group modules beneath the top-level dir that
carries the most dependency mass (Σ fan_in+fan_out, so a flat settings dir can't out-vote a small
source tree — task 105); strip the common prefix *within* that subtree, layer by the first remaining
segment, while every **other** top-level directory becomes its own layer. A **pure
dependency-direction fallback** takes over when the paths yield < 2 named groups (flat legacy, or a
single directory). Identical input yields byte-identical output (R4.2); layer names are the repo's
own path segments (or direction labels), never a per-language taxonomy. ``cross_layer_edges`` (086)
aggregates module-grain edges into the layer → layer crossings the overview tool renders.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from code_atlas.onboarding.metrics import GraphMetrics, NodeMetric

# Derived-from-source: a pin test cross-checks this tuple against the methods assign_layers() emits,
# rather than re-typing a copy (R6.7 / derived-not-listed-invariant).
LAYER_METHODS: tuple[str, ...] = (
    "responsibility",
    "dominant-subtree",
    "dependency-direction-fallback",
)

# A module at the repo root (no directory) has no path segment to name a layer; it lands here
# rather than emitting the empty string (task 104 residual).
_ROOT_LAYER = "(root)"

# The fallback orders modules into direction bands (entry → foundation). The SET is derived: a pin
# test asserts it equals DIRECTION_LABELS, so a new metrics label cannot ship unplaced (R6.7). The
# ORDER is a semantic choice — sources depend on sinks, so sources lead.
_FALLBACK_ORDER: tuple[str, ...] = ("source", "mixed", "sink", "isolated")

UNCATEGORISED = "Uncategorised"

# The responsibility vocabulary (task 110, ratified STANDARD under R2.2 — every word is an industry
# architectural convention, none names a repo, product or framework). Keyword → layer name.
_VOCABULARY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("HTTP / Entry", ("controller", "handler", "route", "endpoint", "api")),
    ("Services", ("service", "usecase")),
    ("Domain / Data", ("model", "entity", "repository")),
    ("Views", ("view", "template", "page", "form")),
    ("Middleware / Auth", ("middleware", "filter", "auth", "session")),
    ("Background Jobs", ("job", "cron", "queue", "worker")),
    ("Integration / Reporting", ("report", "export", "integration")),
    ("Shared Library", ("lib", "util", "helper", "common", "system")),
    ("Tests", ("test", "spec", "mock")),
    ("Config / Migration", ("config", "migration")),
    ("Vendor / Framework", ("vendor",)),
)
RESPONSIBILITY_KEYWORDS: dict[str, str] = {
    keyword: layer for layer, keywords in _VOCABULARY for keyword in keywords
}

# A description for every layer name a run can emit — the 12 responsibility layers, the four
# direction bands, and the root — so 109's C3 is real, not vacuous. LLM prose replaces these in 117.
LAYER_DESCRIPTIONS: dict[str, str] = {
    "HTTP / Entry": "Request entry points: controllers, routes and API handlers.",
    "Services": "Application services and use-cases that coordinate domain logic.",
    "Domain / Data": "Domain models, entities and repositories — the data layer.",
    "Views": "Presentation: views, templates, pages and forms.",
    "Middleware / Auth": "Request middleware, filters, authentication and sessions.",
    "Background Jobs": "Asynchronous work: jobs, cron tasks, queues and workers.",
    "Integration / Reporting": "Outbound integration, reporting and data export.",
    "Shared Library": "Shared libraries, utilities and helpers reused across the codebase.",
    "Tests": "Automated tests, specs and mocks.",
    "Config / Migration": "Configuration and database migrations.",
    "Vendor / Framework": "Third-party vendor and framework code.",
    UNCATEGORISED: "Modules whose path matched no responsibility keyword — a naming-debt signal.",
    "source": "Entry-side modules with outward dependencies and none inbound.",
    "sink": "Foundation modules others depend on, depending on nothing indexed.",
    "mixed": "Modules with dependencies both ways, including cycles.",
    "isolated": "Modules with no dependency either way.",
    _ROOT_LAYER: "Files at the repository root.",
}


def layer_description(layer: str) -> str:
    """A non-empty description for any layer name — ratified prose or a structural default (110)."""
    return LAYER_DESCRIPTIONS.get(layer, f'Modules grouped under "{layer}".')


def _match_keyword(segment: str) -> str | None:
    """The layer a path segment names, or None. Case-insensitive, simple-plural aware (110)."""
    seg = segment.lower()
    candidates = [seg]
    if seg.endswith("ies"):
        candidates.append(seg[:-3] + "y")
    elif seg.endswith("s"):
        candidates.append(seg[:-1])
    for candidate in candidates:
        layer = RESPONSIBILITY_KEYWORDS.get(candidate)
        if layer is not None:
            return layer
    return None


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


@dataclass(frozen=True)
class LayerEdge:
    """How many module-grain dependencies cross from one layer into another (task 086)."""

    source: str
    target: str
    count: int

    def as_dict(self) -> dict[str, object]:
        """A plain, order-stable dict view — the serialisation the overview tool renders."""
        return {"source": self.source, "target": self.target, "count": self.count}


def cross_layer_edges(
    module_edges: tuple[tuple[str, str], ...], assignment: LayerAssignment
) -> tuple[LayerEdge, ...]:
    """Aggregate module-grain edges into layer → layer counts; same-layer pairs are not crossings.

    Heaviest first, ties by name, so identical input yields byte-identical output (R4.2). A module
    the assignment does not cover cannot be placed and is skipped rather than guessed.
    """
    layer_of = {module.module: module.layer for module in assignment.modules}
    counts: dict[tuple[str, str], int] = {}
    for source, target in module_edges:
        pair = (layer_of.get(source), layer_of.get(target))
        if pair[0] is None or pair[1] is None or pair[0] == pair[1]:
            continue
        key = (pair[0], pair[1])
        counts[key] = counts.get(key, 0) + 1
    order = sorted(counts, key=lambda key: (-counts[key], key[0], key[1]))
    return tuple(LayerEdge(source, target, counts[(source, target)]) for source, target in order)


def _dirs(module: str) -> list[str]:
    """The module's directory segments (POSIX ``/``, filename dropped). Paths are POSIX-normalised
    at index time, so splitting on ``/`` is language-agnostic (R1.1); a root file has none."""
    return module.split("/")[:-1]


def _top_dir(module: str) -> str | None:
    """The module's top-level directory segment, or ``None`` for a file sitting at the repo root."""
    dirs = _dirs(module)
    return dirs[0] if dirs else None


def _responsibility_layer(module: str) -> str | None:
    """Deepest directory segment naming a responsibility, or None (deepest-wins, task 110 H2)."""
    for segment in reversed(_dirs(module)):
        layer = _match_keyword(segment)
        if layer is not None:
            return layer
    return None


def responsibility_layer(module: str) -> str | None:
    """The responsibility layer a module's PATH names, or None — 110's signal, without the grouping.

    Public because a consumer must key off the path, not off ``LayerAssignment.layers``: the 091
    refiner may RENAME a layer, which would silently empty a caller's bucket (task 113).
    """
    return _responsibility_layer(module)


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
    """Top-level dir with the most dependency mass (Σ fan_in+fan_out); mass ties fall back to module
    count, then name (R4.2). Mass over count so a flat settings dir can't out-vote a small connected
    source tree (105); count keeps the old most-populous pick on an edgeless index."""
    mass: dict[str, int] = {}
    count: dict[str, int] = {}
    for metric in modules:
        top = _top_dir(metric.key)
        if top is not None:
            mass[top] = mass.get(top, 0) + metric.fan_in + metric.fan_out
            count[top] = count.get(top, 0) + 1
    if not mass:
        return None
    return sorted(mass, key=lambda name: (-mass[name], -count[name], name))[0]


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
    """Assign modules to ordered architectural layers over 083's metrics (tasks 084, 103, 104, 110).

    Responsibility-first (110): group each module by the deepest path segment naming a role
    (``Uncategorised`` when none does), used when that yields >= 2 layers. Otherwise fall back to
    dominant-subtree grouping (105), then a pure dependency-direction fallback (084) for flat legacy
    or a single directory. Deterministic regardless of input order (R4.2). Unit = ``file_path``.
    """
    modules = metrics.modules
    responsibility = {m.key: (_responsibility_layer(m.key) or UNCATEGORISED) for m in modules}
    if len(set(responsibility.values())) >= 2:
        assigned = _by_group(modules, responsibility)
        method = "responsibility"
    else:
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


class LayerRefiner(Protocol):
    """The 091 seam: propose better human names for weak layers (the flat-namespace fallback case).

    Returns a ``{old_layer: new_layer}`` rename map — never a re-grouping, so coverage and order are
    preserved by construction. An LLM impl matches this from **outside** ``code_atlas/`` (R4.1)."""

    def refine_names(self, assignment: LayerAssignment, metrics: GraphMetrics) -> Mapping[str, str]:
        ...


class IdentityLayerRefiner:
    """The deterministic default: no rename, so output is byte-identical to 084 (AC3, R4/R4.1)."""

    def refine_names(
        self, assignment: LayerAssignment, metrics: GraphMetrics
    ) -> Mapping[str, str]:
        return {}


def refine_layers(
    assignment: LayerAssignment, metrics: GraphMetrics, refiner: LayerRefiner
) -> LayerAssignment:
    """Apply a refiner's rename map to 084's assignment, deterministically (task 091, M12).

    Only layer NAMES change; module coverage is preserved and ranks are renormalised (a merge keeps
    the min original rank). An empty/inapplicable map returns the assignment unchanged — the off
    path, byte-identical to 084 (AC3). ``method`` is untouched (its pin covers ``assign_layers``).
    """
    named = set(assignment.layers)
    renames = {
        old: new
        for old, new in refiner.refine_names(assignment, metrics).items()
        if old in named and isinstance(new, str) and new.strip() and new != old
    }
    if not renames:
        return assignment
    best_rank: dict[str, int] = {}
    for module in assignment.modules:
        new = renames.get(module.layer, module.layer)
        best_rank[new] = min(best_rank.get(new, module.rank), module.rank)
    order = sorted(best_rank, key=lambda name: (best_rank[name], name))
    rank_of = {name: rank for rank, name in enumerate(order)}
    modules = tuple(
        sorted(
            (
                ModuleLayer(
                    module.module,
                    renames.get(module.layer, module.layer),
                    rank_of[renames.get(module.layer, module.layer)],
                )
                for module in assignment.modules
            ),
            key=lambda module: module.module,
        )
    )
    return LayerAssignment(layers=tuple(order), modules=modules, method=assignment.method)
