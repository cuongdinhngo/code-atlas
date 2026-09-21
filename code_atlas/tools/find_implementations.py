"""``find_implementations`` — direct EXTENDS/IMPLEMENTS subtypes (§12)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config, clamp_limit
from code_atlas.contract import IMPL_KINDS
from code_atlas.store import GraphStore
from code_atlas.tools.coverage import attach_coverage_note, covered_languages
from code_atlas.tools.freshness import FreshnessGuard, finalize_subject_checked_miss
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    TRY_INSTEAD_FILE_OUTLINE,
    answered_about_ref_for,
    apply_empty_inbound_honesty,
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
        ``EXTENDS``/``IMPLEMENTS`` are resolver-linked when present; an empty linked page still
        routes through the shared empty-inbound predicate (264) so unlinked evidence of any mapped
        kind cannot read as bare ``no_matches``. ``subject_refreshed_only`` is ``true`` only when
        read-through freshness reparsed the subject's file this call — neighbors were not
        re-verified (035 / 061). For transitive subtypes, see ``impact``. A leading-anchor
        difference from the stored qname is re-pointed; ``resolved_qname`` names the stored
        form (075/122). An exact stored qname is unchanged.
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap, limit_clamped = clamp_limit(limit, config.page_limit)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        if not config.db_path.is_file():
            return empty_nav(qname, detail_level=detail_level, db_path=str(config.db_path),
            index_root=config.index_root,
            answered_about_ref=None)
        covered: str | None = None
        freshness = "ok"
        asked = qname
        lookup = qname
        results: list[dict[str, object]] = []
        total_count = 0
        reason = REASON_NO_SUCH_SYMBOL
        unlinked_edge_kinds: list[str] = []
        with GraphStore(config.db_path) as store:
            about_ref = answered_about_ref_for(store)
            covered = covered_languages(store)
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
            answered_about_ref=about_ref),
                    TRY_INSTEAD_FILE_OUTLINE,
                )
            total_count = store.count_edges_by_target(lookup, kinds=IMPL_KINDS)
            subject_nodes = store.nodes_by_qualified_name(lookup, limit=1)
            indexed = bool(subject_nodes)
            if total_count == 0 and not indexed:
                # Under-qualified, untracked, or a genuine absence (075/076/092/122).
                resolution = classify_missing_subject(
                    store, asked, limit=config.page_limit
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
            answered_about_ref=about_ref)
                    shaped = shape_exact_miss(miss, resolution)
                    finalize_subject_checked_miss(shaped, guard)
                    return attach_coverage_note(
                        shaped,
                        config,
                        covered,
                        detail_level=detail_level,
                    )
                lookup = repointed
                total_count = store.count_edges_by_target(lookup, kinds=IMPL_KINDS)
                subject_nodes = store.nodes_by_qualified_name(lookup, limit=1)
                indexed = bool(subject_nodes)
            edges = store.edges_by_target(
                lookup, kinds=IMPL_KINDS, limit=cap, offset=offset
            )
            results = [edge_hit(edge) for edge in edges]
            reason = relation_reason(hit_total=total_count, symbol_indexed=indexed)
            if reason == REASON_NO_MATCHES and subject_nodes:
                # Reuse the rows the indexed-check already fetched — no second lookup.
                reason, unlinked_edge_kinds = apply_empty_inbound_honesty(
                    reason,
                    store,
                    subject_kind=str(subject_nodes[0]["kind"]),
                    raws=(lookup,),
                )
        truncated = offset + len(results) < total_count
        result = nav_result(
            qname,
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            index_root=config.index_root,
            truncated=truncated,
            reason=reason,
            total_count=total_count,
            answered_about_ref=about_ref)
        if unlinked_edge_kinds:
            result["unlinked_edge_kinds"] = unlinked_edge_kinds
        if freshness == "repaired":
            result["subject_refreshed_only"] = True
        attach_limit_capped(result, cap=cap, clamped=limit_clamped)
        attach_resolved_qname(result, asked=asked, answered=lookup)
        return attach_coverage_note(result, config, covered, detail_level=detail_level)

    return find_implementations
