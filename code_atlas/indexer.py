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
import json
import os
import queue
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

from code_atlas import contract, gitutil
from code_atlas.adapter import AdapterError, ParseResult, SubprocessAdapter, extension_index
from code_atlas.config import Config, ConfigError
from code_atlas.enrichment import (
    INDIRECTION_FILE,
    RulesPayload,
    apply_indirection_rules,
    load_indirection_rules,
)
from code_atlas.ignore import BUILTIN_PATTERNS, IgnoreMatcher, compile_pattern, load_ignore
from code_atlas.resolver import delta_scope, resolve_edges
from code_atlas.store import (
    BUILD_COMPLETE,
    BUILD_COMPLETE_KEY,
    BUILD_INCOMPLETE,
    BUILT_AT_KEY,
    COLLECTION_CENSUS_KEY,
    CONFIG_IDENTITY_KEY,
    CONTRACT_VERSION_KEY,
    COVERED_LANGUAGES_KEY,
    COVERED_SUFFIXES_KEY,
    EDGE_HEALTH_BY_LANGUAGE_KEY,
    EMITTED_KINDS_BY_LANGUAGE_KEY,
    IGNORE_SOURCES_KEY,
    INDEXED_SUFFIXES_KEY,
    LAST_COMMIT_KEY,
    LAST_REF_KEY,
    SKIPPED_SUFFIX_COUNTS_KEY,
    UNTRACKED_INDEXABLE_KEY,
    WRITE_ERRORS,
    GraphStore,
)

# How often the watchdog looks for an overrun call: small beside any sane timeout, cheap to poll.
WATCHDOG_INTERVAL = 0.25

# Named phases for optional ``phase_times`` on ``incremental_update`` (task 052 profiler).
INCREMENTAL_PHASES = (
    "announce",
    "tree_walk",
    "reconcile",
    "hashing",
    "parse",
    "meta",
    "enrichment",
    "resolve",
)

# A running build's only outward signal (task 177). ``phase`` comes from INCREMENTAL_PHASES above,
# never a second list (R6.7); ``done``/``total`` are file counts and are 0/0 outside the parse.
ProgressSink = Callable[[str, int, int], None]


class _TooLarge(Exception):
    """A delta whose parse set is past the measured crossover: cheaper as a full build (212).

    It carries the three numbers the report needs, so the ``scope`` key is written by the handler
    that actually takes the route. Writing the key at the decision and raising afterwards let the
    two diverge: a lost ``raise`` would report a full build that never ran — 202's lesson inverted,
    and the ticket-blind challenger's mutation proved a test suite can miss it.
    """

    def __init__(self, to_parse: int, changed: int, crossover: int) -> None:
        self.to_parse = to_parse
        self.changed = changed
        self.crossover = crossover
        super().__init__(f"{to_parse} files to parse, past the {crossover} crossover")


class _ScopeChanged(Exception):
    """The announced suffix set differs from the one the index was built with (task 172).

    Raised inside the incremental body so the existing ``finally`` blocks still stop every adapter,
    and caught one frame out. A file that entered scope because an *adapter* was added is neither a
    git change nor a dependent, so it is never a candidate — the build would report a clean no-op.
    """

    def __init__(self, added: tuple[str, ...], removed: tuple[str, ...]) -> None:
        self.added = added
        self.removed = removed
        super().__init__(f"added={added} removed={removed}")


class _Progress:
    """Report phase and file counts to the sink, or do nothing at all when there is none.

    ``None`` is the default everywhere, so a build with no reader runs the same code path it ran
    before this existed (061) — no formatting, no clock read, no branch inside the parse loop
    beyond one ``is None``.
    """

    __slots__ = ("_sink", "_phase", "_done", "_total")

    def __init__(self, sink: ProgressSink | None) -> None:
        self._sink = sink
        self._phase = ""
        self._done = 0
        self._total = 0

    def phase(self, name: str, *, total: int = 0) -> None:
        if self._sink is None:
            return
        self._phase, self._done, self._total = name, 0, total
        self._sink(name, 0, total)

    def tick(self) -> None:
        if self._sink is None:
            return
        self._done += 1
        self._sink(self._phase, self._done, self._total)


_READ_CHUNK = 1 << 20

# Directory names skipped under a stub walk — same built-in dirs as ignore (§11), minus nothing
# at the walk root (os.walk starts *inside* the stub root).
_STUB_SKIP_DIRS = frozenset(
    pattern.strip("/") for pattern in BUILTIN_PATTERNS if pattern.endswith("/")
)

# File-level builtins still apply under stub walks (vendor/ dirs are skipped above; Blade templates
# must not be routed even inside CA_STUB_ROOTS — task 041).
_STUB_FILE_IGNORE = IgnoreMatcher(
    tuple(
        rule
        for pattern in BUILTIN_PATTERNS
        if not pattern.endswith("/")
        if (rule := compile_pattern(pattern)) is not None
    )
)

