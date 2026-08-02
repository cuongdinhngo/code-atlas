"""Shared hit shaping for navigation tools (§12) — qname + file:line + tier, never bodies."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from code_atlas.contract import CONFIDENCE_TIERS
from code_atlas.store import Row

_RESOLVED = CONFIDENCE_TIERS[0]


def edge_hit(edge: Mapping[str, Any] | Row, *, depth: int | None = None) -> dict[str, object]:
    """One relationship hit: the *source* side is the answer (caller / referrer / subtype)."""
    hit: dict[str, object] = {}
    hit["qname"] = edge["source_qname"]
    hit["file"] = edge["file_path"]
    hit["line"] = edge["line"]
    hit["kind"] = edge["kind"]
    hit["confidence_tier"] = edge.get("confidence_tier") or _RESOLVED
    if depth is not None:
        hit["depth"] = depth
    return hit


def empty_nav(qname: str, *, detail_level: str, db_path: str) -> dict[str, object]:
    """No database yet — read tools must not create one."""
    result: dict[str, object] = {
        "indexed": False,
        "qname": qname,
        "results": [],
        "truncated": False,
    }
    if detail_level == "standard":
        result["db_path"] = db_path
    return result


def nav_result(
    qname: str,
    results: list[dict[str, object]],
    *,
    detail_level: str,
    db_path: str,
    truncated: bool,
    **extra: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "indexed": True,
        "qname": qname,
        "results": results,
        "truncated": truncated,
        **extra,
    }
    if detail_level == "standard":
        payload["db_path"] = db_path
    return payload
