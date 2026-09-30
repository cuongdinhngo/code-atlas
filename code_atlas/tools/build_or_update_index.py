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
from typing import Literal

from code_atlas import contract, gitutil
from code_atlas.adapter import AdapterError
from code_atlas.config import Config
from code_atlas.index_lock import publish_build_progress, try_index_write_lock
from code_atlas.indexer import (
    CONTRACT_REBUILD_REQUIRED,
    COVERAGE_LOSS,
    COVERAGE_LOSS_HINT,
    COVERAGE_LOSS_IN_BAND,
    FULL_REBUILD_ROUTE,
    FULL_REBUILD_USE_SHELL,
    FULL_REBUILD_USE_SHELL_HINT,
    IN_BAND_FULL_REBUILD,
    INCOMPLETE_INDEX,
    INCOMPLETE_INDEX_ROUTE,
    BuildReport,
    CoverageLossError,
    build_incomplete,
    contract_rebuild_required,
    coverage_loss,
    full_build,
    incremental_update,
)
from code_atlas.store import (
    BUILT_AT_KEY,
    CONTRACT_VERSION_KEY,
    COVERED_LANGUAGES_KEY,
    LAST_COMMIT_KEY,
    SCHEMA_OLDER,
    WRITE_ERRORS,
    GraphStore,
    SchemaVersionError,
)
from code_atlas.tools import schema_guard
from code_atlas.tools.collection import collection_field
from code_atlas.tools.config_provenance import attach_config_provenance
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
        full: bool = False,
        detail_level: DetailLevel = "standard",
        allow_full_rebuild: bool = False,
        repair_incomplete: bool = True,
        allow_coverage_loss: bool = False,
    ) -> dict[str, object]:
        """Build or refresh this repo's index so the other tools have current data.

        Returns ``wrote`` counts (and ``graph`` on standard) plus elapsed time. An index written
        under an *older* ``schema_version`` is deleted and rebuilt in-band so an MCP client can
        recover without a shell; a *newer* one is refused untouched — that index is current and this
        server is the stale one (050). Concurrent writers share ``write.lock`` (053); a held lock
        returns ``mode: busy`` carrying the staleness of the index the loser is about to query,
        read-only (072). To *see* a busy refusal on purpose, follow the ``code-atlas-refresh`` race
        recipe in ``docs/runbooks/parallel-agents.md`` (082).

        An index written under an older *vocabulary* era cannot be extended
        incrementally either (030 AC1). Rather than silently starting an hour-long
        rebuild inside a call that cannot outlive its client, ``full=false`` returns
        ``mode: refused`` with ``reason: contract_rebuild_required`` and the route that
        can serve it. ``allow_full_rebuild=true`` runs that rebuild in-band anyway,
        accepting the wait (201). The same refusal shape answers an explicit
        ``full=true`` on an index that already exists — MCP cannot outlive its client,
        and a timed-out "failed" does not stop the server-side build (291).
        """
        started = time.monotonic()
        with try_index_write_lock(config.db_path) as held:
            if not held:
                return _busy(config, full=full, started=started)
            try:
                return _build(
                    config,
                    full=full,
                    detail_level=detail_level,
                    started=started,
                    allow_full_rebuild=allow_full_rebuild,
                    repair_incomplete=repair_incomplete,
                    allow_coverage_loss=allow_coverage_loss,
                )
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
    allow_full_rebuild: bool = False,
    repair_incomplete: bool = True,
    allow_coverage_loss: bool = False,
) -> dict[str, object]:
    rebuilt_schema = False
    try:
        store = GraphStore(config.db_path)
    except SchemaVersionError as mismatch:
        if mismatch.direction != SCHEMA_OLDER:
            return _refused(config, mismatch, full)
        # Readers keep the mismatch answer until the rebuilt index is published over it (356).
        rebuilt_schema = True
        store = GraphStore.open_shadow(config.db_path)
    try:
        if (
            full
            and not allow_full_rebuild
            and not rebuilt_schema
            and store.get_meta(LAST_COMMIT_KEY)
        ):
            # Existing index + explicit full over MCP: refuse (291). First build / schema
            # recovery / allow_full_rebuild still run; the shell always opts in.
            return _full_mcp_refused(config, full=full, started=started)
        if not (full or rebuilt_schema or allow_full_rebuild) and contract_rebuild_required(
            store
        ):
            return _contract_refused(store, config, full=full, started=started)
        if not repair_incomplete and build_incomplete(store):
            return _incomplete_refused(config, full=full, started=started)
        scope: dict[str, object] = {}
        try:
            mode, report = _run(
                config,
                store,
                full=full or rebuilt_schema,
                scope=scope,
                allow_coverage_loss=allow_coverage_loss,
            )
        except CoverageLossError as loss:
            # Raised by `full_build` before it writes, so this covers the escalation paths a
            # `full=False` request can take as well as an explicit `--full` (203).
            return _coverage_refused(store, config, loss.lost, full=full, started=started)
        if store.is_shadow:
            store.publish()
            store = GraphStore(config.db_path)
        result = _result(
            store, config, report, full, mode, detail_level,
            rebuilt_schema=rebuilt_schema,
        )
        # Names why a `full` ran off an incremental request, so `wrote.files` can never again mean
        # both "nothing to do" and "could not act on the request" (task 172 / 060).
        result.update(scope)
        result["seconds"] = round(time.monotonic() - started, 3)
        return result
    finally:
        if store.is_shadow:
            store.discard()
        else:
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
        # Time-throttle only when a known total makes rapid ticks (parse). Resolve uses total=0
        # and must publish every batch tick or a fast pass looks frozen (290 / AC1).
        if phase == last_phase and total and now - last_at < PROGRESS_INTERVAL:
            return
        last_phase, last_at = phase, now
        # total=0 still publishes done so a frozen resolve line is a wedge (290).
        if total:
            counted = f" done={done} total={total}"
        elif done:
            counted = f" done={done}"
        else:
            counted = ""
        publish_build_progress(
            config.db_path, f"phase={phase}{counted} pid={os.getpid()} at={time.time():.0f}"
        )

    return publish


