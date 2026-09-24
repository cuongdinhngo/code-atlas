"""Shared hit shaping for navigation tools (§12) — qname/path + file:line + tier, never bodies."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath
from typing import Any, Literal, NamedTuple

from code_atlas import contract
from code_atlas.build_info import maybe_server_provenance, server_provenance
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
    "index_behind",
    "index_behind_subject_changed",
    "bare_name_truncated",
    "relationship_not_modelled",
    "capability_not_configured",
    "name_not_qualified",
    "subject_ambiguous",
    "rule_matched_no_files",
    "no_architectural_change",
    "index_root_mismatch",
    "dataset_schema_mismatch",
    "incomplete_snapshot",
    "snapshot_not_found",
    "substring_match",
    "relation_unmodelled_for_language",
    "subject_file_checked",
    "separator_normalised",
    "token_candidates",
    "via_members",
    "proximity_candidates",
    "kind_excluded",
    "path_excluded",
]

REASON_OK: NavReason = "ok"
REASON_NO_MATCHES: NavReason = "no_matches"
REASON_NO_SUCH_SYMBOL: NavReason = "no_such_symbol"
REASON_NOT_INDEXED: NavReason = "not_indexed"
REASON_INDEX_STALE: NavReason = "index_stale"  # vocabulary for 035; not emitted by 033
# Opt-in labelled read from a behind index for unchanged subjects (257) — never reason=ok.
REASON_INDEX_BEHIND: NavReason = "index_behind"
REASON_INDEX_BEHIND_SUBJECT_CHANGED: NavReason = "index_behind_subject_changed"
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
# 139's snapshot diff: nothing moved, or the two sides cannot be compared at all.
REASON_NO_ARCHITECTURAL_CHANGE: NavReason = "no_architectural_change"
REASON_INDEX_ROOT_MISMATCH: NavReason = "index_root_mismatch"
REASON_DATASET_SCHEMA_MISMATCH: NavReason = "dataset_schema_mismatch"
REASON_INCOMPLETE_SNAPSHOT: NavReason = "incomplete_snapshot"
REASON_SNAPSHOT_NOT_FOUND: NavReason = "snapshot_not_found"
# search_symbol matched only as a substring/trigram — no result is an exact or prefix match, so a
# near-miss (`storeCRM` → `restoreCRM`) is not a confident hit (167). Carries the 160 coverage note.
REASON_SUBSTRING_MATCH: NavReason = "substring_match"
# Empty because this file's LANGUAGE emitted none of the kinds the tool reads — read from the
# index's own per-language stamp, never from a language name (R1.1, 186). Distinct from
# relationship_not_modelled, which needs unlinked evidence a second language never produces.
REASON_RELATION_UNMODELLED_FOR_LANGUAGE: NavReason = "relation_unmodelled_for_language"
# Miss after the subject's indexed file was checked (246): weaker than clean-tree absence;
# ``other_indexed_files_drifted`` names how many unrelated indexed files also drifted.
REASON_SUBJECT_FILE_CHECKED: NavReason = "subject_file_checked"
# Primary miss; hit only after spelling the last separator as MEMBER_SEPARATOR (249). Near-miss —
# never reason=ok: the agent asked for a name that is not in the graph (R5.6 / R5.2).
REASON_SEPARATOR_NORMALISED: NavReason = "separator_normalised"
# Zero-overlap miss: token decomposition ran over declared names (253). Candidates never enter
# ``results`` / ``total_count`` (R5.6); empty ``candidates`` still means the search ran.
REASON_TOKEN_CANDIDATES: NavReason = "token_candidates"
# Class-level find_references with no modelled class REFERENCES: union of CALLS/NEW
# targeting the subject's CONTAINS children. Never reason=ok — the class-ref relation
# is not in the graph (R5.6 / 252).
REASON_VIA_MEMBERS: NavReason = "via_members"
# Unresolved same-named CALL sites ranked by proximity (258). The rows are candidates the
# resolver declined to link, not measured callers, so never reason=ok — the 252 rule applied
# to the other query-time expansion (R5.6).
REASON_PROXIMITY_CANDIDATES: NavReason = "proximity_candidates"
# search_symbol kind= filter excluded an exact-name hit of another kind (275) — not absence.
REASON_KIND_EXCLUDED: NavReason = "kind_excluded"
# search_symbol path_prefix= filter excluded an exact-name hit outside the subtree (315).
REASON_PATH_EXCLUDED: NavReason = "path_excluded"

NAV_REASONS: tuple[NavReason, ...] = (
    REASON_OK,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_NOT_INDEXED,
    REASON_INDEX_STALE,
    REASON_INDEX_BEHIND,
    REASON_INDEX_BEHIND_SUBJECT_CHANGED,
    REASON_BARE_NAME_TRUNCATED,
    REASON_RELATIONSHIP_NOT_MODELLED,
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_NAME_NOT_QUALIFIED,
    REASON_SUBJECT_AMBIGUOUS,
    REASON_RULE_MATCHED_NO_FILES,
    REASON_NO_ARCHITECTURAL_CHANGE,
    REASON_INDEX_ROOT_MISMATCH,
    REASON_DATASET_SCHEMA_MISMATCH,
    REASON_INCOMPLETE_SNAPSHOT,
    REASON_SNAPSHOT_NOT_FOUND,
    REASON_SUBSTRING_MATCH,
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
    REASON_SUBJECT_FILE_CHECKED,
    REASON_SEPARATOR_NORMALISED,
    REASON_TOKEN_CANDIDATES,
    REASON_VIA_MEMBERS,
    REASON_PROXIMITY_CANDIDATES,
    REASON_KIND_EXCLUDED,
    REASON_PATH_EXCLUDED,
)

def require_path_prefix(path_prefix: str | None) -> str | None:
    """Reject malformed ``path_prefix`` before any SQL (R5.3 / 056 / 315).

    Accepted form: non-empty, index-root-relative, POSIX (``/`` separators), no ``.`` or ``..``
    segments. ``None`` means no filter.
    """
    if path_prefix is None:
        return None
    if path_prefix == "" or "\0" in path_prefix:
        raise ValueError(
            "path_prefix must be a non-empty index-root-relative POSIX path"
        )
    if "\\" in path_prefix:
        raise ValueError("path_prefix must be POSIX (use '/', not '\\')")
    if path_prefix.startswith("/"):
        raise ValueError("path_prefix must be index-root-relative (not absolute)")
    parts = [part for part in path_prefix.split("/") if part != ""]
    if any(part in (".", "..") for part in parts):
        raise ValueError("path_prefix must not contain '.' or '..' segments")
    return path_prefix


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
# The near-miss sibling (245): a different finding and a different re-ask, so a different hint —
# the reuse rule bans a second spelling of the SAME advice, not a second advice.
TRY_INSTEAD_HINT_NARROW_BY_QNAME = (
    "the page is substring near-misses, not hits — outline the file to read the exact qnames, "
    "then re-ask search_symbol with one of them"
)
# Separator spelling miss (249): different finding from substring flood, so a different hint —
# the reuse rule bans a second spelling of the SAME advice, not a second advice (245 review).
TRY_INSTEAD_HINT_TOKEN_CANDIDATES = (
    "guessed name shared no substring with a declared symbol; candidates list name tokens that did "
    "match — retry search_symbol with one of those qnames"
)
TRY_INSTEAD_HINT_TOKEN_CANDIDATES_NONE = (
    "guessed name shared no substring with a declared symbol; token search over declared names "
    "also found none — the concept may be absent under any declared name"
)
TRY_INSTEAD_HINT_MEMBER_SEPARATOR = (
    "the member join is ::, not a container separator — outline the file for exact qnames, "
    "or re-ask with :: before the last segment"
)
# Empty miss while multiple indexed files are dirty — path-named tools are stronger (073).
TRY_INSTEAD_FILE_OUTLINE = "file_outline"
# An under-qualified subject has candidates — search_symbol enumerates them (075/076).
TRY_INSTEAD_SEARCH_SYMBOL = "search_symbol"
# Ambiguous read — progress is the same tool with path_prefix, not search_symbol (327 / R5.4).
TRY_INSTEAD_READ_SYMBOL = "read_symbol"
TRY_INSTEAD_HINT_PATH_PREFIX = (
    "several definitions share this qname — re-ask read_symbol with path_prefix= naming "
    "one site from ambiguous_definitions"
)
# No route on purpose: the evidence is unlinked include TEXT (edges.target_raw) and no registered
# tool reads it — nodes_fts covers name/qname/file_path/params only. A route here would answer
# reason=ok with symbols declared IN the file, silently omitting the includer (075/076).
TRY_INSTEAD_HINT_PATH_BASENAME = (
    "no indexed tool answers this — the include path is bare or dynamic, so search the file's "
    "basename as text outside the index"
)
# No route ON PURPOSE (R5.4 clause c, measured in 186): where the subject's language emits none
# of the kinds a tool reads, no registered tool enumerates the relation either — find_references
# on such a file answers relationship_not_modelled with zero rows. Naming it would be worse.
# 314: name a concrete Grep/loader fallback so honesty is actionable (AC3).
TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE = (
    "this file's language records the dependency under a different edge kind, and no indexed tool "
    "enumerates it — treat the empty answer as unmeasured, not as zero; Grep the subject as text "
    "outside the index, or use the runtime's own loader"
)
# Coverage-edge zeros (314): stamp / gap present — Grep, never a synthetic symbol (R5.2 / 093).
TRY_INSTEAD_HINT_DYNAMIC_SQL = (
    "indexed files stamp dynamic_sql — the name may exist only inside EXEC/sp_executesql text; "
    "Grep the query as literal text outside the index"
)
TRY_INSTEAD_HINT_RESOLUTION_UNMODELLED = (
    "indexed languages stamp unmodelled resolution strategies — Grep the subject as text "
    "outside the index, or use the runtime's own loader"
)
TRY_INSTEAD_HINT_OUTSIDE_COVERAGE = (
    "the index does not cover every configured language — Grep the subject as text outside "
    "the index for sites in an unindexed language"
)
# 188 made a route exist where 186 measured none: the resolver now links a module `IMPORTS` to the
# file it names, so `find_references` enumerates from the File qname `include_graph` already holds.
# Emitted only where the subject's language really does emit the carrying kind (R5.4 clause c).
TRY_INSTEAD_FIND_REFERENCES = "find_references"
TRY_INSTEAD_HINT_RELATION_CARRIED_BY_ANOTHER_KIND = (
    "this file's language records the dependency under IMPORTS, not INCLUDES — re-ask "
    "find_references with this file's path as the qname"
)
# Untracked indexable file — rebuild after git add (092). Real tool name; hint is sibling.
TRY_INSTEAD_BUILD_OR_UPDATE_INDEX = "build_or_update_index"
TRY_INSTEAD_HINT_UNTRACKED = "git add the untracked file, then rebuild"
# Sweep stale under a shared repair budget: retry alone so this subject gets the whole cap (275).
TRY_INSTEAD_HINT_SINGLE_SUBJECT_REPAIR = (
    "retry as query=<this subject> alone to spend the full repair budget on it"
)
RETRY_AS_QUERY = "query"
RETRY_AS_FIELD = "retry_as"
# Caller stale refusal: progress is the opt-in param, not another tool (274 / R5.4).
SERVE_BEHIND_OPT_IN = "serve_behind"
SERVE_BEHIND_OPT_IN_FIELD = "serve_behind_opt_in"
TRY_INSTEAD_HINT_SERVE_BEHIND = (
    "pass serve_behind=true to answer from the built revision (labelled, not ok)"
)
# A twinned path seed is refused, not answered — but a refusal with no route is the carve-out this
# repo keeps re-learning about (065, 171). The qname seed is the half 161 already made safe.
TRY_INSTEAD_HINT_IMPACT_BY_QNAME = (
    "name one symbol from the file and re-run impact with qnames=[...]; the qname seed "
    "resolves a shared name instead of walking both (161)"
)

# A successful body read of a callable symbol earns the next mechanism step at the moment of cost
# (158): who calls it, what breaks if it changes. Registered tool names (093), asserted callable by
# the invariant test. Literals, not imports: the tool modules import THIS module (no cycle).
NEXT_TOOLS_FOR_CALLABLE: tuple[str, ...] = ("find_callers", "impact")
# Class / Interface — the roster step the round-26 retro walked past (285 / 158).
NEXT_TOOLS_FOR_TYPE: tuple[str, ...] = ("find_implementations",)


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


ANSWERED_ABOUT_REF_FIELD = "answered_about_ref"


def attach_answered_about_ref(
    payload: dict[str, object], answered_about_ref: str | None
) -> dict[str, object]:
    """Stamp the index's built-on ref on every nav envelope (317). Single attach site (R6.7)."""
    payload[ANSWERED_ABOUT_REF_FIELD] = answered_about_ref
    return payload


