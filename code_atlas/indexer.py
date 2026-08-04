"""``full_build`` and ``incremental_update`` — one repo into one index (§8.1 / §8.3).

Parsing fans out across N adapter processes; **writing does not**. The caller's thread owns the
store and performs every mutation, which the database driver itself enforces — a connection may only
be used from the thread that made it — so R4.3's single writer is a runtime property, not a habit.

Nothing here knows what a language is. The suffixes to collect, and the value stored in
``files.language``, both come from the adapters' own handshakes (R1.1); this module only ever sees
an opaque configuration key.

A silent adapter is bounded by :class:`_Watchdog`, which kills the child once a blocking call
overruns ``adapter_timeout``. The parked read then returns nothing and the driver raises, so a hang
becomes the failure the driver already models rather than a wedged build (§4.1).
"""

import hashlib
import queue
import threading
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from code_atlas import contract, gitutil
from code_atlas.adapter import AdapterError, ParseResult, SubprocessAdapter, extension_index
from code_atlas.config import Config
from code_atlas.ignore import IgnoreMatcher, load_ignore
from code_atlas.resolver import resolve_edges
from code_atlas.store import BUILT_AT_KEY, CONTRACT_VERSION_KEY, LAST_COMMIT_KEY, GraphStore

# How often the watchdog looks for an overrun call: small beside any sane timeout, cheap to poll.
WATCHDOG_INTERVAL = 0.25

_READ_CHUNK = 1 << 20

_Outcome = tuple[str, str, ParseResult]


@dataclass(frozen=True, slots=True)
class BuildReport:
    """What one build did. Counts only — the rows themselves live in the store."""

    files: int
    parsed: int
    failed: int
    removed: int
    nodes: int
    edges: int


def full_build(config: Config, store: GraphStore) -> BuildReport:
    """Index every collectable file under ``config.root`` into ``store`` (§8.1 steps 1-5).

    Adapters emit bare edges; ``resolve_edges`` links them after every node exists. Every collected
    path leaves a ``files`` row, parsed or not.
    """
    watchdog = _Watchdog(config.adapter_timeout)
    watchdog.start()
    try:
        announced = _announce(config, watchdog)
        try:
            owners = _owners(announced)
            paths = collect(config.root, tuple(owners))
            removed = _reconcile(store, paths)
            counts = _parse_all(config, store, watchdog, announced, owners, paths)
        finally:
            for adapter in announced.values():
                adapter.stop()
    finally:
        watchdog.stop()

    # No FTS rebuild here: §10's triggers keep `nodes_fts` current through every replace, so a
    # rebuild per build would cost a full re-index and change nothing (deviation D1).
    _record_meta(config, store)
    resolve_edges(store, max_candidates=config.max_results)
    return BuildReport(files=len(paths), removed=removed, **counts)


def incremental_update(
    config: Config, store: GraphStore, changed: Sequence[str]
) -> BuildReport:
    """Re-index ``changed ∪ dependents`` and re-link into affected qnames (§8.3).

    ``changed`` is the git path set (commit range ∪ dirty tree); the caller falls back to
    :func:`full_build` when git cannot name one. Deletes and rename sources drop out of ``collect``
    and are reconciled away after their qnames are folded into ``affected``.
    """
    stored = store.get_meta(CONTRACT_VERSION_KEY)
    if stored is not None and stored != str(contract.CONTRACT_VERSION):
        # Vocabulary changed — incremental would mix eras; force a full rebuild (task 030 AC1).
        return full_build(config, store)

    watchdog = _Watchdog(config.adapter_timeout)
    watchdog.start()
    try:
        announced = _announce(config, watchdog)
        try:
            owners = _owners(announced)
            paths = collect(config.root, tuple(owners))
            wanted = set(paths)
            changed_set = set(changed)
            indexed = set(store.file_paths())

            prior = sorted(changed_set & indexed)
            affected = set(store.qnames_in_files(prior))
            # File nodes use the path as qname; include deleted/renamed-away paths so inbound edges
            # re-link (git diff names only the rename destination).
            affected.update(changed_set)
            gone = sorted(indexed - wanted)
            affected.update(store.qnames_in_files(gone))
            affected.update(gone)

            dependents = set(store.file_paths_targeting(sorted(affected))) & wanted
            removed = _reconcile(store, paths)

            candidates = sorted((changed_set | dependents) & wanted)
            # Dependents are unchanged by construction, so hash-skip must not apply to them —
            # replace_file_rows restores adapter tiers and duplicate keys that unlink cannot.
            to_parse = [
                path
                for path in candidates
                if path in dependents or not _hash_matches(store, config.root, path)
            ]
            counts = (
                _parse_all(config, store, watchdog, announced, owners, to_parse)
                if to_parse
                else {"parsed": 0, "failed": 0, "nodes": 0, "edges": 0}
            )
        finally:
            for adapter in announced.values():
                adapter.stop()
    finally:
        watchdog.stop()

    _record_meta(config, store)
    resolve_edges(store, max_candidates=config.max_results)
    return BuildReport(files=len(to_parse), removed=removed, **counts)


