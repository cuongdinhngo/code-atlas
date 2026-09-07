"""``find_callers`` — who CALLS/NEW a qname, with optional depth (§12)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Literal, NamedTuple

from code_atlas.config import Config, clamp_limit
from code_atlas.contract import ARG_SELECTORS, CALLER_KINDS, CONFIDENCE_TIERS, split_qname
from code_atlas.store import GraphStore
from code_atlas.tools import call_site, claim
from code_atlas.tools.coverage import (
    attach_coverage_note,
    covered_languages,
    cross_language_relation_unmodelled,
)
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import (
    CAVEAT_CROSS_LANGUAGE_UNMODELLED,
    CAVEAT_SIBLING_DEFINITIONS,
    REASON_BARE_NAME_TRUNCATED,
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE,
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
    edge_id,
    empty_nav,
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
        limit: int | None = None,
        offset: int = 0,
        sign: bool = False,
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
        ``source_stale`` instead.

        ``arg_position`` (1-based) with ``arg_is`` keeps only call sites whose argument there has
        that shape: a literal category (``null``, ``true``, ``false``, ``number``, ``string``,
        ``array``), ``absent`` (the call passes fewer arguments), or ``dynamic`` (present, but not
        a literal). ``total_count`` then counts matches, and ``args_unrecorded`` says how many
        call sites the filter could not judge — sites whose arguments were never recorded, which
        are never counted as matches. Depth 1 only.

        ``limit`` / ``offset`` page results (057). At depth 1 the store owns OFFSET; deeper walks
        apply offset to the BFS hit stream. Complete enumeration is guaranteed at depth 1.

        When bare-name resolution capped Method candidates alphabetically (task 054), a subject
        outside that cap can have zero inbound edges while CALLS sites named its bare method still
        exist. Those sites are counted in ``unresolved_bare_calls``, and an empty answer then uses
        ``reason=bare_name_truncated`` instead of ``no_matches``.

        When a Function subject still has unlinked CALLS targeting its short name
        (schema-unqualified ``EXEC`` that could not resolve uniquely — task 214), an empty
        answer uses ``reason=relation_unmodelled_for_language`` instead of ``no_matches``.

        ``subject_refreshed_only`` is present (and ``true``) only when read-through freshness
        reparsed the subject's file this call — neighbors were not re-verified (035 / 061).
        An untracked indexable file matching the subject is ``reason=not_indexed`` plus
        ``try_instead=build_or_update_index`` — never ``no_such_symbol`` (092).

        ``sign`` (default off, so the default payload is unchanged) adds ``claim``: one quotable
        ``key=value`` line naming subject, question, answer and the revision the index describes.
        The weakest tier present is named, so the line can never claim ``RESOLVED`` over a
        ``HEURISTIC`` hit. An answer with no index carries no line (task 100).

        A leading-anchor difference from the stored qname is re-pointed and answered;
        ``resolved_qname`` names the stored form (075/122). An exact stored qname is unchanged.
        """
        if depth < 1:
            raise ValueError(f"depth must be >= 1, got {depth}")
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap, limit_clamped = clamp_limit(limit, config.max_results)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        args_at = _args_at(arg_position, arg_is, depth=depth)
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
        unlinked_calls = 0
        cross_lang_census: dict[str, object] | None = None
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
                        depth=depth,
                        frontier_skipped_non_resolved=0,
                    ),
                    TRY_INSTEAD_FILE_OUTLINE,
                ))
            asked = qname
            lookup = qname
            outcome = _callers(
                store, lookup, hops=depth, limit=cap, offset=offset, args_at=args_at
            )
            # Widen the existing indexed-check fetch to surface every definition site (task 070).
            subject_nodes = store.nodes_by_qualified_name(lookup, limit=config.max_results)
            indexed = bool(subject_nodes)
            unrecorded = (
                store.count_edges_without_args(lookup, kinds=CALLER_KINDS)
                if args_at is not None
                else None
            )
            if outcome.total_count == 0 and not indexed:
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
                        depth=depth,
                        frontier_skipped_non_resolved=0,
                    )
                    # A miss still names what the guard repaired (073) and what it could not judge
                    # (049) — the 092 shortcut must not drop signals the fall-through carried.
                    if freshness == "repaired":
                        miss["subject_refreshed_only"] = True
                    if unrecorded is not None:
                        miss["args_unrecorded"] = unrecorded
                    attach_limit_capped(miss, cap=cap, clamped=limit_clamped)
                    return signed(
                        attach_coverage_note(
                            shape_exact_miss(miss, resolution), config, covered
                        )
                    )
                lookup = repointed
                outcome = _callers(
                    store, lookup, hops=depth, limit=cap, offset=offset, args_at=args_at
                )
                subject_nodes = store.nodes_by_qualified_name(
                    lookup, limit=config.max_results
                )
                indexed = bool(subject_nodes)
                unrecorded = (
                    store.count_edges_without_args(lookup, kinds=CALLER_KINDS)
                    if args_at is not None
                    else None
                )
            container, bare_name = split_qname(lookup)
            unresolved_bare = 0
            if indexed and container is not None and outcome.total_count == 0:
                # Method-shaped only — Function ``\App\put`` ≠ bare Method ``put``.
                # Cap uses query-time max_results (index-time may differ — Part A).
                if store.count_nodes_by_name(bare_name, kind="Method") > config.max_results:
                    unresolved_bare = store.count_bare_calls_not_targeting(
                        lookup, bare_name=bare_name
                    )
            sibling_sites: list[dict[str, object]] = []
            # The subject's own file is what "near" is measured against (171).
            subject_file = str(subject_nodes[0]["file_path"]) if subject_nodes else None
            if indexed and str(subject_nodes[0]["kind"]) == "Function":
                # Same bare name, other schema/qname — the AC2 visibility surface for SQL (214).
                # Uses the node's `name` because dotted Function qnames are not `::`-split.
                siblings = sibling_definition_rows(
                    store,
                    bare_name=str(subject_nodes[0]["name"]),
                    kind="Function",
                    lookup=lookup,
                    limit=config.max_results,
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
                    limit=config.max_results,
                )
                sibling_sites = definition_sites(siblings)
            if include_source:
                call_site.annotate(config.root, store, outcome.results)
            # Skewed page 1 hides other subtrees — advertise the full spread (task 067).
            # Depth 1 only: the store spread is exact there; deeper total_count is a floor.
            subtrees = (
                store.edge_subtrees_by_target(lookup, kinds=CALLER_KINDS, args_at=args_at)
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
            if outcome.total_count == 0 and indexed and subject_file is not None:
                # The caller may be in another language whose crossing the index never modelled
                # (221) — read the build-time census, never a per-answer scan.
                cross_lang_census = cross_language_relation_unmodelled(
                    store, file_path=subject_file
                )
        reason = relation_reason(hit_total=outcome.total_count, symbol_indexed=indexed)
        if outcome.total_count == 0 and indexed and unresolved_bare > 0:
            # Cap dropped this subject from bare-name linking — not "no callers exist".
            reason = REASON_BARE_NAME_TRUNCATED
        elif reason == REASON_NO_MATCHES and unlinked_calls > 0:
            reason = REASON_RELATION_UNMODELLED_FOR_LANGUAGE
        elif reason == REASON_NO_MATCHES and cross_lang_census is not None:
            # No linked edge from any other language reaches this one — the zero is unmeasured,
            # not empty (221). Carries authoritative:false + the census below.
            reason = REASON_RELATION_UNMODELLED_FOR_LANGUAGE
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
        )
        if freshness == "repaired":
            result["subject_refreshed_only"] = True
        if unresolved_bare > 0:
            result["unresolved_bare_calls"] = unresolved_bare
        if unrecorded is not None:
            result["args_unrecorded"] = unrecorded
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
        return signed(attach_coverage_note(result, config, covered))

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


def _callers(
    store: GraphStore,
    qname: str,
    *,
    hops: int,
    limit: int,
    offset: int = 0,
    args_at: tuple[int, str] | None = None,
) -> _CallersOutcome:
    """BFS over CALLS/NEW into ``qname``; only RESOLVED edges expand the frontier (A3 / HOW-5)."""
    if hops == 1:
        total = store.count_edges_by_target(qname, kinds=CALLER_KINDS, args_at=args_at)
        edges = store.edges_by_target(
            qname, kinds=CALLER_KINDS, limit=limit, offset=offset, args_at=args_at
        )
        hits = [edge_hit(edge, depth=1) for edge in edges]
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
        for edge in store.edges_by_target(target, kinds=CALLER_KINDS, limit=remaining):
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
