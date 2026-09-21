"""``find_references`` — resolved edges targeting a qname (§12)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config, clamp_limit
from code_atlas.contract import (
    CALLER_KINDS,
    COLUMN_KIND,
    CONTAINS,
    TABLE_KIND,
    TYPE_KINDS,
    UNMODELLED_REFERENCE_KINDS,
    WRITES,
    inbound_kinds_for,
)
from code_atlas.store import GraphStore
from code_atlas.symbol_role import aggregate_test_count_source, stored_test_source
from code_atlas.tools import call_site, claim
from code_atlas.tools.coverage import (
    attach_coverage_note,
    covered_languages,
    cross_language_census_has_edges,
    cross_language_relation_unmodelled,
    relation_unmodelled_for_language,
)
from code_atlas.tools.freshness import (
    FreshnessGuard,
    dirty_indexed_paths,
    finalize_subject_checked_miss,
    label_serve_behind,
    unrepaired_subject_served,
)
from code_atlas.tools.nav_result import (
    CAVEAT_ALL_HITS_DYNAMIC,
    CAVEAT_CROSS_LANGUAGE_UNMODELLED,
    CAVEAT_SIBLING_DEFINITIONS,
    CAVEAT_WRITES_EMITTERS_ONLY,
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
    REASON_VIA_MEMBERS,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_HINT_METHOD_QNAME,
    TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE,
    TRY_INSTEAD_SEARCH_SYMBOL,
    apply_empty_inbound_honesty,
    attach_ambiguous_definitions,
    attach_authoritative_caveats,
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
    empty_nav,
    escalate_zero_production,
    nav_result,
    relation_reason,
    require_path_prefix,
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
# CONTAINS walk for the class-level caller union (252). Same order of magnitude as Table CONTAINS.
_MEMBER_WALK = 10_000
_UNION_SUBJECT_KINDS = frozenset({"Class"})
UNLINKED_WRITES_COUNT = "unlinked_writes_count"
# Table → Column CONTAINS walk for the writer-set union (248/278); same ballpark as read_symbol.
_WRITES_CONTAINS_WALK = 10_000


def _writes_answer_is_partial(
    covered: str | None,
    emitted: dict[str, list[str]] | None,
) -> bool:
    """True when a covered language emits no WRITES — that half is unmeasured (281).

    Keys on ``EMITTED_KINDS_BY_LANGUAGE``, never language count: every covered language
    emitting ``WRITES`` means the answer can hold every writer the index models.
    """
    if not covered:
        return False
    langs = [name for name in covered.split(",") if name]
    if not langs:
        return False
    if emitted is None:
        # Unstamped index (pre-186) never measured itself, which is not evidence that every
        # covered language emits WRITES — keep 278's conservative caveat (R5.6).
        return len(langs) >= 2
    writers = [lang for lang in langs if "WRITES" in emitted.get(lang, [])]
    return len(writers) < len(langs)


def _writes_targets(store: GraphStore, lookup: str, subject_kind: str) -> list[str]:
    """Targets whose inbound WRITES form the writer set (278).

    Column: itself. Table: the table plus every Column under CONTAINS — named-column
    WRITES never target the Table qname (SQL adapter), so the union is the wider set.
    """
    if subject_kind != TABLE_KIND:
        return [lookup]
    targets = [lookup]
    seen = {lookup}
    raws: list[str] = []
    for edge in store.edges_by_source(
        lookup, kinds=(CONTAINS,), limit=_WRITES_CONTAINS_WALK
    ):
        raw = str(edge.get("target_raw") or "")
        if raw and raw not in seen:
            seen.add(raw)
            raws.append(raw)
    if not raws:
        return targets
    found = store.nodes_by_qualified_names(raws, kind=COLUMN_KIND, limit=1)
    targets.extend(qname for qname in raws if found.get(qname))
    return targets


def _test_census(store: GraphStore, qname: str) -> tuple[int, int, str | None]:
    """``(production, test, how the test rows were decided)`` over every inbound edge (262).

    One grouped store read, shared by the first fetch and the re-pointed one.
    """
    return _test_census_for(
        store, [qname], kinds=None
    )


def _test_census_for(
    store: GraphStore,
    targets: list[str],
    *,
    kinds: tuple[str, ...] | None,
) -> tuple[int, int, str | None]:
    """Same 262 census over one or more targets (Table∪columns WRITES union — 278)."""
    production = 0
    test = 0
    role_bits: list[tuple[int, str]] = []
    for target in targets:
        rows = store.inbound_test_rows(target, kinds=kinds)
        production += sum(count for is_test, _path, count in rows if not is_test)
        test += sum(count for is_test, _path, count in rows if is_test)
        role_bits.extend((is_test, path) for is_test, path, _count in rows)
    label = aggregate_test_count_source(
        stored_test_source(is_test, path) for is_test, path in role_bits
    )
    return production, test, label


def _member_caller_union(
    store: GraphStore,
    class_qname: str,
    subject_kind: str,
    *,
    cap: int,
    offset: int,
    path_prefix: str | None = None,
) -> tuple[list[dict[str, object]], int] | None:
    """Page CALLS/NEW that target the class's declared CONTAINS children (252 / 265).

    ``None`` means the union is not available — keep the 065/093 route. An empty
    page with a count is an honest zero (``reason=via_members``), not unmodelled.
    Cost scales with the page: one ``IN`` read, never one walk per member.
    """
    if subject_kind not in _UNION_SUBJECT_KINDS:
        return None
    contains = store.edges_by_source(
        class_qname, kinds=("CONTAINS",), limit=_MEMBER_WALK
    )
    members: list[str] = []
    seen: set[str] = set()
    for edge in contains:
        target = edge.get("target_qname")
        if not target or target in seen:
            continue
        qn = str(target)
        seen.add(qn)
        members.append(qn)
    if not members:
        return None
    total = store.count_edges_by_targets(
        members, kinds=CALLER_KINDS, path_prefix=path_prefix
    )
    inbound = store.edges_by_targets(
        members,
        kinds=CALLER_KINDS,
        limit=cap,
        offset=offset,
        path_prefix=path_prefix,
    )
    hits: list[dict[str, object]] = []
    for edge in inbound:
        hit = edge_hit(edge)
        hit["via_member"] = str(edge.get("target_qname") or "")
        hits.append(hit)
    return hits, total


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def find_references(
        qname: str,
        detail_level: DetailLevel = "standard",
        include_source: bool = False,
        limit: int | None = None,
        offset: int = 0,
        sign: bool = False,
        serve_behind: bool = False,
        exclude_tests: bool = False,
        path_prefix: str | None = None,
    ) -> dict[str, object]:
        """Where is this symbol used across the codebase?

        Resolved edges whose ``target_qname`` is ``qname``, with confidence tiers.
        A **Table** or **Column** subject returns linked ``WRITES`` only (278). A Table
        unions writers of the table and of its CONTAINS columns (named-column sites
        never target the Table qname); a Column is the narrower set. When the graph
        still holds unlinked writers, ``unlinked_writes_count`` names them. On a
        multi-language index the answer carries ``writes_emitters_only`` when a
        covered language emits no ``WRITES`` — host-language string writes are out
        of scope (§19 / 281). ``REFERENCES`` (a
        ``Foo::class`` mention) is FQN-linked at ``DYNAMIC`` — a candidate
        list, not a proven use. When every returned hit is ``DYNAMIC``, the payload sets
        ``authoritative: false``. When another language is indexed but no linked ``*->L``
        pair reaches the subject's language (238/276), a hits-bearing answer is
        ``authoritative: false`` only when the stamped census has cross-language edges;
        an empty census is status-only. ``reason`` stays ``ok``.
        An ``IMPORTS`` naming an indexed file is linked since 188, so a
        **File** subject lists its importers; one naming a symbol or an unresolvable specifier stays
        bare. When unlinked ``REFERENCES``/``IMPORTS`` exist for an indexed subject and linked
        hits are zero, the
        payload uses ``reason=relationship_not_modelled``, ``try_instead=search_symbol`` (it
        enumerates the class's methods) and a ``try_instead_hint`` naming the two-step (065/093)
        — unless the subject is a ``Class`` with ``CONTAINS`` children, in which case the same
        call returns their inbound ``CALLS``/``NEW`` as ``reason=via_members`` (252; never ``ok``).
        When ``production_count`` is 0 but test hits remain, the same unmeasured route runs
        and ``unlinked_same_name_sites`` counts the unlinked inbound that name the subject (272).

        ``include_source`` (default off, so the common case stays token-frugal) adds each site's
        own source line as ``source``, capped in length. A site whose file drifted since indexing
        is never quoted: those hits carry ``source_stale`` instead.

        ``limit`` / ``offset`` page in store edge order (057); default limit is
        ``CA_MAX_RESULTS``. Optional ``path_prefix`` narrows to edges whose stored file
        path is under that index-root-relative POSIX prefix (315).

        ``subject_refreshed_only`` is present (and ``true``) only when read-through freshness
        reparsed the subject's file this call — neighbors were not re-verified (035 / 061).

        ``sign`` (default off, so the default payload is unchanged) adds ``claim``: one quotable
        ``key=value`` line naming subject, question, answer and the revision the index describes,
        carrying ``authoritative`` when every hit is ``DYNAMIC``. An answer with no index carries
        no line (task 100).

        ``serve_behind`` (default off) labels a behind-index answer: unchanged subjects as
        ``index_behind`` (257); unrepaired dirty subjects as ``index_behind_subject_changed``
        (267).

        A leading-anchor difference from the stored qname (``Ns\\Sub\\Enum`` vs
        ``\\Ns\\Sub\\Enum``) is re-pointed and answered; ``resolved_qname`` names the
        stored form (075/122). An exact stored qname is unchanged.
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        path_prefix = require_path_prefix(path_prefix)
        cap, limit_clamped = clamp_limit(limit, config.page_limit)
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
        emitted_kinds: dict[str, list[str]] | None = None
        cross_lang_census: dict[str, object] | None = None
        unlinked_edge_kinds: list[str] = []
        behind_dirty: list[str] = []
        subject_file: str | None = None
        subject_unrepaired = False
        production_count = 0
        test_count = 0
        test_role_label: str | None = None
        unlinked_writes_count = 0
        writes_subject = False
        writes_kinds: tuple[str, ...] | None = None
        writes_targets: list[str] | None = None
        unlinked_same_name_sites = 0
        with GraphStore(config.db_path) as store:
            covered = covered_languages(store)
            emitted_kinds = store.stamped_emitted_kinds_by_language()
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
                    )
                    if not serve_behind:
                        return signed(attach_serve_behind_route(refused))
                    return signed(attach_try_instead(refused, TRY_INSTEAD_FILE_OUTLINE))
                subject_unrepaired = True
            asked = qname
            lookup = qname
            production_count, test_count, test_role_label = _test_census(store, lookup)
            total_count = store.count_edges_by_target(
                lookup, exclude_test_sources=exclude_tests, path_prefix=path_prefix)
            # Widen the existing indexed-check fetch to surface every definition site (task 070).
            nodes = store.nodes_by_qualified_name(lookup, limit=config.page_limit)
            indexed = bool(nodes)
            if indexed and str(nodes[0]["kind"]) in (TABLE_KIND, COLUMN_KIND):
                # Writer set — WRITES only; Table unions CONTAINS columns (278).
                writes_subject = True
                writes_kinds = (WRITES,)
                subject_kind = str(nodes[0]["kind"])
                writes_targets = _writes_targets(store, lookup, subject_kind)
                total_count = store.count_edges_by_targets(
                    writes_targets,
                    kinds=writes_kinds,
                    exclude_test_sources=exclude_tests, path_prefix=path_prefix)
                production_count, test_count, test_role_label = _test_census_for(
                    store, writes_targets, kinds=writes_kinds
                )
                table_key = (
                    lookup.rsplit("::", 1)[0]
                    if subject_kind == COLUMN_KIND and "::" in lookup
                    else lookup
                )
                unlinked_writes_count = store.count_unlinked_writes_relating_to(table_key)
            if total_count == 0 and not indexed:
                # Under-qualified, untracked, or a genuine absence (075/076/092/122).
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
                production_count, test_count, test_role_label = _test_census(store, lookup)
                nodes = store.nodes_by_qualified_name(lookup, limit=config.page_limit)
                indexed = bool(nodes)
                if indexed and str(nodes[0]["kind"]) in (TABLE_KIND, COLUMN_KIND):
                    writes_subject = True
                    writes_kinds = (WRITES,)
                    subject_kind = str(nodes[0]["kind"])
                    writes_targets = _writes_targets(store, lookup, subject_kind)
                    table_key = (
                        lookup.rsplit("::", 1)[0]
                        if subject_kind == COLUMN_KIND and "::" in lookup
                        else lookup
                    )
                    unlinked_writes_count = store.count_unlinked_writes_relating_to(
                        table_key
                    )
                    production_count, test_count, test_role_label = _test_census_for(
                        store, writes_targets, kinds=writes_kinds
                    )
                if writes_targets is not None:
                    total_count = store.count_edges_by_targets(
                        writes_targets,
                        kinds=writes_kinds,
                        exclude_test_sources=exclude_tests, path_prefix=path_prefix)
                else:
                    total_count = store.count_edges_by_target(
                        lookup,
                        kinds=writes_kinds,
                        exclude_test_sources=exclude_tests, path_prefix=path_prefix)
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
                        limit=config.page_limit,
                    )
                )
            if writes_targets is not None:
                edges = store.edges_by_targets(
                    writes_targets,
                    kinds=writes_kinds,
                    limit=cap,
                    offset=offset,
                    exclude_test_sources=exclude_tests, path_prefix=path_prefix)
            else:
                edges = store.edges_by_target(
                    lookup,
                    kinds=writes_kinds,
                    limit=cap,
                    offset=offset,
                    exclude_test_sources=exclude_tests, path_prefix=path_prefix)
            results = [edge_hit(edge) for edge in edges]
            # Skewed page 1 hides other subtrees — advertise the full spread (task 067).
            subtrees = (
                store.edge_subtrees_by_target(lookup, path_prefix=path_prefix)
                if writes_targets is None and offset + len(results) < total_count
                else {}
            )
            if include_source:
                call_site.annotate(config.root, store, results)
            reason = relation_reason(hit_total=total_count, symbol_indexed=indexed)
            try_instead: str | None = None
            try_instead_hint: str | None = None
            # Empty + unlinked inbound ⇒ not a genuine zero (065/255/264). Arms in order:
            # REFERENCES/IMPORTS with bare name (065); language census (232); then the shared
            # predicate over INBOUND_KINDS_BY_SUBJECT at qname only (255/264). Every upgrade to
            # relationship_not_modelled goes through apply_empty_inbound_honesty.
            if reason == REASON_NO_MATCHES and nodes:
                name = str(nodes[0]["name"])
                subject_kind = str(nodes[0]["kind"])
                reason, unlinked_edge_kinds = apply_empty_inbound_honesty(
                    reason,
                    store,
                    subject_kind=subject_kind,
                    raws=(lookup, name),
                    kinds=UNMODELLED_REFERENCE_KINDS,
                )
                if (
                    reason == REASON_NO_MATCHES
                    and not relation_unmodelled_for_language(
                        store, file_path=str(nodes[0]["file_path"]), kinds=("REFERENCES",)
                    )
                ):
                    reason, unlinked_edge_kinds = apply_empty_inbound_honesty(
                        reason,
                        store,
                        subject_kind=subject_kind,
                        raws=(lookup,),
                    )
                if unlinked_edge_kinds:
                    union = _member_caller_union(
                        store,
                        lookup,
                        subject_kind,
                        cap=cap,
                        offset=offset,
                        path_prefix=path_prefix,
                    )
                    if union is not None:
                        results, total_count = union
                        reason = REASON_VIA_MEMBERS
                        subtrees = {}
                        if include_source:
                            call_site.annotate(config.root, store, results)
                    else:
                        # Type-shaped subjects still route to search_symbol for member qnames
                        # (093). Other kinds get the relation hint, never a self-loop tool name.
                        if subject_kind in TYPE_KINDS:
                            try_instead = TRY_INSTEAD_SEARCH_SYMBOL
                            try_instead_hint = TRY_INSTEAD_HINT_METHOD_QNAME
                        else:
                            try_instead_hint = TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE
                elif relation_unmodelled_for_language(
                    store, file_path=str(nodes[0]["file_path"]), kinds=("REFERENCES",)
                ):
                    # Per-kind (232): IMPORTS in the set must not mask a never-emitted REFERENCES.
                    reason = REASON_RELATION_UNMODELLED_FOR_LANGUAGE
                    try_instead_hint = TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE
            if production_count == 0 and indexed and nodes:
                name = str(nodes[0]["name"])
                subject_kind = str(nodes[0]["kind"])
                unlinked_same_name_sites = store.count_unlinked_by_target_raw(
                    (lookup, name), kinds=inbound_kinds_for(subject_kind)
                )
                reason = escalate_zero_production(
                    reason,
                    production_count=production_count,
                    unlinked_same_name_sites=unlinked_same_name_sites,
                )
                if (
                    reason == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
                    and try_instead_hint is None
                ):
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
        if writes_subject and unlinked_writes_count:
            # Bounded incompleteness the graph can name (215/278) — a count, not a buried bool.
            result["unlinked_writes_count"] = unlinked_writes_count
        if production_count or test_count:
            # Nothing inbound: 0 + 0 would only restate `total_count` (061).
            result["production_count"] = production_count
            result["test_count"] = test_count
            if test_role_label is not None:
                result["test_role_source"] = test_role_label
        if unlinked_same_name_sites and test_count:
            result["unlinked_same_name_sites"] = unlinked_same_name_sites

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
        if (
            cross_lang_census is not None
            and total_count > 0
            and cross_language_census_has_edges(cross_lang_census)
        ):
            # 238 hit-path caveat, narrowed by 276: empty census stays on status, not every hit.
            attach_cross_language_census(result, cross_lang_census)
            caveats.append(CAVEAT_CROSS_LANGUAGE_UNMODELLED)
        if writes_subject and _writes_answer_is_partial(covered, emitted_kinds):
            # Emitters-only half — non-emitting covered languages stay unmeasured (§19 / 281).
            caveats.append(CAVEAT_WRITES_EMITTERS_ONLY)
        attach_authoritative_caveats(result, caveats)
        labelled = label_serve_behind(
            result,
            serve_behind=serve_behind,
            subject_path=subject_file,
            revision=staleness or None,
            dirty_paths=behind_dirty,
            subject_unrepaired=subject_unrepaired,
        )
        return signed(
            attach_coverage_note(
                attach_try_instead(labelled, try_instead, try_instead_hint), config, covered,
                detail_level=detail_level,
            )
        )

    return find_references
