"""``get_index_status`` — the cheap entry point a client calls first (§12).

``minimal`` returns stats, ``last_commit``, staleness, process identity (``server_version`` /
``server_build`` / ``server_stale_process`` — 223), and ``next_tool_suggestions`` only when
non-empty. ``standard`` adds provenance plus index-health (``edge_health``, ``parse_failures``,
``dirty_indexed_files``) and a bounded ``cross_language`` census (task 243 — ``linked`` /
``unlinked`` / ``by_tier`` only; ``pairs`` stays inside verbose's ``edge_health_by_language``).
``parse_failures`` mirrors ``failed`` (files with ``parsed_ok = 0``) under the §12 name — same
count, not a subset. ``verbose`` is ``standard`` plus a capped ``parse_failure_paths`` list
(task 058) — never on the cheap path. ``standard`` also carries ``capabilities_by_language``
for the languages the index covers, when the build stamped one (231/244). Nothing here opens the
database when there is none: a read tool must not create an index as a side effect.

Staleness counts only files the index covers (047): editing a README leaves the graph correct, and
a signal that says otherwise costs its reader a rebuild that reindexes nothing.
"""

from collections.abc import Callable, Sequence
from typing import Literal

from code_atlas.adapter import unconfigured_adapters
from code_atlas.build_info import server_provenance
from code_atlas.config import Config
from code_atlas.index_lock import build_in_progress
from code_atlas.indexer import (
    CONTRACT_REBUILD_REQUIRED,
    COVERAGE_LOSS,
    COVERAGE_LOSS_HINT,
    COVERAGE_LOSS_IN_BAND,
    FULL_REBUILD_ROUTE,
    IN_BAND_FULL_REBUILD,
    build_incomplete,
    contract_rebuild_required,
    coverage_loss,
)
from code_atlas.store import (
    BUILT_AT_KEY,
    CONTRACT_VERSION_KEY,
    SCHEMA_OLDER,
    SCHEMA_VERSION_KEY,
    GraphStore,
    SchemaVersionError,
)
from code_atlas.tools import claim, schema_guard
from code_atlas.tools.collection import collection_field
from code_atlas.tools.config_provenance import attach_config_provenance
from code_atlas.tools.coverage import covered_languages
from code_atlas.tools.staleness import BEHIND, CURRENT, UNKNOWN, compute_staleness

NAME = "get_index_status"

DetailLevel = Literal["minimal", "standard", "verbose"]
# 183's field, named once. Same block the build stamped, so the payload adds no computation.
EDGE_HEALTH_BY_LANGUAGE_FIELD = "edge_health_by_language"
# 204's crossing census; 243 surfaces a bounded copy at standard (pairs stay verbose-nested).
CROSS_LANGUAGE_FIELD = "cross_language"
# 231's per-language R1.6 flags; 244 surfaces them on the first-call channel (standard).
CAPABILITIES_BY_LANGUAGE_FIELD = "capabilities_by_language"

QUESTION = "indexed-files"

# Own cap for the verbose failure list — not ``CA_PAGE_LIMIT`` / ``CA_MAX_CANDIDATES`` (259).
PARSE_FAILURE_PATHS_LIMIT = 50

# Staleness vocabulary lives in ``staleness`` (shared with the build busy refusal, task 072);
# re-exported here so callers importing it from this module keep working.
__all__ = ["NAME", "create", "CURRENT", "BEHIND", "UNKNOWN"]

BUILD_TOOL = "build_or_update_index"

# Two axes the revision axis deliberately does not answer (task 178). `staleness` says WHICH
# REVISION this index describes — 072's busy refusal and 077 both read it that way — so "is a build
# running" and "did the last build finish linking" get their own names rather than overloading it.
BUILD_IN_PROGRESS = "build_in_progress"
INDEX_COMPLETE = "index_complete"
FULL_REBUILD_REQUIRED = "full_rebuild_required"
COVERAGE_LOSS_PENDING = "coverage_loss_pending"
# The one state the MCP route cannot report on at all: a build already running. `--status` reads
# the live lock, which is why it is named here rather than left to be discovered (177, 203).
BUILD_PROGRESS_ROUTE = "code-atlas-build --status"
BUILD_PROGRESS_ROUTE_FIELD = "build_progress_route"


