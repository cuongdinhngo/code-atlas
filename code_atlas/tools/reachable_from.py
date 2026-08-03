"""``reachable_from`` — forward reachability from configured entry points (task 031)."""

from __future__ import annotations

import fnmatch
from collections.abc import Callable, Sequence
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import empty_nav, nav_result

NAME = "reachable_from"

DetailLevel = Literal["minimal", "standard"]
NO_ROOTS = "no_roots_configured"


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def reachable_from(
        depth: int | None = None,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """Nodes reachable from ``CA_ENTRY_POINTS`` via RESOLVED IMPACT edges.

        Unset/empty entry points yield ``status=no_roots_configured`` (never an empty
        success that looks like "nothing is reachable"). HEURISTIC/DYNAMIC neighbors
        appear under ``unproven`` and do not expand the frontier.
        """
        hops = config.impact_depth if depth is None else depth
        if hops < 0:
            raise ValueError(f"depth must be >= 0, got {hops}")
        roots = config.entry_points
        if not roots:
            return _no_roots(detail_level, config)
        if not config.db_path.is_file():
            return empty_nav("", detail_level=detail_level, db_path=str(config.db_path))
        with GraphStore(config.db_path) as store:
            seeds = entry_seeds(store, roots)
            outcome = store.reachable_from(
                seeds, depth=hops, max_nodes=config.impact_max_nodes
            )
            health = store.edge_health() if detail_level == "standard" else None
        results = []
        for row in outcome.reachable:
            hit: dict[str, object] = {
                "qname": row["qname"],
                "file": row["file"],
                "depth": row["depth"],
            }
            hit["kind"] = row["kind"]
            hit["line"] = row["line"]
            results.append(hit)
        unproven = []
        for row in outcome.unproven:
            hit = {
                "qname": row["qname"],
                "file": row["file"],
                "confidence_tier": row["confidence_tier"],
            }
            hit["kind"] = row["kind"]
            hit["line"] = row["line"]
            unproven.append(hit)
        if health is not None:
            return nav_result(
                ",".join(roots),
                results,
                detail_level=detail_level,
                db_path=str(config.db_path),
                truncated=outcome.truncated,
                depth=hops,
                status="ok",
                entry_points=list(roots),
                unproven=unproven,
                frontier_skipped_non_resolved=outcome.frontier_skipped_non_resolved,
                authoritative=False,
                edge_health=health,
            )
        return nav_result(
            ",".join(roots),
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            truncated=outcome.truncated,
            depth=hops,
            status="ok",
            entry_points=list(roots),
            unproven=unproven,
            frontier_skipped_non_resolved=outcome.frontier_skipped_non_resolved,
            authoritative=False,
        )

    return reachable_from


def entry_seeds(store: GraphStore, patterns: Sequence[str]) -> list[str]:
    """Every indexed node on files matching any entry-point glob (W1)."""
    paths = store.file_paths()
    matched = [
        path
        for path in paths
        if any(fnmatch.fnmatch(path, pattern) for pattern in patterns)
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


def _no_roots(detail_level: DetailLevel, config: Config) -> dict[str, object]:
    payload: dict[str, object] = {
        "indexed": config.db_path.is_file(),
        "qname": "",
        "results": [],
        "truncated": False,
        "status": NO_ROOTS,
        "entry_points": [],
        "unproven": [],
        "authoritative": False,
        "message": "no roots configured — set CA_ENTRY_POINTS or entry_points in .code-atlas.toml",
    }
    if detail_level == "standard":
        payload["db_path"] = str(config.db_path)
    return payload