def answered_about_ref_for(store: GraphStore | None) -> str | None:
    """``last_ref`` the index holds (077), or ``None`` when unbuilt / pre-077 omit."""
    if store is None:
        return None
    from code_atlas.tools.staleness import OMIT, last_ref_for_payload

    ref = last_ref_for_payload(store)
    if ref is OMIT or ref is None:
        return None
    return str(ref)


def empty_nav(
    subject: str,
    *,
    detail_level: str,
    index_root: str,
    db_path: str = "",
    subject_key: str = "qname",
    reason: NavReason = REASON_NOT_INDEXED,
    total_count: int = 0,
    answered_about_ref: str | None = None,
) -> dict[str, object]:
    """No database yet — read tools must not create one.

    ``db_path`` is accepted for call-site stability but never attached (task 061).
    ``index_root`` is the source tree the server was configured with (task 071).
    ``answered_about_ref`` names the index's built-on ref when known (317 / 077).
    """
    del db_path
    return attach_answered_about_ref(
        {
            "indexed": False,
            subject_key: subject,
            "results": [],
            "truncated": False,
            "reason": reason,
            "total_count": total_count,
            "index_root": index_root,
            **maybe_server_provenance(detail_level),
        },
        answered_about_ref,
    )


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
    answered_about_ref: str | None = None,
    **extra: object,
) -> dict[str, object]:
    """Shape a nav payload; omit ``reason`` / ``total_count`` unless explicitly set.

    ``db_path`` is accepted but never attached — use ``get_index_status`` (task 061).
    ``index_root`` always ships so a caller can compare against its own cwd (task 071).
    ``minimal`` omits ``server_*`` — identity rides ``get_index_status`` (223).
    """
    del db_path
    extra.pop("db_path", None)
    extra.pop("answered_about_ref", None)
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
    payload.update(maybe_server_provenance(detail_level))
    return attach_answered_about_ref(payload, answered_about_ref)


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
    answered_about_ref: str | None = None,
) -> dict[str, object]:
    """Search-style payload — same reason/total_count fields, no subject key."""
    del db_path
    return attach_answered_about_ref(
        {
            "indexed": indexed,
            "results": results,
            "truncated": truncated,
            "reason": reason,
            "total_count": total_count,
            "index_root": index_root,
            **maybe_server_provenance(detail_level),
        },
        answered_about_ref,
    )


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
    answers: list[dict[str, object]],
    *,
    index_root: str,
    answered_about_ref: str | None = None,
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
    payload.update(server_provenance())
    return attach_answered_about_ref(payload, answered_about_ref)


