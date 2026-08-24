"""Shared hit shaping for navigation tools (§12) — qname/path + file:line + tier, never bodies."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any, Literal, NamedTuple

from code_atlas import contract
from code_atlas.contract import CONFIDENCE_TIERS
from code_atlas.enrichment import is_rule_edge_kind, is_rule_edge_path
from code_atlas.store import GraphStore, Row

_RESOLVED = CONFIDENCE_TIERS[0]

NavReason = Literal[
    "ok",
    "no_matches",
    "no_such_symbol",
    "not_indexed",
    "index_stale",
    "bare_name_truncated",
    "relationship_not_modelled",
    "capability_not_configured",
    "name_not_qualified",
    "subject_ambiguous",
    "rule_matched_no_files",
]

REASON_OK: NavReason = "ok"
REASON_NO_MATCHES: NavReason = "no_matches"
REASON_NO_SUCH_SYMBOL: NavReason = "no_such_symbol"
REASON_NOT_INDEXED: NavReason = "not_indexed"
REASON_INDEX_STALE: NavReason = "index_stale"  # vocabulary for 035; not emitted by 033
REASON_BARE_NAME_TRUNCATED: NavReason = "bare_name_truncated"
REASON_RELATIONSHIP_NOT_MODELLED: NavReason = "relationship_not_modelled"
# The tool's capability needs config that is absent — inert, not a genuine zero (069).
REASON_CAPABILITY_NOT_CONFIGURED: NavReason = "capability_not_configured"
# The subject is under-qualified: N indexed symbols end with it — ask a narrower question (075/076).
REASON_NAME_NOT_QUALIFIED: NavReason = "name_not_qualified"
# The subject qname has >1 definition — refuse a single-site body (078).
REASON_SUBJECT_AMBIGUOUS: NavReason = "subject_ambiguous"
# Every declared rule matched no file on one side, so nothing was checked — not a clean pass (138).
REASON_RULE_MATCHED_NO_FILES: NavReason = "rule_matched_no_files"

NAV_REASONS: tuple[NavReason, ...] = (
    REASON_OK,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_NOT_INDEXED,
    REASON_INDEX_STALE,
    REASON_BARE_NAME_TRUNCATED,
    REASON_RELATIONSHIP_NOT_MODELLED,
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_NAME_NOT_QUALIFIED,
    REASON_SUBJECT_AMBIGUOUS,
    REASON_RULE_MATCHED_NO_FILES,
)

# Two registers, one naming rule (093): ``TRY_INSTEAD_*`` is a registered tool name the reader can
# call, ``TRY_INSTEAD_HINT_*`` is prose naming the qualifier. Neither holds the other's kind — prose
# in the identifier slot makes every value ambiguous. Pinned by the invariant test.
# Machine-stable alternate routes when reason is relationship_not_modelled (task 065).
# The route must MAKE PROGRESS, not just resolve: routing a tool back to itself loops for the
# mechanical reader this field exists for, so the class-level miss routes to the enumerator.
TRY_INSTEAD_HINT_METHOD_QNAME = (
    "list the class's methods, then re-ask find_references with a method qname "
    "(Class::method) — the class-level reference is not modelled"
)
# Empty miss while multiple indexed files are dirty — path-named tools are stronger (073).
TRY_INSTEAD_FILE_OUTLINE = "file_outline"
# An under-qualified subject has candidates — search_symbol enumerates them (075/076).
TRY_INSTEAD_SEARCH_SYMBOL = "search_symbol"
# No route on purpose: the evidence is unlinked include TEXT (edges.target_raw) and no registered
# tool reads it — nodes_fts covers name/qname/file_path/params only. A route here would answer
# reason=ok with symbols declared IN the file, silently omitting the includer (075/076).
TRY_INSTEAD_HINT_PATH_BASENAME = (
    "no indexed tool answers this — the include path is bare or dynamic, so search the file's "
    "basename as text outside the index"
)
# Untracked indexable file — rebuild after git add (092). Real tool name; hint is sibling.
TRY_INSTEAD_BUILD_OR_UPDATE_INDEX = "build_or_update_index"
TRY_INSTEAD_HINT_UNTRACKED = "git add the untracked file, then rebuild"


def edge_id(edge: Mapping[str, Any] | Row) -> int:
    """Integer primary key of an edge row — fails loud on a bad shape."""
    raw = edge["id"]
    if not isinstance(raw, int):
        raise TypeError(f"edge id must be int, got {type(raw).__name__}")
    return raw


def edge_hit(
    edge: Mapping[str, Any] | Row,
    *,
    depth: int | None = None,
    subject: str | None = None,
    subject_key: str = "qname",
) -> dict[str, object]:
    """One relationship hit.

    Default subject is the edge's ``source_qname`` under key ``qname`` (callers / refs / impls).
    ``include_graph`` passes the neighbor path with ``subject_key="path"``.
    """
    hit: dict[str, object] = {}
    hit[subject_key] = edge["source_qname"] if subject is None else subject
    if is_rule_edge_path(edge.get("file_path")) or is_rule_edge_kind(edge.get("kind")):
        # Synthetic bookmark — not an on-disk path. Advertise ``rule``; omit file (task 040).
        # PROVIDES_VIEW_DATA keeps ``line`` (call-site line on the handler — task 062).
        hit[contract.RULE_FLAG] = True
        hit["kind"] = edge["kind"]
        hit["confidence_tier"] = edge.get("confidence_tier") or _RESOLVED
        if edge.get("kind") == contract.PROVIDES_VIEW_DATA and type(edge.get("line")) is int:
            hit["line"] = edge["line"]
        if depth is not None:
            hit["depth"] = depth
        return hit
    hit["file"] = edge["file_path"]
    hit["line"] = edge["line"]
    hit["kind"] = edge["kind"]
    hit["confidence_tier"] = edge.get("confidence_tier") or _RESOLVED
    if depth is not None:
        hit["depth"] = depth
    return hit


def empty_nav(
    subject: str,
    *,
    detail_level: str,
    index_root: str,
    db_path: str = "",
    subject_key: str = "qname",
    reason: NavReason = REASON_NOT_INDEXED,
    total_count: int = 0,
) -> dict[str, object]:
    """No database yet — read tools must not create one.

    ``db_path`` is accepted for call-site stability but never attached (task 061).
    ``index_root`` is the source tree the server was configured with (task 071).
    """
    del detail_level, db_path
    return {
        "indexed": False,
        subject_key: subject,
        "results": [],
        "truncated": False,
        "reason": reason,
        "total_count": total_count,
        "index_root": index_root,
    }


def nav_result(
    subject: str,
    results: list[dict[str, object]],
    *,
    detail_level: str,
    index_root: str,
    db_path: str = "",
    truncated: bool,
    reason: NavReason | None = None,
    total_count: int | None = None,
    subject_key: str = "qname",
    **extra: object,
) -> dict[str, object]:
    """Shape a nav payload; omit ``reason`` / ``total_count`` unless explicitly set.

    ``db_path`` is accepted but never attached — use ``get_index_status`` (task 061).
    ``index_root`` always ships so a caller can compare against its own cwd (task 071).
    """
    del detail_level, db_path
    extra.pop("db_path", None)
    payload: dict[str, object] = {
        "indexed": True,
        subject_key: subject,
        "results": results,
        "truncated": truncated,
        "index_root": index_root,
        **extra,
    }
    if reason is not None:
        payload["reason"] = reason
    if total_count is not None:
        payload["total_count"] = total_count
    return payload


def list_result(
    results: list[dict[str, object]],
    *,
    detail_level: str,
    index_root: str,
    db_path: str = "",
    truncated: bool,
    reason: NavReason,
    total_count: int,
    indexed: bool = True,
) -> dict[str, object]:
    """Search-style payload — same reason/total_count fields, no subject key."""
    del detail_level, db_path
    return {
        "indexed": indexed,
        "results": results,
        "truncated": truncated,
        "reason": reason,
        "total_count": total_count,
        "index_root": index_root,
    }


def subject_answer(
    query: str,
    results: list[dict[str, object]],
    *,
    truncated: bool,
    reason: NavReason,
    total_count: int,
) -> dict[str, object]:
    """One subject's own answer inside a batch (task 101).

    Carries no ``indexed`` / ``index_root``: those are facts about the call, and repeating them
    once per subject is the boilerplate 061 forbids. Every field here varies per subject, so one
    miss among ten cannot colour the other nine.
    """
    answer: dict[str, object] = {}
    answer["query"] = query
    answer["results"] = results
    answer["truncated"] = truncated
    answer["reason"] = reason
    answer["total_count"] = total_count
    return answer


def batch_result(
    answers: list[dict[str, object]], *, index_root: str
) -> dict[str, object]:
    """The batch envelope — what is true of the whole call, stated once (task 101; 061).

    ``subjects`` keeps the caller's order and is never deduped or merged: answer *i* answers
    subject *i*. A merged set would re-create 070's defect at batch scale (R4.2).
    """
    payload: dict[str, object] = {}
    payload["indexed"] = True
    payload["subject_count"] = len(answers)
    payload["subjects"] = answers
    payload["index_root"] = index_root
    return payload


def batch_not_indexed(index_root: str) -> dict[str, object]:
    """No index yet, answered once for the whole sweep (task 101).

    Ships no ``subjects`` list on purpose — the same reason ``schema_guard.payload`` ships no
    empty ``results``: N identical empty answers read as N proofs of absence (061).
    """
    payload: dict[str, object] = {}
    payload["indexed"] = False
    payload["reason"] = REASON_NOT_INDEXED
    payload["index_root"] = index_root
    return payload


def attach_subjects_capped(
    payload: dict[str, object], *, cap: int, dropped: Sequence[str]
) -> dict[str, object]:
    """Name the subjects the fan-out bound refused — only when it refused some (066/061; 101).

    The list carries both halves of the disclosure: its length is how many were dropped, its items
    are which. A sweep exists to be complete, so a silent truncation is worse than ten honest calls.
    """
    if dropped:
        payload["subjects_capped_to"] = cap
        payload["subjects_dropped"] = list(dropped)
    return payload


def relation_reason(*, hit_total: int, symbol_indexed: bool) -> NavReason:
    """Classify find_* after counting edges: hits / empty indexed / unknown qname."""
    if hit_total > 0:
        return REASON_OK
    if not symbol_indexed:
        return REASON_NO_SUCH_SYMBOL
    return REASON_NO_MATCHES


# Generic identifier lexis — NOT a language branch (no `if language`); the same tolerance the
# read_symbol comment regex already relies on. A qname component is a run of these chars.
_IDENT_TRAILING = re.compile(r"[A-Za-z0-9_]+$")
_IDENT_CHAR = re.compile(r"[A-Za-z0-9_]")


class SubjectResolution(NamedTuple):
    """How a subject qname the index has no exact node for classifies (miss path only)."""

    status: str  # "absent" | "resolved_unique" | "ambiguous" | "untracked"
    qname: str  # the stored qname to use downstream when resolved_unique; else the input
    candidate_count: int  # boundary-suffix candidate floor (0 when absent)
    untracked_paths: tuple[str, ...] = ()


def classify_missing_subject(
    store: GraphStore, qname: str, *, limit: int
) -> SubjectResolution:
    """Classify a subject the index holds no exact node for, without any language-specific rule.

    Counts indexed qnames that end with ``qname`` at a component boundary — so a leading-anchor
    difference (``Ns\\Sub\\Enum`` vs ``\\Ns\\Sub\\Enum``) resolves as one candidate, and a bare
    member name (``isEnabled``) surfaces as many. Runs on the miss path only (a hit never pays).
    An exact miss that maps to a stored untracked indexable path is ``untracked`` (task 092).
    """
    trailing = _IDENT_TRAILING.search(qname)
    if trailing is None:
        return SubjectResolution("absent", qname, 0)
    candidates = store.nodes_by_qname_endswith(trailing.group(0), qname, limit=limit + 1)
    matches = [
        str(row["qualified_name"])
        for row in candidates
        if _ends_at_boundary(str(row["qualified_name"]), qname)
    ]
    if matches:
        if len(matches) == 1:
            return SubjectResolution("resolved_unique", matches[0], 1)
        return SubjectResolution("ambiguous", qname, len(matches))
    untracked = _matching_untracked(store.untracked_indexable_paths(), qname)
    if untracked:
        return SubjectResolution("untracked", qname, 0, untracked)
    return SubjectResolution("absent", qname, 0)


def _matching_untracked(paths: Sequence[str], qname: str) -> tuple[str, ...]:
    """Untracked files whose stem matches the subject's type-part ident or path stem (092)."""
    keys = _untracked_match_keys(qname)
    if not keys:
        return ()
    return tuple(path for path in paths if PurePosixPath(path).stem in keys)


