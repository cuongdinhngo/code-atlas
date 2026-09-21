"""``find_view_data`` — view-scope keys a handler method publishes (task 062)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas import contract
from code_atlas.config import Config, clamp_limit
from code_atlas.enrichment import view_data_key
from code_atlas.store import GraphStore
from code_atlas.tools.coverage import attach_coverage_note, covered_languages
from code_atlas.tools.freshness import FreshnessGuard, finalize_subject_checked_miss
from code_atlas.tools.nav_result import (
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    TRY_INSTEAD_FILE_OUTLINE,
    answered_about_ref_for,
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

NAME = "find_view_data"

DetailLevel = Literal["minimal", "standard"]

_KIND = (contract.PROVIDES_VIEW_DATA,)


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_view_data(
        qname: str,
        detail_level: DetailLevel = "standard",
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, object]:
        """What variables does this handler make available to its template?

        Each hit carries the ``key`` a caller can read in the view, the call-site ``line``, and
        ``rule: true``. Needs ``CA_INDIRECTION_RULES`` with a ``view_data`` setter rule: with no
        rules configured the answer is ``reason=capability_not_configured`` (the tool is inert on
        this index), which is distinct from a configured repo where this handler simply publishes
        nothing (``no_matches``). ``file`` is the subject's declaration path when known.
        A leading-anchor difference from the stored qname is re-pointed; ``resolved_qname``
        names the stored form (075/122). An exact stored qname is unchanged.
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
            asked = qname
            lookup = qname
            total = store.count_edges_by_source(lookup, kinds=_KIND)
            indexed = bool(store.nodes_by_qualified_name(lookup, limit=1))
            if total == 0 and not indexed:
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
                    # A miss still names what the guard repaired (073) — the 092 shortcut must not
                    # drop a signal the fall-through carried.
                    if freshness == "repaired":
                        miss["subject_refreshed_only"] = True
                    attach_limit_capped(miss, cap=cap, clamped=limit_clamped)
                    shaped = shape_exact_miss(miss, resolution)
                    finalize_subject_checked_miss(shaped, guard)
                    return attach_coverage_note(
                        shaped,
                        config,
                        covered,
                        detail_level=detail_level,
                    )
                lookup = repointed
                total = store.count_edges_by_source(lookup, kinds=_KIND)
                indexed = bool(store.nodes_by_qualified_name(lookup, limit=1))
            rows = store.edges_by_source(lookup, kinds=_KIND, limit=cap, offset=offset)
            file_path = _subject_file(store, lookup)
            results: list[dict[str, object]] = []
            for edge in rows:
                hit = edge_hit(edge, subject=lookup)
                key = view_data_key(edge.get("target_raw"))
                if key is not None:
                    hit["key"] = key
                if file_path is not None:
                    hit["file"] = file_path
                results.append(hit)
            truncated = offset + len(results) < total
            reason = relation_reason(hit_total=total, symbol_indexed=indexed)
            if reason == REASON_NO_MATCHES and config.indirection_rules is None:
                # Indexed handler, empty only because no rules are configured — inert, not a
                # genuine "publishes nothing" zero (069). A missing subject stays no_such_symbol.
                reason = REASON_CAPABILITY_NOT_CONFIGURED
            result = nav_result(
                asked,
                results,
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
                truncated=truncated,
                reason=reason,
                total_count=total,
            answered_about_ref=about_ref)
            if freshness == "repaired":
                result["subject_refreshed_only"] = True
            attach_limit_capped(result, cap=cap, clamped=limit_clamped)
            attach_resolved_qname(result, asked=asked, answered=lookup)
            return attach_coverage_note(result, config, covered, detail_level=detail_level)

    return find_view_data


def _subject_file(store: GraphStore, qname: str) -> str | None:
    nodes = store.nodes_by_qualified_name(qname, limit=1)
    if not nodes:
        return None
    path = nodes[0].get("file_path")
    return path if isinstance(path, str) and path else None
