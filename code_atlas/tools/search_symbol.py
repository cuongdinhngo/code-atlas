"""``search_symbol`` — ranked FTS + name hits (§12), one subject or a sweep of them (101)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Literal, NamedTuple

from code_atlas import contract
from code_atlas.config import Config, clamp_limit, clamp_subjects
from code_atlas.contract import CONFIDENCE_TIERS
from code_atlas.store import GraphStore, Row, is_direct_match
from code_atlas.tools.coverage import (
    attach_coverage_gap,
    attach_coverage_note,
    covered_languages,
)
from code_atlas.tools.freshness import FreshnessGuard, nameable_subject_path
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_KIND_EXCLUDED,
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
    REASON_SEPARATOR_NORMALISED,
    REASON_SUBJECT_FILE_CHECKED,
    REASON_SUBSTRING_MATCH,
    REASON_TOKEN_CANDIDATES,
    RETRY_AS_FIELD,
    RETRY_AS_QUERY,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_HINT_MEMBER_SEPARATOR,
    TRY_INSTEAD_HINT_NARROW_BY_QNAME,
    TRY_INSTEAD_HINT_SINGLE_SUBJECT_REPAIR,
    TRY_INSTEAD_HINT_TOKEN_CANDIDATES,
    TRY_INSTEAD_HINT_TOKEN_CANDIDATES_NONE,
    TRY_INSTEAD_SEARCH_SYMBOL,
    NavReason,
    attach_limit_capped,
    attach_subjects_capped,
    attach_try_instead,
    batch_not_indexed,
    batch_result,
    is_stub,
    list_result,
    subject_answer,
)

_RESOLVED = CONFIDENCE_TIERS[0]

NAME = "search_symbol"

DetailLevel = Literal["minimal", "standard"]


class _Hits(NamedTuple):
    """One subject's own findings — every field varies per subject, none is the batch's."""

    results: list[dict[str, object]]
    truncated: bool
    reason: NavReason
    total_count: int
    other_indexed_files_drifted: int = 0
    candidates: tuple[dict[str, object], ...] = ()
    kind_excluded: tuple[str, ...] = ()


def _require_kind(kind: contract.NodeKind | None) -> contract.NodeKind | None:
    """Reject unknown ``kind`` spellings before any SQL (R5.3); ``None`` means no filter."""
    if kind is not None and kind not in contract.NODE_KINDS:
        raise ValueError(f"unknown kind {kind!r}: one of {', '.join(contract.NODE_KINDS)}")
    return kind


def _require_subjects(query: str | None, queries: list[str] | None) -> list[str]:
    """Exactly one of the two spellings, and a sweep must name a subject (R5.3).

    Preferring one silently would hide a caller bug behind a plausible answer, which is the
    failure mode this tool exists to remove.
    """
    if queries is not None:
        if query is not None:
            raise ValueError("pass query or queries, never both")
        if not queries:
            raise ValueError("queries must name at least one subject")
        return list(queries)
    if query is None:
        raise ValueError("pass query (one subject) or queries (a sweep)")
    return [query]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def search_symbol(
        query: str | None = None,
        kind: contract.NodeKind | None = None,
        namespace: str | None = None,
        limit: int | None = None,
        detail_level: DetailLevel = "standard",
        offset: int = 0,
        queries: list[str] | None = None,
    ) -> dict[str, object]:
        """Find a symbol from part of its name or text — ranked, with where each one lives.

        Pass ``query`` for one subject, or ``queries`` for a sweep of them — *"are any of these ten
        names already taken?"* is one call, not ten (101). Never both. A sweep returns ``subjects``:
        one entry per subject, **in the order you asked**, each with its own ``results``, ``reason``
        and ``total_count``, so one miss never colours the rest. At most ``max_subjects`` are
        accepted; the rest are named in ``subjects_dropped`` beside ``subjects_capped_to``.
        A sweep shares **one** read-through repair budget across every subject, so a subject whose
        file drifted may answer ``index_stale`` where a single call would have repaired it. When a
        sweep mixes ``ok`` with ``index_stale``, the envelope names the refused subjects and states
        that the shared budget decided (275) — a fully-``ok`` sweep stays unchanged (061).

        Returns ``{qname, kind, file, line}`` rows (FTS trigram, or a name/qname prefix scan for
        queries under three characters), capped by ``limit`` or ``CA_MAX_RESULTS``; ``offset`` pages
        in search order (057). **Exact and prefix matches come first**, near-misses after, relevance
        as the tie-break inside each band — over the whole result set, not the page (180).
        At ``standard``, a ``Column`` whose schema declares a foreign key also carries its target(s)
        from existing ``REFERENCES`` edges (239): resolved column targets under ``references``, and
        a column-list-omitted FK — which names only its table — under ``references_unresolved``, so
        the two are never signed alike (R5.6). Both are omitted when empty, and never appear on
        ``minimal`` or non-``Column`` rows. When the first page holds only
        substring/trigram near-misses — no
        result exactly matches or prefixes the query — ``reason=substring_match`` marks the answer a
        near-miss, not a hit, and carries the language-coverage note (167 / 160). A
        ``substring_match`` answer, or a page short of ``total_count``, also carries
        ``try_instead=file_outline`` plus the narrow-by-qname hint, so the reader has a query to
        make next instead of inventing one (245 / 093). On hash drift
        beyond the per-call reparse cap, returns hits with
        ``reason=index_stale`` and an honest ``total_count`` (never an empty proof of absence); a
        zero-hit first page may repair a named subject file or the sole dirty indexed file; an
        unnameable subject amid several dirty files yields empty ``index_stale`` (073/246). Stub-
        indexed nodes carry ``stub: true`` (039); a ``File`` hit that only restates a ``Class``
        hit's declaring file in the same page is suppressed — request File rows via ``kind`` (061).
        """
        subjects = _require_subjects(query, queries)
        batched = queries is not None
        kind = _require_kind(kind)
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap, limit_clamped = clamp_limit(limit, config.page_limit)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        db_path = str(config.db_path)
        index_root = config.index_root
        if not config.db_path.is_file():
            # No index is a fact about the server, not about any one subject (101).
            if batched:
                return batch_not_indexed(index_root)
            return list_result(
                [],
                detail_level=detail_level,
                db_path=db_path,
                index_root=index_root,
                truncated=False,
                reason=REASON_NOT_INDEXED,
                total_count=0,
                indexed=False,
            )
        kept, dropped = clamp_subjects(subjects, config.max_subjects)
        covered: str | None = None
        with GraphStore(config.db_path) as store:
            covered = covered_languages(store)
            # One guard for the call: scaling the repair budget with the subject count is the
            # unbounded fan-out the batch bound exists to prevent (101).
            guard = FreshnessGuard(config, store)
            found = [
                _search_one(
                    store,
                    guard,
                    subject,
                    kind=kind,
                    namespace=namespace,
                    cap=cap,
                    offset=offset,
                    detail_level=detail_level,
                )
                for subject in kept
            ]
        if not batched:
            return attach_coverage_note(
                _single_payload(
                    found[0],
                    detail_level=detail_level,
                    db_path=db_path,
                    index_root=index_root,
                    cap=cap,
                    limit_clamped=limit_clamped,
                ),
                config,
                covered,
                detail_level=detail_level,
            )
        answers = [
            _batch_answer(subject, hits) for subject, hits in zip(kept, found, strict=True)
        ]
        payload = batch_result(answers, index_root=index_root)
        attach_limit_capped(payload, cap=cap, clamped=limit_clamped)
        attach_subjects_capped(payload, cap=config.max_subjects, dropped=dropped)
        _attach_mixed_repair_budget(payload, answers)
        # A swept miss is the same 8-A shape as a single one: name the coverage gap once on the
        # envelope (call-level, never per subject — 061) when any subject came back a genuine zero,
        # a token-candidate miss (253), or a substring near-miss — the sweep path is the one 160's
        # AC1e showed gets missed (167).
        if any(
            (not a["results"] and a["reason"] in (REASON_NO_MATCHES, REASON_TOKEN_CANDIDATES))
            or a["reason"] == REASON_SUBSTRING_MATCH
            for a in answers
        ):
            attach_coverage_gap(payload, config, covered, detail_level=detail_level)
        return payload

    return search_symbol


def _search_one(
    store: GraphStore,
    guard: FreshnessGuard,
    query: str,
    *,
    kind: contract.NodeKind | None,
    namespace: str | None,
    cap: int,
    offset: int,
    detail_level: DetailLevel,
) -> _Hits:
    """One subject's search, verdict included — the same path a single call has always taken."""
    rows = store.search_nodes(query, kind=kind, namespace=namespace, limit=cap + 1, offset=offset)
    hit_paths = [str(row["file_path"]) for row in rows[:cap]]
    status = guard.ensure_paths(hit_paths)
    # Zero hits: miss-repair a named subject or the sole dirty file (073/246).
    # First page only: an empty page past the end is not an empty answer (057).
    # Read the residue only where it was computed: one guard serves every subject of a sweep
    # (101), so carrying it across subjects would put one subject's drift on another's answer.
    residue = 0
    if not rows and offset == 0 and status == "ok":
        status = guard.ensure_miss(nameable_subject_path(store, query))
        residue = guard.other_indexed_files_drifted
    # Re-query only when a repair may have changed FTS/rows.
    if status == "repaired" or (status == "stale" and guard.used > 0):
        rows = store.search_nodes(
            query, kind=kind, namespace=namespace, limit=cap + 1, offset=offset
        )
    truncated = len(rows) > cap
    results = _suppress_redundant_file_hits(
        [_hit(row, store=store, detail_level=detail_level) for row in rows[:cap]]
    )
    if truncated or offset > 0:
        total_count = store.count_search_nodes(query, kind=kind, namespace=namespace)
        truncated = offset + len(results) < total_count
    else:
        total_count = len(results)
    if status == "stale":
        reason: NavReason = REASON_INDEX_STALE
    elif total_count == 0:
        # Page emptiness ≠ answer emptiness once offset can walk past the end (057).
        reason = (
            REASON_SUBJECT_FILE_CHECKED if residue > 0 else REASON_NO_MATCHES
        )
    elif offset == 0 and not any(_direct(query, row) for row in rows[:cap]):
        # First page holds only substring/trigram near-misses — not a confident hit (167).
        reason = REASON_SUBSTRING_MATCH
    else:
        reason = REASON_OK
    # Empty no_matches only: retry with last sep spelled as MEMBER_SEPARATOR (249).
    if reason == REASON_NO_MATCHES and offset == 0:
        alt = contract.member_separator_variant(query)
        if alt is not None:
            alt_rows = store.search_nodes(
                alt, kind=kind, namespace=namespace, limit=cap + 1, offset=0
            )
            if alt_rows:
                # The retry answers from the same graph, so it owes the same freshness verdict as
                # the direct spelling — a misspelled separator must not out-answer a correct one.
                alt_status = guard.ensure_paths([str(row["file_path"]) for row in alt_rows[:cap]])
                if alt_status == "repaired":
                    alt_rows = store.search_nodes(
                        alt, kind=kind, namespace=namespace, limit=cap + 1, offset=0
                    )
                if alt_rows:
                    truncated = len(alt_rows) > cap
                    results = _suppress_redundant_file_hits(
                        [
                            _hit(row, store=store, detail_level=detail_level)
                            for row in alt_rows[:cap]
                        ]
                    )
                    if truncated:
                        total_count = store.count_search_nodes(
                            alt, kind=kind, namespace=namespace
                        )
                        truncated = len(results) < total_count
                    else:
                        total_count = len(results)
                    alt_reason: NavReason = (
                        REASON_INDEX_STALE
                        if alt_status == "stale"
                        else REASON_SEPARATOR_NORMALISED
                    )
                    return _Hits(results, truncated, alt_reason, total_count, residue)
    # Zero-overlap miss: kind filter first (275), then token decomposition (253).
    if reason == REASON_NO_MATCHES and offset == 0:
        if kind is not None:
            excluded = _kind_excluded_hits(
                store, query, kind=kind, namespace=namespace, cap=cap
            )
            if excluded:
                return _Hits(
                    [], False, REASON_KIND_EXCLUDED, 0, residue, (), tuple(excluded)
                )
        tokens = contract.name_tokens(query)
        if tokens:
            candidates = _token_candidates(
                store, tokens, kind=kind, namespace=namespace
            )
            return _Hits(
                [],
                False,
                REASON_TOKEN_CANDIDATES,
                0,
                residue,
                tuple(candidates),
            )
    return _Hits(results, truncated, reason, total_count, residue)