def batch_not_indexed(
    index_root: str, *, answered_about_ref: str | None = None
) -> dict[str, object]:
    """No index yet, answered once for the whole sweep (task 101).

    Ships no ``subjects`` list on purpose — the same reason ``schema_guard.payload`` ships no
    empty ``results``: N identical empty answers read as N proofs of absence (061).
    """
    payload: dict[str, object] = {}
    payload["indexed"] = False
    payload["reason"] = REASON_NOT_INDEXED
    payload["index_root"] = index_root
    payload.update(server_provenance())
    return attach_answered_about_ref(payload, answered_about_ref)


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


def unmeasured_inbound_for_subject(
    store: GraphStore,
    *,
    subject_kind: str,
    raws: Sequence[str],
    kinds: Sequence[str] | None = None,
) -> list[str]:
    """Unlinked inbound kinds for ``subject_kind`` against ``raws`` (264).

    Default ``kinds`` come from ``inbound_kinds_for``. Callers may pass a narrower set
    (e.g. REFERENCES/IMPORTS with a bare-name raw) for a tool-specific earlier arm.
    """
    use = tuple(kinds) if kinds is not None else contract.inbound_kinds_for(subject_kind)
    cleaned = tuple(raw for raw in raws if raw)
    if not use or not cleaned:
        return []
    return store.unlinked_kinds_by_target_raw(cleaned, kinds=use)


