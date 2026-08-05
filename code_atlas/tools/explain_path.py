"""``explain_path`` — shortest control-flow path between two qnames (task 038)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import PATH_STATUS_INCOMPLETE, GraphStore, Row
from code_atlas.tools.nav_result import empty_nav

NAME = "explain_path"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def explain_path(
        from_qname: str,
        to_qname: str,
        depth: int | None = None,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """Shortest path from ``from_qname`` to ``to_qname`` over IMPACT edges.

        Walks outgoing CALLS/NEW/INCLUDES/EXTENDS/IMPLEMENTS (same kinds as
        ``impact`` / ``reachable_from``). Default ``depth`` is unset — walk until
        the frontier empties or ``CA_IMPACT_MAX_NODES`` binds. A RESOLVED-only path
        is ``status=path``; a path that needs HEURISTIC/DYNAMIC hops is
        ``unproven``. Missing endpoints → ``unknown``; bound hit before ``to`` →
        ``incomplete``; both present with no route → ``no_path``.
        """
        if depth is not None and depth < 0:
            raise ValueError(f"depth must be >= 0, got {depth}")
        subject = f"{from_qname}->{to_qname}"
        if not config.db_path.is_file():
            return empty_nav(subject, detail_level=detail_level, db_path=str(config.db_path))
        with GraphStore(config.db_path) as store:
            outcome = store.explain_path(
                from_qname,
                to_qname,
                depth=depth,
                max_nodes=config.impact_max_nodes,
            )
        hops = [_shape_hop(hop) for hop in outcome.hops]
        payload: dict[str, object] = {
            "indexed": True,
            "from_qname": from_qname,
            "to_qname": to_qname,
            "status": outcome.status,
            "path": hops,
            "truncated": outcome.truncated or outcome.status == PATH_STATUS_INCOMPLETE,
            "depth": depth,
            "depth_exhausted": outcome.depth_exhausted,
        }
        if detail_level == "standard":
            payload["db_path"] = str(config.db_path)
        return payload

    return explain_path


def _shape_hop(hop: Row) -> dict[str, object]:
    # One EDGE_FIELDS key per statement — R3.2 sole-source gate.
    shaped: dict[str, object] = {}
    shaped["source_qname"] = hop["source_qname"]
    shaped["target_qname"] = hop["target_qname"]
    shaped["kind"] = hop["kind"]
    shaped["confidence_tier"] = hop["confidence_tier"]
    shaped["file"] = hop["file"]
    shaped["line"] = hop["line"]
    return shaped


__all__ = ["NAME", "create"]
