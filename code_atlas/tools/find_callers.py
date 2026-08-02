"""``find_callers`` — who CALLS/NEW a qname, with optional depth (§12)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Literal, NamedTuple

from code_atlas.config import Config
from code_atlas.contract import CALLER_KINDS, CONFIDENCE_TIERS
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import edge_hit, edge_id, empty_nav, nav_result

NAME = "find_callers"

DetailLevel = Literal["minimal", "standard"]

_RESOLVED = CONFIDENCE_TIERS[0]


class _CallersOutcome(NamedTuple):
    results: list[dict[str, object]]
    truncated: bool
    frontier_skipped_non_resolved: int


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_callers(
        qname: str, depth: int = 1, detail_level: DetailLevel = "standard"
    ) -> dict[str, object]:
        """Who CALLS or NEWs ``qname``.

        ``depth`` defaults to 1 (direct). Deeper values BFS over CALLS/NEW, but only
        ``RESOLVED`` edges expand the frontier — HEURISTIC/DYNAMIC hits are returned and counted
        in ``frontier_skipped_non_resolved`` when a deeper hop was requested.
        """
        if depth < 1:
            raise ValueError(f"depth must be >= 1, got {depth}")
        if not config.db_path.is_file():
            return empty_nav(qname, detail_level=detail_level, db_path=str(config.db_path))
        limit = config.max_results
        with GraphStore(config.db_path) as store:
            outcome = _callers(store, qname, hops=depth, limit=limit)
        return nav_result(
            qname,
            outcome.results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            truncated=outcome.truncated,
            depth=depth,
            frontier_skipped_non_resolved=outcome.frontier_skipped_non_resolved,
        )

    return find_callers


def _callers(store: GraphStore, qname: str, *, hops: int, limit: int) -> _CallersOutcome:
    """BFS over CALLS/NEW into ``qname``; only RESOLVED edges expand the frontier (A3 / HOW-5)."""
    results: list[dict[str, object]] = []
    seen_edge_ids: set[int] = set()
    visited_targets: set[str] = {qname}
    queue: deque[tuple[str, int]] = deque([(qname, 0)])
    skipped_non_resolved = 0

    while queue and len(results) < limit:
        target, hop = queue.popleft()
        if hop >= hops:
            continue
        for edge in store.edges_by_target(target, kinds=CALLER_KINDS, limit=limit):
            eid = edge_id(edge)
            if eid in seen_edge_ids:
                continue
            seen_edge_ids.add(eid)
            results.append(edge_hit(edge, depth=hop + 1))
            if len(results) >= limit:
                break
            tier = str(edge.get("confidence_tier") or _RESOLVED)
            source = str(edge["source_qname"])
            if hop + 1 >= hops or source in visited_targets:
                continue
            if tier == _RESOLVED:
                visited_targets.add(source)
                queue.append((source, hop + 1))
            else:
                skipped_non_resolved += 1
    return _CallersOutcome(
        results=results,
        truncated=len(results) >= limit,
        frontier_skipped_non_resolved=skipped_non_resolved,
    )
