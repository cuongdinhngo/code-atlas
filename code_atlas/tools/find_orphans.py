"""``find_orphans`` — unreachable / zero-inbound complement of entry reachability (task 031)."""

from __future__ import annotations

from collections.abc import Callable

from code_atlas.config import Config, clamp_limit
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import attach_limit_capped, empty_nav
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
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, object]:
        """Which symbols and files look unused — nothing calls them and no entry point reaches them?

        Each orphan carries ``why``: ``no_inbound`` or ``unreachable_from_roots``. Reachability
        starts from ``CA_ENTRY_POINTS``; HEURISTIC-only neighbors are ``unproven``, never orphans.
        Default walk is closure (see ``reachable_from``); unset entry points yield
        ``status=no_roots_configured``.

        ``limit`` defaults to ``CA_MAX_RESULTS``; ``offset`` pages orphans in store order (057).
        ``total_count`` is the full orphan population, not the page length, and ``truncated``
        describes this page alone — page until it is false. A walk that hit its own budget
        (``CA_ORPHANS_MAX_NODES``, separate from ``CA_IMPACT_MAX_NODES``) adds ``walk_truncated``:
        unreached nodes look orphaned, so the population is an over-estimate. ``unproven_total``
        is the full unproven count — at ``minimal`` the rows themselves are omitted so large
        repos stay transport-safe, at ``standard`` they are capped to one page.
        """
        if depth is not None and depth < 0:
            raise ValueError(f"depth must be >= 0, got {depth}")
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap, limit_clamped = clamp_limit(limit, config.max_results)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        roots = config.entry_points
        if not roots:
            return no_roots(detail_level, config)
        if not config.db_path.is_file():
            return empty_nav("", detail_level=detail_level, db_path=str(config.db_path),
            index_root=config.index_root,
        )
        with GraphStore(config.db_path) as store:
            seeds = entry_seeds(store, roots)
            outcome = store.find_orphans(
                seeds,
                depth=depth,
                max_nodes=config.orphans_max_nodes,
                limit=cap,
                offset=offset,
            )
            health = store.edge_health() if detail_level == "standard" else None
        results = [shape_hit(row, extra={"why": row["why"]}) for row in outcome.orphans]
        unproven_rows = outcome.unproven
        if detail_level == "minimal":
            unproven_payload: list[dict[str, object]] = []
        else:
            hits = unproven_hits(unproven_rows)
            unproven_payload = hits[:cap]
        payload = reach_payload(
            roots,
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            index_root=config.index_root,
            truncated=outcome.truncated,
            depth=depth,
            unproven=unproven_payload,
            depth_exhausted=outcome.depth_exhausted,
            edge_health=health,
            total_count=outcome.orphan_total,
        )
        # One name for one fact. Omitted only where the rows themselves already state it (061).
        if detail_level == "minimal" or len(unproven_rows) > len(unproven_payload):
            payload["unproven_total"] = len(unproven_rows)
        if outcome.walk_truncated:
            payload["walk_truncated"] = True
        attach_limit_capped(payload, cap=cap, clamped=limit_clamped)
        return payload

    return find_orphans


__all__ = ["NAME", "NO_ROOTS", "create"]