def _untracked_match_keys(qname: str) -> frozenset[str]:
    # A path-shaped subject matches on its stem only: its trailing ident is the file
    # extension, and ``Foo.aa`` must not match an untracked ``aa.aa`` (092).
    container, _member = contract.split_qname(qname)
    hay = container or qname
    as_path = PurePosixPath(hay)
    if as_path.suffix and as_path.stem:
        return frozenset({as_path.stem})
    trailing = _IDENT_TRAILING.search(hay)
    return frozenset({trailing.group(0)}) if trailing is not None else frozenset()


def _ends_at_boundary(stored: str, suffix: str) -> bool:
    """``stored`` ends with ``suffix`` and the char before it (if any) is a non-identifier."""
    if not stored.endswith(suffix):
        return False
    prefix = stored[: len(stored) - len(suffix)]
    return prefix == "" or _IDENT_CHAR.match(prefix[-1]) is None


def unique_repoint(resolution: SubjectResolution) -> str | None:
    """Stored qname when a miss uniquely resolved; else None (shape the miss)."""
    if resolution.status == "resolved_unique":
        return resolution.qname
    return None


def attach_resolved_qname(
    payload: dict[str, object], *, asked: str, answered: str
) -> dict[str, object]:
    """Disclose the stored qname only when it differs from what the caller typed (061/075)."""
    if answered != asked:
        payload["resolved_qname"] = answered
    return payload


