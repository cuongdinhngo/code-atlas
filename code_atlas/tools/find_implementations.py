"""``find_implementations`` — direct EXTENDS/IMPLEMENTS subtypes (§12)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config
from code_atlas.contract import IMPL_KINDS
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

NAME = "find_implementations"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_implementations(
        qname: str, detail_level: DetailLevel = "standard"
    ) -> dict[str, object]:
        """Direct subtypes that EXTEND or IMPLEMENT ``qname`` (not transitive — see impact/017)."""
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
                )
            total_count = store.count_edges_by_target(qname, kinds=IMPL_KINDS)
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
                )
            edges = store.edges_by_target(qname, kinds=IMPL_KINDS, limit=limit)
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
        )

    return find_implementations
