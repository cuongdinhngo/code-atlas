"""``get_index_status`` — the cheap entry point a client calls first (§12).

``minimal`` returns exactly the four parts §12 names: stats, ``last_commit``, staleness and
``next_tool_suggestions``. ``standard`` adds provenance plus index-health (``edge_health``,
``parse_failures``, ``dirty_indexed_files``). ``parse_failures`` mirrors ``failed`` (files with
``parsed_ok = 0``) under the §12 name — same count, not a subset. ``verbose`` is ``standard`` plus
a capped ``parse_failure_paths`` list (task 058) — never on the cheap path. Nothing here opens the
database when there is none: a read tool must not create an index as a side effect.

Staleness counts only files the index covers (047): editing a README leaves the graph correct, and
a signal that says otherwise costs its reader a rebuild that reindexes nothing.
"""

from collections.abc import Callable, Sequence
from typing import Literal

from code_atlas.config import Config
from code_atlas.gitutil import head_commit
from code_atlas.store import (
    BUILT_AT_KEY,
    CONTRACT_VERSION_KEY,
    LAST_COMMIT_KEY,
    SCHEMA_OLDER,
    SCHEMA_VERSION_KEY,
    GraphStore,
    SchemaVersionError,
)
from code_atlas.tools import schema_guard
from code_atlas.tools.staleness import (
    BEHIND,
    CURRENT,
    UNKNOWN,
    dirty_indexed,
    staleness_of,
)

NAME = "get_index_status"

DetailLevel = Literal["minimal", "standard", "verbose"]

# Own cap for the verbose failure list — not ``CA_MAX_RESULTS`` (disk / nav / resolver knob).
PARSE_FAILURE_PATHS_LIMIT = 50

# Staleness vocabulary lives in ``staleness`` (shared with the build busy refusal, task 072);
# re-exported here so callers importing it from this module keep working.
__all__ = ["NAME", "create", "CURRENT", "BEHIND", "UNKNOWN"]

BUILD_TOOL = "build_or_update_index"


def create(config: Config, registered: Sequence[str]) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo and to the tool names this server actually serves."""
    servable = tuple(registered)

    def get_index_status(
        detail_level: DetailLevel = "standard", offset: int = 0
    ) -> dict[str, object]:
        """Index stats, health, last commit, staleness and next tools. Call this first.

        ``verbose`` adds capped ``parse_failure_paths`` plus ``parse_failures_truncated``;
        pass ``offset`` to page further. ``minimal`` / ``standard`` omit the list (cheap path).

        ``standard``/``verbose`` also carry ``max_results`` — the effective ceiling a caller
        sizes requests against — and its ``governs`` list: it caps both returned rows and the
        resolver's candidate fan-out, so ``total_count`` is not the only cap (066).
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if offset > 0 and detail_level != "verbose":
            raise ValueError("offset requires detail_level='verbose'")
        if not config.db_path.is_file():
            return _unbuilt(servable, detail_level, config)
        try:
            with GraphStore(config.db_path) as store:
                return _status(store, config, servable, detail_level, offset=offset)
        except SchemaVersionError as mismatch:
            return _mismatched(mismatch, servable, detail_level, config)

    return get_index_status


def _max_results_field(config: Config) -> dict[str, object]:
    """The ceiling plus what it governs, so a caller sizes requests without a config read (066)."""
    return {
        "value": config.max_results,
        "governs": ["returned_rows", "resolver_candidate_fanout"],
    }


def _unbuilt(
    servable: Sequence[str], detail_level: DetailLevel, config: Config
) -> dict[str, object]:
    """No database file yet — say so cheaply rather than creating one to count zeroes."""
    status: dict[str, object] = {
        "indexed": False,
        "files": 0,
        "nodes": 0,
        "edges": 0,
        "stubs": 0,
        "last_commit": None,
        "staleness": UNKNOWN,
        "next_tool_suggestions": _suggestions(servable, UNKNOWN, indexed=False),
        "index_root": config.index_root,
    }
    if detail_level in ("standard", "verbose"):
        status["db_path"] = str(config.db_path)
        status["max_results"] = _max_results_field(config)
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
        status["next_tool_suggestions"] = []
    return status


def _status(
    store: GraphStore,
    config: Config,
    servable: Sequence[str],
    detail_level: DetailLevel,
    *,
    offset: int = 0,
) -> dict[str, object]:
    counts = store.counts()
    last_commit = store.get_meta(LAST_COMMIT_KEY)
    head = head_commit(config.root)
    dirty, dirty_count = dirty_indexed(store, config)
    staleness = staleness_of(last_commit, head, dirty=dirty)
    indexed = counts["files"] > 0

    status: dict[str, object] = {
        "indexed": indexed,
        **counts,
        "last_commit": last_commit,
        "staleness": staleness,
        "next_tool_suggestions": _suggestions(servable, staleness, indexed=indexed),
        "index_root": config.index_root,
    }
    if detail_level == "minimal":
        return status
    enriched = status | {
        "head_commit": head,
        "built_at": store.get_meta(BUILT_AT_KEY),
        "contract_version": store.get_meta(CONTRACT_VERSION_KEY),
        "schema_version": store.get_meta(SCHEMA_VERSION_KEY),
        "db_path": str(config.db_path),
        "edge_health": store.edge_health(),
        "parse_failures": counts["failed"],
        "dirty_indexed_files": dirty_count,
        # The ceiling a caller sizes requests against, and its double duty (066).
        "max_results": _max_results_field(config),
    }
    if detail_level == "standard":
        return enriched
    paths = store.failed_paths(PARSE_FAILURE_PATHS_LIMIT, offset=offset)
    return enriched | {
        "parse_failure_paths": list(paths),
        "parse_failures_truncated": counts["failed"] > offset + len(paths),
    }


def _suggestions(servable: Sequence[str], staleness: str, *, indexed: bool) -> list[str]:
    """State-reactive hints — never the full tool list (task 061).

    No index / stale or dirty index → suggest a build. A current index → empty (the
    client already knows the servable tools).
    """
    if not indexed or staleness != CURRENT:
        return [name for name in (BUILD_TOOL,) if name in servable]
    return []
