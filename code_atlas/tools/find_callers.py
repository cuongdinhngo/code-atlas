"""``find_callers`` — who CALLS/NEW a qname, with optional depth (§12)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Literal, NamedTuple

from code_atlas.config import Config, clamp_limit
from code_atlas.contract import ARG_SELECTORS, CALLER_KINDS, CONFIDENCE_TIERS, split_qname
from code_atlas.store import GraphStore
from code_atlas.tools import call_site
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import (
    REASON_BARE_NAME_TRUNCATED,
    REASON_INDEX_STALE,
    REASON_NAME_NOT_QUALIFIED,
    TRY_INSTEAD_FILE_OUTLINE,
    attach_ambiguous_definitions,
    attach_limit_capped,
    attach_name_not_qualified,
    attach_result_subtrees,
    attach_try_instead,
    classify_missing_subject,
    definition_sites,
    edge_hit,
    edge_id,
    empty_nav,
    nav_result,
    relation_reason,
)

NAME = "find_callers"

DetailLevel = Literal["minimal", "standard"]

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

        ``subject_refreshed_only`` is present (and ``true``) only when read-through freshness
        reparsed the subject's file this call — neighbors were not re-verified (035 / 061).
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
                        depth=depth,
                        frontier_skipped_non_resolved=0,
                    ),
                    TRY_INSTEAD_FILE_OUTLINE,
                )
            outcome = _callers(
                store, qname, hops=depth, limit=cap, offset=offset, args_at=args_at
            )
            # Widen the existing indexed-check fetch to surface every definition site (task 070).
            subject_nodes = store.nodes_by_qualified_name(qname, limit=config.max_results)
            indexed = bool(subject_nodes)
            # A subject with no node and no inbound edges: is it truly absent, or under-qualified?
            # N indexed qnames end with it → name_not_qualified, not no_such_symbol (075/076).
            name_not_qualified = (
                classify_missing_subject(store, qname, limit=config.max_results).candidate_count
                if outcome.total_count == 0 and not indexed
                else 0
            )
            container, bare_name = split_qname(qname)
            unresolved_bare = 0
            if indexed and container is not None and outcome.total_count == 0:
                # Method-shaped only — Function ``\App\put`` ≠ bare Method ``put``.
                # Cap uses query-time max_results (index-time may differ — Part A).
                if store.count_nodes_by_name(bare_name, kind="Method") > config.max_results:
                    unresolved_bare = store.count_bare_calls_not_targeting(
                        qname, bare_name=bare_name
                    )
            unrecorded = (
                store.count_edges_without_args(qname, kinds=CALLER_KINDS)
                if args_at is not None
                else None
            )
            if include_source:
                call_site.annotate(config.root, store, outcome.results)
            # Skewed page 1 hides other subtrees — advertise the full spread (task 067).
            # Depth 1 only: the store spread is exact there; deeper total_count is a floor.
            subtrees = (
                store.edge_subtrees_by_target(qname, kinds=CALLER_KINDS, args_at=args_at)
                if depth == 1 and outcome.truncated
                else {}
            )
        reason = relation_reason(hit_total=outcome.total_count, symbol_indexed=indexed)
        if outcome.total_count == 0 and indexed and unresolved_bare > 0:
            # Cap dropped this subject from bare-name linking — not "no callers exist".
            reason = REASON_BARE_NAME_TRUNCATED
        elif name_not_qualified > 0:
            reason = REASON_NAME_NOT_QUALIFIED
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
        if name_not_qualified > 0:
            attach_name_not_qualified(result, name_not_qualified)
        if unrecorded is not None:
            result["args_unrecorded"] = unrecorded
        attach_result_subtrees(result, subtrees)
        attach_ambiguous_definitions(result, definition_sites(subject_nodes))
        attach_limit_capped(result, cap=cap, clamped=limit_clamped)
        return result

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
