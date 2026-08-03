"""Shared helpers for ``reachable_from`` / ``find_orphans`` (task 031)."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Literal

from code_atlas.config import Config
from code_atlas.ignore import translate_path_pattern
from code_atlas.store import GraphStore, Row
from code_atlas.tools.nav_result import nav_result

NO_ROOTS = "no_roots_configured"
DetailLevel = Literal["minimal", "standard"]


def entry_seeds(store: GraphStore, patterns: Sequence[str]) -> list[str]:
    """Every indexed node on files matching any entry-point glob (W1).

    Patterns use the same segment-aware glob language as ignore rules (PLAN §11):
    ``*`` / ``?`` stay inside one path segment; ``**`` crosses directories.
    """
    compiled = tuple(
        re.compile(f"{translate_path_pattern(pattern)}$") for pattern in patterns
    )
    matched = [
        path for path in store.file_paths() if any(rule.match(path) for rule in compiled)
    ]
    found: list[str] = []
    seen: set[str] = set()
    for path in matched:
        for row in store.nodes_by_file_all(path):
            qname = str(row["qualified_name"])
            if qname not in seen:
                seen.add(qname)
                found.append(qname)
    return found


def no_roots(detail_level: DetailLevel, config: Config) -> dict[str, object]:
    """Explicit failure when entry points are unset — never an empty orphan/reachable list."""
    payload: dict[str, object] = {
        "indexed": config.db_path.is_file(),
        "qname": "",
        "results": [],
        "truncated": False,
        "status": NO_ROOTS,
        "entry_points": [],
        "unproven": [],
        "authoritative": False,
        "depth_exhausted": False,
        "message": "no roots configured — set CA_ENTRY_POINTS or entry_points in .code-atlas.toml",
    }
    if detail_level == "standard":
        payload["db_path"] = str(config.db_path)
    return payload


def shape_hit(
    row: Mapping[str, object], *, extra: Mapping[str, object] | None = None
) -> dict[str, object]:
    """Common qname/file/kind/line hit; optional extra fields (depth, why, tier)."""
    hit: dict[str, object] = {
        "qname": row["qname"],
        "file": row["file"],
    }
    hit["kind"] = row["kind"]
    hit["line"] = row["line"]
    if extra:
        hit.update(extra)
    return hit


def reach_payload(
    roots: Sequence[str],
    results: list[dict[str, object]],
    *,
    detail_level: DetailLevel,
    db_path: str,
    truncated: bool,
    depth: int | None,
    unproven: list[dict[str, object]],
    depth_exhausted: bool,
    edge_health: object | None = None,
    frontier_skipped_non_resolved: int | None = None,
) -> dict[str, object]:
    """Shared nav_result shape for both reachability tools."""
    payload = nav_result(
        ",".join(roots),
        results,
        detail_level=detail_level,
        db_path=db_path,
        truncated=truncated,
        depth=depth,
        status="ok",
        entry_points=list(roots),
        unproven=unproven,
        authoritative=False,
        depth_exhausted=depth_exhausted,
    )
    if edge_health is not None:
        payload["edge_health"] = edge_health
    if frontier_skipped_non_resolved is not None:
        payload["frontier_skipped_non_resolved"] = frontier_skipped_non_resolved
    return payload


def unproven_hits(rows: Sequence[Row]) -> list[dict[str, object]]:
    return [
        shape_hit(
            row,
            extra={"confidence_tier": row["confidence_tier"]},
        )
        for row in rows
    ]