def apply_empty_inbound_honesty(
    reason: NavReason,
    store: GraphStore,
    *,
    subject_kind: str,
    raws: Sequence[str],
    kinds: Sequence[str] | None = None,
) -> tuple[NavReason, list[str]]:
    """Shared empty-answer predicate (264). Upgrades bare ``no_matches`` on unlinked inbound."""
    if reason != REASON_NO_MATCHES:
        return reason, []
    unlinked = unmeasured_inbound_for_subject(
        store, subject_kind=subject_kind, raws=raws, kinds=kinds
    )
    if unlinked:
        return REASON_RELATIONSHIP_NOT_MODELLED, unlinked
    return reason, []


def escalate_zero_production(
    reason: NavReason,
    *,
    production_count: int,
    unlinked_same_name_sites: int,
    unresolved_bare: int = 0,
    shared_honesty_reason: NavReason | None = None,
) -> NavReason:
    """A test-only partition is unmeasured when stored evidence falsifies the zero (272)."""
    if reason != REASON_OK or production_count != 0:
        return reason
    if unlinked_same_name_sites > 0:
        return REASON_RELATION_UNMODELLED_FOR_LANGUAGE
    if unresolved_bare > 0:
        return REASON_BARE_NAME_TRUNCATED
    if shared_honesty_reason not in (None, REASON_OK, REASON_NO_MATCHES):
        return shared_honesty_reason
    return reason


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