_Outcome = tuple[str, str, ParseResult]


@dataclass(frozen=True, slots=True)
class BuildReport:
    """What one build did. Counts only — the rows themselves live in the store.

    Every field is **what this run wrote**, not what the graph holds: ``nodes``/``edges`` include
    the rows enrichment and the resolver insert after the parse tally, so a full build agrees with
    ``store.counts()`` while an incremental run still reports its own delta (task 051).
    ``fingerprint_skipped`` counts files whose bytes changed but whose whitespace-normalised
    fingerprint did not — skipped without a parse (213), never confused with ``parsed``.
    """

    files: int
    parsed: int
    failed: int
    removed: int
    nodes: int
    edges: int
    stubs: int = 0
    fingerprint_skipped: int = 0


def full_build(
    config: Config,
    store: GraphStore,
    *,
    progress: ProgressSink | None = None,
    allow_coverage_loss: bool = False,
) -> BuildReport:
    """Index every collectable file under ``config.root`` into ``store`` (§8.1 steps 1-5).

    Adapters emit bare edges; ``resolve_edges`` links them after every node exists. Every collected
    path leaves a ``files`` row, parsed or not. When ``stub_roots`` is set, dependency trees are
    walked outside the normal ignore matcher and parsed declarations-only (task 039).
    """
    # Before ANY write, and here rather than in the caller: `full_build` is reached from five
    # places, two of them escalations inside `incremental_update` — one of which fires precisely
    # BECAUSE the adapter set narrowed (203, R1.8).
    if not allow_coverage_loss:
        lost = coverage_loss(store, config.adapter_cmds)
        if lost:
            raise CoverageLossError(lost)
    # Validate rules before any parse so a bad file fails loud without a half-built index (R5.3).
    rules = load_indirection_rules(config)
    _require_configured_adapters(config)
    report = _Progress(progress)
    store.set_meta(BUILD_COMPLETE_KEY, BUILD_INCOMPLETE)
    watchdog = _Watchdog(config.adapter_timeout)
    watchdog.start()
    try:
        report.phase("announce")
        announced = _announce(config, watchdog)
        try:
            owners = _owners(announced)
            report.phase("tree_walk")
            paths, census, untracked, ignore_sources, skipped_suffixes = _collect_with_census(
                config.root, tuple(owners)
            )
            stubs = (
                collect_stubs(config.root, config.stub_roots, tuple(owners))
                if config.stub_roots
                else ()
            )
            _reject_stub_source_overlap(paths, stubs)
            kept = tuple(sorted(dict.fromkeys([*paths, *stubs])))
            report.phase("reconcile")
            removed = _reconcile(store, kept)
            report.phase("parse", total=len(kept))
            counts = _parse_all(
                config, store, watchdog, announced, owners, kept, progress=report
            )
        finally:
            for adapter in announced.values():
                adapter.stop()
    finally:
        watchdog.stop()

    # No FTS rebuild here: §10's triggers keep `nodes_fts` current through every replace, so a
    # rebuild per build would cost a full re-index and change nothing (deviation D1).
    # The late writers link every bare edge, so the graph is not finished until they return.
    # Stamping before them advertised completion for the whole link phase (task 178).
    _count_late_writes(counts, config, store, rules, progress=report)
    report.phase("meta")
    _record_meta(
        config, store, tuple(owners), census, untracked, ignore_sources, skipped_suffixes
    )
    return BuildReport(files=len(kept), stubs=len(stubs), removed=removed, **counts)


# The answer a caller gets when the stored vocabulary era lags: one name for the cause and one
# for the route, read by both the build tool and `get_index_status` (201).
CONTRACT_REBUILD_REQUIRED = "contract_rebuild_required"
FULL_REBUILD_ROUTE = "code-atlas-build --full"
IN_BAND_FULL_REBUILD = "allow_full_rebuild=true"


COVERAGE_LOSS = "coverage_loss"
# No route. No registered tool can configure an adapter, and naming one that cannot answer the
# question is worse than naming none (R5.4c) — so this carries a hint and no route (203).
COVERAGE_LOSS_HINT = (
    "configure the missing adapter before rebuilding: set `adapter_cmd.<language>` in "
    ".code-atlas.toml, or export CA_<LANGUAGE>_CMD"
)
COVERAGE_LOSS_IN_BAND = "allow_coverage_loss=true"


class CoverageLossError(Exception):
    """A build would discard a language the index covers. Carries the languages (203)."""

    def __init__(self, lost: tuple[str, ...]) -> None:
        self.lost = lost
        super().__init__("would discard covered language(s): " + ", ".join(lost))