def create(config: Config, registered: Sequence[str]) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo and to the tool names this server actually serves."""
    servable = tuple(registered)

    def get_index_status(
        detail_level: DetailLevel = "standard", offset: int = 0, sign: bool = False
    ) -> dict[str, object]:
        """Is the index built, fresh, and healthy — and what should I call next? Call this first.

        Reports stats, health, last commit, staleness, and next-tool suggestions. ``verbose`` adds
        capped ``parse_failure_paths`` plus ``parse_failures_truncated``; pass ``offset`` to page
        further. ``minimal`` / ``standard`` omit the list (cheap path). ``standard``/``verbose``
        also carry ``page_limit`` (query-time row ceiling) and ``max_candidates`` (build-time
        resolver fan-out), each with its own ``governs`` list so the two caps are not conflated
        (066/259). ``verbose`` also carries ``collection`` — the
        denominator to reconcile ``files`` against your own ``git ls-files``:
        ``collected - skipped.suffix - skipped.ignore == kept``, ``kept + stubs == files`` (082).
        ``skipped.untracked`` sits beside that identity: files git does not list, with an indexed
        suffix, that are not ignored (092). ``verbose`` also names ``skipped.ignore_sources`` —
        per-source counts that sum to ``skipped.ignore`` (095); omitted when empty or pre-095.
        ``standard``/``verbose`` carry ``unconfigured_adapters`` — adapters that ship in-repo but
        have no launch command, each with the ``CA_<LANG>_CMD`` that enables it; omitted when all
        are wired (159). On a multi-language index they also carry ``cross_language`` — the
        build-stamped crossing census without ``pairs`` (243); omitted under two language buckets
        and on a pre-204 stamp (R5.6 / 061). ``standard``/``verbose`` also carry
        ``capabilities_by_language`` — the build-stamped R1.6 flags, for the languages this
        index holds files of (231/244/173); omitted when the stamp is absent or empty
        (R5.6 / 061). ``verbose`` still nests the
        full census (with ``pairs``) inside ``edge_health_by_language``.

        ``sign`` (default off, so the default payload is unchanged) adds ``claim``: one quotable
        ``key=value`` line stating how many files this index covers and at which revision. An
        unbuilt or unreadable index carries no line — it cannot name a revision (task 100).
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if offset > 0 and detail_level != "verbose":
            raise ValueError("offset requires detail_level='verbose'")
        if not config.db_path.is_file():
            return _unbuilt(servable, detail_level, config)
        try:
            with GraphStore(config.db_path) as store:
                return _status(store, config, servable, detail_level, offset=offset, sign=sign)
        except SchemaVersionError as mismatch:
            return _mismatched(mismatch, servable, detail_level, config)

    return get_index_status


def _page_limit_field(config: Config) -> dict[str, object]:
    """Query-time page ceiling — never the build fan-out (066/259)."""
    return {
        "value": config.page_limit,
        "governs": ["returned_rows"],
    }


def _max_candidates_field(config: Config) -> dict[str, object]:
    """Build-time resolver fan-out — changing it requires a rebuild (259)."""
    return {
        "value": config.max_candidates,
        "governs": ["resolver_candidate_fanout"],
    }


def _attach_build_state(
    status: dict[str, object], config: Config, store: GraphStore | None
) -> None:
    """Name a build in flight and an unfinished link phase — both omitted when there is nothing
    to say, so a quiet server is byte-identical to before (061).

    ``build_in_progress`` is 177's probe, the one definition site (R6.7): read-only, non-blocking,
    creating nothing, and a missing lock file reads as *no build* rather than unknown (077).
    """
    if build_in_progress(config.db_path):
        status[BUILD_IN_PROGRESS] = True
        # No MCP tool can report a running build's phase — this one answers with a snapshot and
        # the lock is what has the live line. Name the route rather than leave it to be found.
        status[BUILD_PROGRESS_ROUTE_FIELD] = BUILD_PROGRESS_ROUTE
    if store is None:
        return
    # One derivation for this field and for `staleness`, so the two cannot disagree (202, R6.7).
    # An absent key is an index written before the key existed: unknowable, so say nothing.
    if build_incomplete(store):
        status[INDEX_COMPLETE] = False
    # "Call this first" is only worth following if it names the hour-long rebuild waiting
    # behind the next incremental. Omitted when none is pending, like 159 (201).
    if contract_rebuild_required(store):
        status[FULL_REBUILD_REQUIRED] = {
            "reason": CONTRACT_REBUILD_REQUIRED,
            "route": FULL_REBUILD_ROUTE,
            "in_band_option": IN_BAND_FULL_REBUILD,
        }
    # A build here would REFUSE rather than serve, so the caller needs to know before it calls.
    # Hint and no route: no registered tool configures an adapter (R5.4c, 203).
    lost = coverage_loss(store, config.adapter_cmds)
    if lost:
        status[COVERAGE_LOSS_PENDING] = {
            "reason": COVERAGE_LOSS,
            "lost_languages": list(lost),
            "hint": COVERAGE_LOSS_HINT,
            "in_band_option": COVERAGE_LOSS_IN_BAND,
        }


