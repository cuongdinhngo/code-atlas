"""``build_or_update_index`` — run a build and report what it did (§12).

``full=true`` always runs a full build. ``full=false`` runs an incremental update when
``last_commit`` and ``git diff`` are usable; otherwise it falls back to a full build and names the
mode that actually ran. The store is opened here, inside the call, because the caller's thread owns
the connection (R4.3).
"""

import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from code_atlas import gitutil
from code_atlas.config import Config
from code_atlas.indexer import BuildReport, full_build, incremental_update
from code_atlas.store import BUILT_AT_KEY, LAST_COMMIT_KEY, GraphStore, SchemaVersionError

NAME = "build_or_update_index"

DetailLevel = Literal["minimal", "standard"]

FULL = "full"
INCREMENTAL = "incremental"


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def build_or_update_index(
        full: bool = False, detail_level: DetailLevel = "standard"
    ) -> dict[str, object]:
        """Index this repo and return the counts and elapsed time.

        An index written under an older ``schema_version`` is deleted and rebuilt in-band so an MCP
        client can recover without a shell.
        """
        started = time.monotonic()
        rebuilt_schema = False
        try:
            store = GraphStore(config.db_path)
        except SchemaVersionError:
            _unlink_index(config.db_path)
            rebuilt_schema = True
            store = GraphStore(config.db_path)
        try:
            mode, report = _run(config, store, full=full or rebuilt_schema)
            elapsed = round(time.monotonic() - started, 3)
            return _result(
                store, config, report, full, mode, elapsed, detail_level,
                rebuilt_schema=rebuilt_schema,
            )
        finally:
            store.close()

    return build_or_update_index


def _run(config: Config, store: GraphStore, *, full: bool) -> tuple[str, BuildReport]:
    """Pick full vs incremental; degrade to full when git or meta cannot support a diff."""
    if full:
        return FULL, full_build(config, store)
    last = store.get_meta(LAST_COMMIT_KEY)
    if last is None or gitutil.head_commit(config.root) is None:
        return FULL, full_build(config, store)
    changed = gitutil.changed_paths(config.root, last)
    if changed is None:
        return FULL, full_build(config, store)
    return INCREMENTAL, incremental_update(config, store, changed)


def _unlink_index(path: Path) -> None:
    """Remove a foreign-schema DB (and WAL siblings) so the next open creates schema current."""
    for sibling in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
        sibling.unlink(missing_ok=True)


def _result(
    store: GraphStore,
    config: Config,
    report: BuildReport,
    full: bool,
    mode: str,
    elapsed: float,
    detail_level: DetailLevel,
    *,
    rebuilt_schema: bool,
) -> dict[str, object]:
    # The counts come off the report itself, so a field added there reaches clients without an edit.
    result: dict[str, object] = {
        "mode": mode,
        "requested_full": full,
        **asdict(report),
        "seconds": elapsed,
        "schema_rebuilt": rebuilt_schema,
    }
    if detail_level == "minimal":
        return result
    return result | {
        "last_commit": store.get_meta(LAST_COMMIT_KEY),
        "built_at": store.get_meta(BUILT_AT_KEY),
        "db_path": str(config.db_path),
    }