def coverage_loss(store: GraphStore, configured: Iterable[str]) -> tuple[str, ...]:
    """Languages the index COVERS that this run has no adapter command for (203).

    Covered-vs-**configured**, never covered-vs-started: an adapter that is configured and then
    fails to boot already refuses as ``no_usable_adapter``, which is a different fault.
    """
    raw = store.get_meta(COVERED_LANGUAGES_KEY) or ""
    # Both sides folded: config keys are lowercased at load, but `covered` comes from the
    # adapter's announced `name`, which — unlike `extensions` — the contract never lowercases.
    covered = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return tuple(sorted(covered - {name.lower() for name in configured}))


DELTA_TOO_LARGE = "delta_too_large"
# The fourth escalation, and the first that is not a correctness argument (212). The three above
# say a delta would be WRONG; this one says it would be SLOWER than the full build it replaces.
DELTA_TOO_LARGE_ROUTE = "code-atlas-build --full"


INCOMPLETE_INDEX = "incomplete_index"
# A build that was killed mid-write leaves a graph nothing can repair incrementally: HEAD has
# not moved, so the next diff is empty and the delete batches it already committed stay gone.
INCOMPLETE_INDEX_ROUTE = "code-atlas-build --full"


def build_incomplete(store: GraphStore) -> bool:
    """True when the last build started writing and never stamped its completion (202).

    The expression `get_index_status` already used for ``index_complete``, extracted so the
    staleness vocabulary and the write path read one derivation (R1.8/R6.7). An **absent** key
    is an index written before the key existed — unknowable, so it is not a claim either way.
    """
    stamped = store.get_meta(BUILD_COMPLETE_KEY)
    return stamped is not None and stamped != BUILD_COMPLETE


def contract_rebuild_required(store: GraphStore) -> bool:
    """True when the stored vocabulary era lags this build's — an incremental would mix them.

    One definition site for the decision ``incremental_update`` makes (R1.8): the build tool and
    ``get_index_status`` read it to answer *before* a rebuild starts, never a second comparison.
    """
    stored = store.get_meta(CONTRACT_VERSION_KEY)
    return stored is not None and stored != str(contract.CONTRACT_VERSION)