def attach_name_not_qualified(
    payload: dict[str, object], candidate_count: int
) -> dict[str, object]:
    """Disclose the under-qualified candidate floor + the route out (061 conditional; 066 bound)."""
    payload["candidate_count"] = candidate_count
    payload["try_instead"] = TRY_INSTEAD_SEARCH_SYMBOL
    return payload


def attach_try_instead(
    payload: dict[str, object], try_instead: str | None, hint: str | None = None
) -> dict[str, object]:
    """Attach the callable route, and the hint saying how to re-ask. Each omitted when unset (061).

    A hint may stand ALONE: when no registered tool can answer, naming a tool that cannot is worse
    than naming none — the reader spends a call and gets a confident wrong answer (075/076).
    """
    if try_instead:
        payload["try_instead"] = try_instead
    if hint:
        payload["try_instead_hint"] = hint
    return payload


def attach_untracked_not_indexed(
    payload: dict[str, object], paths: Sequence[str]
) -> dict[str, object]:
    """An index exists but this subject lives in an untracked file (task 092; 061 omit-empty)."""
    payload["reason"] = REASON_NOT_INDEXED
    payload["try_instead"] = TRY_INSTEAD_BUILD_OR_UPDATE_INDEX
    payload["try_instead_hint"] = TRY_INSTEAD_HINT_UNTRACKED
    if len(paths) == 1:
        payload["untracked_path"] = paths[0]
    elif paths:
        payload["untracked_paths"] = list(paths)
    return payload