def coverage_edge_hint(
    stamped: Mapping[str, Sequence[str]] | None,
    *,
    has_coverage_gap: bool = False,
) -> str | None:
    """Hint for a coverage-edge zero — stamp preferred, then language gap; else None (061 / 314)."""
    if stamped:
        strategies = {str(s) for langs in stamped.values() for s in langs}
        if contract.RESOLUTION_DYNAMIC_SQL in strategies:
            return TRY_INSTEAD_HINT_DYNAMIC_SQL
        return TRY_INSTEAD_HINT_RESOLUTION_UNMODELLED
    if has_coverage_gap:
        return TRY_INSTEAD_HINT_OUTSIDE_COVERAGE
    return None


def attach_coverage_edge_route(
    payload: dict[str, object],
    stamped: Mapping[str, Sequence[str]] | None,
    *,
    has_coverage_gap: bool = False,
    detail_level: str = "standard",
) -> dict[str, object]:
    """Hint-only Grep handoff on a real coverage-edge *zero*; no-op otherwise (314 / 093 / 061)."""
    if detail_level == "minimal":
        return payload
    reason = payload.get("reason")
    results = payload.get("results")
    empty = isinstance(results, list) and len(results) == 0
    if reason not in (
        REASON_NO_MATCHES,
        REASON_NO_SUCH_SYMBOL,
        REASON_TOKEN_CANDIDATES,
    ) or not empty:
        return payload
    hint = coverage_edge_hint(stamped, has_coverage_gap=has_coverage_gap)
    if hint is None:
        return payload
    if stamped:
        # Stamp is the coverage edge — Grep is not a registered tool (093).
        payload.pop("try_instead", None)
        return attach_try_instead(payload, None, hint)
    if payload.get("try_instead") or payload.get("try_instead_hint"):
        return payload
    return attach_try_instead(payload, None, hint)


