"""SCC condensation + a deterministic reading-order over a module subgraph (task 087 / 131).

Pure graph reasoning — no SQL and no language branches (R1.1/R1.4). The store supplies a
node-budgeted file-grain subgraph; this module condenses cycles and orders the DAG. Among
several roots, the order prefers files that lead somewhere and 110's reading-seed layer rank
(HTTP before Config) — path sort alone opened tours on lint files (131).
"""

from __future__ import annotations

import heapq
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

from code_atlas.onboarding.layers import reading_seed_rank

RATIONALE_ENTRY = "entry point (zero inbound)"
RATIONALE_OUTSIDE = "reached from outside the walk"


@dataclass(frozen=True)
class TourStop:
    """One file in reading order, with a one-line reason a newcomer can use."""

    file: str
    rationale: str
    scc: tuple[str, ...]


def _components(
    nodes: Sequence[str], edges: Sequence[tuple[str, str]]
) -> tuple[tuple[str, ...], ...]:
    """Tarjan SCCs, iterative; members of each component are sorted (R4.2).

    The explicit work-stack is not a style choice: a recursive walk dies with
    ``RecursionError`` once the budget admits a chain deeper than the interpreter limit.
    """
    adj: dict[str, list[str]] = {node: [] for node in nodes}
    for source, target in edges:
        if source in adj and target in adj and source != target:
            adj[source].append(target)
    for neighbours in adj.values():
        neighbours.sort()

    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    low: dict[str, int] = {}
    found: list[tuple[str, ...]] = []

    def close(vertex: str) -> None:
        """Pop one completed component off the SCC stack."""
        members: list[str] = []
        while True:
            member = stack.pop()
            on_stack.remove(member)
            members.append(member)
            if member == vertex:
                break
        found.append(tuple(sorted(members)))

    for root in sorted(nodes):
        if root in indices:
            continue
        work: list[tuple[str, int]] = [(root, 0)]
        while work:
            vertex, cursor = work[-1]
            if cursor == 0:
                indices[vertex] = low[vertex] = index
                index += 1
                stack.append(vertex)
                on_stack.add(vertex)
            descended = False
            neighbours = adj[vertex]
            while cursor < len(neighbours):
                next_vertex = neighbours[cursor]
                cursor += 1
                if next_vertex not in indices:
                    work[-1] = (vertex, cursor)
                    work.append((next_vertex, 0))
                    descended = True
                    break
                if next_vertex in on_stack:
                    low[vertex] = min(low[vertex], indices[next_vertex])
            if descended:
                continue
            work.pop()
            if low[vertex] == indices[vertex]:
                close(vertex)
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[vertex])
    return tuple(found)


def _out_degree(nodes: Collection[str], edges: Sequence[tuple[str, str]]) -> dict[str, int]:
    """Distinct cross-file targets per file — the same breadth signal store ranking uses (106)."""
    universe = frozenset(nodes)
    targets: dict[str, set[str]] = {node: set() for node in nodes}
    for source, target in edges:
        if source in universe and target in universe and source != target:
            targets[source].add(target)
    return {node: len(targets[node]) for node in nodes}


def _ready_key(
    component: tuple[str, ...],
    degrees: Mapping[str, int],
    entries: frozenset[str] | None,
) -> tuple[int, int, int, int, str]:
    """Ready-set order: proven entries, then leads-somewhere, layer, out-degree, path."""
    return min(
        (
            0 if (entries is None or file in entries) else 1,
            0 if degrees.get(file, 0) > 0 else 1,
            reading_seed_rank(file),
            -degrees.get(file, 0),
            file,
        )
        for file in component
    )


def _topo(
    components: Sequence[tuple[str, ...]],
    edges: Sequence[tuple[str, str]],
    entries: frozenset[str] | None,
) -> tuple[tuple[str, ...], ...]:
    """Kahn order of the condensation; ready-set keyed for a reading order (131), total (R4.2)."""
    owner = {node: i for i, component in enumerate(components) for node in component}
    size = len(components)
    inbound = [0] * size
    outbound: list[set[int]] = [set() for _ in range(size)]
    for source, target in edges:
        if source not in owner or target not in owner:
            continue
        src, tgt = owner[source], owner[target]
        if src != tgt and tgt not in outbound[src]:
            outbound[src].add(tgt)
            inbound[tgt] += 1

    degrees = _out_degree(
        tuple(node for component in components for node in component), edges
    )
    ready = [
        (_ready_key(components[i], degrees, entries), i)
        for i in range(size)
        if inbound[i] == 0
    ]
    heapq.heapify(ready)
    ordered: list[tuple[str, ...]] = []
    while ready:
        _, current = heapq.heappop(ready)
        ordered.append(components[current])
        for nxt in sorted(outbound[current]):
            inbound[nxt] -= 1
            if inbound[nxt] == 0:
                heapq.heappush(
                    ready, (_ready_key(components[nxt], degrees, entries), nxt)
                )
    return tuple(ordered)


def _rationale(
    file: str,
    component: tuple[str, ...],
    inbound: dict[str, set[str]],
    emitted: set[str],
    entries: frozenset[str] | None,
) -> str:
    """One line: entry, cycle membership, or the earliest predecessor already walked."""
    if len(component) > 1:
        return "cycle with " + ", ".join(component)
    walked: set[str] = inbound.get(file, set()) & emitted
    if walked:
        return "reached from " + min(walked)
    # No visible predecessor is not proof of none: the budget may have dropped it (102).
    if entries is None or file in entries:
        return RATIONALE_ENTRY
    return RATIONALE_OUTSIDE


def ordered_stops(
    files: Sequence[str],
    edges: Sequence[tuple[str, str]],
    entry_points: Collection[str] | None = None,
) -> tuple[TourStop, ...]:
    """Reading order: source SCCs first, members sorted inside a cycle, each file once.

    ``entry_points`` is the set the store proved has zero inbound. ``None`` trusts the
    subgraph instead — for a caller holding the whole graph, where the two agree.
    """
    if not files:
        return ()
    proven = None if entry_points is None else frozenset(entry_points)
    universe = frozenset(files)
    components = _topo(_components(tuple(sorted(universe)), edges), edges, proven)
    inbound: dict[str, set[str]] = {}
    for source, target in edges:
        if source in universe and target in universe and source != target:
            inbound.setdefault(target, set()).add(source)
    stops: list[TourStop] = []
    emitted: set[str] = set()
    for component in components:
        for file in component:
            stops.append(
                TourStop(
                    file=file,
                    rationale=_rationale(file, component, inbound, emitted, proven),
                    scc=component,
                )
            )
            emitted.add(file)
    return tuple(stops)
