"""``find_orphans`` — unreachable / zero-inbound complement of entry reachability (task 031)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import empty_nav, nav_result
from code_atlas.tools.reachable_from import NO_ROOTS, _no_roots, entry_seeds

NAME = "find_orphans"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_orphans(
        depth: int | None = None,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """Symbols/files outside proven reachability from ``CA_ENTRY_POINTS``.

        Each orphan carries ``why``: ``no_inbound`` or ``unreachable_from_roots``.
        HEURISTIC-only neighbors are ``unproven``, never orphans. Unset entry points
        yield ``status=no_roots_configured`` rather than a misleading empty list.
        Results are never presented as authoritative — ``edge_health`` is included on
        ``standard`` so clients can weigh HEURISTIC ratio (task 028).
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
            outcome = store.find_orphans(
                seeds, depth=hops, max_nodes=config.impact_max_nodes
            )
            health = store.edge_health() if detail_level == "standard" else None
        results = []
        for row in outcome.orphans:
            hit: dict[str, object] = {
                "qname": row["qname"],
                "file": row["file"],
                "why": row["why"],
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
            authoritative=False,
        )

    return find_orphans


__all__ = ["NAME", "NO_ROOTS", "create"]