def reparse_file(config: Config, store: GraphStore, path: str) -> bool:
    """Parse one relative path into ``store`` and re-link (read-through freshness, task 035).

    Returns ``False`` when no announced adapter owns the suffix (caller should treat as stale).
    Uses the same ``_write`` path as a full/incremental build so rows stay deterministic (R4).
    """
    watchdog = _Watchdog(config.adapter_timeout)
    watchdog.start()
    try:
        announced = _announce(config, watchdog)
        try:
            owners = _owners(announced)
            suffix = _suffix(path)
            if suffix not in owners:
                return False
            key = owners[suffix]
            adapter = announced[key]
            language = adapter.name
            try:
                with watchdog.guard(adapter):
                    result = adapter.parse(path)
            except AdapterError as error:
                result = ParseResult(path=path, ok=False, error=str(error))
            tally = {"parsed": 0, "failed": 0, "nodes": 0, "edges": 0}
            _write(store, path, _digest(config.root / path), language, result, tally)
        finally:
            for adapter in announced.values():
                adapter.stop()
    finally:
        watchdog.stop()
    resolve_edges(store, max_candidates=config.max_results)
    return True


def file_is_current(store: GraphStore, root: Path, path: str) -> bool:
    """True when the indexed hash equals on-disk bytes (no reparse needed)."""
    return _hash_matches(store, root, path)


def _hash_matches(store: GraphStore, root: Path, path: str) -> bool:
    """True when the indexed hash equals the file's current bytes — skip a no-op reparse (§8.3)."""
    digest = _digest(root / path)
    return bool(digest) and store.file_hash(path) == digest


def collect(root: Path, suffixes: Sequence[str]) -> tuple[str, ...]:
    """The paths to index: tracked files of a claimed suffix, minus the ignore rules (§8.1, §11).

    Sorted here rather than trusted from git, so the order is a property of this core and not of
    whichever git version the host ships (R4.2).
    """
    matcher = load_ignore(root)
    wanted = {suffix.lower() for suffix in suffixes}
    tracked = gitutil.ls_files(root)
    found = _walk(root, matcher, wanted) if tracked is None else tracked
    return tuple(
        sorted(
            path
            for path in found
            if PurePosixPath(path).suffix.lower() in wanted and not matcher.is_ignored(path)
        )
    )