def _attach_unconfigured_adapters(status: dict[str, object], config: Config) -> None:
    """Name adapters that ship in-repo but are unwired — omit when all configured (159/061)."""
    unwired = unconfigured_adapters(config.adapter_cmds)
    if unwired:
        status["unconfigured_adapters"] = unwired


def _orphans_max_nodes_field(config: Config) -> dict[str, object]:
    """Walk budget for ``find_orphans`` — separate from ``impact_max_nodes`` (124)."""
    return {
        "value": config.orphans_max_nodes,
        "governs": ["orphans_reachability_walk"],
    }


def _attach_suggestions(
    status: dict[str, object], servable: Sequence[str], staleness: str, *, indexed: bool
) -> None:
    """Omit-when-empty (061 / 223): an empty array costs tokens and was never read."""
    suggestions = _suggestions(servable, staleness, indexed=indexed)
    if suggestions:
        status["next_tool_suggestions"] = suggestions


def _unbuilt(
    servable: Sequence[str], detail_level: DetailLevel, config: Config
) -> dict[str, object]:
    """No database file yet — say so cheaply rather than creating one to count zeroes.

    No git spawn: an unbuilt reply must not block on a wedged ``rev-parse`` (077). Refs are null
    beside ``last_commit``, matching every other unbuilt provenance field.
    """
    status: dict[str, object] = {
        "indexed": False,
        "files": 0,
        "nodes": 0,
        "edges": 0,
        "stubs": 0,
        "last_commit": None,
        "last_ref": None,
        "head_ref": None,
        "staleness": UNKNOWN,
        "index_root": config.index_root,
        **server_provenance(),
    }
    _attach_suggestions(status, servable, UNKNOWN, indexed=False)
    if detail_level in ("standard", "verbose"):
        status["db_path"] = str(config.db_path)
        status["page_limit"] = _page_limit_field(config)
        status["max_candidates"] = _max_candidates_field(config)
        _attach_build_state(status, config, None)
        _attach_unconfigured_adapters(status, config)
    if detail_level == "verbose":
        status["parse_failure_paths"] = []
        status["parse_failures_truncated"] = False
    return status


def _mismatched(
    mismatch: SchemaVersionError,
    servable: Sequence[str],
    detail_level: DetailLevel,
    config: Config,
) -> dict[str, object]:
    """A database this server cannot read — answer in the ``_unbuilt`` family, never raise (050).

    ``indexed: false`` means *no index this server can use*, which the ``error`` and the two version
    fields spell out; a build is suggested only when rebuilding is the fix.
    """
    status = _unbuilt(servable, detail_level, config) | schema_guard.payload(mismatch)
    if mismatch.direction != SCHEMA_OLDER:
        status.pop("next_tool_suggestions", None)
    return status


def _status(
    store: GraphStore,
    config: Config,
    servable: Sequence[str],
    detail_level: DetailLevel,
    *,
    offset: int = 0,
    sign: bool = False,
) -> dict[str, object]:
    counts = store.counts()
    revision = compute_staleness(store, config, include_dirty_count=True)
    dirty_count = revision.pop("dirty_indexed_files")
    staleness = str(revision["staleness"])
    indexed = counts["files"] > 0

    def signed(payload: dict[str, object]) -> dict[str, object]:
        """Attach the claim line, or hand the payload back untouched (task 100).

        The caveat comes from ``counts``, not from the payload: ``parse_failures`` is only
        exposed at ``standard``/``verbose``, so carrying it off the payload would drop it from
        the ``minimal`` line while the failures were real.
        """
        if not sign:
            return payload
        return claim.sign(
            payload,
            tool=NAME,
            question=QUESTION,
            subject_parts=[config.index_root],
            staleness={**revision, "dirty_indexed_files": dirty_count},
            answer=counts["files"],
            extra=(("parse_failures", counts["failed"]),) if counts["failed"] else (),
        )

    status: dict[str, object] = {
        "indexed": indexed,
        **counts,
        **{k: v for k, v in revision.items() if k != "head_commit"},
        "index_root": config.index_root,
        **server_provenance(),
    }
    _attach_suggestions(status, servable, staleness, indexed=indexed)
    if detail_level == "minimal":
        return signed(status)
    enriched = status | {
        "head_commit": revision["head_commit"],
        "built_at": store.get_meta(BUILT_AT_KEY),
        "contract_version": store.get_meta(CONTRACT_VERSION_KEY),
        "schema_version": store.get_meta(SCHEMA_VERSION_KEY),
        "db_path": str(config.db_path),
        "edge_health": store.edge_health(),
        "parse_failures": counts["failed"],
        "dirty_indexed_files": dirty_count,
        # Query-time page vs build-time fan-out — separate keys, separate scopes (066/259).
        "page_limit": _page_limit_field(config),
        "max_candidates": _max_candidates_field(config),
        "orphans_max_nodes": _orphans_max_nodes_field(config),
    }
    _attach_build_state(enriched, config, store)
    _attach_unconfigured_adapters(enriched, config)
    attach_config_provenance(enriched, config, store)
    hint = store.count_source_root_hint_imports()
    if hint:
        enriched["source_root_hint_imports"] = hint
    _attach_cross_language_summary(enriched, store)
    _attach_capabilities_by_language(enriched, store)
    if detail_level == "standard":
        return signed(enriched)
    paths = store.failed_paths(PARSE_FAILURE_PATHS_LIMIT, offset=offset)
    verbose = enriched | {
        "parse_failure_paths": list(paths),
        "parse_failures_truncated": counts["failed"] > offset + len(paths),
    }
    collection = collection_field(store, ignore_sources=True)
    if collection is not None:
        verbose["collection"] = collection
    _attach_edge_health_by_language(verbose, store)
    return signed(verbose)


