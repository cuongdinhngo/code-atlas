"""``explain_path`` — shortest control-flow path between two qnames (task 038)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.build_info import maybe_server_provenance
from code_atlas.config import Config
from code_atlas.store import PATH_STATUS_INCOMPLETE, GraphStore, Row
from code_atlas.tools.nav_result import REASON_NOT_INDEXED, classify_missing_subject

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
        """How does one symbol reach another — the shortest path between them?

        Walks outgoing CALLS/NEW/INCLUDES/EXTENDS/IMPLEMENTS from ``from_qname`` to ``to_qname``
        (same kinds as
        ``impact`` / ``reachable_from``). Default ``depth`` is unset — walk until
        the frontier empties or ``CA_IMPACT_MAX_NODES`` binds. A RESOLVED-only path
        is ``status=path``; a path that needs HEURISTIC/DYNAMIC hops is
        ``unproven``. Missing endpoints → ``unknown``; bound hit before ``to`` →
        ``incomplete``; both present with no route → ``no_path``.

        Path search is over linked IMPACT kinds — ``no_path`` is modelled, not
        ``relationship_not_modelled`` (task 065).
        """
        if depth is not None and depth < 0:
            raise ValueError(f"depth must be >= 0, got {depth}")
        if not config.db_path.is_file():
            return _not_indexed(from_qname, to_qname, depth, detail_level, config)
        with GraphStore(config.db_path) as store:
            # Re-point a uniquely-resolvable under-anchored endpoint; echo it (075/076).
            from_qname = _resolve_endpoint(store, from_qname, config.max_results)
            to_qname = _resolve_endpoint(store, to_qname, config.max_results)
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
            "index_root": config.index_root,
            **maybe_server_provenance(detail_level),
        }
        return payload

    return explain_path


def _not_indexed(
    from_qname: str,
    to_qname: str,
    depth: int | None,
    detail_level: DetailLevel,
    config: Config,
) -> dict[str, object]:
    """Same keys as an indexed answer — clients must not KeyError on a missing DB."""
    payload: dict[str, object] = {
        "indexed": False,
        "from_qname": from_qname,
        "to_qname": to_qname,
        "status": REASON_NOT_INDEXED,
        "path": [],
        "truncated": False,
        "depth": depth,
        "depth_exhausted": False,
        "index_root": config.index_root,
        **maybe_server_provenance(detail_level),
    }
    return payload


def _resolve_endpoint(store: GraphStore, qname: str, max_results: int) -> str:
    """The stored qname for an endpoint: exact, or a uniquely-resolvable under-anchored form.

    An ambiguous or absent endpoint is returned unchanged, so ``store.explain_path`` still
    reports ``unknown`` for it exactly as before (075/076).
    """
    if not qname or store.nodes_by_qualified_name(qname, limit=1):
        return qname
    resolution = classify_missing_subject(store, qname, limit=max_results)
    return resolution.qname if resolution.status == "resolved_unique" else qname


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