def _direct(query: str, row: Mapping[str, object] | Row) -> bool:
    """``store.is_direct_match`` over a row — the predicate the search ordering bands on (R6.7)."""
    return is_direct_match(query, str(row["name"]), str(row["qualified_name"]))


def _single_payload(
    hits: _Hits,
    *,
    detail_level: str,
    db_path: str,
    index_root: str,
    cap: int,
    limit_clamped: bool,
) -> dict[str, object]:
    """The one-subject answer, unchanged by 101 — pinned byte-for-byte by its own test."""
    payload = list_result(
        hits.results,
        detail_level=detail_level,
        db_path=db_path,
        index_root=index_root,
        truncated=hits.truncated,
        reason=hits.reason,
        total_count=hits.total_count,
    )
    # Empty + unverified (multi-dirty miss) — point at path-named tools (073).
    if hits.reason == REASON_INDEX_STALE and hits.total_count == 0:
        return attach_try_instead(payload, TRY_INSTEAD_FILE_OUTLINE)
    if hits.reason == REASON_KIND_EXCLUDED:
        payload["kind_excluded"] = list(hits.kind_excluded)
        return payload
    # Near-miss / truncated flood — name the narrower query (245); registry reuse (093).
    if _needs_narrowing_route(hits):
        hint = (
            TRY_INSTEAD_HINT_MEMBER_SEPARATOR
            if hits.reason == REASON_SEPARATOR_NORMALISED
            else TRY_INSTEAD_HINT_NARROW_BY_QNAME
        )
        attach_try_instead(payload, TRY_INSTEAD_FILE_OUTLINE, hint)
    elif hits.reason == REASON_TOKEN_CANDIDATES:
        payload["candidates"] = list(hits.candidates)
        if hits.candidates:
            attach_try_instead(
                payload, TRY_INSTEAD_SEARCH_SYMBOL, TRY_INSTEAD_HINT_TOKEN_CANDIDATES
            )
        else:
            attach_try_instead(
                payload, TRY_INSTEAD_SEARCH_SYMBOL, TRY_INSTEAD_HINT_TOKEN_CANDIDATES_NONE
            )
    attach_limit_capped(payload, cap=cap, clamped=limit_clamped)
    if hits.other_indexed_files_drifted > 0:
        payload["other_indexed_files_drifted"] = hits.other_indexed_files_drifted
    return payload


