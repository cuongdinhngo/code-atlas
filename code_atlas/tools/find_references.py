"""``find_references`` — resolved edges targeting a qname (§12)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools import call_site
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

    def find_references(
        qname: str,
        detail_level: DetailLevel = "standard",
        include_source: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, object]:
        """Edges whose resolved ``target_qname`` is ``qname``, with confidence tiers.

        Only kinds the resolver links are visible (FQN edge kinds + ``INCLUDES``). Bare
        ``IMPORTS`` / ``CONTAINS`` / ``REFERENCES`` stay unlinkable until the resolver grows —
        they never appear here even though the SQL has no kind filter.

        ``include_source`` (default off, so the common case stays token-frugal) adds each site's
        own source line as ``source``, capped in length. A site whose file drifted since indexing
        is never quoted: those hits carry ``source_stale`` instead.

        ``limit`` / ``offset`` page in store edge order (057); default limit is
        ``CA_MAX_RESULTS``.
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap = config.max_results if limit is None else min(limit, config.max_results)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        if not config.db_path.is_file():
            return empty_nav(qname, detail_level=detail_level, db_path=str(config.db_path))
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
            edges = store.edges_by_target(qname, limit=cap, offset=offset)
            results = [edge_hit(edge) for edge in edges]
            if include_source:
                call_site.annotate(config.root, store, results)
        truncated = offset + len(results) < total_count
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
