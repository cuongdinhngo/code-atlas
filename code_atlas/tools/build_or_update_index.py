"""``build_or_update_index`` — run a build and report what it did (§12).

``full=true`` always runs a full build. ``full=false`` runs an incremental update when
``last_commit`` and ``git diff`` are usable; otherwise it falls back to a full build and names the
mode that actually ran. Successful payloads nest run writes under ``wrote`` so a delta cannot be
read as a repo size (task 060); ``standard`` also adds ``graph`` from ``store.counts()``. The store
is opened here, inside the call, because the caller's thread owns the connection (R4.3).
"""

import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from code_atlas import gitutil
from code_atlas.config import Config
from code_atlas.index_lock import try_index_write_lock
from code_atlas.indexer import BuildReport, full_build, incremental_update
from code_atlas.store import (
    BUILT_AT_KEY,
    LAST_COMMIT_KEY,
    SCHEMA_OLDER,
    WRITE_ERRORS,
    GraphStore,
    SchemaVersionError,
)
from code_atlas.tools import schema_guard
from code_atlas.tools.staleness import UNKNOWN, compute_staleness

NAME = "build_or_update_index"

DetailLevel = Literal["minimal", "standard"]

FULL = "full"
INCREMENTAL = "incremental"
REFUSED = "refused"
BUSY = "busy"

# Opening the index for a busy-branch staleness read may hit a foreign schema or, in a cold-start
# race, a write-locked DB; either degrades to ``unknown`` rather than raising (R5.3, C2).
_STALENESS_READ_ERRORS: tuple[type[BaseException], ...] = (SchemaVersionError, *WRITE_ERRORS)


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def build_or_update_index(
        full: bool = False, detail_level: DetailLevel = "standard"
    ) -> dict[str, object]:
        """Build or refresh this repo's index so the other tools have current data.

        Returns ``wrote`` counts (and ``graph`` on standard) plus elapsed time. An index written
        under an *older* ``schema_version`` is deleted and rebuilt in-band so an MCP client can
        recover without a shell; a *newer* one is refused untouched — that index is current and this
        server is the stale one (050). Concurrent writers share ``write.lock`` (053); a held lock
        returns ``mode: busy`` carrying the staleness of the index the loser is about to query,
        read-only (072).
        """
        started = time.monotonic()
        with try_index_write_lock(config.db_path) as held:
            if not held:
                return _busy(config, full=full, started=started)
            return _build(config, full=full, detail_level=detail_level, started=started)

    return build_or_update_index


def _busy(config: Config, *, full: bool, started: float) -> dict[str, object]:
    """Another writer holds the lock: report what the caller is about to query, not just why (072).

    ``performed: false`` states the consequence in the reason channel (033) — the refresh did not
    run — beside the ``staleness``/``last_commit``/``head_commit``/``last_ref``/``head_ref`` fields
    ``get_index_status`` uses, so a caller has one vocabulary. A read-only open cannot corrupt the
    winner's build (053) and degrades to ``unknown`` rather than raising when there is no readable
    index (R5.3).
    """
    return {
        "mode": BUSY,
        "requested_full": full,
        "performed": False,
        "reason": "another_build_running",
        **_busy_staleness(config),
        "db_path": str(config.db_path),
        "seconds": round(time.monotonic() - started, 3),
    }


def _unknown_staleness() -> dict[str, str | None]:
    """Soft degrade for a busy refusal that cannot read the index (072 / 077)."""
    return {
        "staleness": UNKNOWN,
        "last_commit": None,
        "head_commit": None,
        "last_ref": None,
        "head_ref": None,
    }


def _busy_staleness(config: Config) -> dict[str, str | None]:
    """Best-effort staleness of the index the loser will read; never raises (R5.3, C2).

    ``WRITE_ERRORS`` guards the cold-start race: a first build in flight leaves the DB file present
    but its schema uncommitted, so opening it here would block on the winner's write lock and time
    out — degrade to ``unknown`` rather than let the busy refusal raise.
    """
    if not config.db_path.is_file():
        return _unknown_staleness()
    try:
        with GraphStore(config.db_path) as store:
            return compute_staleness(store, config)
    except _STALENESS_READ_ERRORS:
        return _unknown_staleness()


def _build(
    config: Config,
    *,
    full: bool,
    detail_level: DetailLevel,
    started: float,
) -> dict[str, object]:
    rebuilt_schema = False
    try:
        store = GraphStore(config.db_path)
    except SchemaVersionError as mismatch:
        if mismatch.direction != SCHEMA_OLDER:
            return _refused(config, mismatch, full)
        _unlink_index(config.db_path)
        rebuilt_schema = True
        store = GraphStore(config.db_path)
    try:
        mode, report = _run(config, store, full=full or rebuilt_schema)
        result = _result(
            store, config, report, full, mode, detail_level,
            rebuilt_schema=rebuilt_schema,
        )
        result["seconds"] = round(time.monotonic() - started, 3)
        return result
    finally:
        store.close()


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


def _refused(config: Config, mismatch: SchemaVersionError, full: bool) -> dict[str, object]:
    """Only an index this server has outgrown may be deleted; the rest is someone else's data.

    Returned rather than raised so the caller reads the action, but it reports no counts — nothing
    was built, and a build payload full of zeroes would say the repo is empty.
    """
    return schema_guard.payload(mismatch) | {
        "mode": REFUSED,
        "requested_full": full,
        "schema_rebuilt": False,
        "db_path": str(config.db_path),
    }


def _result(
    store: GraphStore,
    config: Config,
    report: BuildReport,
    full: bool,
    mode: str,
    detail_level: DetailLevel,
    *,
    rebuilt_schema: bool,
) -> dict[str, object]:
    # ``wrote`` is always nested so a delta cannot be read as a repo size (060).
    # A field added to BuildReport still reaches clients via asdict without an edit here.
    result: dict[str, object] = {
        "mode": mode,
        "requested_full": full,
        "wrote": asdict(report),
        "schema_rebuilt": rebuilt_schema,
    }
    if detail_level == "minimal":
        return result
    # ``graph`` is standard-only — not on the cheap path (counts() can scan stubs at scale).
    return result | {
        "graph": store.counts(),
        "last_commit": store.get_meta(LAST_COMMIT_KEY),
        "built_at": store.get_meta(BUILT_AT_KEY),
        "db_path": str(config.db_path),
    }
