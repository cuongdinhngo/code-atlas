"""``find_references`` — resolved edges targeting a qname (§12)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config, clamp_limit
from code_atlas.contract import EDGE_KINDS, TYPE_KINDS
from code_atlas.store import GraphStore
from code_atlas.tools import call_site, claim
from code_atlas.tools.coverage import (
    attach_coverage_note,
    covered_languages,
    cross_language_relation_unmodelled,
    relation_unmodelled_for_language,
)
from code_atlas.tools.freshness import FreshnessGuard, finalize_subject_checked_miss
from code_atlas.tools.nav_result import (
    CAVEAT_ALL_HITS_DYNAMIC,
    CAVEAT_CROSS_LANGUAGE_UNMODELLED,
    CAVEAT_SIBLING_DEFINITIONS,
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
    REASON_RELATIONSHIP_NOT_MODELLED,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_HINT_METHOD_QNAME,
    TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE,
    TRY_INSTEAD_SEARCH_SYMBOL,
    attach_ambiguous_definitions,
    attach_authoritative_caveats,
    attach_cross_language_census,
    attach_limit_capped,
    attach_resolved_qname,
    attach_result_subtrees,
    attach_sibling_definitions,
    attach_try_instead,
    classify_missing_subject,
    definition_sites,
    edge_hit,
    empty_nav,
    nav_result,
    relation_reason,
    shape_exact_miss,
    sibling_definition_rows,
    unique_repoint,
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
        ``authoritative: false``. When another language is indexed but no linked ``*->L``
        pair reaches the subject's language (238), a hits-bearing answer is also
        ``authoritative: false`` and carries the cross-language census; ``reason`` stays ``ok``.
        An ``IMPORTS`` naming an indexed file is linked since 188, so a
        **File** subject lists its importers; one naming a symbol or an unresolvable specifier stays
        bare. When unlinked ``REFERENCES``/``IMPORTS`` exist for an indexed subject and linked
        hits are zero, the
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

        A leading-anchor difference from the stored qname (``Ns\\Sub\\Enum`` vs
        ``\\Ns\\Sub\\Enum``) is re-pointed and answered; ``resolved_qname`` names the
        stored form (075/122). An exact stored qname is unchanged.
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

        covered: str | None = None
        cross_lang_census: dict[str, object] | None = None
        unlinked_edge_kinds: list[str] = []
        with GraphStore(config.db_path) as store:
            covered = covered_languages(store)
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
            asked = qname
            lookup = qname
            total_count = store.count_edges_by_target(lookup)
            # Widen the existing indexed-check fetch to surface every definition site (task 070).
            nodes = store.nodes_by_qualified_name(lookup, limit=config.max_results)
            indexed = bool(nodes)
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
                    shaped = shape_exact_miss(miss, resolution)
                    finalize_subject_checked_miss(shaped, guard)
                    return signed(
                        attach_coverage_note(
                            shaped, config, covered,
                            detail_level=detail_level,
                        )
                    )
                lookup = repointed
                total_count = store.count_edges_by_target(lookup)
                nodes = store.nodes_by_qualified_name(lookup, limit=config.max_results)
                indexed = bool(nodes)
            # A same-named definition under another qname makes this count a partition (168).
            # One bounded query, keyed on the subject's own kind — 054's rule, not a constant.
            sibling_sites: list[dict[str, object]] = []
            # The subject's own file is what "near" is measured against (171).
            subject_file = str(nodes[0]["file_path"]) if nodes else None
            if indexed and subject_file is not None:
                # Language-scope, not hit-count (238). Same predicate as find_callers.
                cross_lang_census = cross_language_relation_unmodelled(
                    store, file_path=subject_file
                )
            if indexed and nodes:
                sibling_sites = definition_sites(
                    sibling_definition_rows(
                        store,
                        bare_name=str(nodes[0]["name"]),
                        kind=str(nodes[0]["kind"]),
                        lookup=lookup,
                        limit=config.max_results,
                    )
                )
            edges = store.edges_by_target(lookup, limit=cap, offset=offset)
            results = [edge_hit(edge) for edge in edges]
            # Skewed page 1 hides other subtrees — advertise the full spread (task 067).
            subtrees = (
                store.edge_subtrees_by_target(lookup)
                if offset + len(results) < total_count
                else {}
            )
            if include_source:
                call_site.annotate(config.root, store, results)
            reason = relation_reason(hit_total=total_count, symbol_indexed=indexed)
            try_instead: str | None = None
            try_instead_hint: str | None = None
            # Empty + any unlinked inbound edge of a contract kind ⇒ not a genuine zero (065/255).
            # Keyed to EDGE_KINDS (the contract vocabulary), never the PHP-shaped REFERENCES/IMPORTS
            # pair alone — a Table with unlinked WRITES must not read as no_matches (R1.1).
            if reason == REASON_NO_MATCHES and nodes:
                name = str(nodes[0]["name"])
                unlinked_edge_kinds = store.unlinked_kinds_by_target_raw(
                    (lookup, name), kinds=EDGE_KINDS
                )
                if unlinked_edge_kinds:
                    reason = REASON_RELATIONSHIP_NOT_MODELLED
                    # Type-shaped subjects still route to search_symbol for member qnames
                    # (093). Other kinds get the relation hint, never a self-loop tool name.
                    # TYPE_KINDS is imported, never re-listed here (R3.2).
                    if str(nodes[0]["kind"]) in TYPE_KINDS:
                        try_instead = TRY_INSTEAD_SEARCH_SYMBOL
                        try_instead_hint = TRY_INSTEAD_HINT_METHOD_QNAME
                    else:
                        try_instead_hint = TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE
                elif relation_unmodelled_for_language(
                    store, file_path=str(nodes[0]["file_path"]), kinds=("REFERENCES",)
                ):
                    # Per-kind (232): IMPORTS in the set must not mask a never-emitted REFERENCES.
                    # language_emits_none_of(UNMODELLED_REFERENCE_KINDS) stays the set-level reader.
                    reason = REASON_RELATION_UNMODELLED_FOR_LANGUAGE
                    try_instead_hint = TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE
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
        if unlinked_edge_kinds:
            # Names the unmeasured relation(s) — not hits (R5.6 / 255 AC1).
            result["unlinked_edge_kinds"] = unlinked_edge_kinds

        if freshness == "repaired":
            result["subject_refreshed_only"] = True
        attach_result_subtrees(result, subtrees)
        attach_ambiguous_definitions(result, definition_sites(nodes))
        attach_limit_capped(result, cap=cap, clamped=limit_clamped)
        attach_resolved_qname(result, asked=asked, answered=lookup)
        caveats: list[str] = []
        if results and all(hit.get("confidence_tier") == "DYNAMIC" for hit in results):
            caveats.append(CAVEAT_ALL_HITS_DYNAMIC)
        if attach_sibling_definitions(result, sibling_sites, subject_file=subject_file):
            caveats.append(CAVEAT_SIBLING_DEFINITIONS)
        if cross_lang_census is not None and total_count > 0:
            attach_cross_language_census(result, cross_lang_census)
            caveats.append(CAVEAT_CROSS_LANGUAGE_UNMODELLED)
        attach_authoritative_caveats(result, caveats)
        return signed(
            attach_coverage_note(
                attach_try_instead(result, try_instead, try_instead_hint), config, covered,
                detail_level=detail_level,
            )
        )

    return find_references
