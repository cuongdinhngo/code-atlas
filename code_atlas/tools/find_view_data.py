"""``find_view_data`` — view-scope keys a handler method publishes (task 062)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas import contract
from code_atlas.config import Config, clamp_limit
from code_atlas.enrichment import view_data_key
from code_atlas.store import GraphStore
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import (
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    TRY_INSTEAD_FILE_OUTLINE,
    attach_limit_capped,
    attach_try_instead,
    edge_hit,
    empty_nav,
    nav_result,
    relation_reason,
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
            total = store.count_edges_by_source(qname, kinds=_KIND)
            indexed = bool(store.nodes_by_qualified_name(qname, limit=1))
            rows = store.edges_by_source(qname, kinds=_KIND, limit=cap, offset=offset)
            file_path = _subject_file(store, qname)
            results: list[dict[str, object]] = []
            for edge in rows:
                hit = edge_hit(edge, subject=qname)
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
                qname,
                results,
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
                truncated=truncated,
                reason=reason,
                total_count=total,
            )
            if freshness == "repaired":
                result["subject_refreshed_only"] = True
            attach_limit_capped(result, cap=cap, clamped=limit_clamped)
            return result

    return find_view_data


def _subject_file(store: GraphStore, qname: str) -> str | None:
    nodes = store.nodes_by_qualified_name(qname, limit=1)
    if not nodes:
        return None
    path = nodes[0].get("file_path")
    return path if isinstance(path, str) and path else None