def _batch_answer(query: str, hits: _Hits) -> dict[str, object]:
    """One entry of ``subjects`` — its route stays inside it, never on the envelope (101)."""
    answer = subject_answer(
        query,
        hits.results,
        truncated=hits.truncated,
        reason=hits.reason,
        total_count=hits.total_count,
    )
    if hits.reason == REASON_INDEX_STALE:
        # Shared-budget refuse: single-subject retry is the progress route (275 / R5.4).
        answer[RETRY_AS_FIELD] = RETRY_AS_QUERY
        attach_try_instead(answer, None, TRY_INSTEAD_HINT_SINGLE_SUBJECT_REPAIR)
    elif hits.reason == REASON_KIND_EXCLUDED:
        answer["kind_excluded"] = list(hits.kind_excluded)
    elif _needs_narrowing_route(hits):
        hint = (
            TRY_INSTEAD_HINT_MEMBER_SEPARATOR
            if hits.reason == REASON_SEPARATOR_NORMALISED
            else TRY_INSTEAD_HINT_NARROW_BY_QNAME
        )
        attach_try_instead(answer, TRY_INSTEAD_FILE_OUTLINE, hint)
    elif hits.reason == REASON_TOKEN_CANDIDATES:
        answer["candidates"] = list(hits.candidates)
        if hits.candidates:
            attach_try_instead(
                answer, TRY_INSTEAD_SEARCH_SYMBOL, TRY_INSTEAD_HINT_TOKEN_CANDIDATES
            )
        else:
            attach_try_instead(
                answer, TRY_INSTEAD_SEARCH_SYMBOL, TRY_INSTEAD_HINT_TOKEN_CANDIDATES_NONE
            )
    if hits.other_indexed_files_drifted > 0:
        answer["other_indexed_files_drifted"] = hits.other_indexed_files_drifted
    return answer