def _language_bucket_count(stamped: dict[str, object]) -> int:
    """How many language buckets the 183 stamp carries, counting ``unattributed`` (183 / 243)."""
    by_language = stamped.get("by_language")
    buckets = len(by_language) if isinstance(by_language, dict) else 0
    if "unattributed" in stamped:
        buckets += 1
    return buckets


def _attach_cross_language_summary(payload: dict[str, object], store: GraphStore) -> None:
    """Bounded crossing census at ``standard`` (task 243), or nothing.

    Silent when the stamp is absent (R5.6) and when a single-language graph adds nothing (061).
    Drops ``pairs`` — that map grows with the square of the language count and stays nested under
    verbose's ``edge_health_by_language``. One meta read; never a query-time scan (R4.2).
    """
    stamped = store.stamped_edge_health_by_language()
    if stamped is None or _language_bucket_count(stamped) < 2:
        return
    census = store.stamped_cross_language_edges()
    if census is None:
        return
    payload[CROSS_LANGUAGE_FIELD] = {
        "by_tier": census["by_tier"],
        "linked": census["linked"],
        "unlinked": census["unlinked"],
    }



def _attach_capabilities_by_language(payload: dict[str, object], store: GraphStore) -> None:
    """Per-language R1.6 flags at ``standard`` (task 244), or nothing.

    The first-call channel is the only one that reaches a non-caller. The stamp already exists
    (231); this is the one meta read that puts it where the session looks. Silent when absent,
    empty, or every flag is false — nothing to disclose stays byte-identical (R5.6 / 061).
    Never a query-time scan (R4.2).

    Scoped to the languages this index covers (173's stamp): 231 stamps every adapter that
    announced, so an unfiltered map answers for languages the graph holds no file of — cost on
    the session's most expensive call, about an index that cannot answer either way (061).
    """
    stamped = store.stamped_capabilities_by_language()
    if not stamped:
        return
    # No coverage stamp (pre-173) is not evidence of no coverage — do not filter on it (R5.6).
    covered = covered_languages(store)
    if covered is not None:
        names = {name for name in covered.split(",") if name}
        stamped = {name: caps for name, caps in stamped.items() if name in names}
    if not any(any(caps.values()) for caps in stamped.values()):
        return
    payload[CAPABILITIES_BY_LANGUAGE_FIELD] = {
        name: dict(caps) for name, caps in sorted(stamped.items())
    }


def _attach_edge_health_by_language(payload: dict[str, object], store: GraphStore) -> None:
    """The per-language tier mix at verbose, or nothing at all (task 183).

    Silent on two counts. A pre-183 index has no stamp and says nothing rather than guessing (R5.6);
    and a single-bucket graph adds no answer the whole-graph ``edge_health`` does not already give,
    so it stays byte-identical (061). "Bucket" counts ``unattributed`` — a graph whose split is
    incomplete has something to report even with one language.
    """
    stamped = store.stamped_edge_health_by_language()
    if stamped is None or _language_bucket_count(stamped) < 2:
        return
    payload[EDGE_HEALTH_BY_LANGUAGE_FIELD] = stamped


def _suggestions(servable: Sequence[str], staleness: str, *, indexed: bool) -> list[str]:
    """State-reactive hints — never the full tool list (task 061).

    No index / stale or dirty index → suggest a build. A current index → empty (the
    client already knows the servable tools).
    """
    if not indexed or staleness != CURRENT:
        return [name for name in (BUILD_TOOL,) if name in servable]
    return []
