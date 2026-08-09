"""``find_references`` — resolved edges targeting a qname (§12)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config
from code_atlas.contract import UNMODELLED_REFERENCE_KINDS
from code_atlas.store import GraphStore
from code_atlas.tools import call_site
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_RELATIONSHIP_NOT_MODELLED,
    TRY_INSTEAD_FIND_REFERENCES_ON_METHOD_QNAME,
    attach_try_instead,
    edge_hit,
    empty_nav,
    nav_result,
    relation_reason,
)

NAME = "find_references"

DetailLevel = Literal["minimal", "standard"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_references(
        qname: str,
        detail_level: DetailLevel = "standard",
        include_source: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, object]:
        """Edges whose resolved ``target_qname`` is ``qname``, with confidence tiers.

        Only kinds the resolver links are visible (FQN edge kinds + ``INCLUDES``). Bare
        ``IMPORTS`` / ``CONTAINS`` / ``REFERENCES`` stay unlinkable until the resolver grows —
        they never appear here even though the SQL has no kind filter. When unlinked
        ``REFERENCES``/``IMPORTS`` exist for an indexed subject and linked hits are zero, the
        payload uses ``reason=relationship_not_modelled`` and ``try_instead`` (task 065).

        ``include_source`` (default off, so the common case stays token-frugal) adds each site's
        own source line as ``source``, capped in length. A site whose file drifted since indexing
        is never quoted: those hits carry ``source_stale`` instead.

        ``limit`` / ``offset`` page in store edge order (057); default limit is
        ``CA_MAX_RESULTS``.

        ``subject_refreshed_only`` is present (and ``true``) only when read-through freshness
        reparsed the subject's file this call — neighbors were not re-verified (035 / 061).
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap = config.max_results if limit is None else min(limit, config.max_results)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        if not config.db_path.is_file():
            return empty_nav(qname, detail_level=detail_level, db_path=str(config.db_path))
        with GraphStore(config.db_path) as store:
            guard = FreshnessGuard(config, store)
            freshness = guard.ensure_qname(qname)
            if freshness == "stale":
                return nav_result(
                    qname,
                    [],
                    detail_level=detail_level,
                    db_path=str(config.db_path),
                    truncated=False,
                    reason=REASON_INDEX_STALE,
                    total_count=0,
                )
            total_count = store.count_edges_by_target(qname)
            nodes = store.nodes_by_qualified_name(qname, limit=1)
            indexed = bool(nodes)
            if total_count == 0 and not indexed:
                return nav_result(
                    qname,
                    [],
                    detail_level=detail_level,
                    db_path=str(config.db_path),
                    truncated=False,
                    reason=REASON_NO_SUCH_SYMBOL,
                    total_count=0,
                )
            edges = store.edges_by_target(qname, limit=cap, offset=offset)
            results = [edge_hit(edge) for edge in edges]
            if include_source:
                call_site.annotate(config.root, store, results)
            reason = relation_reason(hit_total=total_count, symbol_indexed=indexed)
            try_instead: str | None = None
            # Empty + unlinked REFERENCES/IMPORTS ⇒ relationship not modelled (not a genuine zero).
            if reason == REASON_NO_MATCHES and nodes:
                name = str(nodes[0]["name"])
                unlinked = store.count_unlinked_by_target_raw(
                    (qname, name), kinds=UNMODELLED_REFERENCE_KINDS
                )
                if unlinked > 0:
                    reason = REASON_RELATIONSHIP_NOT_MODELLED
                    try_instead = TRY_INSTEAD_FIND_REFERENCES_ON_METHOD_QNAME
        truncated = offset + len(results) < total_count
        result = nav_result(
            qname,
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            truncated=truncated,
            reason=reason,
            total_count=total_count,
        )
        if freshness == "repaired":
            result["subject_refreshed_only"] = True
        return attach_try_instead(result, try_instead)

    return find_references