def _attach_mixed_repair_budget(
    payload: dict[str, object], answers: list[dict[str, object]]
) -> None:
    """Flag a sweep that mixed ok with index_stale under one repair budget (275 / 061)."""
    stale = [
        str(a["query"])
        for a in answers
        if a.get("reason") == REASON_INDEX_STALE
    ]
    if not stale:
        return
    if not any(a.get("reason") == REASON_OK for a in answers):
        return
    payload["repair_budget_shared"] = True
    payload["index_stale_subjects"] = stale
    # queries order decides who spends the one reparse (stated, not silent).
    payload["repair_budget_order"] = "queries"


def _kind_excluded_hits(
    store: GraphStore,
    query: str,
    *,
    kind: contract.NodeKind,
    namespace: str | None,
    cap: int,
) -> list[str]:
    """Exact-name kinds present without the filter that the kind= filter dropped (275)."""
    rows = store.search_nodes(
        query, kind=None, namespace=namespace, limit=cap + 1, offset=0
    )
    found = {
        str(row["kind"])
        for row in rows
        if _direct(query, row) and str(row["kind"]) != kind
    }
    return sorted(found)


def _needs_narrowing_route(hits: _Hits) -> bool:
    """True when the page is a near-miss or short of the full hit set (245/249)."""
    if hits.reason in (REASON_SUBSTRING_MATCH, REASON_SEPARATOR_NORMALISED):
        return True
    return hits.truncated and hits.total_count > len(hits.results)


