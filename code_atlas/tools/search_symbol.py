"""``search_symbol`` — ranked FTS + name hits (§12)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore, Row
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
    list_result,
)

NAME = "search_symbol"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def search_symbol(
        query: str,
        kind: str | None = None,
        namespace: str | None = None,
        limit: int | None = None,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """Ranked symbols matching ``query`` (FTS trigram, or name-prefix for queries < 3 chars).

        Returns ``{qname, kind, file, line}`` rows, capped by ``limit`` or ``CA_MAX_RESULTS``.
        Trigram cannot match terms under three characters; those use a name/qname prefix scan.
        """
        db_path = str(config.db_path)
        if not config.db_path.is_file():
            return list_result(
                [],
                detail_level=detail_level,
                db_path=db_path,
                truncated=False,
                reason=REASON_NOT_INDEXED,
                total_count=0,
                indexed=False,
            )
        cap = config.max_results if limit is None else min(limit, config.max_results)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        with GraphStore(config.db_path) as store:
            guard = FreshnessGuard(config, store)
            rows = store.search_nodes(query, kind=kind, namespace=namespace, limit=cap + 1)
            hit_paths = [str(row["file_path"]) for row in rows[:cap]]
            if guard.ensure_paths(hit_paths) == "stale":
                return list_result(
                    [],
                    detail_level=detail_level,
                    db_path=db_path,
                    truncated=False,
                    reason=REASON_INDEX_STALE,
                    total_count=0,
                )
            # Re-query after any repair so FTS/rows reflect the new content.
            rows = store.search_nodes(query, kind=kind, namespace=namespace, limit=cap + 1)
            truncated = len(rows) > cap
            results = [_hit(row) for row in rows[:cap]]
            if truncated:
                total_count = store.count_search_nodes(
                    query, kind=kind, namespace=namespace
                )
            else:
                total_count = len(results)
        reason = REASON_OK if results else REASON_NO_MATCHES
        return list_result(
            results,
            detail_level=detail_level,
            db_path=db_path,
            truncated=truncated,
            reason=reason,
            total_count=total_count,
        )

    return search_symbol


def _hit(row: Mapping[str, object] | Row) -> dict[str, object]:
    hit: dict[str, object] = {}
    hit["qname"] = row["qualified_name"]
    hit["kind"] = row["kind"]
    hit["file"] = row["file_path"]
    hit["line"] = row["line_start"]
    return hit
