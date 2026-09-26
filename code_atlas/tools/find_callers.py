"""``find_callers`` — who CALLS/NEW a qname, with optional depth (§12)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Literal, NamedTuple

from code_atlas.config import Config, clamp_limit
from code_atlas.contract import (
    ARG_SELECTORS,
    CALLER_KINDS,
    CONFIDENCE_TIERS,
    ConfidenceTier,
    inbound_kinds_for,
    split_qname,
)
from code_atlas.store import GraphStore, Row
from code_atlas.symbol_role import (
    aggregate_test_count_source,
    stored_test_source,
)
from code_atlas.tools import call_site, claim
from code_atlas.tools.coverage import (
    attach_coverage_note,
    coverage_gap,
    covered_languages,
    cross_language_census_has_edges,
    cross_language_relation_unmodelled,
)
from code_atlas.tools.freshness import (
    FreshnessGuard,
    dirty_indexed_paths,
    finalize_subject_checked_miss,
    label_serve_behind,
    unrepaired_subject_served,
)
from code_atlas.tools.nav_result import (
    CAVEAT_ARGS_NOT_CAPTURED,
    CAVEAT_CROSS_LANGUAGE_UNMODELLED,
    CAVEAT_SIBLING_DEFINITIONS,
    CAVEAT_TIER_PARTITION,
    CAVEAT_UNLINKED_SAME_NAME_SITES,
    REASON_BARE_NAME_TRUNCATED,
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_PROXIMITY_CANDIDATES,
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE,
    answered_about_ref_for,
    apply_empty_inbound_honesty,
    attach_ambiguous_definitions,
    attach_authoritative_caveats,
    attach_coverage_edge_route,
    attach_cross_language_census,
    attach_limit_capped,
    attach_resolved_qname,
    attach_result_subtrees,
    attach_serve_behind_route,
    attach_sibling_definitions,
    attach_try_instead,
    classify_missing_subject,
    definition_sites,
    edge_hit,
    edge_id,
    empty_nav,
    escalate_zero_production,
    nav_result,
    relation_reason,
    shape_exact_miss,
    sibling_definition_rows,
    unique_repoint,
)
from code_atlas.tools.staleness import compute_staleness

NAME = "find_callers"

DetailLevel = Literal["minimal", "standard"]

QUESTION = "callers"
# Caveats that ride the claim line when present — each omitted when the payload has no such key.
CLAIM_CARRY = (
    "frontier_skipped_non_resolved",
    "unresolved_bare_calls",
    "args_unrecorded",
    "tier_filter",
    "authoritative",
)

# The subject shares a trailing method name with definitions under other qnames — callers reached
# by simple name may bind to a sibling, so this answer is a partition, not the whole (task 165).

_RESOLVED = CONFIDENCE_TIERS[0]
# Cap BFS counting so total_count stays honest-as-a-floor without walking the whole graph.
_COUNT_BUDGET_FACTOR = 10


class _CallersOutcome(NamedTuple):
    results: list[dict[str, object]]
    truncated: bool
    total_count: int
    frontier_skipped_non_resolved: int


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_callers(
        qname: str,
        depth: int = 1,
        detail_level: DetailLevel = "standard",
        include_source: bool = False,
        arg_position: int | None = None,
        arg_is: str | None = None,
        confidence_tier: ConfidenceTier | None = None,
        limit: int | None = None,
        offset: int = 0,
        sign: bool = False,
        serve_behind: bool = False,
        exclude_tests: bool = False,
    ) -> dict[str, object]:
        """Who calls this function or method? Every call site, with confidence and optional depth.

        ``depth`` defaults to 1 (direct). Deeper values BFS over CALLS/NEW, but only
        ``RESOLVED`` edges expand the frontier — HEURISTIC/DYNAMIC hits are returned and counted
        in ``frontier_skipped_non_resolved`` when a deeper hop was requested.

        ``total_count`` is the size of the BFS hit set within ``depth`` (exact at depth 1;
        a lower bound when a deeper walk hits the count budget — and at depth > 1 that floor
        is valid for the requested page only, because the budget grows with ``offset``).

        ``include_source`` (default off, so the common case stays token-frugal) adds each call
        site's own source line as ``source``, capped in length — answering "show me" without a
        second call. A site whose file drifted since indexing is never quoted: those hits carry
        ``source_stale`` instead. At depth 1 a caller that calls the subject from two or more
        lines carries them all as ``call_lines`` (``line`` stays the first), quoted as
        ``call_sources`` under ``include_source``; it is still one caller in ``total_count``.

        ``arg_position`` (1-based) with ``arg_is`` keeps only call sites whose argument there has
        that shape: a literal category (``null``, ``true``, ``false``, ``number``, ``string``,
        ``array``), ``absent`` (the call passes fewer arguments), or ``dynamic`` (present, but not
        a literal). ``total_count`` then counts matches, and ``args_unrecorded`` says how many
        call sites the filter could not judge — sites whose arguments were never recorded, which
        are never counted as matches. Depth 1 only.

        ``confidence_tier`` (default off) keeps only callers at that tier — the predicate runs in
        the store query next to ``kinds`` / ``args_at``, so a RESOLVED-only page is not a
        post-filter over an alphabetically truncated page (task 251). ``total_count`` then counts
        matches of that request, and ``tier_filter`` names the filter (R5.6). Without the filter,
        ``tier_census`` reports the full hit set's tier breakdown when more than one tier is
        present (omit-when-empty, 061). Depth 1 only.

        A Method subject whose linked answer is empty may expand to the unresolved same-named
        CALL sites near it, ranked by shared subtree (258). Those rows are candidates the
        resolver declined to link, so the answer is ``proximity_candidates``, never ``ok``, and
        each row names ``candidate_of``.

        ``limit`` / ``offset`` page results (057). At depth 1 the store owns OFFSET; deeper walks
        apply offset to the BFS hit stream. Complete enumeration is guaranteed at depth 1.

        When bare-name resolution capped Method candidates alphabetically (task 054), a subject
        outside that cap can have zero inbound edges while CALLS sites named its bare method still
        exist. Those sites are counted in ``unresolved_bare_calls``, and an empty answer then uses
        ``reason=bare_name_truncated`` instead of ``no_matches``.

        When a Function subject still has unlinked CALLS targeting its short name
        (schema-unqualified ``EXEC`` that could not resolve uniquely — task 214), an empty
        answer uses ``reason=relation_unmodelled_for_language`` instead of ``no_matches``.
        The same unmeasured route fires when ``production_count`` is 0 on a depth-1 indexed
        subject with surviving test callers: ``reason`` is not ``ok``, and
        ``unlinked_same_name_sites`` counts the unlinked inbound that name it (272). A Function
        answer with hits carries the same count, ``authoritative: false`` and the
        ``unlinked_same_name_sites`` caveat when such CALLS remain beside them (334).

        When another language is indexed but no linked ``*->L`` pair reaches the subject's
        language (221/238), an empty answer upgrades to ``relation_unmodelled_for_language``.
        Hits carry ``authoritative: false`` only when the stamped census has cross-language
        edges (276); an empty census is status-only. ``caveat_limits`` states the cost (251).

        ``subject_refreshed_only`` is present (and ``true``) only when read-through freshness
        reparsed the subject's file this call — neighbors were not re-verified (035 / 061).
        An untracked indexable file matching the subject is ``reason=not_indexed`` plus
        ``try_instead=build_or_update_index`` — never ``no_such_symbol`` (092).

        ``sign`` (default off, so the default payload is unchanged) adds ``claim``: one quotable
        ``key=value`` line naming subject, question, answer and the revision the index describes.
        The weakest tier present is named, so the line can never claim ``RESOLVED`` over a
        ``HEURISTIC`` hit. An answer with no index carries no line (task 100).

        ``exclude_tests`` (default off) drops test-role callers in SQL; at depth > 1
        they are pruned from the walk so they never expand (313 shape; 332).
        ``serve_behind`` (default off) labels a behind-index answer: unchanged subjects as
        ``index_behind`` (257); unrepaired dirty subjects as ``index_behind_subject_changed``
        (267). Off keeps today's refuse-when-stale default (022 AC3).

        A leading-anchor difference from the stored qname is re-pointed and answered;
        ``resolved_qname`` names the stored form (075/122). An exact stored qname is unchanged.
        """
        if depth < 1:
            raise ValueError(f"depth must be >= 1, got {depth}")
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap, limit_clamped = clamp_limit(limit, config.page_limit)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        # exclude_tests at any depth: prune test-role sources inside the walk (313 shape; 332).
        args_at = _args_at(arg_position, arg_is, depth=depth)
        tier = _confidence_tier(confidence_tier, depth=depth)
        if not config.db_path.is_file():
            return empty_nav(
                qname,
                detail_level=detail_level,
                db_path=str(config.db_path),
                index_root=config.index_root,
                answered_about_ref=None,
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
        unlinked_calls = 0
        unlinked_same_name_sites = 0
        unlinked_beside_hits = 0
        shared_unlinked: list[str] = []
        shared_honesty_reason = REASON_NO_MATCHES
        unlinked_edge_kinds: list[str] = []
        cross_lang_census: dict[str, object] | None = None
        args_capture_absent = False
        proximity_used = False
        behind_dirty: list[str] = []
        subject_file: str | None = None
        subject_unrepaired = False
        test_role_label: str | None = None
        production_count = 0
        test_count = 0
        about_ref: str | None = None
        with GraphStore(config.db_path) as store:
            covered = covered_languages(store)
            stamped = store.stamped_unmodelled_resolution_by_language()
            about_ref = answered_about_ref_for(store)
            if sign or serve_behind:
                staleness = compute_staleness(store, config, include_dirty_count=True)
            if serve_behind:
                behind_dirty = dirty_indexed_paths(store, config)
            guard = FreshnessGuard(config, store)
            freshness = guard.ensure_qname(qname)
            if freshness == "stale":
                if not unrepaired_subject_served(
                    store, qname, serve_behind=serve_behind, dirty_paths=behind_dirty
                ):
                    refused = nav_result(
                        qname,
                        [],
                        detail_level=detail_level,
                        db_path=str(config.db_path),
                        index_root=config.index_root,
                        truncated=False,
                        reason=REASON_INDEX_STALE,
                        total_count=0,
                        depth=depth,
                        frontier_skipped_non_resolved=0,
                        answered_about_ref=about_ref,
                    )
                    # 274: name the opt-in that answers; file_outline cannot fix a stale subject.
                    if not serve_behind:
                        return signed(attach_serve_behind_route(refused))
                    return signed(attach_try_instead(refused, TRY_INSTEAD_FILE_OUTLINE))
                subject_unrepaired = True
            asked = qname
            lookup = qname
            outcome = _callers(
                store,
                lookup,
                hops=depth,
                limit=cap,
                offset=offset,
                args_at=args_at,
                confidence_tier=tier,
                exclude_test_sources=exclude_tests,
            )
            # Widen the existing indexed-check fetch to surface every definition site (task 070).
            subject_nodes = store.nodes_by_qualified_name(lookup, limit=config.page_limit)
            indexed = bool(subject_nodes)
            production_count, test_count, test_role_label = _test_census(
                store, lookup, depth=depth, args_at=args_at, confidence_tier=tier
            )
            unrecorded = (
                store.count_edges_without_args(lookup, kinds=CALLER_KINDS)
                if args_at is not None
                else None
            )
            tier_census = _tier_census(
                store,
                lookup,
                args_at=args_at,
                depth=depth,
                tier=tier,
                indexed=indexed,
                hit_total=outcome.total_count,
            )
            if outcome.total_count == 0 and not indexed:
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
                        depth=depth,
                        frontier_skipped_non_resolved=0,
                        answered_about_ref=about_ref,
                    )
                    # A miss still names what the guard repaired (073) and what it could not judge
                    # (049) — the 092 shortcut must not drop signals the fall-through carried.
                    if freshness == "repaired":
                        miss["subject_refreshed_only"] = True
                    if unrecorded is not None:
                        miss["args_unrecorded"] = unrecorded
                    attach_limit_capped(miss, cap=cap, clamped=limit_clamped)
                    shaped = shape_exact_miss(miss, resolution)
                    finalize_subject_checked_miss(shaped, guard)
                    attach_coverage_edge_route(
                        shaped,
                        stamped,
                        has_coverage_gap=bool(coverage_gap(config)),
                        detail_level=detail_level,
                    )
                    return signed(
                        attach_coverage_note(
                            shaped, config, covered,
                            detail_level=detail_level,
                        )
                    )
                lookup = repointed
                outcome = _callers(
                    store,
                    lookup,
                    hops=depth,
                    limit=cap,
                    offset=offset,
                    args_at=args_at,
                    confidence_tier=tier,
                    exclude_test_sources=exclude_tests,
                )
                subject_nodes = store.nodes_by_qualified_name(
                    lookup, limit=config.page_limit
                )
                indexed = bool(subject_nodes)
                production_count, test_count, test_role_label = _test_census(
                    store, lookup, depth=depth, args_at=args_at, confidence_tier=tier
                )
                unrecorded = (
                    store.count_edges_without_args(lookup, kinds=CALLER_KINDS)
                    if args_at is not None
                    else None
                )
                tier_census = _tier_census(
                    store,
                    lookup,
                    args_at=args_at,
                    depth=depth,
                    tier=tier,
                    indexed=indexed,
                    hit_total=outcome.total_count,
                )
            container, bare_name = split_qname(lookup)
            unresolved_bare = 0
            if (
                indexed
                and container is not None
                and (outcome.total_count == 0 or (depth == 1 and production_count == 0))
            ):
                # Method-shaped only — Function ``\App\put`` ≠ bare Method ``put``.
                # Cap uses query-time page_limit (build fan-out may differ — 259).
                if store.count_nodes_by_name(bare_name, kind="Method") > config.page_limit:
                    unresolved_bare = store.count_bare_calls_not_targeting(
                        lookup, bare_name=bare_name
                    )
            sibling_sites: list[dict[str, object]] = []
            # The subject's own file is what "near" is measured against (171).
            subject_file = str(subject_nodes[0]["file_path"]) if subject_nodes else None
            # 258: unresolved same-named CALL sites — query-time proximity, not build fan-out.
            if (
                depth == 1
                and indexed
                and outcome.total_count == 0
                and subject_file is not None
                and args_at is None
                and str(subject_nodes[0]["kind"]) == "Method"
            ):
                prox = _proximity_unresolved_callers(
                    store,
                    bare_name=str(subject_nodes[0]["name"]),
                    language=store.language_of_file(subject_file),
                    subject_file=subject_file,
                    subject_qname=lookup,
                    limit=cap,
                    offset=offset,
                    confidence_tier=tier,
                )
                if prox is not None and prox.total_count > 0:
                    outcome = prox
                    proximity_used = True
                    if tier is None:
                        # Linked census was empty; HEURISTIC sites are the answer.
                        tier_census = {"HEURISTIC": prox.total_count}
            if indexed and str(subject_nodes[0]["kind"]) == "Function":
                # Same bare name, other schema/qname — the AC2 visibility surface for SQL (214).
                # Uses the node's `name` because dotted Function qnames are not `::`-split.
                siblings = sibling_definition_rows(
                    store,
                    bare_name=str(subject_nodes[0]["name"]),
                    kind="Function",
                    lookup=lookup,
                    limit=config.page_limit,
                )
                sibling_sites = definition_sites(siblings)
            elif indexed and container is not None:
                # A same-named Method under a different qname; a simple-name caller may bind
                # there, so this count is a partition (task 165). One bounded query.
                siblings = sibling_definition_rows(
                    store,
                    bare_name=bare_name,
                    kind="Method",
                    lookup=lookup,
                    limit=config.page_limit,
                )
                sibling_sites = definition_sites(siblings)
            if include_source:
                call_site.annotate(config.root, store, outcome.results)
            # Skewed page 1 hides other subtrees — advertise the full spread (task 067).
            # Depth 1 only: the store spread is exact there; deeper total_count is a floor.
            subtrees = (
                store.edge_subtrees_by_target(
                    lookup,
                    kinds=CALLER_KINDS,
                    args_at=args_at,
                    confidence_tier=tier,
                )
                if depth == 1 and outcome.truncated
                else {}
            )
            unlinked_calls = 0
            if (
                outcome.total_count == 0
                and indexed
                and unresolved_bare == 0
                and str(subject_nodes[0]["kind"]) == "Function"
            ):
                # CALLS exist but never linked (bare EXEC vs schema-qualified proc — 214).
                # Function-only: Method subjects keep the bare_name_truncated / no_matches path.
                subject_name = str(subject_nodes[0]["name"])
                unlinked_calls = store.count_unlinked_by_target_raw(
                    (lookup, subject_name), kinds=CALLER_KINDS
                )
            if (
                outcome.total_count > 0
                and indexed
                and str(subject_nodes[0]["kind"]) == "Function"
            ):
                # Hits do not close the list: a same-name call left unlinked may be another
                # caller (334). Function-only — the predicate the empty path above uses (214).
                unlinked_beside_hits = store.count_unlinked_by_target_raw(
                    (lookup, str(subject_nodes[0]["name"])), kinds=CALLER_KINDS
                )
            if depth == 1 and production_count == 0 and indexed and subject_nodes:
                subject_name = str(subject_nodes[0]["name"])
                kinds = inbound_kinds_for(str(subject_nodes[0]["kind"]))
                unlinked_same_name_sites = store.count_unlinked_by_target_raw(
                    (lookup, subject_name), kinds=kinds
                )
            if (
                (outcome.total_count == 0 or (depth == 1 and production_count == 0))
                and indexed
                and unresolved_bare == 0
                and subject_nodes
            ):
                # Shared predicate (264) while the store is open.
                shared_honesty_reason, shared_unlinked = apply_empty_inbound_honesty(
                    REASON_NO_MATCHES,
                    store,
                    subject_kind=str(subject_nodes[0]["kind"]),
                    raws=(lookup,),
                )

            if indexed and subject_file is not None:
                # Language-scope, not hit-count (221/238): an unmeasured crossing is unmeasured
                # whether this answer found in-language hits. Build-time census, never a scan.
                cross_lang_census = cross_language_relation_unmodelled(
                    store, file_path=subject_file
                )
            # Handshake stamp (231): read before the store closes. Null args is not "no capture".
            if args_at is not None and subject_file is not None:
                caps_stamp = store.stamped_capabilities_by_language()
                lang = store.language_of_file(subject_file)
                if caps_stamp is not None and lang is not None:
                    lang_caps = caps_stamp.get(lang) or {}
                    if not lang_caps.get("args", False):
                        args_capture_absent = True
        reason = relation_reason(hit_total=outcome.total_count, symbol_indexed=indexed)
        if proximity_used:
            # Candidates the resolver declined to link, ranked by proximity — never ok, the
            # 252 rule for a query-time expansion (R5.6 / 258). Each row names `candidate_of`.
            reason = REASON_PROXIMITY_CANDIDATES
        elif outcome.total_count == 0 and indexed and unresolved_bare > 0:
            # Cap dropped this subject from bare-name linking — not "no callers exist".
            reason = REASON_BARE_NAME_TRUNCATED
        elif reason == REASON_NO_MATCHES and unlinked_calls > 0:
            reason = REASON_RELATION_UNMODELLED_FOR_LANGUAGE
        elif reason == REASON_NO_MATCHES and cross_lang_census is not None:
            # No linked edge from any other language reaches this one — the zero is unmeasured,
            # not empty (221). Carries authoritative:false + the census below.
            reason = REASON_RELATION_UNMODELLED_FOR_LANGUAGE
        elif reason == REASON_NO_MATCHES and shared_unlinked:
            reason = shared_honesty_reason
            unlinked_edge_kinds = shared_unlinked
        reason = escalate_zero_production(
            reason,
            production_count=production_count,
            unlinked_same_name_sites=unlinked_same_name_sites,
            unresolved_bare=unresolved_bare,
            shared_honesty_reason=shared_honesty_reason if shared_unlinked else None,
        )
        if args_capture_absent:
            # The filter cannot judge one site in this language, so no count above is an answer
            # about it — this outranks every reason the chain can reach (231).
            reason = REASON_CAPABILITY_NOT_CONFIGURED
        result = nav_result(
            qname,
            outcome.results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            index_root=config.index_root,
            truncated=outcome.truncated,
            reason=reason,
            total_count=outcome.total_count,
            depth=depth,
            frontier_skipped_non_resolved=outcome.frontier_skipped_non_resolved,
            answered_about_ref=about_ref,
        )
        if freshness == "repaired":
            result["subject_refreshed_only"] = True
        if unresolved_bare > 0:
            result["unresolved_bare_calls"] = unresolved_bare
        if unrecorded is not None:
            result["args_unrecorded"] = unrecorded
        if tier is not None:
            result["tier_filter"] = tier
        if tier_census is not None:
            result["tier_census"] = tier_census
            if tier is not None or len(tier_census) > 1:
                # A filter ran, or the hit set spans tiers this page orders — either way the
                # page is a partition of it (251/265), even when it has no rows.
                attach_authoritative_caveats(result, [CAVEAT_TIER_PARTITION])
        if unlinked_edge_kinds:
            # Names the unmeasured relation(s) — not hits (R5.6 / 255 AC1), as find_references does.
            result["unlinked_edge_kinds"] = unlinked_edge_kinds
        if depth == 1 and (production_count or test_count):
            # A depth-1 partition of a multi-hop total would not add up, so it is omitted above 1;
            # 0 + 0 would only restate `total_count`, so it is omitted there too (262/061).
            result["production_count"] = production_count
            result["test_count"] = test_count
            if test_role_label is not None:
                result["test_role_source"] = test_role_label
        if unlinked_same_name_sites and test_count:
            result["unlinked_same_name_sites"] = unlinked_same_name_sites
        if unlinked_beside_hits:
            result.setdefault("unlinked_same_name_sites", unlinked_beside_hits)
            attach_authoritative_caveats(result, [CAVEAT_UNLINKED_SAME_NAME_SITES])
        if args_capture_absent:
            attach_authoritative_caveats(result, [CAVEAT_ARGS_NOT_CAPTURED])
        attach_result_subtrees(result, subtrees)
        attach_ambiguous_definitions(result, definition_sites(subject_nodes))
        # A partition of the callers, not the whole — mark it non-authoritative (165, R5.5), name
        # the reason (168), and rank the sites nearest-subtree-first (171).
        if attach_sibling_definitions(result, sibling_sites, subject_file=subject_file):
            attach_authoritative_caveats(result, [CAVEAT_SIBLING_DEFINITIONS])
        attach_limit_capped(result, cap=cap, clamped=limit_clamped)
        attach_resolved_qname(result, asked=asked, answered=lookup)
        if reason == REASON_RELATION_UNMODELLED_FOR_LANGUAGE:
            attach_try_instead(
                result, None, TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE
            )
            # The cross-language case (221) rides the census + authoritative:false; the 214
            # SQL-side path (unlinked_calls > 0) is left exactly as it was.
            if unlinked_calls == 0 and cross_lang_census is not None:
                attach_cross_language_census(result, cross_lang_census)
                attach_authoritative_caveats(result, [CAVEAT_CROSS_LANGUAGE_UNMODELLED])
        elif cross_lang_census is not None and cross_language_census_has_edges(
            cross_lang_census
        ):
            # Hits whose *->L crossing the index cannot measure (238), and only when the
            # census counted a cross-language edge (276) — an empty census is status, not a
            # per-answer partition.
            attach_cross_language_census(result, cross_lang_census)
            attach_authoritative_caveats(result, [CAVEAT_CROSS_LANGUAGE_UNMODELLED])
        labelled = label_serve_behind(
            result,
            serve_behind=serve_behind,
            subject_path=subject_file,
            revision=staleness or None,
            dirty_paths=behind_dirty,
            subject_unrepaired=subject_unrepaired,
        )
        attach_coverage_edge_route(
            labelled,
            stamped,
            has_coverage_gap=bool(coverage_gap(config)),
            detail_level=detail_level,
        )
        return signed(attach_coverage_note(labelled, config, covered, detail_level=detail_level))

    return find_callers


def _args_at(
    arg_position: int | None, arg_is: str | None, *, depth: int
) -> tuple[int, str] | None:
    """Validate the argument filter loud and early — a typo must not read as "no matches" (R5.3)."""
    if arg_position is None and arg_is is None:
        return None
    if arg_position is None or arg_is is None:
        raise ValueError("arg_position and arg_is are set together or not at all")
    if arg_position < 1:
        raise ValueError(f"arg_position is 1-based, got {arg_position}")
    if arg_is not in ARG_SELECTORS:
        raise ValueError(f"unknown arg_is {arg_is!r}: one of {', '.join(ARG_SELECTORS)}")
    if depth != 1:
        raise ValueError("an argument filter describes a direct call, so it needs depth=1")
    return arg_position, arg_is


def _test_census(
    store: GraphStore,
    qname: str,
    *,
    depth: int,
    args_at: tuple[int, str] | None,
    confidence_tier: str | None,
) -> tuple[int, int, str | None]:
    """``(production, test, how the test rows were decided)`` for the depth-1 inbound set (262).

    One grouped store read for both fetch paths. Above depth 1 the answer is a BFS total this
    partition could not add up to, so nothing is counted and nothing is reported.
    """
    if depth != 1:
        return 0, 0, None
    rows = store.inbound_test_rows(
        qname,
        kinds=CALLER_KINDS,
        args_at=args_at,
        confidence_tier=confidence_tier,
        distinct_sources=True,
    )
    production = sum(count for is_test, _path, count in rows if not is_test)
    test = sum(count for is_test, _path, count in rows if is_test)
    label = aggregate_test_count_source(
        stored_test_source(is_test, path) for is_test, path, _count in rows
    )
    return production, test, label


def _tier_census(
    store: GraphStore,
    qname: str,
    *,
    args_at: tuple[int, str] | None,
    depth: int,
    tier: str | None,
    indexed: bool,
    hit_total: int,
) -> dict[str, int] | None:
    """The full hit set's tier breakdown, or None when it would add nothing (061).

    A tier filter normally suppresses it (251). The exception is a filtered page with no
    rows: there the census is the only thing that says which tiers the filter removed (265).
    """
    if depth != 1 or not indexed:
        return None
    census = store.tier_census_by_target(qname, kinds=CALLER_KINDS, args_at=args_at)
    if not census:
        return None
    if tier is not None:
        return census if hit_total == 0 else None
    if len(census) > 1 or _RESOLVED not in census:
        return census
    return None


def _confidence_tier(
    confidence_tier: ConfidenceTier | None, *, depth: int
) -> ConfidenceTier | None:
    """Validate the tier filter loud and early — a typo must not read as "no matches" (R5.3)."""
    if confidence_tier is None:
        return None
    if confidence_tier not in CONFIDENCE_TIERS:
        raise ValueError(
            f"unknown confidence_tier {confidence_tier!r}: "
            f"one of {', '.join(CONFIDENCE_TIERS)}"
        )
    if depth != 1:
        raise ValueError("a tier filter describes a direct call page, so it needs depth=1")
    return confidence_tier


def _shared_subtree_depth(subject_file: str, site_file: str) -> int:
    """How many leading directory components the two files share (258 proximity)."""
    subject = PurePosixPath(subject_file).parent.parts
    site = PurePosixPath(site_file).parent.parts
    depth = 0
    for left, right in zip(subject, site, strict=False):
        if left != right:
            break
        depth += 1
    return depth


def _proximity_qualifies(subject_file: str, site_file: str) -> bool:
    """Whether an unresolved site may count as a caller of this subject (258 AC3).

    Same file or same parent directory, or a positive shared-subtree depth. A vendored
    Zend path and an application controller share none of these.
    """
    if subject_file == site_file:
        return True
    if PurePosixPath(subject_file).parent == PurePosixPath(site_file).parent:
        return True
    return _shared_subtree_depth(subject_file, site_file) >= 1


def _proximity_unresolved_callers(
    store: GraphStore,
    *,
    bare_name: str,
    language: str | None,
    subject_file: str,
    subject_qname: str,
    limit: int,
    offset: int,
    confidence_tier: str | None,
) -> _CallersOutcome | None:
    """Query-time candidates for unresolved same-named CALL sites (task 258).

    Ranked by shared-subtree depth (desc), then source_qname.
    """
    if confidence_tier is not None and confidence_tier != "HEURISTIC":
        return None
    sites = store.unresolved_caller_sites(
        bare_name, kinds=CALLER_KINDS, language=language
    )
    ranked: list[tuple[int, str, Row]] = []
    for site in sites:
        site_file = str(site["file_path"])
        if not _proximity_qualifies(subject_file, site_file):
            continue
        depth = _shared_subtree_depth(subject_file, site_file)
        ranked.append((depth, str(site["source_qname"]), site))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    total = len(ranked)
    page = ranked[offset : offset + limit]
    hits = [edge_hit(site, depth=1) for _, _, site in page]
    for hit in hits:
        hit["confidence_tier"] = "HEURISTIC"
        hit["candidate_of"] = subject_qname
    return _CallersOutcome(
        results=hits,
        truncated=offset + len(hits) < total,
        total_count=total,
        frontier_skipped_non_resolved=0,
    )


def _attach_call_lines(
    store: GraphStore,
    qname: str,
    hits: list[dict[str, object]],
    *,
    args_at: tuple[int, str] | None,
    confidence_tier: str | None,
    exclude_test_sources: bool,
) -> None:
    """A row whose caller calls ``qname`` from two or more lines names them all (338).

    One read for the page; one line keeps the row byte-identical (061).
    """
    lines = store.call_lines_by_source(
        qname,
        sorted({str(hit["qname"]) for hit in hits if isinstance(hit.get("file"), str)}),
        kinds=CALLER_KINDS,
        args_at=args_at,
        confidence_tier=confidence_tier,
        exclude_test_sources=exclude_test_sources,
    )
    for hit in hits:
        found = lines.get((str(hit["qname"]), str(hit.get("file"))), [])
        if len(found) > 1:
            hit["call_lines"] = found


def _callers(
    store: GraphStore,
    qname: str,
    *,
    hops: int,
    limit: int,
    offset: int = 0,
    args_at: tuple[int, str] | None = None,
    confidence_tier: str | None = None,
    exclude_test_sources: bool = False,
) -> _CallersOutcome:
    """BFS over CALLS/NEW into ``qname``; only RESOLVED edges expand the frontier (A3 / HOW-5)."""
    if hops == 1:
        total = store.count_edges_by_target(
            qname,
            kinds=CALLER_KINDS,
            args_at=args_at,
            confidence_tier=confidence_tier,
            exclude_test_sources=exclude_test_sources,
            distinct_sources=True,
        )
        edges = store.edges_by_target(
            qname,
            kinds=CALLER_KINDS,
            limit=limit,
            offset=offset,
            args_at=args_at,
            confidence_tier=confidence_tier,
            exclude_test_sources=exclude_test_sources,
            distinct_sources=True,
        )
        hits = [edge_hit(edge, depth=1) for edge in edges]
        _attach_call_lines(
            store,
            qname,
            hits,
            args_at=args_at,
            confidence_tier=confidence_tier,
            exclude_test_sources=exclude_test_sources,
        )
        return _CallersOutcome(
            results=hits,
            truncated=offset + len(hits) < total,
            total_count=total,
            frontier_skipped_non_resolved=0,
        )

    results: list[dict[str, object]] = []
    seen_edge_ids: set[int] = set()
    visited_targets: set[str] = {qname}
    queue: deque[tuple[str, int]] = deque([(qname, 0)])
    skipped_non_resolved = 0
    total_count = 0
    skipped = 0
    count_budget = max(limit * _COUNT_BUDGET_FACTOR, limit + 1) + offset
    hit_budget = False

    while queue and total_count < count_budget:
        target, hop = queue.popleft()
        if hop >= hops:
            continue
        remaining = count_budget - total_count
        for edge in store.edges_by_target(
            target,
            kinds=CALLER_KINDS,
            limit=remaining,
            exclude_test_sources=exclude_test_sources,
        ):
            eid = edge_id(edge)
            if eid in seen_edge_ids:
                continue
            seen_edge_ids.add(eid)
            total_count += 1
            if skipped < offset:
                skipped += 1
            elif len(results) < limit:
                results.append(edge_hit(edge, depth=hop + 1))
            tier = str(edge.get("confidence_tier") or _RESOLVED)
            source = str(edge["source_qname"])
            if hop + 1 >= hops or source in visited_targets:
                if total_count >= count_budget:
                    hit_budget = True
                    break
                continue
            if tier == _RESOLVED:
                visited_targets.add(source)
                queue.append((source, hop + 1))
            else:
                skipped_non_resolved += 1
            if total_count >= count_budget:
                hit_budget = True
                break
    truncated = offset + len(results) < total_count or hit_budget or bool(queue)
    return _CallersOutcome(
        results=results,
        truncated=truncated,
        total_count=total_count,
        frontier_skipped_non_resolved=skipped_non_resolved,
    )