def attach_serve_behind_route(payload: dict[str, object]) -> dict[str, object]:
    """Name the caller opt-in on an ``index_stale`` refusal (274).

    ``serve_behind`` is a parameter, not a registered tool — hint only, no ``try_instead`` (R5.4).
    """
    payload[SERVE_BEHIND_OPT_IN_FIELD] = SERVE_BEHIND_OPT_IN
    return attach_try_instead(payload, None, TRY_INSTEAD_HINT_SERVE_BEHIND)


def attach_next_tools(payload: dict[str, object], kind: str) -> dict[str, object]:
    """On a successful answer, name the next mechanism step keyed on node kind (158 / 285).

    Contract vocabulary only — never language (R1.1). Callables keep find_callers/impact;
    Class/Interface name find_implementations; every other kind earns no field (061).
    """
    if kind in contract.CALLABLE_KINDS:
        payload["next_tool_suggestions"] = list(NEXT_TOOLS_FOR_CALLABLE)
    elif kind in contract.SUPERTYPE_SUBJECT_KINDS:
        payload["next_tool_suggestions"] = list(NEXT_TOOLS_FOR_TYPE)
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


# A same-named definition under a *different* qname: a simple-name reference may bind there, so an
# answer keyed on one qname is a partition (165). One definition site, both tools (R6.7).
SIBLING_DEFINITIONS = "sibling_definitions"
AUTHORITATIVE = "authoritative"
AUTHORITATIVE_CAVEATS = "authoritative_caveats"
# The distinct reasons an answer is a partition. Named, because `authoritative: false` alone cannot
# tell an agent whether to widen the query or to distrust the tier (task 168 AC3).
CAVEAT_ALL_HITS_DYNAMIC = "all_hits_dynamic"
CAVEAT_SIBLING_DEFINITIONS = "sibling_definitions"
# The caller is in another language whose crossing into the subject's language the index never
# modelled — the zero is a partition, not the whole (task 221). Rides the cross-language census.
CAVEAT_CROSS_LANGUAGE_UNMODELLED = "cross_language_relation_unmodelled"
# Page shows one tier of a multi-tier hit set (or none of the filtered tier) — 251/265.
CAVEAT_TIER_PARTITION = "tier_partition"
# Table/Column writer answer is only languages that emit WRITES (278/281) — covered
# languages that emit none leave host-language writes unmeasured (§19).
CAVEAT_WRITES_EMITTERS_ONLY = "writes_emitters_only"
# Mirror twin on read_symbol — boundary, never a dispatch verdict (286).
CAVEAT_MIRROR_TWIN = "mirror_twin"
CAVEAT_LIMIT_CROSS_LANGUAGE = (
    "This answer is reachability within one language's call graph and does not "
    "establish which entry point the front end invokes."
)
CAVEAT_LIMIT_WRITES_EMITTERS_ONLY = (
    "This answer lists WRITES from emitting adapters only; covered languages that "
    "do not emit WRITES leave host-language writes unmeasured and out of scope"
)
CAVEAT_LIMIT_MIRROR_TWIN = (
    "A mirrored counterpart is named (or honestly absent); this tool cannot say "
    "which side a request reaches."
)
CAVEAT_LIMITS: dict[str, str] = {
    CAVEAT_CROSS_LANGUAGE_UNMODELLED: CAVEAT_LIMIT_CROSS_LANGUAGE,
    CAVEAT_WRITES_EMITTERS_ONLY: CAVEAT_LIMIT_WRITES_EMITTERS_ONLY,
    CAVEAT_MIRROR_TWIN: CAVEAT_LIMIT_MIRROR_TWIN,
}
CAVEAT_LIMITS_KEY = "caveat_limits"
CAVEAT_ARGS_NOT_CAPTURED = "args_not_captured_by_adapter"
CROSS_LANGUAGE = "cross_language"