def _run(
    config: Config,
    store: GraphStore,
    *,
    full: bool,
    scope: dict[str, object],
    allow_coverage_loss: bool = False,
) -> tuple[str, BuildReport]:
    """Pick full vs incremental; degrade to full when git or meta cannot support a diff.

    ``scope`` is filled in place when the incremental path escalates because the adapter set
    moved, so a build that could not act on the request never reports like one that had nothing
    to do (task 172).
    """
    progress = _progress_sink(config)
    # BEFORE any write, on EVERY path. `full_build` raises this too, but by then an escalating
    # incremental has already stamped `build_complete = 0`, so the refusal would not be free.
    # A narrowed adapter set has no safe outcome: escalate and discard, or leave rows nothing can
    # reparse. Both are refused here, and `allow_coverage_loss` restores either (203).
    if not allow_coverage_loss:
        lost = coverage_loss(store, config.adapter_cmds)
        if lost:
            raise CoverageLossError(lost)
    if full:
        return FULL, full_build(
            config, store, progress=progress, allow_coverage_loss=allow_coverage_loss
        )
    last = store.get_meta(LAST_COMMIT_KEY)
    if last is None or gitutil.head_commit(config.root) is None:
        return FULL, full_build(
            config, store, progress=progress, allow_coverage_loss=allow_coverage_loss
        )
    changed = gitutil.changed_paths(config.root, last)
    if changed is None:
        return FULL, full_build(
            config, store, progress=progress, allow_coverage_loss=allow_coverage_loss
        )
    report = incremental_update(
        config, store, changed, progress=progress, scope=scope,
        allow_coverage_loss=allow_coverage_loss,
    )
    return (FULL if scope else INCREMENTAL), report


def _contract_refused(
    store: GraphStore, config: Config, *, full: bool, started: float
) -> dict[str, object]:
    """A lagging vocabulary era forces a full rebuild — say so instead of starting one (201).

    The 050 shape, for the other version key: returned rather than raised so the caller reads
    the action, and carrying no counts because nothing was built (060). ``route`` answers *what
    do I do now*, which the previous silence left the caller to find by watching a lock file.
    """
    return {
        "mode": REFUSED,
        "requested_full": full,
        "performed": False,
        "reason": CONTRACT_REBUILD_REQUIRED,
        "stored_contract_version": store.get_meta(CONTRACT_VERSION_KEY),
        "contract_version": contract.CONTRACT_VERSION,
        "route": FULL_REBUILD_ROUTE,
        "in_band_option": IN_BAND_FULL_REBUILD,
        "index_root": config.index_root,
        "db_path": str(config.db_path),
        "seconds": round(time.monotonic() - started, 3),
    }


def _full_mcp_refused(config: Config, *, full: bool, started: float) -> dict[str, object]:
    """Explicit full over MCP on an existing index — answer, do not attempt (291)."""
    return {
        "mode": REFUSED,
        "requested_full": full,
        "performed": False,
        "reason": FULL_REBUILD_USE_SHELL,
        "route": FULL_REBUILD_ROUTE,
        "in_band_option": IN_BAND_FULL_REBUILD,
        "hint": FULL_REBUILD_USE_SHELL_HINT,
        "index_root": config.index_root,
        "db_path": str(config.db_path),
        "seconds": round(time.monotonic() - started, 3),
    }


def _coverage_refused(
    store: GraphStore,
    config: Config,
    lost: tuple[str, ...],
    *,
    full: bool,
    started: float,
) -> dict[str, object]:
    """The run cannot parse a language the index covers — refuse before writing the loss (203).

    The 050/201 shape, and deliberately **no** `route`: no registered tool can configure an
    adapter, so this carries a hint instead of a tool that could not answer (R5.4c).
    """
    return {
        "mode": REFUSED,
        "requested_full": full,
        "performed": False,
        "reason": COVERAGE_LOSS,
        "lost_languages": list(lost),
        "covered_languages": store.get_meta(COVERED_LANGUAGES_KEY) or "",
        "configured_languages": sorted(config.adapter_cmds),
        "hint": COVERAGE_LOSS_HINT,
        "in_band_option": COVERAGE_LOSS_IN_BAND,
        "index_root": config.index_root,
        "db_path": str(config.db_path),
        "seconds": round(time.monotonic() - started, 3),
    }


def _incomplete_refused(config: Config, *, full: bool, started: float) -> dict[str, object]:
    """The index needs a full rebuild, for a caller that must not start one itself (202).

    The git refresh hook is the caller: 053 says it never builds, and the ticket's own trigger
    list includes closing the terminal that owns it — so a hook that self-repaired could loop.
    """
    return {
        "mode": REFUSED,
        "requested_full": full,
        "performed": False,
        "reason": INCOMPLETE_INDEX,
        "route": INCOMPLETE_INDEX_ROUTE,
        "index_root": config.index_root,
        "db_path": str(config.db_path),
        "seconds": round(time.monotonic() - started, 3),
    }


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
    attach_config_provenance(enriched, config, store)
    return enriched