def shape_exact_miss(
    miss: dict[str, object], resolution: SubjectResolution
) -> dict[str, object]:
    """Fill an exact-miss payload from the classifier (075/076/092/122).

    ``resolved_unique`` is not under-qualified — callers re-point onto ``resolution.qname``.
    """
    if resolution.status == "untracked":
        return attach_untracked_not_indexed(miss, resolution.untracked_paths)
    if resolution.status == "resolved_unique":
        asked = miss.get("qname")
        asked_qname = asked if isinstance(asked, str) else resolution.qname
        return attach_resolved_qname(miss, asked=asked_qname, answered=resolution.qname)
    if resolution.candidate_count:
        miss["reason"] = REASON_NAME_NOT_QUALIFIED
        return attach_name_not_qualified(miss, resolution.candidate_count)
    miss["reason"] = REASON_NO_SUCH_SYMBOL
    return miss


def attach_limit_capped(
    payload: dict[str, object], *, cap: int, clamped: bool
) -> dict[str, object]:
    """Report a reduced ``limit`` as ``limit_capped_to`` — only when a clamp occurred (066/061).

    The effective cap tells a caller their request was reduced and to what, without a config
    read. Omitted when the request was honoured, keeping the non-clamp payload unchanged.
    """
    if clamped:
        payload["limit_capped_to"] = cap
    return payload