def incremental_update(
    config: Config,
    store: GraphStore,
    changed: Sequence[str],
    *,
    phase_times: dict[str, float] | None = None,
    progress: ProgressSink | None = None,
    scope: dict[str, object] | None = None,
    allow_coverage_loss: bool = False,
) -> BuildReport:
    """Re-index ``changed ∪ dependents`` and re-link into affected qnames (§8.3).

    ``changed`` is the git path set (commit range ∪ dirty tree); the caller falls back to
    :func:`full_build` when git cannot name one. Deletes and rename sources drop out of ``collect``
    and are reconciled away after their qnames are folded into ``affected``.

    When ``phase_times`` is set (profiler only — task 052), records per-phase wall seconds in place.
    When ``scope`` is set and the announced suffix set has moved, the escalation to a full build is
    recorded in place, so the report can name why it was not a no-op (task 172).
    """
    # Two independent reasons an incremental cannot extend this graph. Both are recorded when both
    # hold — disjoint keys, so neither has to win a precedence argument the caller cannot see.
    incomplete, era_moved = build_incomplete(store), contract_rebuild_required(store)
    if incomplete and scope is not None:
        # A graph left mid-write is not one an incremental can extend (202): HEAD has not moved,
        # so the next diff is empty over whatever the killed build had already deleted.
        scope[INCOMPLETE_INDEX] = {
            "escalated_to": "full",
            "route": INCOMPLETE_INDEX_ROUTE,
        }
    if era_moved and scope is not None:
        # Vocabulary changed — incremental would mix eras; force a full rebuild (task 030 AC1).
        scope["contract_change"] = {
            "stored": store.get_meta(CONTRACT_VERSION_KEY),
            "current": str(contract.CONTRACT_VERSION),
            "escalated_to": "full",
        }
    if incomplete or era_moved:
        return full_build(
            config, store, progress=progress, allow_coverage_loss=allow_coverage_loss
        )

    rules = load_indirection_rules(config)
    _require_configured_adapters(config)
    # Snapshot before the parse: a delta-scoped resolve is only equivalent to a full one while
    # the alias map is fixed, and the parse is what can change it (task 096).
    aliases_before = store.alias_targets()
    report = _Progress(progress)
    store.set_meta(BUILD_COMPLETE_KEY, BUILD_INCOMPLETE)
    watchdog = _Watchdog(config.adapter_timeout)
    watchdog.start()
    fingerprint_skipped = 0
    try:
        mark = time.monotonic()
        report.phase("announce")
        announced = _announce(config, watchdog)
        _phase_add(phase_times, "announce", mark)
        try:
            owners = _owners(announced)
            _require_unchanged_scope(store, owners)
            mark = time.monotonic()
            report.phase("tree_walk")
            paths, census, untracked, ignore_sources, skipped_suffixes = _collect_with_census(
                config.root, tuple(owners)
            )
            stubs = (
                collect_stubs(config.root, config.stub_roots, tuple(owners))
                if config.stub_roots
                else ()
            )
            _reject_stub_source_overlap(paths, stubs)
            _phase_add(phase_times, "tree_walk", mark)
            stub_set = set(stubs)
            wanted = set(paths)
            kept = tuple(sorted(wanted | stub_set))
            changed_set = set(changed)

            mark = time.monotonic()
            report.phase("reconcile")
            indexed = set(store.file_paths())
            prior = sorted(changed_set & indexed)
            affected = set(store.qnames_in_files(prior))
            # File nodes use the path as qname; include deleted/renamed-away paths so inbound edges
            # re-link (git diff names only the rename destination).
            affected.update(changed_set)
            gone = sorted(indexed - set(kept))
            affected.update(store.qnames_in_files(gone))
            affected.update(gone)
            dependents = set(store.file_paths_targeting(sorted(affected))) & wanted
            removed = _reconcile(store, kept)
            _phase_add(phase_times, "reconcile", mark)

            mark = time.monotonic()
            report.phase("hashing")
            candidates = sorted((changed_set | dependents) & wanted)
            # Dependents are unchanged by construction, so hash-skip must not apply to them —
            # replace_file_rows restores adapter tiers and duplicate keys that unlink cannot.
            to_parse: list[str] = []
            for path in candidates:
                if path in dependents:
                    to_parse.append(path)
                    continue
                if file_is_current(store, config.root, path):
                    continue
                if _fingerprint_skip(store, config.root, path):
                    fingerprint_skipped += 1
                    continue
                to_parse.append(path)
            # Stub roots bypass git collect; hash-gate them like normal files (R4.2).
            for path in sorted(stub_set):
                if path in indexed and file_is_current(store, config.root, path):
                    continue
                if path in indexed and _fingerprint_skip(store, config.root, path):
                    fingerprint_skipped += 1
                    continue
                if path not in to_parse:
                    to_parse.append(path)
            to_parse = list(dict.fromkeys(to_parse))
            _phase_add(phase_times, "hashing", mark)
            # 212: the first escalation that is about cost rather than correctness, and it is
            # decided HERE because `to_parse` — not the git diff — is the work the delta would do.
            # Off unless the operator sets a crossover: measuring this repo found none below its own
            # size (the delta's slope collapses once resolve saturates), and R2.3 forbids importing
            # another project's constant. `<= 0` is the disabled sentinel, so the comparison can
            # never fire on a repo that never measured its own crossover.
            crossover = config.full_build_crossover
            if crossover > 0 and len(to_parse) >= crossover:
                raise _TooLarge(len(to_parse), len(changed_set), crossover)

            mark = time.monotonic()
            report.phase("parse", total=len(to_parse))
            counts = (
                _parse_all(config, store, watchdog, announced, owners, to_parse, progress=report)
                if to_parse
                else {"parsed": 0, "failed": 0, "nodes": 0, "edges": 0}
            )
            _phase_add(phase_times, "parse", mark)
        finally:
            for adapter in announced.values():
                adapter.stop()
    except _TooLarge as heavy:
        # Same answer as the three correctness routes, for the opposite reason: this delta is not
        # wrong, it is slower. The key is written HERE, by the handler that takes the route, so the
        # report cannot name a full build that did not run.
        if scope is not None:
            scope[DELTA_TOO_LARGE] = {
                "to_parse": heavy.to_parse,
                "changed": heavy.changed,
                "crossover": heavy.crossover,
                "escalated_to": "full",
                "route": DELTA_TOO_LARGE_ROUTE,
            }
        return full_build(
            config, store, progress=progress, allow_coverage_loss=allow_coverage_loss
        )
    except _ScopeChanged as moved:
        # The same class of change as a `contract_version` bump above, and the same answer: a
        # suffix that entered scope is invisible to a delta the git diff never names (task 172).
        if scope is not None:
            scope["scope_change"] = {
                "added": list(moved.added),
                "removed": list(moved.removed),
                "escalated_to": "full",
            }
        return full_build(
            config, store, progress=progress, allow_coverage_loss=allow_coverage_loss
        )
    finally:
        watchdog.stop()

    # A true no-op (nothing parsed, nothing reconciled) leaves the graph unchanged, so the late
    # writers would only re-derive rows already present — full-graph work that was the ~56 s floor
    # and the 6,071-edge no-op number (task 080). Skip them; ``wrote.*`` then means the delta.
    if to_parse or removed:
        _count_late_writes(
            counts,
            config,
            store,
            rules,
            phase_times=phase_times,
            parsed=tuple(to_parse),
            aliases_before=aliases_before,
            progress=report,
        )
    else:
        # Record the skipped phases as ~0 so the profile shows the cut, not a missing phase (052).
        skipped = time.monotonic()
        _phase_add(phase_times, "enrichment", skipped)
        _phase_add(phase_times, "resolve", skipped)
    # After the link phase, never before it — see full_build (task 178).
    mark = time.monotonic()
    report.phase("meta")
    _record_meta(
        config, store, tuple(owners), census, untracked, ignore_sources, skipped_suffixes
    )
    _phase_add(phase_times, "meta", mark)
    return BuildReport(
        files=len(to_parse),
        stubs=len(stub_set & set(to_parse)),
        removed=removed,
        fingerprint_skipped=fingerprint_skipped,
        **counts,
    )


