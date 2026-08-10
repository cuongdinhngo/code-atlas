"""Shared hit shaping for navigation tools (§12) — qname/path + file:line + tier, never bodies."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Literal

from code_atlas import contract
from code_atlas.contract import CONFIDENCE_TIERS
from code_atlas.enrichment import is_rule_edge_kind, is_rule_edge_path
from code_atlas.store import Row

_RESOLVED = CONFIDENCE_TIERS[0]

NavReason = Literal[
    "ok",
    "no_matches",
    "no_such_symbol",
    "not_indexed",
    "index_stale",
    "bare_name_truncated",
    "relationship_not_modelled",
]

REASON_OK: NavReason = "ok"
REASON_NO_MATCHES: NavReason = "no_matches"
REASON_NO_SUCH_SYMBOL: NavReason = "no_such_symbol"
REASON_NOT_INDEXED: NavReason = "not_indexed"
REASON_INDEX_STALE: NavReason = "index_stale"  # vocabulary for 035; not emitted by 033
REASON_BARE_NAME_TRUNCATED: NavReason = "bare_name_truncated"
REASON_RELATIONSHIP_NOT_MODELLED: NavReason = "relationship_not_modelled"

NAV_REASONS: tuple[NavReason, ...] = (
    REASON_OK,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_NOT_INDEXED,
    REASON_INDEX_STALE,
    REASON_BARE_NAME_TRUNCATED,
    REASON_RELATIONSHIP_NOT_MODELLED,
)

# Machine-stable alternate routes when reason is relationship_not_modelled (task 065).
TRY_INSTEAD_FIND_REFERENCES_ON_METHOD_QNAME = "find_references_on_method_qname"
TRY_INSTEAD_PATH_BASENAME_SEARCH = "path_basename_search"
# Empty miss while multiple indexed files are dirty — path-named tools are stronger (073).
TRY_INSTEAD_FILE_OUTLINE = "file_outline"


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
    if is_rule_edge_path(edge.get("file_path")) or is_rule_edge_kind(edge.get("kind")):
        # Synthetic bookmark — not an on-disk path. Advertise ``rule``; omit file (task 040).
        # PROVIDES_VIEW_DATA keeps ``line`` (call-site line on the handler — task 062).
        hit[contract.RULE_FLAG] = True
        hit["kind"] = edge["kind"]
        hit["confidence_tier"] = edge.get("confidence_tier") or _RESOLVED
        if edge.get("kind") == contract.PROVIDES_VIEW_DATA and type(edge.get("line")) is int:
            hit["line"] = edge["line"]
        if depth is not None:
            hit["depth"] = depth
        return hit
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
    index_root: str,
    db_path: str = "",
    subject_key: str = "qname",
    reason: NavReason = REASON_NOT_INDEXED,
    total_count: int = 0,
) -> dict[str, object]:
    """No database yet — read tools must not create one.

    ``db_path`` is accepted for call-site stability but never attached (task 061).
    ``index_root`` is the source tree the server was configured with (task 071).
    """
    del detail_level, db_path
    return {
        "indexed": False,
        subject_key: subject,
        "results": [],
        "truncated": False,
        "reason": reason,
        "total_count": total_count,
        "index_root": index_root,
    }


def nav_result(
    subject: str,
    results: list[dict[str, object]],
    *,
    detail_level: str,
    index_root: str,
    db_path: str = "",
    truncated: bool,
    reason: NavReason | None = None,
    total_count: int | None = None,
    subject_key: str = "qname",
    **extra: object,
) -> dict[str, object]:
    """Shape a nav payload; omit ``reason`` / ``total_count`` unless explicitly set.

    ``db_path`` is accepted but never attached — use ``get_index_status`` (task 061).
    ``index_root`` always ships so a caller can compare against its own cwd (task 071).
    """
    del detail_level, db_path
    extra.pop("db_path", None)
    payload: dict[str, object] = {
        "indexed": True,
        subject_key: subject,
        "results": results,
        "truncated": truncated,
        "index_root": index_root,
        **extra,
    }
    if reason is not None:
        payload["reason"] = reason
    if total_count is not None:
        payload["total_count"] = total_count
    return payload


def list_result(
    results: list[dict[str, object]],
    *,
    detail_level: str,
    index_root: str,
    db_path: str = "",
    truncated: bool,
    reason: NavReason,
    total_count: int,
    indexed: bool = True,
) -> dict[str, object]:
    """Search-style payload — same reason/total_count fields, no subject key."""
    del detail_level, db_path
    return {
        "indexed": indexed,
        "results": results,
        "truncated": truncated,
        "reason": reason,
        "total_count": total_count,
        "index_root": index_root,
    }


def relation_reason(*, hit_total: int, symbol_indexed: bool) -> NavReason:
    """Classify find_* after counting edges: hits / empty indexed / unknown qname."""
    if hit_total > 0:
        return REASON_OK
    if not symbol_indexed:
        return REASON_NO_SUCH_SYMBOL
    return REASON_NO_MATCHES


def attach_try_instead(payload: dict[str, object], try_instead: str | None) -> dict[str, object]:
    """Attach ``try_instead`` only when set (task 061 — omit when it means nothing)."""
    if try_instead:
        payload["try_instead"] = try_instead
    return payload


def attach_limit_capped(
    payload: dict[str, object], *, cap: int, clamped: bool
) -> dict[str, object]:
    """Report a reduced ``limit`` as ``limit_capped_to`` — only when a clamp occurred (066/061).

    The effective cap tells a caller their request was reduced and to what, without a config
    read. Omitted when the request was honoured, keeping the non-clamp payload unchanged.
    """
    if clamped:
        payload["limit_capped_to"] = cap
    return payload


def attach_result_subtrees(
    payload: dict[str, object], subtrees: Mapping[str, int]
) -> dict[str, object]:
    """Advertise the full result's top-level subtrees when a page hides some (task 067).

    Attached only when the set spans >1 subtree; otherwise a one-page reader sees the whole
    spread anyway and the field would only add tokens. Callers gate on ``truncated`` first.
    """
    if len(subtrees) > 1:
        payload["result_subtrees"] = dict(subtrees)
    return payload


def is_stub(raw: object) -> bool:
    """True when a node's ``extra`` JSON carries the stub marker (task 039)."""
    if not isinstance(raw, str) or not raw.strip():
        return False
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return isinstance(data, dict) and data.get(contract.STUB_FLAG) is True
