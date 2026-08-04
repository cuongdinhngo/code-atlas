"""``find_callers`` — who CALLS/NEW a qname, with optional depth (§12)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Literal, NamedTuple

from code_atlas.config import Config
from code_atlas.contract import CALLER_KINDS, CONFIDENCE_TIERS
from code_atlas.store import GraphStore
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    edge_hit,
    edge_id,
    empty_nav,
    nav_result,
    relation_reason,
)

NAME = "find_callers"

DetailLevel = Literal["minimal", "standard"]

_RESOLVED = CONFIDENCE_TIERS[0]
# Cap BFS counting so total_count stays honest-as-a-floor without walking the whole graph.
_COUNT_BUDGET_FACTOR = 10


class _CallersOutcome(NamedTuple):
    results: list[dict[str, object]]
    truncated: bool
    total_count: int
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

        ``total_count`` is the size of the BFS hit set within ``depth`` (exact at depth 1;
        a lower bound when a deeper walk hits the count budget).
        """
        if depth < 1:
            raise ValueError(f"depth must be >= 1, got {depth}")
        if not config.db_path.is_file():
            return empty_nav(qname, detail_level=detail_level, db_path=str(config.db_path))
        limit = config.max_results
        with GraphStore(config.db_path) as store:
            guard = FreshnessGuard(config, store)
            if guard.ensure_qname(qname) == "stale":
                return nav_result(
                    qname,
                    [],
                    detail_level=detail_level,
                    db_path=str(config.db_path),
                    truncated=False,
                    reason=REASON_INDEX_STALE,
                    total_count=0,
                    depth=depth,
                    frontier_skipped_non_resolved=0,
                    subject_refreshed_only=True,
                )
            outcome = _callers(store, qname, hops=depth, limit=limit)
            indexed = bool(store.nodes_by_qualified_name(qname, limit=1))
        reason = relation_reason(hit_total=outcome.total_count, symbol_indexed=indexed)
        return nav_result(
            qname,
            outcome.results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            truncated=outcome.truncated,
            reason=reason,
            total_count=outcome.total_count,
            depth=depth,
            frontier_skipped_non_resolved=outcome.frontier_skipped_non_resolved,
            subject_refreshed_only=True,
        )

    return find_callers


def _callers(store: GraphStore, qname: str, *, hops: int, limit: int) -> _CallersOutcome:
    """BFS over CALLS/NEW into ``qname``; only RESOLVED edges expand the frontier (A3 / HOW-5)."""
    if hops == 1:
        total = store.count_edges_by_target(qname, kinds=CALLER_KINDS)
        edges = store.edges_by_target(qname, kinds=CALLER_KINDS, limit=limit)
        hits = [edge_hit(edge, depth=1) for edge in edges]
        return _CallersOutcome(
            results=hits,
            truncated=total > len(hits),
            total_count=total,
            frontier_skipped_non_resolved=0,
        )

    results: list[dict[str, object]] = []
    seen_edge_ids: set[int] = set()
    visited_targets: set[str] = {qname}
    queue: deque[tuple[str, int]] = deque([(qname, 0)])
    skipped_non_resolved = 0
    total_count = 0
    count_budget = max(limit * _COUNT_BUDGET_FACTOR, limit + 1)
    hit_budget = False

    while queue and total_count < count_budget:
        target, hop = queue.popleft()
        if hop >= hops:
            continue
        remaining = count_budget - total_count
        for edge in store.edges_by_target(target, kinds=CALLER_KINDS, limit=remaining):
            eid = edge_id(edge)
            if eid in seen_edge_ids:
                continue
            seen_edge_ids.add(eid)
            total_count += 1
            if len(results) < limit:
                results.append(edge_hit(edge, depth=hop + 1))
            tier = str(edge.get("confidence_tier") or _RESOLVED)
            source = str(edge["source_qname"])
            if hop + 1 >= hops or source in visited_targets:
                if total_count >= count_budget:
                    hit_budget = True
                    break
                continue
            if tier == _RESOLVED:
                visited_targets.add(source)
                queue.append((source, hop + 1))
            else:
                skipped_non_resolved += 1
            if total_count >= count_budget:
                hit_budget = True
                break
    truncated = total_count > len(results) or hit_budget or bool(queue)
    return _CallersOutcome(
        results=results,
        truncated=truncated,
        total_count=total_count,
        frontier_skipped_non_resolved=skipped_non_resolved,
    )
