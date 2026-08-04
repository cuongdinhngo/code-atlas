"""``find_references`` — resolved edges targeting a qname (§12)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_SUCH_SYMBOL,
    edge_hit,
    empty_nav,
    nav_result,
    relation_reason,
)

NAME = "find_references"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_references(qname: str, detail_level: DetailLevel = "standard") -> dict[str, object]:
        """Edges whose resolved ``target_qname`` is ``qname``, with confidence tiers.

        Only kinds the resolver links are visible (FQN edge kinds + ``INCLUDES``). Bare
        ``IMPORTS`` / ``CONTAINS`` / ``REFERENCES`` stay unlinkable until the resolver grows —
        they never appear here even though the SQL has no kind filter.
        """
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
                    subject_refreshed_only=True,
                )
            total_count = store.count_edges_by_target(qname)
            indexed = bool(store.nodes_by_qualified_name(qname, limit=1))
            if total_count == 0 and not indexed:
                return nav_result(
                    qname,
                    [],
                    detail_level=detail_level,
                    db_path=str(config.db_path),
                    truncated=False,
                    reason=REASON_NO_SUCH_SYMBOL,
                    total_count=0,
                    subject_refreshed_only=True,
                )
            edges = store.edges_by_target(qname, limit=limit)
            results = [edge_hit(edge) for edge in edges]
        truncated = total_count > len(results)
        return nav_result(
            qname,
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            truncated=truncated,
            reason=relation_reason(hit_total=total_count, symbol_indexed=indexed),
            total_count=total_count,
            subject_refreshed_only=True,
        )

    return find_references
