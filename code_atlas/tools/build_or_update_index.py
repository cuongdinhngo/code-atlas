"""``build_or_update_index`` — run a build and report what it did (§12).

``full=true`` always runs a full build. ``full=false`` runs an incremental update when
``last_commit`` and ``git diff`` are usable; otherwise it falls back to a full build and names the
mode that actually ran. Successful payloads nest run writes under ``wrote`` so a delta cannot be
read as a repo size (task 060); ``standard`` also adds ``graph`` from ``store.counts()``
and ``collection`` (the 082 census, including ``skipped.untracked`` — task 092). The store
is opened here, inside the call, because the caller's thread owns the connection (R4.3).
"""

import os
import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from code_atlas import gitutil
from code_atlas.adapter import AdapterError
from code_atlas.config import Config
from code_atlas.index_lock import publish_build_progress, try_index_write_lock
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
from code_atlas.tools.collection import collection_field
from code_atlas.tools.staleness import OMIT, UNKNOWN, compute_staleness, last_ref_for_payload

NAME = "build_or_update_index"

# How often a running build rewrites its progress line. A phase change always writes; between
# phases the parse loop is throttled to this, so the cost is bounded by wall time, never by file
# count (task 177). One fixed-width rewrite of one 200-byte file — never a second pass.
PROGRESS_INTERVAL = 0.5

DetailLevel = Literal["minimal", "standard"]

FULL = "full"
INCREMENTAL = "incremental"
REFUSED = "refused"
BUSY = "busy"
# One reason for any adapter-unusable build (unconfigured / bad handshake): the caller's situation
# is the same — no build ran, here is the tree and why — and ``detail`` carries the specifics (064).
NO_USABLE_ADAPTER = "no_usable_adapter"

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
        read-only (072). To *see* a busy refusal on purpose, follow the ``code-atlas-refresh`` race
        recipe in ``docs/runbooks/parallel-agents.md`` (082).
        """
        started = time.monotonic()
        with try_index_write_lock(config.db_path) as held:
            if not held:
                return _busy(config, full=full, started=started)
            try:
                return _build(config, full=full, detail_level=detail_level, started=started)
            except AdapterError as broken:
                return _adapter_refused(config, broken, full=full, started=started)

    return build_or_update_index


def _adapter_refused(
    config: Config, broken: AdapterError, *, full: bool, started: float
) -> dict[str, object]:
    """No usable adapter: refuse as a payload naming the tree, never a stack trace (064 / 079).

    A build with no configured adapter or a bad handshake used to raise; a raised error carries no
    ``index_root``, so a parallel agent could not tell which tree the refusal was about. Mirrors
    ``schema_guard``: the refusal reaches the caller as a payload, still writing no index (064's
    concern) and naming the tree it declined to write (071/079).
    """
    return {
        "mode": REFUSED,
        "requested_full": full,
        "performed": False,
        "reason": NO_USABLE_ADAPTER,
        "detail": str(broken),
        "index_root": config.index_root,
        "db_path": str(config.db_path),
        "seconds": round(time.monotonic() - started, 3),
    }


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
        "index_root": config.index_root,
        "seconds": round(time.monotonic() - started, 3),
    }


def _unknown_staleness() -> dict[str, object]:
    """Soft degrade for a busy refusal that cannot read the index (072 / 077)."""
    return {
        "staleness": UNKNOWN,
        "last_commit": None,
        "head_commit": None,
        "last_ref": None,
        "head_ref": None,
    }


def _busy_staleness(config: Config) -> dict[str, object]:
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


def _progress_sink(config: Config) -> Callable[[str, int, int], None]:
    """Publish the running build's phase and file counts into the lock it already holds (177).

    Throttled by wall time, and always on a phase change: a file counter alone reaches 100% and
    then sits in ``resolve`` for an unbounded share of the build, which reads as a wedge one
    screen later. The phase name is the carrier that cannot do that.
    """
    last_phase = ""
    last_at = 0.0

    def publish(phase: str, done: int, total: int) -> None:
        nonlocal last_phase, last_at
        now = time.monotonic()
        if phase == last_phase and now - last_at < PROGRESS_INTERVAL:
            return
        last_phase, last_at = phase, now
        counted = f" done={done} total={total}" if total else ""
        publish_build_progress(
            config.db_path, f"phase={phase}{counted} pid={os.getpid()} at={time.time():.0f}"
        )

    return publish


def _run(config: Config, store: GraphStore, *, full: bool) -> tuple[str, BuildReport]:
    """Pick full vs incremental; degrade to full when git or meta cannot support a diff."""
    progress = _progress_sink(config)
    if full:
        return FULL, full_build(config, store, progress=progress)
    last = store.get_meta(LAST_COMMIT_KEY)
    if last is None or gitutil.head_commit(config.root) is None:
        return FULL, full_build(config, store, progress=progress)
    changed = gitutil.changed_paths(config.root, last)
    if changed is None:
        return FULL, full_build(config, store, progress=progress)
    return INCREMENTAL, incremental_update(config, store, changed, progress=progress)


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
        "index_root": config.index_root,
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
    # ``index_root`` ships on both detail levels — it is the fingerprint every payload names (079).
    result: dict[str, object] = {
        "mode": mode,
        "requested_full": full,
        "wrote": asdict(report),
        "schema_rebuilt": rebuilt_schema,
        "index_root": config.index_root,
    }
    if detail_level == "minimal":
        return result
    # ``graph`` is standard-only — not on the cheap path (counts() can scan stubs at scale).
    enriched = result | {
        "graph": store.counts(),
        "last_commit": store.get_meta(LAST_COMMIT_KEY),
        "built_at": store.get_meta(BUILT_AT_KEY),
        "db_path": str(config.db_path),
    }
    # ``last_ref`` names the revision beside the commit (077); omitted, never null, for a pre-077
    # index — a just-built index always has it, so OMIT is a guard, not the live path.
    ref = last_ref_for_payload(store)
    if ref is not OMIT:
        enriched["last_ref"] = ref
    collection = collection_field(store)
    if collection is not None:
        enriched["collection"] = collection
    return enriched
