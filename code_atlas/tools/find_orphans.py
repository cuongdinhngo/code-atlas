"""``find_orphans`` — unreachable / zero-inbound complement of entry reachability (task 031)."""

from __future__ import annotations

from collections.abc import Callable

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import empty_nav
from code_atlas.tools.reach_shared import (
    NO_ROOTS,
    DetailLevel,
    entry_seeds,
    no_roots,
    reach_payload,
    shape_hit,
    unproven_hits,
)

NAME = "find_orphans"


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_orphans(
        depth: int | None = None,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """Symbols/files outside proven reachability from ``CA_ENTRY_POINTS``.

        Each orphan carries ``why``: ``no_inbound`` or ``unreachable_from_roots``.
        HEURISTIC-only neighbors are ``unproven``, never orphans. Default walk is
        closure (see ``reachable_from``); unset entry points yield
        ``status=no_roots_configured``.
        """
        if depth is not None and depth < 0:
            raise ValueError(f"depth must be >= 0, got {depth}")
        roots = config.entry_points
        if not roots:
            return no_roots(detail_level, config)
        if not config.db_path.is_file():
            return empty_nav("", detail_level=detail_level, db_path=str(config.db_path))
        with GraphStore(config.db_path) as store:
            seeds = entry_seeds(store, roots)
            outcome = store.find_orphans(
                seeds, depth=depth, max_nodes=config.impact_max_nodes
            )
            health = store.edge_health() if detail_level == "standard" else None
        results = [shape_hit(row, extra={"why": row["why"]}) for row in outcome.orphans]
        return reach_payload(
            roots,
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            truncated=outcome.truncated,
            depth=depth,
            unproven=unproven_hits(outcome.unproven),
            depth_exhausted=outcome.depth_exhausted,
            edge_health=health,
        )

    return find_orphans


__all__ = ["NAME", "NO_ROOTS", "create"]
