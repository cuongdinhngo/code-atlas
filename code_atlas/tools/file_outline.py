"""``file_outline`` — symbols + line ranges for one path, no bodies (§12)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore, Row

NAME = "file_outline"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def file_outline(path: str, detail_level: DetailLevel = "standard") -> dict[str, object]:
        """Symbols in ``path`` with ``line_start``/``line_end`` — never source bodies."""
        if not config.db_path.is_file():
            return _empty(path, detail_level=detail_level, db_path=str(config.db_path))
        limit = config.max_results
        with GraphStore(config.db_path) as store:
            rows = store.nodes_by_file(path, limit=limit + 1)
        truncated = len(rows) > limit
        results = [_hit(row) for row in rows[:limit]]
        return _result(
            path,
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            truncated=truncated,
        )

    return file_outline


def _hit(row: Mapping[str, object] | Row) -> dict[str, object]:
    hit: dict[str, object] = {}
    hit["qname"] = row["qualified_name"]
    hit["kind"] = row["kind"]
    hit["name"] = row["name"]
    hit["line_start"] = row["line_start"]
    hit["line_end"] = row["line_end"]
    return hit


def _empty(path: str, *, detail_level: str, db_path: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "indexed": False,
        "path": path,
        "results": [],
        "truncated": False,
    }
    if detail_level == "standard":
        payload["db_path"] = db_path
    return payload


def _result(
    path: str,
    results: list[dict[str, object]],
    *,
    detail_level: str,
    db_path: str,
    truncated: bool,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "indexed": True,
        "path": path,
        "results": results,
        "truncated": truncated,
    }
    if detail_level == "standard":
        payload["db_path"] = db_path
    return payload
