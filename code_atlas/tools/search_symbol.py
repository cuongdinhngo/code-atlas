"""``search_symbol`` — ranked FTS + name hits (§12)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore, Row

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
        if not config.db_path.is_file():
            return _empty(detail_level=detail_level, db_path=str(config.db_path))
        cap = config.max_results if limit is None else min(limit, config.max_results)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        with GraphStore(config.db_path) as store:
            rows = store.search_nodes(query, kind=kind, namespace=namespace, limit=cap + 1)
        truncated = len(rows) > cap
        results = [_hit(row) for row in rows[:cap]]
        return _result(
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            truncated=truncated,
        )

    return search_symbol


def _hit(row: Mapping[str, object] | Row) -> dict[str, object]:
    hit: dict[str, object] = {}
    hit["qname"] = row["qualified_name"]
    hit["kind"] = row["kind"]
    hit["file"] = row["file_path"]
    hit["line"] = row["line_start"]
    return hit


def _empty(*, detail_level: str, db_path: str) -> dict[str, object]:
    payload: dict[str, object] = {"indexed": False, "results": [], "truncated": False}
    if detail_level == "standard":
        payload["db_path"] = db_path
    return payload


def _result(
    results: list[dict[str, object]],
    *,
    detail_level: str,
    db_path: str,
    truncated: bool,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "indexed": True,
        "results": results,
        "truncated": truncated,
    }
    if detail_level == "standard":
        payload["db_path"] = db_path
    return payload
