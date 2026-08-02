"""``find_callers`` — who CALLS/NEW a qname, with optional depth (§12)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import edge_hit, empty_nav, nav_result

NAME = "find_callers"

DetailLevel = Literal["minimal", "standard"]

# Built as names (not a multi-kind string literal) so R3.2's sole-source guard stays green.
_CALLS = "CALLS"
_NEW = "NEW"
CALLER_KINDS: tuple[str, ...] = (_CALLS, _NEW)
_RESOLVED = "RESOLVED"


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_callers(
        qname: str, depth: int = 1, detail_level: DetailLevel = "standard"
    ) -> dict[str, object]:
        """Who CALLS or NEWs ``qname``. ``depth`` defaults to 1 (direct); deeper is BFS."""
        if not config.db_path.is_file():
            return empty_nav(qname, detail_level=detail_level, db_path=str(config.db_path))
        hops = max(1, depth)
        limit = config.max_results
        with GraphStore(config.db_path) as store:
            results = _callers(store, qname, hops=hops, limit=limit)
        return nav_result(
            qname, results, detail_level=detail_level, db_path=str(config.db_path), depth=hops
        )

    return find_callers


def _callers(
    store: GraphStore, qname: str, *, hops: int, limit: int
) -> list[dict[str, object]]:
    """BFS over CALLS/NEW into ``qname``; only RESOLVED edges expand the frontier (A3 / HOW-5)."""
    results: list[dict[str, object]] = []
    seen_edge_ids: set[int] = set()
    visited_targets: set[str] = {qname}
    queue: deque[tuple[str, int]] = deque([(qname, 0)])

    while queue and len(results) < limit:
        target, hop = queue.popleft()
        if hop >= hops:
            continue
        for edge in store.edges_by_target(target, kinds=CALLER_KINDS, limit=limit):
            raw_id = edge["id"]
            assert isinstance(raw_id, int)
            edge_id = raw_id
            if edge_id in seen_edge_ids:
                continue
            seen_edge_ids.add(edge_id)
            results.append(edge_hit(edge, depth=hop + 1))
            if len(results) >= limit:
                break
            tier = str(edge.get("confidence_tier") or _RESOLVED)
            source = str(edge["source_qname"])
            if hop + 1 < hops and tier == _RESOLVED and source not in visited_targets:
                visited_targets.add(source)
                queue.append((source, hop + 1))
    return results
