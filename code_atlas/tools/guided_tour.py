"""``guided_tour`` — dependency-ordered reading order, cycle-safe via SCC (task 087, M11).

Presentation only. The store walks a node-budgeted module subgraph (R4.3); ``onboarding.tour``
condenses cycles and orders the DAG; this module renders stops. No SQL and no LLM (R1.1/R1.4/R4).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config
from code_atlas.onboarding.tour import TourStop, ordered_stops
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
    NavReason,
)

NAME = "guided_tour"

DetailLevel = Literal["minimal", "standard"]

__all__ = ["NAME", "create"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def guided_tour(
        detail_level: DetailLevel = "standard", offset: int = 0
    ) -> dict[str, object]:
        """What should I read first in this codebase, in dependency order?

        A topological walk of the include/call graph, seeded from entry-point files (zero
        inbound) that **lead somewhere**, ranked by out-degree and reading-seed layer (HTTP /
        Entry before Config — 131), at most a quarter of the budget so the walk always has room
        to expand — a repo with more entry points than budget would otherwise spend it all on
        roots and traverse no edge at all (106). A component no entry point reaches is
        re-seeded rather than dropped. Cycles
        become one strongly-connected component so the walk cannot loop. Each stop is a file
        with a one-line rationale. The walk is bounded by ``CA_IMPACT_MAX_NODES``; ``results``
        is one page of ``CA_MAX_RESULTS`` stops from ``offset``, and ``results_offset`` says
        which page. ``truncated`` is true when the node budget left an indexed file out of the
        tour or when stops remain after this page, so the rest of the order stays reachable.
        ``minimal`` returns files only; ``standard`` adds ``rationale`` and, for a cycle, the
        ``scc`` members.
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if not config.db_path.is_file():
            return _unbuilt(config)
        with GraphStore(config.db_path) as store:
            subgraph = store.tour_subgraph(max_nodes=config.impact_max_nodes)
        stops = ordered_stops(subgraph.files, subgraph.edges, subgraph.entry_points)
        if not stops:
            return _empty(config)
        return _payload(config, stops, subgraph.truncated, detail_level, offset)

    return guided_tour


def _base(config: Config, *, indexed: bool, reason: NavReason) -> dict[str, object]:
    """The keys every outcome carries: 071's ``index_root``, 033/065's reason + count."""
    return {
        "indexed": indexed,
        "results": [],
        "results_offset": 0,
        "truncated": False,
        "reason": reason,
        "total_count": 0,
        "index_root": config.index_root,
    }


def _unbuilt(config: Config) -> dict[str, object]:
    """No database yet — a read tool must not create one to answer with zeroes."""
    return _base(config, indexed=False, reason=REASON_NOT_INDEXED)


def _empty(config: Config) -> dict[str, object]:
    """An index with no module: a genuine zero, distinct from the unbuilt one above (033/065)."""
    return _base(config, indexed=True, reason=REASON_NO_MATCHES)


def _row(stop: TourStop, *, detail_level: DetailLevel) -> dict[str, object]:
    row: dict[str, object] = {"file": stop.file}
    if detail_level == "minimal":
        return row
    row["rationale"] = stop.rationale
    if len(stop.scc) > 1:
        row["scc"] = list(stop.scc)
    return row


def _payload(
    config: Config,
    stops: tuple[TourStop, ...],
    walk_truncated: bool,
    detail_level: DetailLevel,
    offset: int,
) -> dict[str, object]:
    """One page of the order. ``truncated`` covers both bounds; ``offset`` reaches the tail."""
    limit = config.max_results
    page = stops[offset : offset + limit]
    return {
        "indexed": True,
        "results": [_row(stop, detail_level=detail_level) for stop in page],
        "results_offset": offset,
        "truncated": walk_truncated or offset + len(page) < len(stops),
        "reason": REASON_OK,
        "total_count": len(stops),
        "index_root": config.index_root,
    }
