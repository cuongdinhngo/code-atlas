"""Narrative reading-steps over the budgeted tour subgraph (task 111, M11).

A tour is a reading order with a reason, not one line per file: ``ordered_stops`` (087) yields one
stop per module, so a 500-module budget renders a 500-stop ``tour.md``. This module groups those
stops into ``[5, 15]`` steps — layer rank (110) crossed with BFS depth from the entry seeds, each
SCC collapsed to one contribution — so a cycle is stated once, never listed per member (AC2). Pure
graph/derivation: no SQL, no LLM, no language branch (R1.1/R1.4/R4). Prose is 117; here every field
is assembled from dataset facts, so a regenerated tour cannot go stale.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from code_atlas.onboarding.layers import UNCATEGORISED, LayerAssignment, layer_description
from code_atlas.onboarding.metrics import GraphMetrics
from code_atlas.onboarding.prose import SLOT_STEP, ProseRequest, ProseRun
from code_atlas.onboarding.tour import TourStop

MIN_STEPS = 5
MAX_STEPS = 15
MODULES_PER_STEP = 5

# How many of a step's modules one prose request may show, with their summaries. The request
# identity folds in the full named list, so two steps differing past the cap stay distinct.
MODULES_IN_PROSE = 5

__all__ = ["MAX_STEPS", "MIN_STEPS", "MODULES_PER_STEP", "TourStep", "build_steps"]


@dataclass(frozen=True)
class TourStep:
    """One reading step: an ordered group of modules with a structural reason (117 adds prose)."""

    order: int
    title: str
    modules: tuple[str, ...]
    why: str
    covers: int
    cycle_size: int


@dataclass(frozen=True)
class _Bucket:
    """A group of SCC components sharing a layer band; the pre-render unit that clamping moves."""

    components: tuple[tuple[str, ...], ...]
    rank: int
    depth: int
    layer: str
    covers: int
    cycle_size: int


def _bfs_depth(
    files: Sequence[str],
    edges: Sequence[tuple[str, str]],
    entry_points: Sequence[str],
) -> dict[str, int]:
    """Shortest edge-distance from the entry seeds; an unreached file sits one past the deepest.

    Seeds are the proven zero-inbound files that fall inside the budget, else the whole set — a
    subgraph with no visible entry still bands deterministically (R4.2).
    """
    universe = set(files)
    adjacency: dict[str, list[str]] = {file: [] for file in files}
    for source, target in edges:
        if source in universe and target in universe and source != target:
            adjacency[source].append(target)
    for neighbours in adjacency.values():
        neighbours.sort()
    seeds = sorted(file for file in entry_points if file in universe) or sorted(universe)
    depth: dict[str, int] = {}
    queue: deque[str] = deque()
    for seed in seeds:
        depth[seed] = 0
        queue.append(seed)
    while queue:
        current = queue.popleft()
        for neighbour in adjacency[current]:
            if neighbour not in depth:
                depth[neighbour] = depth[current] + 1
                queue.append(neighbour)
    unreached = max(depth.values(), default=-1) + 1
    for file in files:
        depth.setdefault(file, unreached)
    return depth


def _components(stops: Sequence[TourStop]) -> tuple[tuple[str, ...], ...]:
    """The distinct SCC components in reading order; each appears once (087 emits one stop/file)."""
    seen: set[str] = set()
    ordered: list[tuple[str, ...]] = []
    for stop in stops:
        if stop.file in seen:
            continue
        component = tuple(sorted(stop.scc)) if stop.scc else (stop.file,)
        ordered.append(component)
        seen.update(component)
    return tuple(ordered)


def build_steps(
    stops: Sequence[TourStop],
    assignment: LayerAssignment,
    metrics: GraphMetrics,
    edges: Sequence[tuple[str, str]],
    entry_points: Sequence[str],
    *,
    community_of: Mapping[str, str] | None = None,
    min_steps: int = MIN_STEPS,
    max_steps: int = MAX_STEPS,
    modules_per_step: int = MODULES_PER_STEP,
    prose: ProseRun | None = None,
    docline_of: Mapping[str, str] | None = None,
    descriptions: Mapping[str, str] | None = None,
) -> tuple[TourStep, ...]:
    """Group the ordered stops into ``[min, max]`` reading steps (see module docstring).

    ``min_steps`` is a target the grouping reaches by splitting when material allows, never a floor
    the caller can rely on for a tiny subgraph; ``max_steps`` is the hard ceiling the quality gate
    enforces (109 C4). Identical input yields identical steps, titles and order (R4.2).

    ``prose`` is the 117 seam over the ``why`` slot: with it unset every step keeps the structural
    sentence below (AC1). Grouping, order, titles and counts are never the seam's to change.
    """
    if not stops:
        return ()
    rank_of = {module.module: module.rank for module in assignment.modules}
    layer_of = {module.module: module.layer for module in assignment.modules}
    # Override UNCATEGORISED with community label when community detection is available (211).
    if community_of:
        layer_of = {
            f: community_of.get(f, layer_of.get(f, ""))
            if layer_of.get(f, UNCATEGORISED) == UNCATEGORISED
            else layer_of.get(f, "")
            for f in layer_of
        }
    fan_in = {metric.key: metric.fan_in for metric in metrics.modules}
    depth = _bfs_depth([stop.file for stop in stops], edges, entry_points)

    buckets = _initial_buckets(_components(stops), rank_of, layer_of, depth)
    buckets = _merge_to_ceiling(buckets, layer_of, max_steps)
    buckets = _split_to_floor(buckets, layer_of, fan_in, min_steps)
    steps = _render_steps(buckets, fan_in, modules_per_step)
    if prose is None:
        return steps
    return _narrate(steps, prose, fan_in, docline_of or {}, descriptions or {})


def _bucket_of(
    components: Sequence[tuple[str, ...]],
    rank_of: Mapping[str, int],
    layer_of: Mapping[str, str],
) -> _Bucket:
    """Build one bucket from a set of components, deriving rank/cycle/covers from members."""
    ordered = tuple(sorted(components))
    lead = ordered[0][0]
    ranks = [rank_of.get(member, 0) for component in ordered for member in component]
    covers = sum(len(component) for component in ordered)
    biggest = max((len(component) for component in ordered), default=0)
    return _Bucket(
        components=ordered,
        rank=min(ranks, default=0),
        depth=0,
        layer=layer_of.get(lead, ""),
        covers=covers,
        cycle_size=biggest if biggest > 1 else 0,
    )


def _initial_buckets(
    components: Sequence[tuple[str, ...]],
    rank_of: Mapping[str, int],
    layer_of: Mapping[str, str],
    depth: Mapping[str, int],
) -> list[_Bucket]:
    """One bucket per (rank, depth) band; an SCC bands by its min member so it is one step (AC2)."""
    grouped: dict[tuple[int, int], list[tuple[str, ...]]] = {}
    for component in components:
        rank = min(rank_of.get(member, 0) for member in component)
        band = min(depth.get(member, 0) for member in component)
        grouped.setdefault((rank, band), []).append(component)
    buckets: list[_Bucket] = []
    for (rank, band) in sorted(grouped):
        bucket = _bucket_of(grouped[(rank, band)], rank_of, layer_of)
        buckets.append(replace(bucket, rank=rank, depth=band))
    return buckets


def _merge_pair(left: _Bucket, right: _Bucket, layer_of: Mapping[str, str]) -> _Bucket:
    """Fuse two adjacent buckets, keeping the lower band and the dominant (min-rank) layer."""
    components = left.components + right.components
    lead = min(components, key=lambda component: component[0])[0]
    covers = left.covers + right.covers
    cycle = max(left.cycle_size, right.cycle_size)
    return _Bucket(
        components=tuple(sorted(components)),
        rank=min(left.rank, right.rank),
        depth=min(left.depth, right.depth),
        layer=layer_of.get(lead, left.layer if left.rank <= right.rank else right.layer),
        covers=covers,
        cycle_size=cycle if cycle > 1 else 0,
    )


def _merge_to_ceiling(buckets: list[_Bucket], layer_of: Mapping[str, str],
                      max_steps: int) -> list[_Bucket]:
    """Merge the smallest adjacent same-rank pair until at most ``max_steps`` remain (ticket).

    When no same-rank neighbours remain the smallest adjacent pair overall is merged, so the loop
    always terminates rather than stalling above the ceiling.
    """
    while len(buckets) > max_steps:
        same = [i for i in range(len(buckets) - 1) if buckets[i].rank == buckets[i + 1].rank]
        candidates = same or list(range(len(buckets) - 1))
        index = min(candidates, key=lambda i: (buckets[i].covers + buckets[i + 1].covers, i))
        merged = _merge_pair(buckets[index], buckets[index + 1], layer_of)
        buckets[index : index + 2] = [merged]
    return buckets


def _split_to_floor(buckets: list[_Bucket], layer_of: Mapping[str, str],
                    fan_in: Mapping[str, int], min_steps: int) -> list[_Bucket]:
    """Split the largest multi-component bucket by fan-in until ``min_steps`` is met or none can.

    A single-component bucket (one file, or one SCC) is indivisible, so a subgraph with too few
    components simply yields fewer than ``min_steps`` steps — the floor is a target, not a promise.
    """
    while len(buckets) < min_steps:
        splittable = [i for i, bucket in enumerate(buckets) if len(bucket.components) > 1]
        if not splittable:
            break
        index = max(splittable, key=lambda i: (buckets[i].covers, -i))
        head, tail = _split_bucket(buckets[index], layer_of, fan_in)
        buckets[index : index + 1] = [head, tail]
    return buckets


def _split_bucket(bucket: _Bucket, layer_of: Mapping[str, str],
                  fan_in: Mapping[str, int]) -> tuple[_Bucket, _Bucket]:
    """Halve a bucket's components by descending fan-in, keeping band order stable (R4.2)."""
    ranked = sorted(
        bucket.components,
        key=lambda component: (-max(fan_in.get(member, 0) for member in component), component[0]),
    )
    cut = (len(ranked) + 1) // 2
    ranks = {member: bucket.rank for component in ranked for member in component}
    head = _bucket_of(ranked[:cut], ranks, layer_of)
    tail = _bucket_of(ranked[cut:], ranks, layer_of)
    head = replace(head, rank=bucket.rank, depth=bucket.depth)
    tail = replace(tail, rank=bucket.rank, depth=bucket.depth)
    return head, tail


