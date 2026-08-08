"""``search_symbol`` — ranked FTS + name hits (§12)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Literal

from code_atlas import contract
from code_atlas.config import Config
from code_atlas.store import GraphStore, Row
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
    is_stub,
    list_result,
)

NAME = "search_symbol"

DetailLevel = Literal["minimal", "standard"]


def _require_kind(kind: contract.NodeKind | None) -> contract.NodeKind | None:
    """Reject unknown ``kind`` spellings before any SQL (R5.3); ``None`` means no filter."""
    if kind is not None and kind not in contract.NODE_KINDS:
        raise ValueError(f"unknown kind {kind!r}: one of {', '.join(contract.NODE_KINDS)}")
    return kind


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def search_symbol(
        query: str,
        kind: contract.NodeKind | None = None,
        namespace: str | None = None,
        limit: int | None = None,
        detail_level: DetailLevel = "standard",
        offset: int = 0,
    ) -> dict[str, object]:
        """Ranked symbols matching ``query`` (FTS trigram, or name-prefix for queries < 3 chars).

        Returns ``{qname, kind, file, line}`` rows, capped by ``limit`` or ``CA_MAX_RESULTS``.
        ``offset`` pages in search order (057). Trigram cannot match terms under three characters;
        those use a name/qname prefix scan. On hash drift beyond the per-call reparse cap, returns
        hits with ``reason=index_stale`` and an honest ``total_count`` (never an empty proof of
        absence). Stub-indexed nodes (task 039) also carry ``stub: true``.

        A ``File`` hit whose path is already the declaring file of a ``Class`` hit in the same
        page is suppressed (task 061) — use ``kind`` to request File rows explicitly.
        """
        kind = _require_kind(kind)
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap = config.max_results if limit is None else min(limit, config.max_results)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
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
        with GraphStore(config.db_path) as store:
            guard = FreshnessGuard(config, store)
            rows = store.search_nodes(
                query, kind=kind, namespace=namespace, limit=cap + 1, offset=offset
            )
            hit_paths = [str(row["file_path"]) for row in rows[:cap]]
            status = guard.ensure_paths(hit_paths)
            # Re-query only when a repair may have changed FTS/rows.
            if status == "repaired" or (status == "stale" and guard.used > 0):
                rows = store.search_nodes(
                    query, kind=kind, namespace=namespace, limit=cap + 1, offset=offset
                )
            truncated = len(rows) > cap
            results = _suppress_redundant_file_hits([_hit(row) for row in rows[:cap]])
            if truncated or offset > 0:
                total_count = store.count_search_nodes(
                    query, kind=kind, namespace=namespace
                )
                truncated = offset + len(results) < total_count
            else:
                total_count = len(results)
        if status == "stale":
            reason = REASON_INDEX_STALE
        else:
            # Page emptiness ≠ answer emptiness once offset can walk past the end (057).
            reason = REASON_OK if total_count > 0 else REASON_NO_MATCHES
        return list_result(
            results,
            detail_level=detail_level,
            db_path=db_path,
            truncated=truncated,
            reason=reason,
            total_count=total_count,
        )

    return search_symbol


def _suppress_redundant_file_hits(
    results: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Drop File rows that only restate a Class's declaring file in this page (061)."""
    class_files = {r["file"] for r in results if r.get("kind") == "Class"}
    if not class_files:
        return results
    return [
        row
        for row in results
        if not (row.get("kind") == "File" and row.get("file") in class_files)
    ]


def _hit(row: Mapping[str, object] | Row) -> dict[str, object]:
    hit: dict[str, object] = {}
    hit["qname"] = row["qualified_name"]
    hit["kind"] = row["kind"]
    hit["file"] = row["file_path"]
    hit["line"] = row["line_start"]
    if is_stub(row.get("extra")):
        hit[contract.STUB_FLAG] = True
    return hit
