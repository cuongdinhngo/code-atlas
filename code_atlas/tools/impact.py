"""``impact`` — bounded best-score blast radius (§12 / M6)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import classify_missing_subject, empty_nav, nav_result

NAME = "impact"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def impact(
        paths: list[str] | None = None,
        qnames: list[str] | None = None,
        depth: int | None = None,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """What could break if I change this file or symbol — the blast radius?

        Bounded best-score over changed paths and/or qnames. Seeds are the union of every indexed
        node on ``paths`` and the explicit ``qnames``.
        ``depth`` defaults to ``CA_IMPACT_DEPTH``; the node budget is ``CA_IMPACT_MAX_NODES``.
        HEURISTIC/DYNAMIC neighbors are returned with their tier but do not expand the
        frontier. Missing seeds and a missing database yield an empty successful result.

        Walks resolver-linked IMPACT kinds only — an empty answer is a modelled zero for those
        kinds, not ``relationship_not_modelled`` (task 065; see ``find_references``).
        """
        hops = config.impact_depth if depth is None else depth
        if hops < 0:
            raise ValueError(f"depth must be >= 0, got {hops}")
        subject = _subject(paths, qnames)
        if not config.db_path.is_file():
            return empty_nav(subject, detail_level=detail_level, db_path=str(config.db_path),
            index_root=config.index_root,
        )
        with GraphStore(config.db_path) as store:
            seeds = _seeds(
                store, paths=paths or [], qnames=qnames or [], max_results=config.max_results
            )
            outcome = store.impact_radius(
                seeds, depth=hops, max_nodes=config.impact_max_nodes + 1
            )
        truncated = len(outcome.rows) > config.impact_max_nodes
        results = outcome.rows[: config.impact_max_nodes]
        return nav_result(
            subject,
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            index_root=config.index_root,
            truncated=truncated,
            depth=hops,
            frontier_skipped_non_resolved=outcome.frontier_skipped_non_resolved,
            seeds_dropped=outcome.seeds_dropped,
        )

    return impact


def _subject(paths: list[str] | None, qnames: list[str] | None) -> str:
    bits: list[str] = []
    if qnames:
        bits.extend(qnames)
    if paths:
        bits.extend(paths)
    return ",".join(bits) if bits else ""


def _seeds(
    store: GraphStore, *, paths: Sequence[str], qnames: Sequence[str], max_results: int
) -> list[str]:
    """Union path-file nodes with explicit qnames (stable order: qnames then path nodes)."""
    found: list[str] = []
    seen: set[str] = set()
    for qname in qnames:
        resolved = _resolve_seed(store, qname, max_results) if qname else None
        if resolved is not None and resolved not in seen:
            seen.add(resolved)
            found.append(resolved)
    for path in paths:
        if not path:
            continue
        for row in store.nodes_by_file_all(path):
            qname = str(row["qualified_name"])
            if qname not in seen:
                seen.add(qname)
                found.append(qname)
    return found


def _resolve_seed(store: GraphStore, qname: str, max_results: int) -> str | None:
    """A seed's stored qname: exact, or a uniquely-resolvable under-anchored form (075/076).

    An ambiguous or absent seed returns None — impact has no per-seed reason channel, so it
    stays counted in ``seeds_dropped`` exactly as before.
    """
    if store.nodes_by_qualified_name(qname, limit=1):
        return qname
    resolution = classify_missing_subject(store, qname, limit=max_results)
    return resolution.qname if resolution.status == "resolved_unique" else None