# What the sibling order means. A caveat that fires on 83% of calls cannot be a signal to act on
# unless it says which site to open first — and it must say what it ranked by, or the order is just
# another thing to trust (task 171, R5.5).
SIBLING_RANKED_BY = "sibling_definitions_ranked_by"
RANK_SHARED_SUBTREE = "shared_subtree_with_subject"
# 189: nearness is the wrong axis for *"which of these is my twin?"* — a twin lives in a SIBLING
# region while same-name noise lives inside the subject's own, so subtree depth ranks the answer
# last. The one container fact the core can read for free is the file the container is declared in.
RANK_SHARED_FILE_NAME = "shared_file_name_with_subject"
# The VERDICT, always stated once there is an order to have (task 181): a caller must be able to ask
# "is position meaningful here?" without knowing that the old `ranked_by: "path"` meant *unranked*.
SIBLING_RANKED = "sibling_definitions_ranked"
# An unranked list is a dump, so it is capped and says so; a RANKED list is never capped, because
# position is the answer and dropping a row would remove it (171).
SIBLING_TRUNCATED = "sibling_definitions_truncated"
SIBLING_TOTAL = "sibling_definitions_total"
UNRANKED_SIBLING_CAP = 10


def _shared_subtree_depth(subject_file: str, site_file: str) -> int:
    """How many leading directory components the two files share."""
    subject = PurePosixPath(subject_file).parent.parts
    site = PurePosixPath(site_file).parent.parts
    depth = 0
    for left, right in zip(subject, site, strict=False):
        if left != right:
            break
        depth += 1
    return depth


def rank_sibling_sites(
    sites: list[dict[str, object]], *, subject_file: str | None
) -> tuple[list[dict[str, object]], str | None]:
    """Order twins first, else nearest first, or admit there was nothing to rank by (171/181/189).

    Drops nothing — the sites that were noise for one question are the answer to another (171).
    Pure reordering of rows already fetched: no query per sibling, and none per caller.

    Two bases, and **the one named is the one that decided the order** (180's rule, R5.5).
    ``shared_file_name_with_subject`` bands the sites that are declared in a file of the subject's
    own name above those that are not — the twin question. It is named only when it actually
    PARTITIONED the list: if every site matches, or none does, the order was decided entirely by
    nearness and ``shared_subtree_with_subject`` is the honest name. That is a structural fact
    ("did this predicate split the list?"), not a tuned number (161 AC1).

    With no subject file there is no evidence to rank against, so the basis is ``None``: rows stay
    ordered by path for determinism (R4.2), but *alphabetical* is a sort, not a ranking, and
    calling it ``ranked_by: "path"`` made the two indistinguishable in the payload (181).
    """
    by_path = sorted(sites, key=lambda site: str(site["file"]))
    if subject_file is None:
        return by_path, None
    wanted = PurePosixPath(subject_file).name

    def shares_file_name(site: dict[str, object]) -> bool:
        return PurePosixPath(str(site["file"])).name == wanted

    matched = sum(1 for site in by_path if shares_file_name(site))
    partitioned = 0 < matched < len(by_path)
    ordered = sorted(
        by_path,
        key=lambda site: (
            not (partitioned and shares_file_name(site)),
            -_shared_subtree_depth(subject_file, str(site["file"])),
            str(site["file"]),
        ),
    )
    return ordered, RANK_SHARED_FILE_NAME if partitioned else RANK_SHARED_SUBTREE


