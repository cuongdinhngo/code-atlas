"""Shared hit shaping for navigation tools (§12) — qname/path + file:line + tier, never bodies."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from code_atlas.contract import CONFIDENCE_TIERS
from code_atlas.store import Row

_RESOLVED = CONFIDENCE_TIERS[0]


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
    subject: str, *, detail_level: str, db_path: str, subject_key: str = "qname"
) -> dict[str, object]:
    """No database yet — read tools must not create one."""
    result: dict[str, object] = {
        "indexed": False,
        subject_key: subject,
        "results": [],
        "truncated": False,
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
    subject_key: str = "qname",
    **extra: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "indexed": True,
        subject_key: subject,
        "results": results,
        "truncated": truncated,
        **extra,
    }
    if detail_level == "standard":
        payload["db_path"] = db_path
    return payload
