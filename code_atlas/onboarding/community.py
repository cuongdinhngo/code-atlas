"""Union-find community detection over the import graph (task 211, M11).

Groups tour files into communities from the edge graph — deriving structure the path vocabulary
cannot. Two passes: RESOLVED edges first (high confidence), HEURISTIC edges only where RESOLVED
left a file singleton (R5.2/AC5). The result replaces ``Uncategorised`` in the tour's step
grouping where path vocabulary is silent (R3 — vocabulary wins when it fires).

Pure graph computation — no SQL, no LLM, no language branch (R1.1/R1.4/R4). All iteration is
sorted so identical input yields identical output (R4.2/AC1).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath

from code_atlas.contract import CONFIDENCE_TIERS

# Derived, never re-spelled: a tier rename must not leave this module matching nothing (R3).
_RESOLVED, _HEURISTIC, _DYNAMIC = CONFIDENCE_TIERS
COMMUNITY_PREFIX = "Community/"

__all__ = ["COMMUNITY_PREFIX", "assign_communities"]


class _UnionFind:
    """Deterministic union-find with path compression; iteration order is sorted input order."""

    def __init__(self, nodes: Sequence[str]) -> None:
        self._parent: dict[str, str] = {node: node for node in nodes}

    def find(self, node: str) -> str:
        while self._parent.get(node, node) != node:
            grandparent = self._parent.get(self._parent[node], self._parent[node])
            self._parent[node] = grandparent
            node = grandparent
        return node

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        # Smaller root (alphabetically) becomes parent — the label is chosen separately.
        if ra < rb:
            self._parent[rb] = ra
        else:
            self._parent[ra] = rb

    def roots(self) -> frozenset[str]:
        return frozenset(self.find(node) for node in self._parent)

    def component(self, root: str) -> frozenset[str]:
        return frozenset(node for node in self._parent if self.find(node) == root)


def _undirected_degree(
    universe: frozenset[str],
    edge_tiers: Sequence[tuple[str, str, str]],
    allowed: frozenset[str],
) -> dict[str, int]:
    """Distinct neighbours per file over the given tiers; keys sorted for R4.2."""
    neighbours: dict[str, set[str]] = {node: set() for node in universe}
    for source, target, tier in edge_tiers:
        if source not in universe or target not in universe or source == target:
            continue
        if tier not in allowed:
            continue
        neighbours[source].add(target)
        neighbours[target].add(source)
    return {node: len(neighbours[node]) for node in universe}


def _labels(representative_of: Mapping[str, str]) -> dict[str, str]:
    """Label each community by its representative's stem — a named member, never a bare id (AC3).

    Two communities can share a stem (a mirrored tree does it routinely), and one label for both
    would merge them in the tour and union their layers in the crossings finding. A collided stem
    falls back to the representative's full extension-less path, which is unique by construction.
    """
    by_stem: dict[str, list[str]] = {}
    for root in sorted(representative_of):
        by_stem.setdefault(PurePosixPath(representative_of[root]).stem, []).append(root)
    labels: dict[str, str] = {}
    for stem, roots in sorted(by_stem.items()):
        for root in roots:
            unique = PurePosixPath(representative_of[root]).with_suffix("")
            name = stem if len(roots) == 1 else str(unique)
            labels[root] = f"{COMMUNITY_PREFIX}{name}"
    return labels


def assign_communities(
    files: Sequence[str],
    edge_tiers: Sequence[tuple[str, str, str]],
) -> Mapping[str, str]:
    """Map every file in ``files`` to a community label derived from the edge graph.

    Pass 1 unions files connected by RESOLVED edges. Pass 2 unions remaining singletons
    via HEURISTIC edges only (DYNAMIC never joins a community). A file with no edges is
    its own community. Labels are ``Community/<stem of most-connected member>`` (R2);
    degree ties break alphabetically (R4.2).
    """
    sorted_files = sorted(files)
    universe = frozenset(sorted_files)
    if not universe:
        return {}

    uf = _UnionFind(sorted_files)
    for source, target, tier in sorted(edge_tiers):
        if source in universe and target in universe and tier == _RESOLVED:
            uf.union(source, target)

    resolved_singletons = frozenset(
        node for node in sorted_files if uf.component(uf.find(node)) == frozenset({node})
    )
    for source, target, tier in sorted(edge_tiers):
        if (
            source in resolved_singletons
            and target in resolved_singletons
            and tier == _HEURISTIC
        ):
            uf.union(source, target)

    degree = _undirected_degree(universe, edge_tiers, frozenset({_RESOLVED, _HEURISTIC}))
    components = {root: uf.component(root) for root in sorted(uf.roots())}
    representative_of = {
        root: min(members, key=lambda member: (-degree[member], member))
        for root, members in components.items()
    }
    labels = _labels(representative_of)
    result: dict[str, str] = {}
    for root, members in components.items():
        for member in members:
            result[member] = labels[root]
    return result