class _Watchdog:
    """Kills an adapter whose blocking call has overrun, so no read waits forever (§4.1).

    One polling thread for the whole build: a timer per request would cost a thread per file, which
    is the per-request reader thread this design exists to avoid.
    """

    def __init__(self, timeout: float) -> None:
        self._timeout = timeout
        self._watched: dict[object, tuple[float, SubprocessAdapter]] = {}
        self._lock = threading.Lock()
        self._done = threading.Event()
        self._thread = threading.Thread(target=self._poll, name="code-atlas-watchdog", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._done.set()
        self._thread.join(timeout=WATCHDOG_INTERVAL * 4)

    @contextmanager
    def guard(self, adapter: SubprocessAdapter) -> Iterator[None]:
        """Bound one blocking call on ``adapter``; on overrun the child is killed, not signalled."""
        token = object()
        with self._lock:
            self._watched[token] = (time.monotonic() + self._timeout, adapter)
        try:
            yield
        finally:
            with self._lock:
                self._watched.pop(token, None)

    def _poll(self) -> None:
        while not self._done.wait(WATCHDOG_INTERVAL):
            now = time.monotonic()
            # Under the lock, so a deadline is read and acted on atomically. A call that returns in
            # the same instant may still be killed; it costs one restart, never a lost result.
            with self._lock:
                for deadline, adapter in self._watched.values():
                    if deadline <= now:
                        adapter.kill()


def _announce(config: Config, watchdog: _Watchdog) -> dict[str, SubprocessAdapter]:
    """Start one adapter per configured command and read its handshake.

    This is the only way to learn which suffixes exist, so a failure here is a configuration error
    and stays loud (R5.3) — a silent boot included, since no file is yet known to record unparsed.
    """
    started: dict[str, SubprocessAdapter] = {}
    try:
        for key in sorted(config.adapter_cmds):
            adapter = _adapter(config, key)
            with watchdog.guard(adapter):
                adapter.start()
            started[key] = adapter
    except BaseException:
        for adapter in started.values():
            adapter.stop()
        raise
    return started


def _adapter(config: Config, key: str) -> SubprocessAdapter:
    command = config.adapter_cmd(key)
    if command is None:
        raise AdapterError(
            f"adapter {key!r} has no configured command — set CA_{key.upper()}_CMD"
        )
    return SubprocessAdapter(
        key,
        command,
        config.root,
        host_root=config.host_root,
        container_root=config.container_root,
    )


def _owners(announced: Mapping[str, SubprocessAdapter]) -> dict[str, str]:
    """Suffix -> configuration key, built through the driver's own duplicate-claim check."""
    index = extension_index(announced.values())
    key_of = {id(adapter): key for key, adapter in announced.items()}
    return {suffix: key_of[id(adapter)] for suffix, adapter in index.items()}


def _walk(root: Path, matcher: IgnoreMatcher, wanted: set[str]) -> list[str]:
    """The fallback when there is no git index: walk the tree, pruning ignored directories."""
    found: list[str] = []
    stack = [root]
    while stack:
        for entry in sorted(stack.pop().iterdir()):
            relative = entry.relative_to(root).as_posix()
            if entry.is_dir():
                if not matcher.is_ignored(relative, is_dir=True):
                    stack.append(entry)
            elif entry.suffix.lower() in wanted:
                found.append(relative)
    return found


def _reconcile(store: GraphStore, paths: Sequence[str]) -> int:
    """Drop every indexed path the collection no longer yields, with its nodes and edges (§8.1)."""
    gone = sorted(set(store.file_paths()) - set(paths))
    for path in gone:
        store.remove_file(path)
    return len(gone)


def _parse_all(
    config: Config,
    store: GraphStore,
    watchdog: _Watchdog,
    announced: Mapping[str, SubprocessAdapter],
    owners: Mapping[str, str],
    paths: Sequence[str],
) -> dict[str, int]:
    """Fan each adapter's paths across its own workers, writing every result on this thread."""
    # Read the announced names now: an adapter that dies later can no longer say what it was.
    languages = {key: adapter.name for key, adapter in announced.items()}
    tally = {"parsed": 0, "failed": 0, "nodes": 0, "edges": 0}
    pending = set(paths)

    for key in sorted(announced):
        group = [path for path in paths if owners[_suffix(path)] == key]
        if group:
            first = announced[key]
            _parse_group(config, store, watchdog, key, languages[key], first, group, tally, pending)

    for path in sorted(pending):
        # Nothing ever answered for these: every worker retired, or none could be started.
        language = languages[owners[_suffix(path)]]
        store.upsert_file(path, _digest(config.root / path), language, parsed_ok=False)
        tally["failed"] += 1
    return tally


def _parse_group(
    config: Config,
    store: GraphStore,
    watchdog: _Watchdog,
    key: str,
    language: str,
    first: SubprocessAdapter,
    group: Sequence[str],
    tally: dict[str, int],
    pending: set[str],
) -> None:
    """One adapter's whole share, on ``min(workers, len(group))`` processes and one writer."""
    work: queue.Queue[str] = queue.Queue()
    for path in group:
        work.put(path)
    # Bounded, so a slow writer back-pressures the workers instead of buffering the whole graph.
    results: queue.Queue[_Outcome | None] = queue.Queue(maxsize=max(2, config.workers * 2))

    count = max(1, min(config.workers, len(group)))
    workers = [
        threading.Thread(
            target=_work,
            args=(config, watchdog, key, work, results, first if index == 0 else None),
            name=f"code-atlas-worker-{key}-{index}",
            daemon=True,
        )
        for index in range(count)
    ]
    for worker in workers:
        worker.start()

    alive = count
    while alive:
        item = results.get()
        if item is None:
            alive -= 1
            continue
        path, digest, result = item
        _write(store, path, digest, language, result, tally)
        pending.discard(path)
    for worker in workers:
        worker.join()


def _work(
    config: Config,
    watchdog: _Watchdog,
    key: str,
    work: queue.Queue[str],
    results: queue.Queue[_Outcome | None],
    started: SubprocessAdapter | None,
) -> None:
    """One worker: own one adapter, drain the queue, report every outcome, then signal with None.

    A dead or killed adapter is replaced and the worker carries on; one that cannot be started at
    all retires the worker, handing the path back so another worker can still try it.
    """
    adapter = started
    try:
        while True:
            try:
                path = work.get_nowait()
            except queue.Empty:
                return
            if adapter is None:
                try:
                    adapter = _start(config, watchdog, key)
                except AdapterError:
                    work.put(path)
                    return
            try:
                with watchdog.guard(adapter):
                    result = adapter.parse(path)
            except AdapterError as error:
                result = ParseResult(path=path, ok=False, error=str(error))
                adapter.stop()
                adapter = None
            results.put((path, _digest(config.root / path), result))
    finally:
        if adapter is not None and adapter is not started:
            adapter.stop()
        results.put(None)


def _start(config: Config, watchdog: _Watchdog, key: str) -> SubprocessAdapter:
    adapter = _adapter(config, key)
    with watchdog.guard(adapter):
        adapter.start()
    return adapter


def _write(
    store: GraphStore,
    path: str,
    digest: str,
    language: str,
    result: ParseResult,
    tally: dict[str, int],
) -> None:
    """Persist one file's outcome. Edges go in exactly as the adapter emitted them — bare (R3.3)."""
    store.upsert_file(path, digest, language, parsed_ok=result.ok)
    store.replace_file_rows(path, result.nodes, result.edges)
    if result.ok:
        tally["parsed"] += 1
        tally["nodes"] += len(result.nodes)
        tally["edges"] += len(result.edges)
    else:
        tally["failed"] += 1


def _record_meta(config: Config, store: GraphStore) -> None:
    """Stamp the build (§8.1 step 4). ``last_commit`` stays unset when git cannot name one."""
    store.set_meta(CONTRACT_VERSION_KEY, str(contract.CONTRACT_VERSION))
    store.set_meta(BUILT_AT_KEY, store.now())
    commit = gitutil.head_commit(config.root)
    if commit is not None:
        store.set_meta(LAST_COMMIT_KEY, commit)


def _suffix(path: str) -> str:
    return PurePosixPath(path).suffix.lower()


def _digest(path: Path) -> str:
    """A content hash of the file's **bytes**, or the empty string when it cannot be read."""
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(_READ_CHUNK):
                hasher.update(chunk)
    except OSError:
        return ""
    return hasher.hexdigest()
