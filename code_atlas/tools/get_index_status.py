"""``get_index_status`` — the cheap entry point a client calls first (§12).

``minimal`` returns exactly the four parts §12 names: stats, ``last_commit``, staleness and
``next_tool_suggestions``. ``standard`` adds the provenance a reader may want next. Nothing here
opens the database when there is none: a read tool must not create an index as a side effect.
"""

from collections.abc import Callable, Sequence
from typing import Literal

from code_atlas.config import Config
from code_atlas.gitutil import head_commit
from code_atlas.store import (
    BUILT_AT_KEY,
    CONTRACT_VERSION_KEY,
    LAST_COMMIT_KEY,
    SCHEMA_VERSION_KEY,
    GraphStore,
)

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
        """Index stats, last indexed commit, staleness and what to call next. Call this first."""
        if not config.db_path.is_file():
            return _unbuilt(servable, detail_level, config)
        with GraphStore(config.db_path) as store:
            return _status(store, config, servable, detail_level)

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
        "last_commit": None,
        "staleness": UNKNOWN,
        "next_tool_suggestions": _suggestions(servable, UNKNOWN),
    }
    if detail_level == "standard":
        status["db_path"] = str(config.db_path)
    return status


def _status(
    store: GraphStore, config: Config, servable: Sequence[str], detail_level: DetailLevel
) -> dict[str, object]:
    counts = store.counts()
    last_commit = store.get_meta(LAST_COMMIT_KEY)
    head = head_commit(config.root)
    staleness = _staleness(last_commit, head)

    status: dict[str, object] = {
        "indexed": counts["files"] > 0,
        **counts,
        "last_commit": last_commit,
        "staleness": staleness,
        "next_tool_suggestions": _suggestions(servable, staleness),
    }
    if detail_level == "minimal":
        return status
    return status | {
        "head_commit": head,
        "built_at": store.get_meta(BUILT_AT_KEY),
        "contract_version": store.get_meta(CONTRACT_VERSION_KEY),
        "schema_version": store.get_meta(SCHEMA_VERSION_KEY),
        "db_path": str(config.db_path),
    }


def _staleness(last_commit: str | None, head: str | None) -> str:
    """``unknown`` unless both commits are known — an unbuilt index and a repo-less tree both."""
    if last_commit is None or head is None:
        return UNKNOWN
    return CURRENT if last_commit == head else BEHIND


def _suggestions(servable: Sequence[str], staleness: str) -> list[str]:
    """Only tools this server serves, so a suggestion is never one the client cannot call."""
    wanted = [BUILD_TOOL] if staleness != CURRENT else []
    wanted += [name for name in servable if name not in {NAME, BUILD_TOOL}]
    return [name for name in wanted if name in servable]
