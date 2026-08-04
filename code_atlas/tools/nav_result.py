"""Shared hit shaping for navigation tools (§12) — qname/path + file:line + tier, never bodies."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from code_atlas.contract import CONFIDENCE_TIERS
from code_atlas.store import Row

_RESOLVED = CONFIDENCE_TIERS[0]

NavReason = Literal[
    "ok",
    "no_matches",
    "no_such_symbol",
    "not_indexed",
    "index_stale",
]

REASON_OK: NavReason = "ok"
REASON_NO_MATCHES: NavReason = "no_matches"
REASON_NO_SUCH_SYMBOL: NavReason = "no_such_symbol"
REASON_NOT_INDEXED: NavReason = "not_indexed"
REASON_INDEX_STALE: NavReason = "index_stale"  # vocabulary for 035; not emitted by 033

NAV_REASONS: tuple[NavReason, ...] = (
    REASON_OK,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_NOT_INDEXED,
    REASON_INDEX_STALE,
)


def edge_id(edge: Mapping[str, Any] | Row) -> int:
    """Integer primary key of an edge row — fails loud on a bad shape."""
    raw = edge["id"]
    if not isinstance(raw, int):
        raise TypeError(f"edge id must be int, got {type(raw).__name__}")
    return raw


def edge_hit(
    edge: Mapping[str, Any] | Row,
    *,
    depth: int | None = None,
    subject: str | None = None,
    subject_key: str = "qname",
) -> dict[str, object]:
    """One relationship hit.

    Default subject is the edge's ``source_qname`` under key ``qname`` (callers / refs / impls).
    ``include_graph`` passes the neighbor path with ``subject_key="path"``.
    """
    hit: dict[str, object] = {}
    hit[subject_key] = edge["source_qname"] if subject is None else subject
    hit["file"] = edge["file_path"]
    hit["line"] = edge["line"]
    hit["kind"] = edge["kind"]
    hit["confidence_tier"] = edge.get("confidence_tier") or _RESOLVED
    if depth is not None:
        hit["depth"] = depth
    return hit


def empty_nav(
    subject: str,
    *,
    detail_level: str,
    db_path: str,
    subject_key: str = "qname",
    reason: NavReason = REASON_NOT_INDEXED,
    total_count: int = 0,
) -> dict[str, object]:
    """No database yet — read tools must not create one."""
    result: dict[str, object] = {
        "indexed": False,
        subject_key: subject,
        "results": [],
        "truncated": False,
        "reason": reason,
        "total_count": total_count,
    }
    if detail_level == "standard":
        result["db_path"] = db_path
    return result


def nav_result(
    subject: str,
    results: list[dict[str, object]],
    *,
    detail_level: str,
    db_path: str,
    truncated: bool,
    reason: NavReason | None = None,
    total_count: int | None = None,
    subject_key: str = "qname",
    **extra: object,
) -> dict[str, object]:
    """Shape a nav payload; omit ``reason`` / ``total_count`` unless explicitly set."""
    payload: dict[str, object] = {
        "indexed": True,
        subject_key: subject,
        "results": results,
        "truncated": truncated,
        **extra,
    }
    if reason is not None:
        payload["reason"] = reason
    if total_count is not None:
        payload["total_count"] = total_count
    if detail_level == "standard":
        payload["db_path"] = db_path
    return payload


def list_result(
    results: list[dict[str, object]],
    *,
    detail_level: str,
    db_path: str,
    truncated: bool,
    reason: NavReason,
    total_count: int,
    indexed: bool = True,
) -> dict[str, object]:
    """Search-style payload — same reason/total_count fields, no subject key."""
    payload: dict[str, object] = {
        "indexed": indexed,
        "results": results,
        "truncated": truncated,
        "reason": reason,
        "total_count": total_count,
    }
    if detail_level == "standard":
        payload["db_path"] = db_path
    return payload


def relation_reason(*, hit_total: int, symbol_indexed: bool) -> NavReason:
    """Classify find_* after counting edges: hits / empty indexed / unknown qname."""
    if hit_total > 0:
        return REASON_OK
    if not symbol_indexed:
        return REASON_NO_SUCH_SYMBOL
    return REASON_NO_MATCHES