def attach_result_subtrees(
    payload: dict[str, object], subtrees: Mapping[str, int]
) -> dict[str, object]:
    """Advertise the full result's top-level subtrees when a page hides some (task 067).

    Attached only when the set spans >1 subtree; otherwise a one-page reader sees the whole
    spread anyway and the field would only add tokens. Callers gate on ``truncated`` first.
    """
    if len(subtrees) > 1:
        payload["result_subtrees"] = dict(subtrees)
    return payload


def attach_result_kinds(
    payload: dict[str, object], kinds: Mapping[str, int]
) -> dict[str, object]:
    """Advertise the full file's symbol-kind spread when a page hides some (task 123).

    Same 067/061 contract as ``attach_result_subtrees``: only when >1 kind, and callers
    gate on ``truncated`` first so a one-page reader never pays for a redundant field.
    """
    if len(kinds) > 1:
        payload["result_kinds"] = dict(kinds)
    return payload


AMBIGUOUS_DEFINITIONS = "ambiguous_definitions"


def definition_sites(rows: list[Row]) -> list[dict[str, object]]:
    """Shape definition nodes into ``{file, line, kind}`` sites, in ``_NODE_ORDER`` (R4).

    ``stub: true`` is attached per site only when set (039 / 078) — omitted otherwise (061).
    """
    sites: list[dict[str, object]] = []
    for row in rows:
        # One key per statement — R3.2 sole-source gate forbids a vocabulary dict literal.
        site: dict[str, object] = {}
        site["file"] = row["file_path"]
        site["line"] = row["line_start"]
        site["kind"] = row["kind"]
        if is_stub(row.get("extra")):
            site[contract.STUB_FLAG] = True
        sites.append(site)
    return sites


def attach_ambiguous_definitions(
    payload: dict[str, object], sites: list[dict[str, object]]
) -> dict[str, object]:
    """Warn the subject qname is non-unique — attached only when >1 (task 070; 061 conditional).

    Absent for a unique qname, so that payload is byte-identical to before. The list names every
    definition site and never picks one (R4) — binding may be load-order dependent. Body-returning
    tools must not ship ``source``/site fields alongside this list (078).
    """
    if len(sites) > 1:
        payload[AMBIGUOUS_DEFINITIONS] = sites
    return payload


def is_stub(raw: object) -> bool:
    """True when a node's ``extra`` JSON carries the stub marker (task 039)."""
    if not isinstance(raw, str) or not raw.strip():
        return False
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return isinstance(data, dict) and data.get(contract.STUB_FLAG) is True
