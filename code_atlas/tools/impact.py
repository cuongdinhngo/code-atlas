"""``impact`` — bounded best-score blast radius (§12 / M6)."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Literal, NamedTuple

from code_atlas import records as record_table
from code_atlas import routes as route_table
from code_atlas.config import Config, clamp_limit
from code_atlas.contract import BARE_SUBJECT_KINDS, CALLER_KINDS
from code_atlas.mirror_search import label_mirror_rows, load_mirror_search_stamp
from code_atlas.store import GraphStore
from code_atlas.symbol_role import stored_test_source
from code_atlas.tools import claim
from code_atlas.tools.nav_result import (
    CAVEAT_SIBLING_DEFINITIONS,
    CAVEAT_UNLINKED_SAME_NAME_SITES,
    REASON_NO_SUCH_SYMBOL,
    REASON_SUBJECT_AMBIGUOUS,
    RESOLVED_FROM,
    RESOLVED_FROM_BARE,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_FIND_CALLERS,
    TRY_INSTEAD_HINT_IMPACT_BY_QNAME,
    TRY_INSTEAD_HINT_UNLINKED_CALLS,
    SubjectResolution,
    answered_about_ref_for,
    attach_ambiguous_definitions,
    attach_authoritative_caveats,
    attach_limit_capped,
    attach_rules_stale,
    attach_sibling_definitions,
    attach_try_instead,
    bare_subject,
    classify_missing_subject,
    definition_sites,
    empty_nav,
    nav_result,
    require_records_filter,
    shape_exact_miss,
    sibling_definition_rows,
)
from code_atlas.tools.staleness import compute_staleness
from code_atlas.tools.symbol_pointers import declared_precedence, precedence_first

NAME = "impact"

# ``subject_parts`` / ``resolve_seeds`` / ``explain_lost_subject`` / ``SeedSet`` are public so the
# module rollup (140) answers about the same seeds this tool does. One definition, two answers.

DetailLevel = Literal["minimal", "standard"]
RecordScope = Literal["direct", "radius"]

QUESTION = "blast-radius"
# Empty modelled zero vs failed query (065); unlinked same-name sites spoil a closed zero (330).
CLAIM_CARRY = ("seeds_dropped", "frontier_skipped_non_resolved", "unlinked_same_name_sites")


class SeedSet(NamedTuple):
    """Resolved seeds, plus one resolution per requested subject that produced none (task 102).

    ``from_paths`` names the seeds a path expanded into, so the payload can state the expansion and
    the twin check can be applied to exactly the seeds nobody asked for by name (task 169).
    """

    seeds: list[str]
    dropped: tuple[SubjectResolution, ...]
    from_paths: tuple[str, ...] = ()
    # A bare name re-pointed onto its one Table or Function, or refused with each (392).
    from_bare: tuple[tuple[str, str], ...] = ()  # (asked, qname)
    bare_refused: tuple[tuple[str, list[dict[str, object]]], ...] = ()


class SeedPlan(NamedTuple):
    """The whole seed decision, made once for every tool that walks a blast radius (task 179).

    `impact` had the two splits inline, so `impact_modules` inherited the classification and neither
    refusal — and rolled a twin's modules into the answer, where it is harder to notice than 169's
    symbol list. One decision, one implementation (R1.8/R6.7); the tools differ in their rows, never
    in which seeds may be walked.
    """

    walk_seeds: list[str]
    from_paths: tuple[str, ...]
    ambiguous_sites: list[tuple[str, list[dict[str, object]]]]
    twinned_sites: list[tuple[str, list[dict[str, object]]]]
    dropped: tuple[SubjectResolution, ...]
    from_bare: tuple[tuple[str, str], ...] = ()
    # Seeds walked through the declared precedence: the answering site, then the others (414).
    preferred: tuple[tuple[str, list[dict[str, object]]], ...] = ()

    @property
    def refused(self) -> int:
        """Seeds this plan removed — every one accounted for in ``seeds_dropped`` (102)."""
        return len(self.dropped) + len(self.ambiguous_sites) + len(self.twinned_sites)


def plan_seeds(
    store: GraphStore, *, paths: Sequence[str], qnames: Sequence[str], max_results: int
) -> SeedPlan:
    """Resolve the subjects, then remove the seeds that cannot honestly be walked (161 + 169)."""
    seed_set = resolve_seeds(store, paths=paths, qnames=qnames, max_results=max_results)
    walk_seeds, ambiguous_sites, preferred = _split_ambiguous(
        store, seed_set.seeds, max_results, from_paths=frozenset(seed_set.from_paths)
    )
    ambiguous_sites = [*ambiguous_sites, *seed_set.bare_refused]
    # Only the seeds a PATH expanded into: 161 closed the qname half, and a caller who named a
    # qname asked for that qname (169).
    from_paths = set(seed_set.from_paths)
    twinned_sites: list[tuple[str, list[dict[str, object]]]] = []
    if from_paths:
        walkable, twinned_sites = _split_twinned(
            store, [seed for seed in walk_seeds if seed in from_paths], max_results
        )
        keep = set(walkable)
        walk_seeds = [seed for seed in walk_seeds if seed not in from_paths or seed in keep]
    return SeedPlan(
        walk_seeds=walk_seeds,
        from_paths=seed_set.from_paths,
        ambiguous_sites=ambiguous_sites,
        twinned_sites=twinned_sites,
        dropped=seed_set.dropped,
        from_bare=seed_set.from_bare,
        preferred=tuple(preferred),
    )


def attach_seed_refusals(payload: dict[str, object], plan: SeedPlan) -> None:
    """Name every refused seed on the payload — the same disclosure, whatever the rows look like.

    A module list that silently lost a seed is worse than one that names the loss, and a rollup is
    acted on destructively exactly as `impact` is. Copied nowhere: both tools call this (R6.7).
    """
    if plan.from_bare:
        payload[RESOLVED_FROM] = RESOLVED_FROM_BARE
        payload["resolved_qnames"] = dict(plan.from_bare)
    if plan.twinned_sites:
        # The bare-name links would pull in the twin's callers and callees, at RESOLVED-looking
        # confidence, on a tool whose answer is acted on destructively (169).
        attach_sibling_definitions(
            payload,
            [site for _, sites in plan.twinned_sites for site in sites],
            subject_file=None,
        )
        attach_authoritative_caveats(payload, [CAVEAT_SIBLING_DEFINITIONS])
    if plan.ambiguous_sites:
        # A seed qname with >1 definitions cannot be attributed to one twin — the edge model is
        # qname-keyed — so disclose the sites instead of walking one silently at RESOLVED (9-A).
        attach_ambiguous_definitions(
            payload, [site for _, sites in plan.ambiguous_sites for site in sites]
        )
        if not plan.walk_seeds:
            payload["reason"] = REASON_SUBJECT_AMBIGUOUS
    if plan.twinned_sites and not plan.walk_seeds:
        payload["reason"] = REASON_SUBJECT_AMBIGUOUS
        attach_try_instead(payload, TRY_INSTEAD_FILE_OUTLINE, TRY_INSTEAD_HINT_IMPACT_BY_QNAME)
    if (
        plan.dropped
        and not plan.walk_seeds
        and not plan.ambiguous_sites
        and not plan.twinned_sites
    ):
        explain_lost_subject(payload, plan.dropped)


def attach_other_definitions(payload: dict[str, object], plan: SeedPlan) -> None:
    """The definitions a declared precedence did not choose, per walked seed (414)."""
    if plan.preferred:
        payload["other_definitions"] = [site for _, sites in plan.preferred for site in sites[1:]]


def attach_seed_expansion(
    payload: dict[str, object], plan: SeedPlan, paths: Sequence[str] | None
) -> None:
    """One file became N seeds: say so, on every tool that accepts a path (169)."""
    if not paths:
        return
    payload["seed_expansion"] = {
        "paths": len([path for path in paths if path]),
        "seeds": len(plan.from_paths),
    }


def _depth(value: object) -> int:
    """A radius row's depth, which the walk always stores as an int."""
    if not isinstance(value, int):
        raise TypeError(f"depth must be int, got {type(value).__name__}")
    return value


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def impact(
        paths: list[str] | None = None,
        qnames: list[str] | None = None,
        depth: int | None = None,
        detail_level: DetailLevel = "standard",
        sign: bool = False,
        exclude_tests: bool = False,
        routes: list[str] | None = None,
        records: RecordScope = "radius",
        records_limit: int | None = None,
        records_filter: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """What could break if I change this file or symbol — the blast radius?

        Bounded best-score over changed paths and/or qnames. Seeds are the union of every indexed
        node on ``paths`` and the explicit ``qnames``.
        ``depth`` defaults to ``CA_IMPACT_DEPTH``; the node budget is ``CA_IMPACT_MAX_NODES``.
        HEURISTIC/DYNAMIC neighbors are returned with their tier but do not expand the
        frontier. Missing seeds and a missing database yield an empty successful result.

        Walks resolver-linked IMPACT kinds only — an empty answer is a modelled zero for those
        kinds, not ``relationship_not_modelled`` (task 065; see ``find_references``). When a
        Method seed still has unlinked same-name CALLS, ``unlinked_same_name_sites`` names them
        and the answer is not authoritative (330).

        ``seeds_dropped`` counts every requested subject that produced no seed — a qname that is
        absent or resolves to many, a path with no indexed node — plus any seed the node budget
        pruned. ``results: []`` with ``seeds_dropped: 0`` therefore means a modelled zero and
        nothing else (task 102). When every named subject was lost the answer also carries
        ``reason`` (``no_such_symbol`` / ``name_not_qualified`` / ``not_indexed``, with
        ``candidate_count`` / ``try_instead`` where the classifier has them).

        A seed whose qname has more than one definition is **not** walked (the graph links callers
        by qname, so it cannot be attributed to one twin): its sites are listed under
        ``ambiguous_definitions``; when no seed was walkable, ``reason=subject_ambiguous`` (161).
        A rules file's ``definitions.precedence`` naming one definition walks it instead, the rest
        under ``other_definitions`` (414).
        The default payload names the revision it describes — ``staleness`` plus ``last_commit`` —
        so a blast radius acted on destructively is never silently undated (8-E).

        At ``standard`` a row whose symbol is stored as test carries ``test_role_source``
        (``adapter`` / ``path_convention``, how it was decided); a row without it is production.
        A row on a stamped mirror pair carries ``mirror_counterpart`` (its indexed twin) or
        ``mirror_no_counterpart: true``. These are row properties — no count splits the radius.
        ``exclude_tests`` drops test sources inside the walk, before the node budget and the page,
        so page one holds production rows rather than those a page of tests left over.

        ``routes`` names URLs a declared ``routes`` table maps to a handler (385): each seeds its
        target, and one that matches no route counts in ``seeds_dropped``; one whose key several
        declared rows give different targets seeds them all and, unless each row carries its own
        ``when`` (a conditional route, 415), the answer carries ``ambiguity: "route_collision"``
        with ``route_candidates`` (411). Whenever a table is
        declared, ``routes`` in the answer lists each route whose target is a seed or in the radius
        (``HEURISTIC``, ``rule: true``) — omitted when none reaches it.

        With a ``records`` rule, ``records`` lists the declared records on the subject and its
        radius, each with ``via`` (its carrier), ``distance`` and ``direct`` (on a seed, a member a
        seed contains, or a seed's file): direct rows first, then by distance, at most
        ``records_limit`` (at most the page, ``limit_capped_to`` when reduced); ``records_total``
        counts them all.
        ``records="direct"`` keeps the direct rows alone; a ``stop_at`` hub file carries none into
        the radius and ``records_stopped`` counts what it kept out (407, 412). ``records_filter``
        (``{"tier": ["A", "B"]}``) keeps records whose declared attribute equals a value; a name
        no block declares raises ``ValueError`` (413).

        ``sign`` (default off, so the default payload is unchanged) adds ``claim``: one quotable
        ``key=value`` line naming subject, question, answer and the revision the index describes,
        with ``seeds`` beside ``answer`` (``answer == seeds`` is the modelled zero: nothing beyond
        the seeds depends on them) and ``seeds_dropped`` / ``frontier_skipped_non_resolved``.
        No line is emitted when there is no index, or when no seed resolved — a question nothing
        answered would be signed ``answer=0``, and a claim that cannot be re-run is decoration.
        """
        call = claim.call_args(impact, locals())
        hops = config.impact_depth if depth is None else depth
        if hops < 0:
            raise ValueError(f"depth must be >= 0, got {hops}")
        if records not in ("direct", "radius"):
            raise ValueError(f"records must be 'direct' or 'radius', got {records!r}")
        if records_limit is not None and records_limit < 1:
            raise ValueError(f"records_limit must be >= 1, got {records_limit}")
        limit, clamped = clamp_limit(records_limit, config.page_limit)
        require_records_filter(config, records_filter)
        parts = [*subject_parts(paths, qnames), *(routes or [])]
        subject = ",".join(parts)
        if not config.db_path.is_file():
            return empty_nav(subject, detail_level=detail_level, db_path=str(config.db_path),
            index_root=config.index_root,
            answered_about_ref=None)
        with GraphStore(config.db_path) as store:
            about_ref = answered_about_ref_for(store)
            table = route_table.load(store.get_meta(route_table.ROUTES_META_KEY))
            stored_records = record_table.load_selected(
                store.get_meta(record_table.RECORDS_META_KEY),
                store.get_meta(record_table.RECORDS_ATTRIBUTES_META_KEY),
                records_filter,
            )
            stop_at = json.loads(store.get_meta(record_table.RECORDS_STOP_AT_META_KEY) or "[]")
            matched = [route_table.matches(table or [], url) for url in routes or []]
            routed = [route for found in matched for route in found]
            plan = plan_seeds(
                store,
                paths=[*(paths or []), *(r.target for r in routed if r.target == r.file)],
                qnames=[*(qnames or []), *(r.target for r in routed if r.target != r.file)],
                max_results=config.page_limit,
            )
            seed_qnames = [
                *plan.walk_seeds,
                *(qname for qname, _ in plan.ambiguous_sites),
                *(qname for qname, _ in plan.twinned_sites),
            ]
            seed_files = sorted(
                {
                    str(row["file_path"])
                    for found in store.nodes_by_qualified_names(
                        seed_qnames, limit=config.page_limit
                    ).values()
                    for row in found
                }
            ) if stored_records else []
            outcome = store.impact_radius(
                plan.walk_seeds,
                depth=hops,
                max_nodes=config.impact_max_nodes + 1,
                exclude_test_sources=exclude_tests,
            )
            results = outcome.rows[: config.impact_max_nodes]
            place_preferred_seeds(results, plan)
            if detail_level != "minimal":
                _label_rows(store, results)
            # A blast radius is acted on destructively, so it names the revision in-band, not only
            # behind sign (8-E). One git HEAD read on this low-frequency, high-stakes tool.
            staleness = compute_staleness(store, config, include_dirty_count=True)
            unlinked_same_name_sites = _method_seed_unlinked_sites(store, plan.walk_seeds)
        truncated = len(outcome.rows) > config.impact_max_nodes
        result = nav_result(
            subject,
            results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            index_root=config.index_root,
            truncated=truncated,
            depth=hops,
            frontier_skipped_non_resolved=outcome.frontier_skipped_non_resolved,
            seeds_dropped=outcome.seeds_dropped + plan.refused + matched.count([]),
            answered_about_ref=about_ref)
        if table:
            reached = route_table.reaching(
                table,
                [*plan.walk_seeds, *(str(row["qname"]) for row in results)],
                paths or [],
                [str(row["file"]) for row in results],
            )
            if reached:
                result["routes"] = [route.as_row() for route in reached]
            # A URL several declared rows give different targets seeds them all, flagged (411).
            result.update(route_table.collision_fields(
                [route for found in matched if len(found) > 1 for route in found]
            ))
        if stored_records:
            # The subject's own records first — a seed, a member, a seed's file — then the radius
            # by distance, symbols before files at one depth (407, 412).
            hops_of = [(row, _depth(row["depth"])) for row in results]
            radius = [
                *((str(row["qname"]), hop, str(row["file"])) for row, hop in hops_of),
                *((str(row["file"]), hop, str(row["file"])) for row, hop in hops_of),
            ]
            record_rows, stopped = record_table.ranked(
                stored_records,
                [*seed_qnames, *(paths or []), *seed_files],
                radius,
                stop_at=stop_at,
                direct_only=records == "direct",
            )
            if record_rows:
                result["records"] = record_rows[:limit]
                result["records_total"] = len(record_rows)
                attach_limit_capped(result, cap=limit, clamped=clamped)
            if stopped:
                result["records_stopped"] = stopped
        _attach_freshness(result, staleness)
        if routes or "routes" in result or "records" in result:
            # A route subject feeds the rows, matched or not; a reached route is a side-field (396).
            attach_rules_stale(result, config, relabel=bool(routes))
        attach_other_definitions(result, plan)
        attach_seed_expansion(result, plan, paths)
        attach_seed_refusals(result, plan)
        if unlinked_same_name_sites:
            result["unlinked_same_name_sites"] = unlinked_same_name_sites
            attach_authoritative_caveats(result, [CAVEAT_UNLINKED_SAME_NAME_SITES])
            attach_try_instead(
                result, TRY_INSTEAD_FIND_CALLERS, TRY_INSTEAD_HINT_UNLINKED_CALLS
            )
        # A question no seed answered gets no line: it would be signed ``answer=0`` for a subject
        # the index never held. The payload names the loss in ``seeds_dropped`` (tasks 100, 102).
        # An all-ambiguous call walked nothing, so it is not signed either.
        if not sign or not plan.walk_seeds:
            return result
        return claim.sign(
            result,
            tool=NAME,
            question=QUESTION,
            subject_parts=parts,
            staleness=staleness,
            call=call,
            carry=CLAIM_CARRY,
            extra=(("seeds", len(plan.walk_seeds)),),
        )

    return impact


def _method_seed_unlinked_sites(store: GraphStore, seeds: Sequence[str]) -> int:
    """Sum unlinked same-name CALLS/NEW for Method seeds (272's query; 330)."""
    total = 0
    for qname in seeds:
        rows = list(store.nodes_by_qualified_name(qname, limit=1))
        if not rows or str(rows[0]["kind"]) != "Method":
            continue
        name = str(rows[0]["name"])
        total += store.count_unlinked_by_target_raw(
            (qname, name), kinds=CALLER_KINDS
        )
    return total


def _split_ambiguous(
    store: GraphStore,
    seeds: Sequence[str],
    max_results: int,
    *,
    from_paths: frozenset[str] = frozenset(),
) -> tuple[
    list[str],
    list[tuple[str, list[dict[str, object]]]],
    list[tuple[str, list[dict[str, object]]]],
]:
    """Partition seeds into walkable (one definition) and ambiguous (a shared qname, 9-A).

    The graph links callers by qname, not node identity, so a qname with >1 definitions cannot be
    attributed to one twin; such a seed is disclosed, never walked as an arbitrary one — unless
    the project's declared precedence names the one that answers (414): it is walked, its other
    definitions listed. A seed a path expanded into is that file's, so the precedence never moves
    it. Order-stable (R4.2); the site list is ``definition_sites`` order.
    """
    walk: list[str] = []
    ambiguous: list[tuple[str, list[dict[str, object]]]] = []
    preferred: list[tuple[str, list[dict[str, object]]]] = []
    precedence = declared_precedence(store)
    for qname in seeds:
        rows = store.nodes_by_qualified_name(qname, limit=max_results)
        ordered, held = precedence_first(rows, precedence, complete=len(rows) < max_results)
        if len(rows) > 1 and held and qname not in from_paths:
            walk.append(qname)
            sites = [{**site, "qname": qname} for site in definition_sites(ordered)]
            preferred.append((qname, sites))
        elif len(rows) > 1:
            sites = definition_sites(rows)
            for site in sites:  # one site shape with the bare refusal's (392)
                site["qname"] = qname
            ambiguous.append((qname, sites))
        else:
            walk.append(qname)
    return walk, ambiguous, preferred


def place_preferred_seeds(rows: Sequence[dict[str, object]], plan: SeedPlan) -> None:
    """A seed walked through the declared precedence sits at its answering definition (414)."""
    sites = {qname: listed[0] for qname, listed in plan.preferred}
    for row in rows:
        site = sites.get(str(row["qname"]))
        if site is not None and row.get("depth") == 0:
            row["file"], row["line"] = site["file"], site["line"]


def _split_twinned(
    store: GraphStore, seeds: Sequence[str], max_results: int
) -> tuple[list[str], list[tuple[str, list[dict[str, object]]]]]:
    """Split path-derived seeds into walkable and twinned (a shared *trailing name*, 165's shape).

    161 closed the shared-*qname* case; the consuming repo's actual shape is a shared trailing name
    under different qnames, and the walk's bare-name HEURISTIC links then pull in the twin's callers
    and callees. `impact` is acted on destructively, so a twinned seed is disclosed rather than
    walked — the same answer `_split_ambiguous` already gives one qname over (R1.8).
    """
    walk: list[str] = []
    twinned: list[tuple[str, list[dict[str, object]]]] = []
    for qname in seeds:
        rows = store.nodes_by_qualified_name(qname, limit=1)
        if not rows:
            walk.append(qname)
            continue
        siblings = sibling_definition_rows(
            store,
            bare_name=str(rows[0]["name"]),
            kind=str(rows[0]["kind"]),
            lookup=qname,
            limit=max_results,
        )
        if siblings:
            twinned.append((qname, definition_sites(siblings)))
        else:
            walk.append(qname)
    return walk, twinned


def _label_rows(store: GraphStore, rows: list[dict[str, object]]) -> None:
    """Test role and mirror twin per row — stored facts, read once per call (262/277/313)."""
    qnames = [str(row["qname"]) for row in rows]
    # limit=1 in ``_NODE_ORDER`` is the node the walk took the row's file and line from.
    nodes = store.nodes_by_qualified_names(qnames, limit=1)
    for row in rows:
        found = nodes.get(str(row["qname"]))
        if found:
            source = stored_test_source(1 if found[0].get("is_test") else 0, str(row["file"]))
            if source is not None:
                row["test_role_source"] = source
    stamp = load_mirror_search_stamp(store)
    if stamp and stamp.get("pairs"):
        label_mirror_rows(rows, stamp, frozenset(store.file_paths()), store=store)


def _attach_freshness(result: dict[str, object], staleness: dict[str, object]) -> None:
    """Name the revision the answer describes, in-band on the default payload (8-E).

    ``staleness`` is the state (current/behind/unknown); ``last_commit`` is the revision the index
    holds. Omitted only when the index never recorded a commit (pre-077), never silently (061).
    """
    result["staleness"] = staleness["staleness"]
    if staleness.get("last_commit"):
        result["last_commit"] = staleness["last_commit"]


def subject_parts(paths: list[str] | None, qnames: list[str] | None) -> list[str]:
    """Subject items in stable order (qnames then paths) — joined for the payload, capped in the
    claim line."""
    bits: list[str] = []
    if qnames:
        bits.extend(qnames)
    if paths:
        bits.extend(paths)
    return bits


def resolve_seeds(
    store: GraphStore, *, paths: Sequence[str], qnames: Sequence[str], max_results: int
) -> SeedSet:
    """Union path-file nodes with explicit qnames (stable order: qnames then path nodes).

    A requested subject that resolves to nothing is kept as its resolution rather than forgotten,
    so the caller can count the loss and say why it happened (task 102). A subject whose nodes were
    all seen already is a duplicate, not a drop.
    """
    found: list[str] = []
    seen: set[str] = set()
    dropped: list[SubjectResolution] = []
    from_bare: list[tuple[str, str]] = []
    bare_refused: list[tuple[str, list[dict[str, object]]]] = []

    def take(resolution: SubjectResolution) -> None:
        # One rule for both subject slots: a subject that resolved is a seed, whichever argument
        # it arrived in. Counting a resolvable subject as lost is the bug 102 exists to remove.
        if resolution.status != "resolved_unique":
            dropped.append(resolution)
        elif resolution.qname not in seen:
            seen.add(resolution.qname)
            found.append(resolution.qname)

    for qname in qnames:
        if not qname:
            continue
        resolution = _resolve_seed(store, qname, max_results)
        if resolution.status == "ambiguous":
            bare, sites = bare_subject(
                store, qname, kinds=BARE_SUBJECT_KINDS, limit=max_results
            )
            if sites:
                bare_refused.append((qname, sites))
                continue
            if bare is not None:
                if (qname, bare) not in from_bare:
                    from_bare.append((qname, bare))
                resolution = SubjectResolution("resolved_unique", bare, 1)
        take(resolution)
    expanded: list[str] = []
    for path in paths:
        if not path:
            continue
        rows = store.nodes_by_file_all(path)
        if not rows:
            take(classify_missing_subject(store, path, limit=max_results))
            continue
        for row in rows:
            qname = str(row["qualified_name"])
            if qname in seen:
                continue
            # Through the same gate a qname seed uses (169): a path-derived seed used to be
            # appended raw, so it was never classified, never counted and never explained.
            before = len(found)
            take(_resolve_seed(store, qname, max_results))
            if len(found) > before:
                expanded.append(qname)
    return SeedSet(
        found, tuple(dropped), tuple(expanded), tuple(from_bare), tuple(bare_refused)
    )


def _resolve_seed(store: GraphStore, qname: str, max_results: int) -> SubjectResolution:
    """A seed's stored qname: exact, or a uniquely-resolvable under-anchored form (075/076).

    An exact hit short-circuits before the classifier, so the hit path pays no extra query (R4).
    An absent or ambiguous seed comes back carrying the classification that says why (task 102).
    """
    if store.nodes_by_qualified_name(qname, limit=1):
        return SubjectResolution("resolved_unique", qname, 1)
    return classify_missing_subject(store, qname, limit=max_results)


def explain_lost_subject(
    result: dict[str, object], dropped: tuple[SubjectResolution, ...]
) -> dict[str, object]:
    """Say why the answer is empty when every named subject was lost (065/075/076; task 102).

    One subject carries its own classification and route. A merged multi-subject radius carries
    only the base class it can prove for every one of them — it has no per-subject channel (100).
    """
    if len(dropped) == 1:
        return shape_exact_miss(result, dropped[0])
    result["reason"] = REASON_NO_SUCH_SYMBOL
    return result
