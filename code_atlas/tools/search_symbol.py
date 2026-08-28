"""``search_symbol`` — ranked FTS + name hits (§12), one subject or a sweep of them (101)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Literal, NamedTuple

from code_atlas import contract
from code_atlas.config import Config, clamp_limit, clamp_subjects
from code_atlas.store import GraphStore, Row
from code_atlas.tools.coverage import (
    attach_coverage_gap,
    attach_coverage_note,
    covered_languages,
)
from code_atlas.tools.freshness import FreshnessGuard
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
    REASON_SUBSTRING_MATCH,
    TRY_INSTEAD_FILE_OUTLINE,
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

NAME = "search_symbol"

DetailLevel = Literal["minimal", "standard"]


class _Hits(NamedTuple):
    """One subject's own findings — every field varies per subject, none is the batch's."""

    results: list[dict[str, object]]
    truncated: bool
    reason: NavReason
    total_count: int


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
        file drifted may answer ``index_stale`` where a single call would have repaired it.

        Returns ``{qname, kind, file, line}`` rows (FTS trigram, or a name/qname prefix scan for
        queries under three characters), capped by ``limit`` or ``CA_MAX_RESULTS``; ``offset`` pages
        in search order (057). When the first page holds only substring/trigram near-misses — no
        result exactly matches or prefixes the query — ``reason=substring_match`` marks the answer a
        near-miss, not a hit, and carries the language-coverage note (167 / 160). On hash drift
        beyond the per-call reparse cap, returns hits with
        ``reason=index_stale`` and an honest ``total_count`` (never an empty proof of absence); a
        zero-hit first page may repair the sole dirty indexed file, and several dirty files yield
        empty ``index_stale`` plus ``try_instead`` (073). Stub-indexed nodes carry ``stub: true``
        (039); a ``File`` hit that only restates a ``Class`` hit's declaring file in the same page
        is suppressed — request File rows via ``kind`` (061).
        """
        subjects = _require_subjects(query, queries)
        batched = queries is not None
        kind = _require_kind(kind)
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap, limit_clamped = clamp_limit(limit, config.max_results)
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
                    store, guard, subject, kind=kind, namespace=namespace, cap=cap, offset=offset
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
            )
        answers = [
            _batch_answer(subject, hits) for subject, hits in zip(kept, found, strict=True)
        ]
        payload = batch_result(answers, index_root=index_root)
        attach_limit_capped(payload, cap=cap, clamped=limit_clamped)
        attach_subjects_capped(payload, cap=config.max_subjects, dropped=dropped)
        # A swept miss is the same 8-A shape as a single one: name the coverage gap once on the
        # envelope (call-level, never per subject — 061) when any subject came back a genuine zero
        # or a substring near-miss — the sweep path is the one 160's AC1e showed gets missed (167).
        if any(
            (not a["results"] and a["reason"] == REASON_NO_MATCHES)
            or a["reason"] == REASON_SUBSTRING_MATCH
            for a in answers
        ):
            attach_coverage_gap(payload, config, covered)
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
) -> _Hits:
    """One subject's search, verdict included — the same path a single call has always taken."""
    rows = store.search_nodes(query, kind=kind, namespace=namespace, limit=cap + 1, offset=offset)
    hit_paths = [str(row["file_path"]) for row in rows[:cap]]
    status = guard.ensure_paths(hit_paths)
    # Zero hits never yield hit paths — miss-repair the sole dirty indexed file (073).
    # First page only: an empty page past the end is not an empty answer (057).
    if not rows and offset == 0 and status == "ok":
        status = guard.ensure_miss()
    # Re-query only when a repair may have changed FTS/rows.
    if status == "repaired" or (status == "stale" and guard.used > 0):
        rows = store.search_nodes(
            query, kind=kind, namespace=namespace, limit=cap + 1, offset=offset
        )
    truncated = len(rows) > cap
    results = _suppress_redundant_file_hits([_hit(row) for row in rows[:cap]])
    if truncated or offset > 0:
        total_count = store.count_search_nodes(query, kind=kind, namespace=namespace)
        truncated = offset + len(results) < total_count
    else:
        total_count = len(results)
    if status == "stale":
        reason: NavReason = REASON_INDEX_STALE
    elif total_count == 0:
        # Page emptiness ≠ answer emptiness once offset can walk past the end (057).
        reason = REASON_NO_MATCHES
    elif offset == 0 and not any(_is_direct_match(query, row) for row in rows[:cap]):
        # First page holds only substring/trigram near-misses — not a confident hit (167).
        reason = REASON_SUBSTRING_MATCH
    else:
        reason = REASON_OK
    return _Hits(results, truncated, reason, total_count)


def _is_direct_match(query: str, row: Mapping[str, object] | Row) -> bool:
    """True when the query is an exact match or a prefix of the row's name or qname (167).

    Case-insensitive and language-agnostic (R1.1): a run of the query against the symbol the search
    returned, no SQL. Everything else is a substring / trigram near-miss.
    """
    q = query.casefold()
    name = str(row["name"]).casefold()
    if name == q or name.startswith(q):
        return True
    qname = str(row["qualified_name"]).casefold()
    return qname == q or qname.startswith(q)


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
    attach_limit_capped(payload, cap=cap, clamped=limit_clamped)
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
    if hits.reason == REASON_INDEX_STALE and hits.total_count == 0:
        attach_try_instead(answer, TRY_INSTEAD_FILE_OUTLINE)
    return answer


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


def _hit(row: Mapping[str, object] | Row) -> dict[str, object]:
    hit: dict[str, object] = {}
    hit["qname"] = row["qualified_name"]
    hit["kind"] = row["kind"]
    hit["file"] = row["file_path"]
    hit["line"] = row["line_start"]
    if is_stub(row.get("extra")):
        hit[contract.STUB_FLAG] = True
    return hit