def _require_unchanged_scope(store: GraphStore, owners: Mapping[str, str]) -> None:
    """Raise when the announced suffix set differs from the one the index was built with (172)."""
    stored = store.get_meta(INDEXED_SUFFIXES_KEY)
    if stored is None:
        return
    was = {suffix for suffix in stored.split(",") if suffix}
    now = {suffix.lower() for suffix in owners}
    if was != now:
        raise _ScopeChanged(tuple(sorted(now - was)), tuple(sorted(was - now)))


def _phase_add(times: dict[str, float] | None, phase: str, started: float) -> None:
    """Accumulate one phase's wall seconds when the profiler dict is present (052)."""
    if times is None:
        return
    times[phase] = times.get(phase, 0.0) + (time.monotonic() - started)


def _count_late_writes(
    counts: dict[str, int],
    config: Config,
    store: GraphStore,
    rules: RulesPayload | None,
    *,
    phase_times: dict[str, float] | None = None,
    parsed: tuple[str, ...] | None = None,
    aliases_before: dict[str, str] | None = None,
    progress: "_Progress | None" = None,
) -> None:
    """Run the two writers that come after the parse tally, and fold what they wrote into it (051).

    Enrichment inserts its synthetic rows and the resolver inserts a sibling per extra candidate.
    A report built from the parse tally alone describes a smaller graph than the build just made.

    ``parsed`` scopes the resolve to that delta (096); it falls back to a full pass when the
    alias map moved, because ``_lookup_raw`` is only key-pure while that map is fixed.
    """
    mark = time.monotonic()
    if progress is not None:
        progress.phase("enrichment")
    enriched = apply_indirection_rules(config, store, payload=rules)
    _phase_add(phase_times, "enrichment", mark)
    mark = time.monotonic()
    if progress is not None:
        progress.phase("resolve")
    delta = None
    aliases_now = store.alias_targets()
    if parsed is not None and aliases_now == aliases_before:
        # Enrichment rewrites its rows *after* the parse under a synthetic path no delta lists,
        # so the bookmark is always in scope or its fresh edges would never resolve.
        delta = delta_scope(store, (*parsed, INDIRECTION_FILE), aliases=aliases_now)
    siblings = resolve_edges(store, max_candidates=config.max_results, delta=delta)
    _phase_add(phase_times, "resolve", mark)
    counts["nodes"] += enriched.nodes
    counts["edges"] += enriched.edges + siblings


def reparse_file(config: Config, store: GraphStore, path: str) -> bool:
    """Parse one relative path into ``store`` and re-link (read-through freshness, task 035).

    Returns ``False`` when no adapter owns the suffix, announce/parse/write fails, or the DB is
    locked — callers treat that as ``index_stale`` instead of crashing the read tool.
    Uses the same ``_write`` path as a full/incremental build so rows stay deterministic (R4).
    Soft-fails on any exception so a broken adapter never escapes a read tool (PR #41).
    """
    watchdog = _Watchdog(config.adapter_timeout)
    watchdog.start()
    try:
        try:
            announced = _announce(config, watchdog)
        except AdapterError:
            return False
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
                    result = adapter.parse(
                        path, declarations_only=is_stub_path(path, config.stub_roots)
                    )
            except AdapterError as error:
                result = ParseResult(path=path, ok=False, error=str(error))
            if is_stub_path(path, config.stub_roots) and result.ok:
                result = as_stub_result(result)
            tally = {"parsed": 0, "failed": 0, "nodes": 0, "edges": 0}
            try:
                digest = _digest(config.root / path)
                fingerprint = _whitespace_fingerprint(config.root / path)
                _write(
                    store,
                    path,
                    digest,
                    language,
                    result,
                    tally,
                    fingerprint=fingerprint,
                )
                resolve_edges(store, max_candidates=config.max_results, file_path=path)
            except Exception:
                return False
        finally:
            for adapter in announced.values():
                adapter.stop()
    except (OSError, TimeoutError):
        return False
    finally:
        watchdog.stop()
    return True


def file_is_current(store: GraphStore, root: Path, path: str) -> bool:
    """True when the indexed hash equals the file's current bytes — skip a no-op reparse (§8.3)."""
    digest = _digest(root / path)
    return bool(digest) and store.file_hash(path) == digest


