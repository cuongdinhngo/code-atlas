"""``find_orphans`` — unreachable / zero-inbound complement of entry reachability (task 031)."""

from __future__ import annotations

from collections.abc import Callable

from code_atlas.config import Config, clamp_limit
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import answered_about_ref_for, attach_limit_capped, empty_nav
from code_atlas.tools.reach_shared import (
    NO_ROOTS,
    RESOLUTION_UNMODELLED,
    ROOTS_MATCHED_NOTHING,
    WALK_BUDGET_EXHAUSTED,
    DetailLevel,
    entry_seeds,
    no_roots,
    reach_payload,
    refuse_reachability,
    shape_hit,
    unmatched_entry_patterns,
    unproven_hits,
)

NAME = "find_orphans"
# Re-export refuse statuses for tests that pin the vocabulary (182 / 279).
RESOLUTION_UNMODELLED = RESOLUTION_UNMODELLED
ROOTS_MATCHED_NOTHING = ROOTS_MATCHED_NOTHING
WALK_BUDGET_EXHAUSTED = WALK_BUDGET_EXHAUSTED

_HINT_RESOLUTION_UNMODELLED = (
    "a registered resolution strategy leaves include-based reachability unmeasured — "
    "treat a large no_inbound population as unmeasured, not as zero; Grep entry-point "
    "names as text outside the index, or use the language runtime's own loader diagnostics, "
    "not this orphan list"
)


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_orphans(
        depth: int | None = None,
        detail_level: DetailLevel = "minimal",
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
        describes this page alone — page until it is false. ``unproven_total`` is the full unproven
        count — at ``minimal`` the rows themselves are omitted so large repos stay transport-safe,
        at ``standard`` they are capped to one page.

        **Three refusals, and none return rows** (182 / 279). Roots that match no file give
        ``status=roots_matched_nothing``; a walk that hit ``CA_ORPHANS_MAX_NODES`` gives
        ``status=walk_budget_exhausted``; an index stamped with an unmodelled resolution strategy
        (registered class autoload, …) gives ``status=resolution_unmodelled`` — include-based
        orphan counts are unmeasured there, not dead code. ``status=ok`` with no rows still means
        nothing is orphaned, which is a real answer (102).
        """
        if depth is not None and depth < 0:
            raise ValueError(f"depth must be >= 0, got {depth}")
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap, limit_clamped = clamp_limit(limit, config.page_limit)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
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
            stamped = store.stamped_unmodelled_resolution_by_language()
            if stamped:
                # R5.6: stamp says unmeasured — never invent reachability or a bare orphan list.
                return refuse_reachability(
                    RESOLUTION_UNMODELLED,
                    roots,
                    config=config,
                    message=(
                        "indexed languages stamp unmodelled resolution strategies; "
                        "include-based orphan populations are unmeasured, not zero"
                    ),
                    detail_level=detail_level,
                    try_instead_hint=_HINT_RESOLUTION_UNMODELLED,
                    unmodelled_resolution_by_language=stamped,
                    answered_about_ref=about_ref)
            # One fetch of the path list, shared by the walk's seeds and the unmatched-root report.
            indexed_paths = store.file_paths()
            seeds = entry_seeds(store, roots, indexed_paths)
            unmatched_roots = unmatched_entry_patterns(indexed_paths, roots)
            if not seeds:
                # Configured roots that resolve to nothing never started a walk, so every node is
                # trivially "unreachable" — an answer about the config, not about the code.
                return refuse_reachability(
                    ROOTS_MATCHED_NOTHING,
                    roots,
                    config=config,
                    message=(
                        "the configured entry points resolve to no indexed node, so nothing was "
                        "walked — fix CA_ENTRY_POINTS (path globs, not qnames) and re-ask"
                    ),
                    unmatched=unmatched_roots,
                    reached=0,
                    nodes_total=store.counts()["nodes"],
                    detail_level=detail_level,
                    answered_about_ref=about_ref)
            outcome = store.find_orphans(
                seeds,
                depth=depth,
                max_nodes=config.orphans_max_nodes,
                limit=cap,
                offset=offset,
            )
            # The BUDGET half only. A caller's own `depth=` also sets `walk_truncated`, and a
            # deliberately shallow question deserves its rows — refusing it would be a new defect.
            if outcome.budget_exhausted:
                # 215,177 rows already flagged unreliable is worse than a refusal (round 12 §9.b).
                return refuse_reachability(
                    WALK_BUDGET_EXHAUSTED,
                    roots,
                    config=config,
                    message=(
                        "the reachability walk hit CA_ORPHANS_MAX_NODES, so unreached nodes cannot "
                        "be distinguished from unreachable ones — raise the budget, or narrow the "
                        "question with impact/reachable_from"
                    ),
                    unmatched=unmatched_roots,
                    reached=outcome.reached,
                    nodes_total=outcome.nodes_total,
                    detail_level=detail_level,
                    answered_about_ref=about_ref)
            health = store.edge_health() if detail_level == "standard" else None
            by_language = (
                store.stamped_edge_health_by_language() if detail_level == "standard" else None
            )
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
            edge_health_by_language=by_language,
            total_count=outcome.orphan_total,
            answered_about_ref=about_ref,
        )
        # One name for one fact. Omitted only where the rows themselves already state it (061).
        if detail_level == "minimal" or len(unproven_rows) > len(unproven_payload):
            payload["unproven_total"] = len(unproven_rows)
        if outcome.walk_truncated:
            # Still a caveat where it is the caller's own depth bound (124); the budget case above
            # never reaches here, so this now means exactly "you asked for a shallow walk".
            payload["walk_truncated"] = True
        # A root that matched no file is named even on a complete answer — the population it
        # silently narrowed is the reader's to judge. Omitted when every root matched (061).
        if unmatched_roots:
            payload["entry_points_unmatched"] = unmatched_roots
        attach_limit_capped(payload, cap=cap, clamped=limit_clamped)
        return payload

    return find_orphans


__all__ = [
    "NAME",
    "NO_ROOTS",
    "ROOTS_MATCHED_NOTHING",
    "WALK_BUDGET_EXHAUSTED",
    "create",
]