def _token_candidates(
    store: GraphStore,
    tokens: tuple[str, ...],
    *,
    kind: contract.NodeKind | None,
    namespace: str | None,
) -> list[dict[str, object]]:
    """Rank declared symbols by how many query tokens they carry; bound by TOKEN_CANDIDATE_K."""
    # Over-fetch per token so a symbol carrying two tokens can outrank single-token noise.
    per_token = contract.TOKEN_CANDIDATE_K * 2
    scored: dict[str, tuple[int, str, str, str, str, tuple[str, ...]]] = {}
    for token in tokens:
        rows = store.search_nodes(
            token, kind=kind, namespace=namespace, limit=per_token, offset=0
        )
        for row in rows:
            if str(row["kind"]) == "File":
                continue
            qname = str(row["qualified_name"])
            name = str(row["name"])
            hay = f"{name} {qname}".casefold()
            matched = tuple(t for t in tokens if t in hay)
            if not matched:
                continue
            score = len(matched)
            prev = scored.get(qname)
            if prev is None or score > prev[0]:
                scored[qname] = (
                    score,
                    name.casefold(),
                    name,
                    qname,
                    str(row["kind"]),
                    matched,
                )
    ordered = sorted(scored.values(), key=lambda row: (-row[0], row[1], row[3]))
    out: list[dict[str, object]] = []
    for _score, _sort, name, qname, kind_s, matched in ordered[: contract.TOKEN_CANDIDATE_K]:
        # Keys assigned via subscript so the dict literal does not re-list NODE_FIELDS (R3.2).
        cand: dict[str, object] = {"qname": qname, "matched_tokens": list(matched)}
        cand["name"] = name
        cand["kind"] = kind_s
        out.append(cand)
    return out


def _suppress_redundant_file_hits(
    results: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Drop File rows that only restate a Class's declaring file in this page (061)."""
    class_files = {r["file"] for r in results if r.get("kind") == "Class"}
    if not class_files:
        return results
    return [
        row
        for row in results
        if not (row.get("kind") == "File" and row.get("file") in class_files)
    ]


def _hit(
    row: Mapping[str, object] | Row,
    *,
    store: GraphStore | None = None,
    detail_level: DetailLevel = "standard",
) -> dict[str, object]:
    hit: dict[str, object] = {}
    hit["qname"] = row["qualified_name"]
    hit["kind"] = row["kind"]
    hit["file"] = row["file_path"]
    hit["line"] = row["line_start"]
    if is_stub(row.get("extra")):
        hit[contract.STUB_FLAG] = True
    # Kind-scoped (061): only Column at standard; read existing REFERENCES edges (239).
    if (
        store is not None
        and detail_level != "minimal"
        and row["kind"] == "Column"
    ):
        resolved, unresolved = _column_reference_targets(store, str(row["qualified_name"]))
        if resolved:
            hit["references"] = resolved
        if unresolved:
            hit["references_unresolved"] = unresolved
    return hit


def _column_reference_targets(store: GraphStore, qname: str) -> tuple[list[str], list[str]]:
    """Stable, deduped ``REFERENCES`` targets split by tier — resolved columns, then table-only.

    A column-list-omitted FK can only name the table, so signing it as a resolved target would
    attest past what the payload can tell apart (R5.6).
    """
    resolved: set[str] = set()
    unresolved: set[str] = set()
    for edge in store.edges_by_source(qname, kinds=("REFERENCES",), limit=32):
        target = edge["target_qname"] or edge["target_raw"]
        if not target:
            continue
        bucket = resolved if edge["confidence_tier"] == _RESOLVED else unresolved
        bucket.add(str(target))
    return sorted(resolved), sorted(unresolved)