def _named_modules(bucket: _Bucket, fan_in: Mapping[str, int],
                   modules_per_step: int) -> tuple[str, ...]:
    """The step's headline modules: the highest-fan-in member of each component, capped, sorted."""
    leads = [max(component, key=lambda member: (fan_in.get(member, 0), member))
             for component in bucket.components]
    leads.sort(key=lambda member: (-fan_in.get(member, 0), member))
    return tuple(leads[:modules_per_step])


def _why(bucket: _Bucket) -> str:
    """A structural sentence from dataset facts only — 117 replaces it with prose (AC6)."""
    line = f"{layer_description(bucket.layer)} Covers {bucket.covers} module(s)."
    if bucket.cycle_size:
        line += f" Includes a cycle of {bucket.cycle_size} modules."
    return line


def _render_steps(buckets: Sequence[_Bucket], fan_in: Mapping[str, int],
                  modules_per_step: int) -> tuple[TourStep, ...]:
    """Number the buckets, and where a layer spans several steps label each ``(i/k)`` (AC6)."""
    spans: dict[str, int] = {}
    for bucket in buckets:
        spans[bucket.layer] = spans.get(bucket.layer, 0) + 1
    seen: dict[str, int] = {}
    steps: list[TourStep] = []
    for order, bucket in enumerate(buckets, start=1):
        total = spans[bucket.layer]
        title = bucket.layer or "Modules"
        if total > 1:
            seen[bucket.layer] = seen.get(bucket.layer, 0) + 1
            title = f"{title} ({seen[bucket.layer]}/{total})"
        steps.append(
            TourStep(
                order=order,
                title=title,
                modules=_named_modules(bucket, fan_in, modules_per_step),
                why=_why(bucket),
                covers=bucket.covers,
                cycle_size=bucket.cycle_size,
            )
        )
    return tuple(steps)


