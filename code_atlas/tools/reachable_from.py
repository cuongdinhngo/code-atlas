"""``reachable_from`` — forward reachability from configured entry points (task 031)."""

from __future__ import annotations

from collections.abc import Callable

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import answered_about_ref_for, empty_nav
from code_atlas.tools.reach_shared import (
    NO_ROOTS,
    DetailLevel,
    entry_seeds,
    no_roots,
    reach_payload,
    shape_hit,
    unproven_hits,
)

NAME = "reachable_from"


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def reachable_from(
        depth: int | None = None,
        detail_level: DetailLevel = "minimal",
    ) -> dict[str, object]:
        """What is actually reachable from the app's entry points (and what is dead)?

        Needs ``CA_ENTRY_POINTS``; unset gives ``status=no_roots_configured``. ``depth`` unset walks
        to closure; ``depth_exhausted`` / ``truncated`` mean incomplete. RESOLVED relations only.
        For the unused list use find_orphans.
        """
        if depth is not None and depth < 0:
            raise ValueError(f"depth must be >= 0, got {depth}")
        roots = config.entry_points
        if not roots:
            return no_roots(detail_level, config)
        if not config.db_path.is_file():
            return empty_nav(
                "",
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
                answered_about_ref=None,
            )
        with GraphStore(config.db_path) as store:
            about_ref = answered_about_ref_for(store)
            seeds = entry_seeds(store, roots)
            outcome = store.reachable_from(
                seeds, depth=depth, max_nodes=config.impact_max_nodes
            )
            health = store.edge_health() if detail_level == "standard" else None
            by_language = (
                store.stamped_edge_health_by_language() if detail_level == "standard" else None
            )
        results = [
            shape_hit(row, extra={"depth": row["depth"]}) for row in outcome.reachable
        ]
        return reach_payload(
            roots,
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            index_root=config.index_root,
            truncated=outcome.truncated,
            depth=depth,
            unproven=unproven_hits(outcome.unproven),
            depth_exhausted=outcome.depth_exhausted,
            edge_health=health,
            edge_health_by_language=by_language,
            frontier_skipped_non_resolved=outcome.frontier_skipped_non_resolved,
            answered_about_ref=about_ref,
        )

    return reachable_from


__all__ = ["NAME", "NO_ROOTS", "create", "entry_seeds"]
