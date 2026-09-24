"""``impact`` — bounded best-score blast radius (§12 / M6)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal, NamedTuple

from code_atlas.config import Config
from code_atlas.contract import CALLER_KINDS
from code_atlas.mirror_search import label_mirror_rows, load_mirror_search_stamp
from code_atlas.store import GraphStore
from code_atlas.symbol_role import stored_test_source
from code_atlas.tools import claim
from code_atlas.tools.nav_result import (
    CAVEAT_SIBLING_DEFINITIONS,
    CAVEAT_UNLINKED_SAME_NAME_SITES,
    REASON_NO_SUCH_SYMBOL,
    REASON_SUBJECT_AMBIGUOUS,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_FIND_CALLERS,
    TRY_INSTEAD_HINT_IMPACT_BY_QNAME,
    TRY_INSTEAD_HINT_UNLINKED_CALLS,
    SubjectResolution,
    answered_about_ref_for,
    attach_ambiguous_definitions,
    attach_authoritative_caveats,
    attach_sibling_definitions,
    attach_try_instead,
    classify_missing_subject,
    definition_sites,
    empty_nav,
    nav_result,
    shape_exact_miss,
    sibling_definition_rows,
)
from code_atlas.tools.staleness import compute_staleness

NAME = "impact"

# ``subject_parts`` / ``resolve_seeds`` / ``explain_lost_subject`` / ``SeedSet`` are public so the
# module rollup (140) answers about the same seeds this tool does. One definition, two answers.

DetailLevel = Literal["minimal", "standard"]

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

    @property
    def refused(self) -> int:
        """Seeds this plan removed — every one accounted for in ``seeds_dropped`` (102)."""
        return len(self.dropped) + len(self.ambiguous_sites) + len(self.twinned_sites)


def plan_seeds(
    store: GraphStore, *, paths: Sequence[str], qnames: Sequence[str], max_results: int
) -> SeedPlan:
    """Resolve the subjects, then remove the seeds that cannot honestly be walked (161 + 169)."""
    seed_set = resolve_seeds(store, paths=paths, qnames=qnames, max_results=max_results)
    walk_seeds, ambiguous_sites = _split_ambiguous(store, seed_set.seeds, max_results)
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
    )


def attach_seed_refusals(payload: dict[str, object], plan: SeedPlan) -> None:
    """Name every refused seed on the payload — the same disclosure, whatever the rows look like.

    A module list that silently lost a seed is worse than one that names the loss, and a rollup is
    acted on destructively exactly as `impact` is. Copied nowhere: both tools call this (R6.7).
    """
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


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def impact(
        paths: list[str] | None = None,
        qnames: list[str] | None = None,
        depth: int | None = None,
        detail_level: DetailLevel = "standard",
        sign: bool = False,
        exclude_tests: bool = False,
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
        The default payload names the revision it describes — ``staleness`` plus ``last_commit`` —
        so a blast radius acted on destructively is never silently undated (8-E).

        At ``standard`` a row whose symbol is stored as test carries ``test_role_source``
        (``adapter`` / ``path_convention``, how it was decided); a row without it is production.
        A row on a stamped mirror pair carries ``mirror_counterpart`` (its indexed twin) or
        ``mirror_no_counterpart: true``. These are row properties — no count splits the radius.
        ``exclude_tests`` drops test sources inside the walk, before the node budget and the page,
        so page one holds production rows rather than those a page of tests left over.

        ``sign`` (default off, so the default payload is unchanged) adds ``claim``: one quotable
        ``key=value`` line naming subject, question, answer and the revision the index describes,
        with ``seeds`` beside ``answer`` (``answer == seeds`` is the modelled zero: nothing beyond
        the seeds depends on them) and ``seeds_dropped`` / ``frontier_skipped_non_resolved``.
        No line is emitted when there is no index, or when no seed resolved — a question nothing
        answered would be signed ``answer=0``, and a claim that cannot be re-run is decoration.
        """
        hops = config.impact_depth if depth is None else depth
        if hops < 0:
            raise ValueError(f"depth must be >= 0, got {hops}")
        parts = subject_parts(paths, qnames)
        subject = ",".join(parts)
        if not config.db_path.is_file():
            return empty_nav(subject, detail_level=detail_level, db_path=str(config.db_path),
            index_root=config.index_root,
            answered_about_ref=None)
        with GraphStore(config.db_path) as store:
            about_ref = answered_about_ref_for(store)
            plan = plan_seeds(
                store, paths=paths or [], qnames=qnames or [], max_results=config.page_limit
            )
            outcome = store.impact_radius(
                plan.walk_seeds,
                depth=hops,
                max_nodes=config.impact_max_nodes + 1,
                exclude_test_sources=exclude_tests,
            )
            results = outcome.rows[: config.impact_max_nodes]
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
            seeds_dropped=outcome.seeds_dropped + plan.refused,
            answered_about_ref=about_ref)
        _attach_freshness(result, staleness)
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
    store: GraphStore, seeds: Sequence[str], max_results: int
) -> tuple[list[str], list[tuple[str, list[dict[str, object]]]]]:
    """Partition seeds into walkable (one definition) and ambiguous (a shared qname, 9-A).

    The graph links callers by qname, not node identity, so a qname with >1 definitions cannot be
    attributed to one twin; such a seed is disclosed, never walked as an arbitrary one. Order-stable
    (R4.2); the site list is ``definition_sites`` order.
    """
    walk: list[str] = []
    ambiguous: list[tuple[str, list[dict[str, object]]]] = []
    for qname in seeds:
        rows = store.nodes_by_qualified_name(qname, limit=max_results)
        if len(rows) > 1:
            ambiguous.append((qname, definition_sites(rows)))
        else:
            walk.append(qname)
    return walk, ambiguous


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
        label_mirror_rows(rows, stamp, frozenset(store.file_paths()))


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
        take(_resolve_seed(store, qname, max_results))
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
    return SeedSet(found, tuple(dropped), tuple(expanded))


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
