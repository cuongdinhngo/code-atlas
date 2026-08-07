"""``get_index_status`` — the cheap entry point a client calls first (§12).

``minimal`` returns exactly the four parts §12 names: stats, ``last_commit``, staleness and
``next_tool_suggestions``. ``standard`` adds provenance plus index-health (``edge_health``,
``parse_failures``, ``dirty_indexed_files``). ``parse_failures`` mirrors ``failed`` (files with
``parsed_ok = 0``) under the §12 name — same count, not a subset. Nothing here opens the database
when there is none: a read tool must not create an index as a side effect.

Staleness counts only files the index covers (047): editing a README leaves the graph correct, and
a signal that says otherwise costs its reader a rebuild that reindexes nothing.
"""

from collections.abc import Callable, Sequence
from typing import Literal

from code_atlas.config import Config
from code_atlas.gitutil import dirty_paths, head_commit
from code_atlas.indexer import indexable
from code_atlas.store import (
    BUILT_AT_KEY,
    CONTRACT_VERSION_KEY,
    INDEXED_SUFFIXES_KEY,
    LAST_COMMIT_KEY,
    SCHEMA_OLDER,
    SCHEMA_VERSION_KEY,
    GraphStore,
    SchemaVersionError,
)
from code_atlas.tools import schema_guard

NAME = "get_index_status"

DetailLevel = Literal["minimal", "standard"]

CURRENT = "current"
BEHIND = "behind"
UNKNOWN = "unknown"

BUILD_TOOL = "build_or_update_index"


def create(config: Config, registered: Sequence[str]) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo and to the tool names this server actually serves."""
    servable = tuple(registered)

    def get_index_status(detail_level: DetailLevel = "standard") -> dict[str, object]:
        """Index stats, health, last commit, staleness and what to call next. Call this first."""
        if not config.db_path.is_file():
            return _unbuilt(servable, detail_level, config)
        try:
            with GraphStore(config.db_path) as store:
                return _status(store, config, servable, detail_level)
        except SchemaVersionError as mismatch:
            return _mismatched(mismatch, servable, detail_level, config)

    return get_index_status


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
    }
    if detail_level == "standard":
        status["db_path"] = str(config.db_path)
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
    store: GraphStore, config: Config, servable: Sequence[str], detail_level: DetailLevel
) -> dict[str, object]:
    counts = store.counts()
    last_commit = store.get_meta(LAST_COMMIT_KEY)
    head = head_commit(config.root)
    dirty, dirty_count = _dirty_indexed(store, config)
    staleness = _staleness(last_commit, head, dirty=dirty)
    indexed = counts["files"] > 0

    status: dict[str, object] = {
        "indexed": indexed,
        **counts,
        "last_commit": last_commit,
        "staleness": staleness,
        "next_tool_suggestions": _suggestions(servable, staleness, indexed=indexed),
    }
    if detail_level == "minimal":
        return status
    return status | {
        "head_commit": head,
        "built_at": store.get_meta(BUILT_AT_KEY),
        "contract_version": store.get_meta(CONTRACT_VERSION_KEY),
        "schema_version": store.get_meta(SCHEMA_VERSION_KEY),
        "db_path": str(config.db_path),
        "edge_health": store.edge_health(),
        "parse_failures": counts["failed"],
        "dirty_indexed_files": dirty_count,
    }


def _dirty_indexed(store: GraphStore, config: Config) -> tuple[bool | None, int | None]:
    """Are any *indexed* files dirty, and how many — a dirty README is not a stale graph (047).

    Falls back to the whole tracked tree when the index predates this key, which over-reports
    rather than promising freshness it cannot check (R5.2's spirit: never claim the stronger tier).
    """
    paths = dirty_paths(config.root)
    if paths is None:
        return None, None
    suffixes = store.get_meta(INDEXED_SUFFIXES_KEY)
    if not suffixes:
        return bool(paths), None
    hits = indexable(paths, config.root, suffixes.split(","))
    return bool(hits), len(hits)


def _staleness(last_commit: str | None, head: str | None, *, dirty: bool | None) -> str:
    """``unknown`` unless both commits known; ``behind`` if HEAD moved or ``dirty`` (047)."""
    if last_commit is None or head is None:
        return UNKNOWN
    if last_commit != head:
        return BEHIND
    if dirty:
        return BEHIND
    return CURRENT


def _suggestions(servable: Sequence[str], staleness: str, *, indexed: bool) -> list[str]:
    """Only tools this server serves; nav tools only once there is an index to navigate."""
    if not indexed:
        wanted = [BUILD_TOOL]
    else:
        wanted = [BUILD_TOOL] if staleness != CURRENT else []
        wanted += [name for name in servable if name not in {NAME, BUILD_TOOL}]
    return [name for name in wanted if name in servable]