def attach_sibling_definitions(
    payload: dict[str, object], sites: list[dict[str, object]], *, subject_file: str | None
) -> bool:
    """Attach the sites, say whether position means anything, and cap the list when it does not.

    Nothing is added below two sites — with one sibling there is no order to explain, and a lone
    caveat must not grow a field (061 / 171).

    At two or more, ``sibling_definitions_ranked`` is **always** present: it is the verdict a caller
    branches on, and it must not require knowing that one basis value used to mean *unranked* (181).
    ``sibling_definitions_ranked_by`` is the value and rides only when there is a basis to name.
    An unranked list is capped and says so; a ranked one never is, because position is the answer.
    """
    if not sites:
        return False
    ordered, basis = rank_sibling_sites(sites, subject_file=subject_file)
    if len(ordered) < 2:
        payload[SIBLING_DEFINITIONS] = ordered
        return True
    payload[SIBLING_RANKED] = basis is not None
    if basis is not None:
        payload[SIBLING_RANKED_BY] = basis
        payload[SIBLING_DEFINITIONS] = ordered
        return True
    # Unranked: 93 alphabetical rows were 91% of a field session's disclosure bytes, and 55% of them
    # shared only a name with the subject. The total is still reported, so nothing is hidden (066).
    payload[SIBLING_DEFINITIONS] = ordered[:UNRANKED_SIBLING_CAP]
    if len(ordered) > UNRANKED_SIBLING_CAP:
        payload[SIBLING_TRUNCATED] = True
        payload[SIBLING_TOTAL] = len(ordered)
    return True


def attach_authoritative_caveats(
    payload: dict[str, object], caveats: list[str]
) -> dict[str, object]:
    """Mark the answer a partition and name every reason it is one. Omit-when-empty (061).

    Merges (238): a second call names an additional reason. Replacing dropped a partition the
    payload still carries — the one thing this field exists to prevent.
    """
    if not caveats:
        return payload
    named = payload.get(AUTHORITATIVE_CAVEATS)
    already = {str(name) for name in named} if isinstance(named, list) else set()
    merged = already | set(caveats)
    payload[AUTHORITATIVE] = False
    payload[AUTHORITATIVE_CAVEATS] = sorted(merged)
    attach_caveat_limits(payload, sorted(merged))
    return payload


def attach_caveat_limits(
    payload: dict[str, object], caveats: list[str]
) -> dict[str, object]:
    """Name what each caveat costs the reader (task 251). Omit-when-empty (061)."""
    notes = {
        name: CAVEAT_LIMITS[name] for name in caveats if name in CAVEAT_LIMITS
    }
    if notes:
        payload[CAVEAT_LIMITS_KEY] = notes
    return payload


def attach_cross_language_census(
    payload: dict[str, object], census: dict[str, object] | None
) -> dict[str, object]:
    """Surface the cross-language census on the answer it invalidates (task 221). Omit-when-None."""
    if census is not None:
        payload[CROSS_LANGUAGE] = census
    return payload


def sibling_definition_rows(store: object, *, bare_name: str, kind: str, lookup: str, limit: int):
    """Same-named definitions of the same kind under other qnames. One bounded query (165).

    ``kind`` is the *subject's own* kind rather than a constant: 054's lesson is that a bare Method
    name and a Function qname are different subjects, and that rule stated once covers both tools.
    """
    rows = store.nodes_by_name(bare_name, kind=kind, limit=limit)  # type: ignore[attr-defined]
    return [row for row in rows if str(row["qualified_name"]) != lookup]


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
