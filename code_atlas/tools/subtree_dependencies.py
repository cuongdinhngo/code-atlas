"""``subtree_dependencies`` — tree-to-tree crossing with duplicate-declaration attribution (120)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Literal

from code_atlas.build_info import maybe_server_provenance
from code_atlas.config import Config, clamp_limit
from code_atlas.onboarding.mirrors import find_mirror_subtrees
from code_atlas.store import GraphStore, SubtreeDependencyResult, SubtreeTierAttribution
from code_atlas.tools.nav_result import attach_limit_capped, empty_nav

NAME = "subtree_dependencies"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def subtree_dependencies(
        subtree: str,
        counterpart: str | None = None,
        detail_level: DetailLevel = "standard",
        limit: int | None = None,
    ) -> dict[str, object]:
        """Can this subtree be deleted — what still crosses into or out of it?

        Reports crossing edges at directory-prefix grain, split by ``confidence_tier`` and by
        whether the target symbol is declared only under ``subtree`` (attributable) or also
        elsewhere (unattributable). The unattributable total always sits beside the attributable
        one — a blocker count without its unknown companion is structurally unavailable.

        ``counterpart`` optionally narrows the other side (e.g. ``src/`` when ``subtree`` is
        ``legacy/``). Ranked ``dependent_files`` (outside) and ``depended_on_paths`` (inside,
        mirror-collapsed when siblings mirror) carry edge counts for prioritisation.
        ``dynamic_bridges`` surfaces alias files whose only link is ``DYNAMIC`` — no static edge
        is never rendered as no dependency. Node-budgeted like ``impact``; truncation is disclosed.
        ``depended_on_path_total`` counts declaration paths before the mirror collapse, so it can
        exceed the collapsed list even when nothing was truncated.
        """
        if not subtree.strip():
            raise ValueError("subtree must be non-empty")
        cap, limit_clamped = clamp_limit(limit, config.max_results)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        normalized = _normalize_prefix(subtree)
        assert normalized is not None
        cp = _normalize_prefix(counterpart)
        subject = normalized if cp is None else f"{normalized}↔{cp}"
        if not config.db_path.is_file():
            return empty_nav(
                subject,
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
            )
        with GraphStore(config.db_path) as store:
            report = store.subtree_dependency_report(
                normalized, counterpart=cp, max_list=cap
            )
            # minimal drops the collapsed list, so it must not pay the all-paths load (115).
            mirror_map = (
                {}
                if detail_level == "minimal"
                else _mirror_collapse_map(store, config.stub_roots)
            )
        payload = _shape_payload(
            subject,
            normalized,
            cp,
            report,
            mirror_map,
            detail_level=detail_level,
            db_path=str(config.db_path),
            index_root=config.index_root,
        )
        attach_limit_capped(payload, cap=cap, clamped=limit_clamped)
        return payload

    return subtree_dependencies


def _normalize_prefix(prefix: str | None) -> str | None:
    if prefix is None or not prefix.strip():
        return None
    text = prefix.strip().rstrip("/")
    return f"{text}/"


def _mirror_collapse_map(
    store: GraphStore, stub_roots: tuple[str, ...] | None
) -> dict[str, str]:
    """Map each path to a mirror-collapsed form when sibling subtrees overlap (115)."""
    paths = store.file_paths()
    pairs = find_mirror_subtrees(paths, stub_roots=stub_roots, sample_limit=3).pairs
    mapping: dict[str, str] = {}
    for pair in pairs:
        left, right = pair.left + "/", pair.right + "/"
        for path in paths:
            if path.startswith(right):
                mapping[path] = left + path[len(right) :]
    return mapping


def _collapse_paths(
    rows: list[dict[str, object]], mirror_map: Mapping[str, str]
) -> list[dict[str, object]]:
    """Sum edge counts by mirror-collapsed path (task 120 AC1 path grain)."""
    merged: dict[str, int] = {}
    for row in rows:
        path = str(row["path"])
        collapsed = mirror_map.get(path, path)
        raw_edges = row["edges"]
        edge_count = raw_edges if isinstance(raw_edges, int) else int(str(raw_edges))
        merged[collapsed] = merged.get(collapsed, 0) + edge_count
    return [
        {"path": path, "edges": count}
        for path, count in sorted(merged.items(), key=lambda item: (-item[1], item[0]))
    ]


def _tier_dict(by_tier: dict[str, SubtreeTierAttribution]) -> dict[str, dict[str, int]]:
    return {
        tier: {
            "attributable": counts.attributable,
            "unattributable": counts.unattributable,
        }
        for tier, counts in sorted(by_tier.items())
    }


def _totals(by_tier: dict[str, SubtreeTierAttribution]) -> tuple[int, int]:
    attr = sum(item.attributable for item in by_tier.values())
    unattr = sum(item.unattributable for item in by_tier.values())
    return attr, unattr


def _shape_payload(
    subject: str,
    subtree: str,
    counterpart: str | None,
    report: SubtreeDependencyResult,
    mirror_map: Mapping[str, str],
    *,
    detail_level: DetailLevel,
    db_path: str,
    index_root: str,
) -> dict[str, object]:
    in_attr, in_unattr = _totals(report.inbound.by_tier)
    out_attr, out_unattr = _totals(report.outbound.by_tier)
    raw_paths = [
        {"path": row["path"], "edges": row["edges"]} for row in report.inbound.ranked_paths
    ]
    depended_on = _collapse_paths(raw_paths, mirror_map)
    payload: dict[str, object] = {
        "indexed": True,
        "qname": subject,
        "subtree": subtree,
        "counterpart": counterpart,
        "inbound": {
            "by_tier": _tier_dict(report.inbound.by_tier),
            "attributable": in_attr,
            "unattributable": in_unattr,
        },
        "outbound": {
            "by_tier": _tier_dict(report.outbound.by_tier),
            "attributable": out_attr,
            "unattributable": out_unattr,
        },
        "dependent_files": [
            {"path": row["path"], "edges": row["edges"]}
            for row in report.inbound.ranked_files
        ],
        "dependent_file_total": report.inbound.file_total,
        "depended_on_paths": depended_on,
        "depended_on_path_total": report.inbound.path_total,
        "dynamic_bridges": [
            {"path": row["path"], "edges": row["edges"]}
            for row in report.dynamic_bridges
        ],
        "dynamic_bridge_total": report.bridge_total,
        "truncated": report.lists_truncated,
        "db_path": db_path,
        "index_root": index_root,
    }
    if detail_level == "minimal":
        payload.pop("dependent_files", None)
        payload.pop("depended_on_paths", None)
        payload.pop("dynamic_bridges", None)
    payload.update(maybe_server_provenance(detail_level))
    return payload


__all__ = ["NAME", "create"]