def _fingerprint_skip(store: GraphStore, root: Path, path: str) -> bool:
    """True when bytes changed but the whitespace-normalised fingerprint did not (213).

    On a hit, refreshes the stored byte hash so the next run is a byte-hash hit. A fingerprint
    that cannot be computed (empty digest) never skips — fail loud into parse (R5.3).
    """
    fingerprint = _whitespace_fingerprint(root / path)
    if not fingerprint:
        return False
    stored = store.file_fingerprint(path)
    if stored is None or stored != fingerprint:
        return False
    digest = _digest(root / path)
    if not digest:
        return False
    store.touch_file_bytes(path, digest, fingerprint)
    return True


def _whitespace_fingerprint(path: Path) -> str:
    """SHA-256 of the file with line endings normalised and trailing whitespace stripped (213).

    Every newline and all leading whitespace survive, so two files sharing a fingerprint share
    every line number the graph stores — collapsing them would let a reformat skip the parse and
    strand ``line_start`` / ``line_end`` / ``edges.line`` at their pre-reformat values (R4.2).
    Language-agnostic: operates on bytes, never syntax (R1.1). Empty string when unreadable so
    the caller fails loud into parse (R5.3). Does not catch comment or string-literal edits.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    normalised = b"\n".join(line.rstrip() for line in raw.splitlines())
    return hashlib.sha256(normalised).hexdigest()


@dataclass(frozen=True)
class CollectionCensus:
    """The collect walk's own tally so an outsider can reconcile ``files`` (task 082).

    A partition of the walked set: ``collected - skipped_suffix - skipped_ignore == kept`` by
    construction. On a git repo ``collected == len(git ls-files)``. ``skipped_untracked`` sits
    beside that partition (task 092) — untracked files are never in ``collected``.
    """

    collected: int
    skipped_suffix: int
    skipped_ignore: int
    kept: int
    skipped_untracked: int = 0


def collect(root: Path, suffixes: Sequence[str]) -> tuple[str, ...]:
    """The paths to index: tracked files of a claimed suffix, minus the ignore rules (§8.1, §11).

    Sorted here rather than trusted from git, so the order is a property of this core and not of
    whichever git version the host ships (R4.2).
    """
    return _collect_with_census(root, suffixes)[0]


def _collect_with_census(
    root: Path, suffixes: Sequence[str]
) -> tuple[tuple[str, ...], CollectionCensus, tuple[str, ...], dict[str, int], dict[str, int]]:
    """``collect`` plus the by-cause census, from the SAME single walk (task 082, R4).

    Partitions the walked set into suffix-skipped / ignore-skipped / kept in one pass, so the
    reconciliation arithmetic closes by construction and no second traversal invents a rival count.
    Untracked indexable paths are a second **git spawn**, not a second filesystem walk (task 092).
    Ignore-skip attribution is a per-path source tag from the matcher already used (task 095).
    The by-suffix breakdown of ``skipped_suffix`` is counted in the same loop (task 174) — the whole
    tally, capped only where it is published, so the reader can say what the total is made of.
    """
    matcher = load_ignore(root)
    wanted = {suffix.lower() for suffix in suffixes}
    tracked = gitutil.ls_files(root)
    found = _walk(root, matcher, wanted) if tracked is None else tracked
    kept: list[str] = []
    skipped_suffix = skipped_ignore = 0
    ignore_sources: Counter[str] = Counter()
    skipped_suffixes: Counter[str] = Counter()
    for path in found:
        if (suffix := _suffix(path)) not in wanted:
            skipped_suffix += 1
            # A suffix-less file is its own bucket rather than an empty key nothing can read.
            skipped_suffixes[suffix or "(none)"] += 1
        elif (source := matcher.ignore_source(path)) is not None:
            skipped_ignore += 1
            ignore_sources[source] += 1
        else:
            kept.append(path)
    untracked = _indexable_untracked(root, wanted, matcher) if tracked is not None else ()
    census = CollectionCensus(
        len(found), skipped_suffix, skipped_ignore, len(kept), len(untracked)
    )
    return (
        tuple(sorted(kept)),
        census,
        untracked,
        dict(ignore_sources),
        dict(skipped_suffixes),
    )


def _indexable_untracked(
    root: Path, wanted: set[str], matcher: IgnoreMatcher
) -> tuple[str, ...]:
    """Untracked paths with a claimed suffix that code-atlas does not ignore (task 092)."""
    found = gitutil.ls_untracked(root)
    if found is None:
        return ()
    return tuple(
        path
        for path in found
        if _suffix(path) in wanted and not matcher.is_ignored(path)
    )


def indexable(paths: Iterable[str], root: Path, suffixes: Sequence[str]) -> tuple[str, ...]:
    """The subset of ``paths`` this index covers: claimed suffix, not ignored (§8.1, §11).

    The one definition of "indexable", so a caller asking *would this file be in the graph* can
    never drift from what :func:`collect` actually walks (047). Order follows ``paths``.
    """
    matcher = load_ignore(root)
    wanted = {suffix.lower() for suffix in suffixes}
    return tuple(
        path for path in paths if _suffix(path) in wanted and not matcher.is_ignored(path)
    )


def collect_stubs(
    root: Path, stub_roots: Sequence[str], suffixes: Sequence[str]
) -> tuple[str, ...]:
    """Filesystem walk of configured dependency roots — bypasses ignore/git (task 039).

    ``vendor/`` is a built-in ignore and usually gitignored, so neither ``collect`` nor
    ``git ls-files`` can see it. Stub indexing walks these trees directly. A configured root
    that is missing or not a directory fails loud (R5.3) — a typo must not look like stubs-off.
    """
    wanted = {suffix.lower() for suffix in suffixes}
    found: list[str] = []
    for stub in stub_roots:
        base = root / stub
        if not base.is_dir():
            raise ConfigError(f"stub_roots: {stub!r} is not a directory under {root}")
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in _STUB_SKIP_DIRS)
            for name in filenames:
                full = Path(dirpath) / name
                if full.suffix.lower() not in wanted:
                    continue
                rel = full.relative_to(root).as_posix()
                if _STUB_FILE_IGNORE.is_ignored(rel):
                    continue
                found.append(rel)
    return tuple(sorted(dict.fromkeys(found)))


def is_stub_path(path: str, stub_roots: Sequence[str] | None) -> bool:
    """True when ``path`` sits under a configured stub root."""
    if not stub_roots:
        return False
    return any(path == root or path.startswith(f"{root}/") for root in stub_roots)


def as_stub_result(result: ParseResult) -> ParseResult:
    """Stamp stub marker on nodes; drop CALLS/NEW edges (declarations-only backstop).

    The backstop is only ``CALLER_KINDS`` (CALLS/NEW). Body-level REFERENCES/IMPORTS from an
    adapter that ignores ``declarations_only`` can still land; honouring the flag is the adapter's
    job. Core never invents a language-specific body filter (R1.1).
    """
    if not result.ok:
        return result
    drop = frozenset(contract.CALLER_KINDS)
    nodes = tuple(_stamp_stub_node(dict(node)) for node in result.nodes)
    edges = tuple(
        edge for edge in result.edges if str(edge.get("kind") or "") not in drop
    )
    return ParseResult(
        path=result.path, ok=True, nodes=nodes, edges=edges, error=result.error
    )


def _reject_stub_source_overlap(paths: Sequence[str], stubs: Sequence[str]) -> None:
    """Fail loud when a stub root overlaps git-collected source (R5.3)."""
    clash = sorted(set(paths) & set(stubs))
    if clash:
        preview = ", ".join(clash[:3])
        raise ConfigError(
            f"stub_roots overlap collected source: {preview} "
            f"({len(clash)} files) — a stub root must hold dependencies only"
        )


def _stamp_stub_node(node: dict[str, object]) -> dict[str, object]:
    """Merge the stub flag into ``extra`` JSON without dropping a prior payload."""
    data: dict[str, object] = {}
    raw = node.get("extra")
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                data = parsed
            else:
                data = {"extra_value": parsed}
        except json.JSONDecodeError:
            data = {"raw_extra": raw}
    elif isinstance(raw, dict):
        data = dict(raw)
    data[contract.STUB_FLAG] = True
    node["extra"] = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return node


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


def _require_configured_adapters(config: Config) -> None:
    """Empty ``adapter_cmds`` is misconfiguration, not an empty repo (task 064 / R5.3)."""
    if config.adapter_cmds:
        return
    raise AdapterError(
        "no adapters configured — set CA_<LANG>_CMD or .code-atlas.toml [adapter_cmd].<lang>"
    )


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
    """Drop every indexed path the collection no longer yields, with its nodes and edges (§8.1).

    No bookmark exemption: since 068 the rules path has no ``files`` row, so it cannot appear here.
    A pre-068 row does, and reconciling it away *is* the purge — enrichment, which runs after,
    re-inserts its edges in the same build.
    """
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
    progress: "_Progress | None" = None,
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
            _parse_group(
                config,
                store,
                watchdog,
                key,
                languages[key],
                first,
                group,
                tally,
                pending,
                progress,
            )

    for path in sorted(pending):
        # Nothing ever answered for these: every worker retired, or none could be started.
        language = languages[owners[_suffix(path)]]
        store.upsert_file(
            path,
            _digest(config.root / path),
            language,
            parsed_ok=False,
            fingerprint=_whitespace_fingerprint(config.root / path) or None,
        )
        tally["failed"] += 1
        if progress is not None:
            progress.tick()
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
    progress: "_Progress | None" = None,
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
        fingerprint = _whitespace_fingerprint(config.root / path)
        _write(
            store, path, digest, language, result, tally, fingerprint=fingerprint
        )
        pending.discard(path)
        if progress is not None:
            progress.tick()
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
                    result = adapter.parse(
                        path, declarations_only=is_stub_path(path, config.stub_roots)
                    )
            except AdapterError as error:
                result = ParseResult(path=path, ok=False, error=str(error))
                adapter.stop()
                adapter = None
            if is_stub_path(path, config.stub_roots) and result.ok:
                result = as_stub_result(result)
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
    *,
    fingerprint: str | None = None,
) -> None:
    """Persist one file's outcome. Edges go in exactly as the adapter emitted them — bare (R3.3)."""
    store.upsert_file(
        path, digest, language, parsed_ok=result.ok, fingerprint=fingerprint or None
    )
    try:
        deduped = store.replace_file_rows(path, result.nodes, result.edges)
    except WRITE_ERRORS:
        # A per-file store error is a bad *file*, not a bad build: soft-fail and continue (R5.1).
        store.upsert_file(
            path, digest, language, parsed_ok=False, fingerprint=fingerprint or None
        )
        tally["failed"] += 1
        return
    if result.ok:
        tally["parsed"] += 1
        tally["nodes"] += len(result.nodes) - deduped
        tally["edges"] += len(result.edges)
    else:
        tally["failed"] += 1


