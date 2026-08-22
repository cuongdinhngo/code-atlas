"""``find_implementations`` — direct EXTENDS/IMPLEMENTS subtypes (§12)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config, clamp_limit
from code_atlas.contract import IMPL_KINDS
from code_atlas.store import GraphStore
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_SUCH_SYMBOL,
    TRY_INSTEAD_FILE_OUTLINE,
    attach_limit_capped,
    attach_resolved_qname,
    attach_try_instead,
    classify_missing_subject,
    edge_hit,
    empty_nav,
    nav_result,
    relation_reason,
    shape_exact_miss,
    unique_repoint,
)

NAME = "find_implementations"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_implementations(
        qname: str,
        detail_level: DetailLevel = "standard",
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, object]:
        """Which types extend or implement this one? Direct subtypes only (not transitive).

        ``limit`` defaults to ``CA_MAX_RESULTS``; ``offset`` pages in store edge order (057).
        ``EXTENDS``/``IMPLEMENTS`` are resolver-linked, so empty here is a genuine zero, never
        ``relationship_not_modelled`` (065). ``subject_refreshed_only`` is ``true`` only when
        read-through freshness reparsed the subject's file this call — neighbors were not
        re-verified (035 / 061). For transitive subtypes, see ``impact``. A leading-anchor
        difference from the stored qname is re-pointed; ``resolved_qname`` names the stored
        form (075/122). An exact stored qname is unchanged.
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap, limit_clamped = clamp_limit(limit, config.max_results)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        if not config.db_path.is_file():
            return empty_nav(qname, detail_level=detail_level, db_path=str(config.db_path),
            index_root=config.index_root,
        )
        with GraphStore(config.db_path) as store:
            guard = FreshnessGuard(config, store)
            freshness = guard.ensure_qname(qname)
            if freshness == "stale":
                return attach_try_instead(
                    nav_result(
                        qname,
                        [],
                        detail_level=detail_level,
                        db_path=str(config.db_path),
                        index_root=config.index_root,
                        truncated=False,
                        reason=REASON_INDEX_STALE,
                        total_count=0,
                    ),
                    TRY_INSTEAD_FILE_OUTLINE,
                )
            asked = qname
            lookup = qname
            total_count = store.count_edges_by_target(lookup, kinds=IMPL_KINDS)
            indexed = bool(store.nodes_by_qualified_name(lookup, limit=1))
            if total_count == 0 and not indexed:
                # Under-qualified, untracked, or a genuine absence (075/076/092/122).
                resolution = classify_missing_subject(
                    store, asked, limit=config.max_results
                )
                repointed = unique_repoint(resolution)
                if repointed is None:
                    miss = nav_result(
                        asked,
                        [],
                        detail_level=detail_level,
                        db_path=str(config.db_path),
                        index_root=config.index_root,
                        truncated=False,
                        reason=REASON_NO_SUCH_SYMBOL,
                        total_count=0,
                    )
                    return shape_exact_miss(miss, resolution)
                lookup = repointed
                total_count = store.count_edges_by_target(lookup, kinds=IMPL_KINDS)
                indexed = bool(store.nodes_by_qualified_name(lookup, limit=1))
            edges = store.edges_by_target(
                lookup, kinds=IMPL_KINDS, limit=cap, offset=offset
            )
            results = [edge_hit(edge) for edge in edges]
        truncated = offset + len(results) < total_count
        result = nav_result(
            qname,
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            index_root=config.index_root,
            truncated=truncated,
            reason=relation_reason(hit_total=total_count, symbol_indexed=indexed),
            total_count=total_count,
        )
        if freshness == "repaired":
            result["subject_refreshed_only"] = True
        attach_limit_capped(result, cap=cap, clamped=limit_clamped)
        attach_resolved_qname(result, asked=asked, answered=lookup)
        return result

    return find_implementations
