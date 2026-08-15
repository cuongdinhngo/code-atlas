"""``file_outline`` — symbols + line ranges for one path, no bodies (§12)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore, Row
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import REASON_INDEX_STALE, REASON_OK

NAME = "file_outline"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def file_outline(path: str, detail_level: DetailLevel = "standard") -> dict[str, object]:
        """What does this file define, and on what lines — without printing the source?

        Call this before you read or port a large file — it is the symbol map, not a body.
        Returns each symbol with its ``line_start``/``line_end``, never bodies. ``path`` may be
        absolute (under the repo root) or ``./``-prefixed; it is normalised to the repo-relative
        form stored in the index. ``found`` is false when that path is not indexed.
        """
        if not config.db_path.is_file():
            return _empty(
                path,
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
            )
        rel = _repo_relative(config.root, path)
        limit = config.max_results
        with GraphStore(config.db_path) as store:
            if store.file_hash(rel) is None:
                return _result(
                    rel,
                    [],
                    detail_level=detail_level,
                    db_path=str(config.db_path),
                    index_root=config.index_root,
                    truncated=False,
                    found=False,
                )
            guard = FreshnessGuard(config, store)
            if guard.ensure(rel) == "stale":
                return _result(
                    rel,
                    [],
                    detail_level=detail_level,
                    db_path=str(config.db_path),
                    index_root=config.index_root,
                    truncated=False,
                    found=True,
                    reason=REASON_INDEX_STALE,
                    total_count=0,
                )
            rows = store.nodes_by_file(rel, limit=limit + 1)
        truncated = len(rows) > limit
        results = [_hit(row) for row in rows[:limit]]
        return _result(
            rel,
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            index_root=config.index_root,
            truncated=truncated,
            found=True,
            reason=REASON_OK,
            total_count=len(results),
        )

    return file_outline


def _repo_relative(root: Path, path: str) -> str:
    """Map an absolute or ``./``-prefixed path to the repo-relative posix form the index stores."""
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return PurePosixPath(path).as_posix()
    return PurePosixPath(path).as_posix()


def _hit(row: Mapping[str, object] | Row) -> dict[str, object]:
    hit: dict[str, object] = {}
    hit["qname"] = row["qualified_name"]
    hit["kind"] = row["kind"]
    hit["name"] = row["name"]
    hit["line_start"] = row["line_start"]
    hit["line_end"] = row["line_end"]
    return hit


def _empty(
    path: str, *, detail_level: str, db_path: str, index_root: str
) -> dict[str, object]:
    del detail_level, db_path
    return {
        "indexed": False,
        "path": path,
        "found": False,
        "results": [],
        "truncated": False,
        "index_root": index_root,
    }


def _result(
    path: str,
    results: list[dict[str, object]],
    *,
    detail_level: str,
    db_path: str,
    index_root: str,
    truncated: bool,
    found: bool,
    reason: str | None = None,
    total_count: int | None = None,
) -> dict[str, object]:
    del detail_level, db_path
    payload: dict[str, object] = {
        "indexed": True,
        "path": path,
        "found": found,
        "results": results,
        "truncated": truncated,
        "index_root": index_root,
    }
    if reason is not None:
        payload["reason"] = reason
    if total_count is not None:
        payload["total_count"] = total_count
    return payload
