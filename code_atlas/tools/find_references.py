"""``find_references`` — resolved edges targeting a qname (§12)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config, clamp_limit
from code_atlas.contract import UNMODELLED_REFERENCE_KINDS
from code_atlas.store import GraphStore
from code_atlas.tools import call_site, claim
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_RELATIONSHIP_NOT_MODELLED,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_HINT_METHOD_QNAME,
    TRY_INSTEAD_SEARCH_SYMBOL,
    attach_ambiguous_definitions,
    attach_limit_capped,
    attach_result_subtrees,
    attach_try_instead,
    classify_missing_subject,
    definition_sites,
    edge_hit,
    empty_nav,
    nav_result,
    relation_reason,
    shape_exact_miss,
)
from code_atlas.tools.staleness import compute_staleness

NAME = "find_references"

DetailLevel = Literal["minimal", "standard"]

QUESTION = "references"
# ``authoritative: false`` (every hit DYNAMIC) is the caveat this answer can lose to a bare count.
CLAIM_CARRY = ("authoritative",)


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_references(
        qname: str,
        detail_level: DetailLevel = "standard",
        include_source: bool = False,
        limit: int | None = None,
        offset: int = 0,
        sign: bool = False,
    ) -> dict[str, object]:
        """Where is this symbol used across the codebase?

        Resolved edges whose ``target_qname`` is ``qname``, with confidence tiers.
        ``REFERENCES`` (a ``Foo::class`` mention) is FQN-linked at ``DYNAMIC`` — a candidate
        list, not a proven use. When every returned hit is ``DYNAMIC``, the payload sets
        ``authoritative: false``. Bare ``IMPORTS`` stay unlinkable. When unlinked
        ``REFERENCES``/``IMPORTS`` exist for an indexed subject and linked hits are zero, the
        payload uses ``reason=relationship_not_modelled``, ``try_instead=search_symbol`` (it
        enumerates the class's methods) and a ``try_instead_hint`` naming the two-step (065/093).

        ``include_source`` (default off, so the common case stays token-frugal) adds each site's
        own source line as ``source``, capped in length. A site whose file drifted since indexing
        is never quoted: those hits carry ``source_stale`` instead.

        ``limit`` / ``offset`` page in store edge order (057); default limit is
        ``CA_MAX_RESULTS``.

        ``subject_refreshed_only`` is present (and ``true``) only when read-through freshness
        reparsed the subject's file this call — neighbors were not re-verified (035 / 061).

        ``sign`` (default off, so the default payload is unchanged) adds ``claim``: one quotable
        ``key=value`` line naming subject, question, answer and the revision the index describes,
        carrying ``authoritative`` when every hit is ``DYNAMIC``. An answer with no index carries
        no line (task 100).
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
        staleness: dict[str, object] = {}

        def signed(payload: dict[str, object]) -> dict[str, object]:
            """Attach the claim line, or hand the payload back untouched (task 100)."""
            if not sign:
                return payload
            return claim.sign(
                payload,
                tool=NAME,
                question=QUESTION,
                subject_parts=[qname],
                staleness=staleness,
                carry=CLAIM_CARRY,
            )

        with GraphStore(config.db_path) as store:
            if sign:
                staleness = compute_staleness(store, config, include_dirty_count=True)
            guard = FreshnessGuard(config, store)
            freshness = guard.ensure_qname(qname)
            if freshness == "stale":
                return signed(attach_try_instead(
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
                ))
            total_count = store.count_edges_by_target(qname)
            # Widen the existing indexed-check fetch to surface every definition site (task 070).
            nodes = store.nodes_by_qualified_name(qname, limit=config.max_results)
            indexed = bool(nodes)
            if total_count == 0 and not indexed:
                # Under-qualified, untracked, or a genuine absence (075/076/092).
                resolution = classify_missing_subject(
                    store, qname, limit=config.max_results
                )
                miss = nav_result(
                    qname,
                    [],
                    detail_level=detail_level,
                    db_path=str(config.db_path),
                    index_root=config.index_root,
                    truncated=False,
                    reason=REASON_NO_SUCH_SYMBOL,
                    total_count=0,
                )
                return signed(shape_exact_miss(miss, resolution))
            edges = store.edges_by_target(qname, limit=cap, offset=offset)
            results = [edge_hit(edge) for edge in edges]
            # Skewed page 1 hides other subtrees — advertise the full spread (task 067).
            subtrees = (
                store.edge_subtrees_by_target(qname)
                if offset + len(results) < total_count
                else {}
            )
            if include_source:
                call_site.annotate(config.root, store, results)
            reason = relation_reason(hit_total=total_count, symbol_indexed=indexed)
            try_instead: str | None = None
            try_instead_hint: str | None = None
            # Empty + unlinked REFERENCES/IMPORTS ⇒ relationship not modelled (not a genuine zero).
            # The bare-name arm is approximate — an unqualified same-name target counts as
            # evidence, erring toward "may be unmodelled" over a confident zero.
            if reason == REASON_NO_MATCHES and nodes:
                name = str(nodes[0]["name"])
                unlinked = store.count_unlinked_by_target_raw(
                    (qname, name), kinds=UNMODELLED_REFERENCE_KINDS
                )
                if unlinked > 0:
                    reason = REASON_RELATIONSHIP_NOT_MODELLED
                    # search_symbol enumerates the class's methods — the qnames the hint
                    # asks for. Routing back to find_references would loop (093 review).
                    try_instead = TRY_INSTEAD_SEARCH_SYMBOL
                    try_instead_hint = TRY_INSTEAD_HINT_METHOD_QNAME
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
        )
        if freshness == "repaired":
            result["subject_refreshed_only"] = True
        attach_result_subtrees(result, subtrees)
        attach_ambiguous_definitions(result, definition_sites(nodes))
        attach_limit_capped(result, cap=cap, clamped=limit_clamped)
        if results and all(hit.get("confidence_tier") == "DYNAMIC" for hit in results):
            result["authoritative"] = False
        return signed(attach_try_instead(result, try_instead, try_instead_hint))

    return find_references