def _record_meta(
    config: Config,
    store: GraphStore,
    suffixes: Sequence[str],
    census: CollectionCensus,
    untracked: tuple[str, ...] = (),
    ignore_sources: Mapping[str, int] | None = None,
    skipped_suffixes: Mapping[str, int] | None = None,
) -> None:
    """Stamp the build (§8.1 step 4). Clear commit/ref when git cannot name them (077).

    The collection census is stamped so verbose ``get_index_status`` can publish the denominator an
    outsider reconciles ``files`` against, without re-walking the tree (task 082, R4). Untracked
    indexable paths and per-source ignore counts live on sibling keys — ``collection_census()``
    int-casts every value (092 / 095).
    """
    store.set_meta(CONTRACT_VERSION_KEY, str(contract.CONTRACT_VERSION))
    store.set_meta(BUILT_AT_KEY, store.now())
    # Both build paths reach here only after the late writes, so this is the graph's completion
    # stamp as well as its revision stamp (task 178).
    store.set_meta(BUILD_COMPLETE_KEY, BUILD_COMPLETE)
    claimed = sorted({s.lower() for s in suffixes})
    store.set_meta(INDEXED_SUFFIXES_KEY, ",".join(claimed))
    # What the graph HOLDS, beside what the build CLAIMED (task 173). Both are stamped here, once
    # per build, so no answer pays a scan of ``files`` to know the index's own coverage gaps.
    store.set_meta(COVERED_SUFFIXES_KEY, ",".join(store.suffixes_with_files(claimed)))
    store.set_meta(COVERED_LANGUAGES_KEY, ",".join(store.indexed_languages()))
    # Which adapter's edges are healthy, stamped here for the same reason (task 183): a
    # whole-graph blend cannot be attributed, and a GROUP BY over edges must not reach an answer.
    # One scan, both facts (183's tier mix + 186's emitted-kind sets) — see edge_language_census.
    languages = store.edge_language_census()
    store.set_meta(EDGE_HEALTH_BY_LANGUAGE_KEY, json.dumps(languages.health, sort_keys=True))
    store.set_meta(EMITTED_KINDS_BY_LANGUAGE_KEY, json.dumps(languages.kinds, sort_keys=True))
    store.set_meta(COLLECTION_CENSUS_KEY, json.dumps(asdict(census)))
    store.set_meta(UNTRACKED_INDEXABLE_KEY, json.dumps(list(untracked)))
    sources = {key: count for key, count in dict(ignore_sources or {}).items() if count}
    store.set_meta(IGNORE_SOURCES_KEY, json.dumps(dict(sorted(sources.items()))))
    # Which config produced these contents (task 175). The index can now be asked, so a rebuild
    # after a config edit is checkable rather than a matter of remembering.
    store.set_meta(CONFIG_IDENTITY_KEY, config.identity)
    # What `skipped_suffix` is made of — its own key, not inside the int-casting census (R1.7).
    by_suffix = {key: count for key, count in dict(skipped_suffixes or {}).items() if count}
    store.set_meta(SKIPPED_SUFFIX_COUNTS_KEY, json.dumps(dict(sorted(by_suffix.items()))))
    commit, ref = gitutil.head_commit_and_ref(config.root)
    if commit is not None:
        store.set_meta(LAST_COMMIT_KEY, commit)
    else:
        store.delete_meta(LAST_COMMIT_KEY)
    if ref is not None:
        store.set_meta(LAST_REF_KEY, ref)
    else:
        store.delete_meta(LAST_REF_KEY)


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
