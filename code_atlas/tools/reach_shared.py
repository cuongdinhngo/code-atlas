"""Shared helpers for ``reachable_from`` / ``find_orphans`` (task 031)."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Literal

from code_atlas.build_info import maybe_server_provenance
from code_atlas.config import Config
from code_atlas.ignore import translate_path_pattern
from code_atlas.store import GraphStore, Row
from code_atlas.tools.nav_result import nav_result

NO_ROOTS = "no_roots_configured"
# Two refusals, both sourced from the computation rather than from a threshold (task 182 / R5.2).
# A truncated walk cannot support a reachability claim, and roots that match no file never started
# one — either way the honest answer is a named refusal, not 215,177 rows flagged unreliable.
ROOTS_MATCHED_NOTHING = "roots_matched_nothing"
WALK_BUDGET_EXHAUSTED = "walk_budget_exhausted"
DetailLevel = Literal["minimal", "standard"]


def entry_seeds(
    store: GraphStore, patterns: Sequence[str], paths: Sequence[str] | None = None
) -> list[str]:
    """Every indexed node on files matching any entry-point glob (W1).

    Patterns use the same segment-aware glob language as ignore rules (PLAN §11):
    ``*`` / ``?`` stay inside one path segment; ``**`` crosses directories.

    ``paths`` lets a caller that already holds the file list hand it over, so naming the unmatched
    roots costs no second query (task 182).
    """
    compiled = tuple(
        re.compile(f"{translate_path_pattern(pattern)}$") for pattern in patterns
    )
    all_paths = store.file_paths() if paths is None else paths
    matched = [path for path in all_paths if any(rule.match(path) for rule in compiled)]
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
        "index_root": config.index_root,
        **maybe_server_provenance(detail_level),
    }
    return payload


def unmatched_entry_patterns(
    paths: Sequence[str], patterns: Sequence[str]
) -> list[str]:
    """Entry-point patterns that matched no indexed file (task 182).

    A root matching nothing is the commonest way an orphan answer goes wrong, and the payload could
    not say so. Pure over the path list the caller already has — no second query.
    """
    unmatched: list[str] = []
    for pattern in patterns:
        rule = re.compile(f"{translate_path_pattern(pattern)}$")
        if not any(rule.match(path) for path in paths):
            unmatched.append(pattern)
    return unmatched


def refuse_reachability(
    status: str,
    roots: Sequence[str],
    *,
    config: Config,
    message: str,
    unmatched: Sequence[str] = (),
    reached: int | None = None,
    nodes_total: int | None = None,
    detail_level: DetailLevel = "standard",
) -> dict[str, object]:
    """A reachability refusal: what it CAN say, and no row list (task 182).

    Distinct from ``status: ok`` with an empty list, which is the real and useful answer *nothing is
    orphaned* (102). ``reached`` / ``nodes_total`` are the two numbers that show whether a huge
    orphan share is dead code or the wrong roots; they ride here, where the reader needs them, so a
    complete plausible answer stays byte-identical (061).
    """
    payload: dict[str, object] = {
        "indexed": config.db_path.is_file(),
        "qname": ",".join(roots),
        "results": [],
        "truncated": False,
        "status": status,
        "entry_points": list(roots),
        "unproven": [],
        "authoritative": False,
        "depth_exhausted": False,
        "message": message,
        "index_root": config.index_root,
        **maybe_server_provenance(detail_level),
    }
    if unmatched:
        payload["entry_points_unmatched"] = list(unmatched)
    if reached is not None:
        payload["roots_reached"] = reached
    if nodes_total is not None:
        payload["nodes_total"] = nodes_total
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
    index_root: str,
    truncated: bool,
    depth: int | None,
    unproven: list[dict[str, object]],
    depth_exhausted: bool,
    edge_health: object | None = None,
    edge_health_by_language: object | None = None,
    frontier_skipped_non_resolved: int | None = None,
    total_count: int | None = None,
) -> dict[str, object]:
    """Shared nav_result shape for both reachability tools."""
    payload = nav_result(
        ",".join(roots),
        results,
        detail_level=detail_level,
        db_path=db_path,
        index_root=index_root,
        truncated=truncated,
        depth=depth,
        status="ok",
        entry_points=list(roots),
        unproven=unproven,
        authoritative=False,
        depth_exhausted=depth_exhausted,
        total_count=total_count,
    )
    if edge_health is not None:
        payload["edge_health"] = edge_health
    if edge_health_by_language is not None:
        # The walk is cross-language, so the blended figure above IS this answer's denominator — but
        # a blend cannot be attributed (183), and round 12 could not ask which adapter moved it.
        payload["edge_health_by_language"] = edge_health_by_language
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