def _narrate(
    steps: Sequence[TourStep],
    prose: ProseRun,
    fan_in: Mapping[str, int],
    docline_of: Mapping[str, str],
    descriptions: Mapping[str, str],
) -> tuple[TourStep, ...]:
    """Rewrite each step's ``why`` through the 117 seam, in order, chaining the previous step.

    Sequential on purpose: a reading order reads better when step N can refer to step N-1, so each
    request carries the prose already settled for its predecessor. That makes step N's cache key
    depend on N-1's, a chain that still replays byte-for-byte from a committed cache (AC3).
    """
    narrated: list[TourStep] = []
    previous = ""
    for step in steps:
        previous = prose.text(
            ProseRequest(
                slot=SLOT_STEP,
                key=str(step.order),
                default=step.why,
                facts=_step_facts(step, fan_in, docline_of, descriptions),
                names=(step.title, *step.modules),
                previous=previous,
            )
        )
        narrated.append(replace(step, why=previous))
    return tuple(narrated)


def _step_facts(
    step: TourStep,
    fan_in: Mapping[str, int],
    docline_of: Mapping[str, str],
    descriptions: Mapping[str, str],
) -> tuple[tuple[str, str], ...]:
    """One step's structural context: its layer, what it covers, and its modules with degrees."""
    layer = step.title.split(" (")[0]
    shown = step.modules[:MODULES_IN_PROSE]
    modules = "; ".join(
        f"{module} ({fan_in.get(module, 0)} dependents)"
        + (f": {docline_of[module]}" if docline_of.get(module) else "")
        for module in shown
    )
    return (
        ("step", str(step.order)),
        ("title", step.title),
        ("layer", layer),
        ("layer description", descriptions.get(layer, layer_description(layer))),
        ("modules covered", str(step.covers)),
        ("cycle size", str(step.cycle_size)),
        ("modules named", modules),
    )
