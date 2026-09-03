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

# Tier strings that count as high-confidence community evidence.
_RESOLVED_TIERS = frozenset({"RESOLVED"})
# The label prefix that distinguishes community names from vocabulary layer names.
COMMUNITY_PREFIX = "Community/"

__all__ = ["COMMUNITY_PREFIX", "assign_communities"]


class _UnionFind:
    """Deterministic union-find with path compression; iteration order is sorted input order."""

    def __init__(self, nodes: Sequence[str]) -> None:
        self._parent: dict[str, str] = {node: node for node in nodes}

    def find(self, node: str) -> str:
        while self._parent.get(node, node) != node:
            # Path compression — keep parent sorted, never random.
            grandparent = self._parent.get(self._parent[node], self._parent[node])
            self._parent[node] = grandparent
            node = grandparent
        return node

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        # Smaller root (alphabetically) becomes the representative — deterministic (R4.2).
        if ra < rb:
            self._parent[rb] = ra
        else:
            self._parent[ra] = rb

    def roots(self) -> frozenset[str]:
        return frozenset(self.find(node) for node in self._parent)

    def component(self, root: str) -> frozenset[str]:
        return frozenset(node for node in self._parent if self.find(node) == root)


def _community_label(representative: str) -> str:
    """Label from the representative's path stem — a named member, never a bare id (AC3)."""
    stem = PurePosixPath(representative).stem
    return f"{COMMUNITY_PREFIX}{stem}"


def assign_communities(
    files: Sequence[str],
    edge_tiers: Sequence[tuple[str, str, str]],
) -> Mapping[str, str]:
    """Map every file in ``files`` to a community label derived from the edge graph.

    Pass 1 unions files connected by RESOLVED edges. Pass 2 unions files that remain singletons
    via HEURISTIC edges (C2 — HEURISTIC evidence is weaker; it cannot override a RESOLVED
    community, only fill the gap when none exists). A file with no edges is its own community.

    Community labels are ``"Community/" + <stem of alphabetically-first member>`` — a
    path-derived name, never a bare integer (AC3). Identical input → identical output (R4.2).
    """
    sorted_files = sorted(files)
    universe = frozenset(sorted_files)
    if not universe:
        return {}

    uf = _UnionFind(sorted_files)

    # Pass 1 — RESOLVED edges only.
    for source, target, tier in sorted(edge_tiers):
        if source in universe and target in universe and tier in _RESOLVED_TIERS:
            uf.union(source, target)

    # Pass 2 — HEURISTIC edges, but only between files that RESOLVED left as singletons.
    resolved_singletons = frozenset(
        node for node in sorted_files if uf.component(uf.find(node)) == frozenset({node})
    )
    for source, target, tier in sorted(edge_tiers):
        if (
            source in resolved_singletons
            and target in resolved_singletons
            and tier not in _RESOLVED_TIERS
        ):
            uf.union(source, target)

    # Build label map: each component's label is derived from its alphabetically-first member.
    result: dict[str, str] = {}
    for root in sorted(uf.roots()):
        members = sorted(uf.component(root))
        label = _community_label(members[0])
        for member in members:
            result[member] = label
    return result
