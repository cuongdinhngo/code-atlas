"""Query-time read-through freshness — repair drifted files before answering (035 / 073 / 246)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from code_atlas import gitutil
from code_atlas.config import Config
from code_atlas.contract import MEMBER_SEPARATOR
from code_atlas.index_lock import build_in_progress
from code_atlas.indexer import file_is_current, indexable, reparse_file
from code_atlas.store import (
    INDEXED_SUFFIXES_KEY,
    LAST_COMMIT_KEY,
    GraphStore,
    shadow_db_path,
)
from code_atlas.tools.claim import REV_CHARS
from code_atlas.tools.nav_result import (
    REASON_INDEX_BEHIND,
    REASON_INDEX_BEHIND_SUBJECT_CHANGED,
    REASON_INDEX_STALE,
    REASON_OK,
    REASON_SUBJECT_FILE_CHECKED,
    classify_missing_subject,
)
from code_atlas.tools.staleness import BEHIND

# Cap reparses per tool call (WANT-1 / Goal: one adapter call). Overflow → index_stale.
# 246 keeps this at 1: subject-scoped miss spends ≤1 reparse; raising with dirty-count
# would reparse a branch on one call (measured: AC1 fixture, 3 unrelated drifts → 0 reparses).
READ_THROUGH_CAP = 1

EnsureResult = Literal["ok", "repaired", "stale"]


def nameable_subject_path(store: GraphStore, qname: str) -> str | None:
    """Return the indexed file path encoded in ``qname``, if any (246).

    A path-shaped qname (``src/Foo.aa::bar``, ``src/user.ts::User::save``) names a ``files``
    row. Namespace-shaped names (``\\App\\Foo::bar``) do not — mapping those would be a
    language branch in the core (R1.1). Walk ``::`` prefixes; first ``files`` hit wins.
    """
    if not qname:
        return None
    if store.file_hash(qname) is not None:
        return qname
    parts = qname.split(MEMBER_SEPARATOR)
    for i in range(1, len(parts)):
        prefix = MEMBER_SEPARATOR.join(parts[:i])
        if store.file_hash(prefix) is not None:
            return prefix
    return None


def miss_subject_path(store: GraphStore, qname: str, *, limit: int) -> str | None:
    """The file a zero-hit ``qname`` is about: its own path, else its one name variant's (354).

    Without the variant a misqualified name is unnameable, so several dirty files refuse it as
    ``index_stale`` before the miss path could name the symbol it meant.
    """
    named = nameable_subject_path(store, qname)
    if named is not None:
        return named
    resolution = classify_missing_subject(store, qname, limit=limit)
    if resolution.status == "resolved_unique":
        variant = resolution.qname
    elif resolution.stored_shorter:
        variant = resolution.stored_shorter[0]
    else:
        return None
    rows = store.nodes_by_qualified_name(variant, limit=1)
    return str(rows[0]["file_path"]) if rows else None


@dataclass
class FreshnessGuard:
    """Per-call budget for inline reparses against one open store.

    Result-driven repair (035): paths already on the answer are hash-checked. Miss-driven
    repair (073/246): a zero-hit query may spend the same cap on a *named* subject's file,
    or on the sole dirty indexed file when the subject cannot be named. Unrelated dirty
    files no longer force ``stale`` when the subject file is known (246).
    """

    config: Config
    store: GraphStore
    cap: int = READ_THROUGH_CAP
    _used: int = field(default=0, init=False)
    other_indexed_files_drifted: int = field(default=0, init=False)
    # A writer held the DB when a repair was due: the refresh is the repair (365).
    build_held: bool = field(default=False, init=False)

    @property
    def used(self) -> int:
        """How many reparses this guard has spent (for gating post-repair re-queries)."""
        return self._used

    def ensure(self, path: str) -> EnsureResult:
        """Return ``ok`` if current, ``repaired`` after a successful reparse, else ``stale``."""
        if not path:
            return "ok"
        # Missing on disk: cannot vouch for indexed rows (planted fixtures must write real bytes).
        if not (self.config.root / path).is_file():
            return "stale"
        if file_is_current(self.store, self.config.root, path):
            return "ok"
        if self._used >= self.cap:
            return "stale"
        if self._index_held():
            self.build_held = True
            return "stale"
        if not reparse_file(self.config, self.store, path):
            return "stale"
        self._used += 1
        return "repaired"

    def _index_held(self) -> bool:
        """Is an in-place writer on the live DB, so a repair would wait behind it? (365)

        Mid-transaction, or between its transactions while it holds ``write.lock``. A 356 full
        rebuild writes the shadow and leaves the live DB free, so it never counts.
        """
        if self.store.write_locked():
            return True
        db_path = self.config.db_path
        return build_in_progress(db_path) and not shadow_db_path(db_path).exists()

    def ensure_qname(self, qname: str) -> EnsureResult:
        """Ensure the indexed file for ``qname``, or miss-repair when no node row exists (073)."""
        rows = self.store.nodes_by_qualified_name(qname, limit=1)
        if rows:
            return self.ensure(str(rows[0]["file_path"]))
        return self.ensure_miss(miss_subject_path(self.store, qname, limit=self.config.page_limit))

    def ensure_miss(self, subject_path: str | None = None) -> EnsureResult:
        """When a query matched nothing: repair a named subject file, or the sole dirty file.

        Zero dirty → ``ok``. Named ``subject_path`` → decide on that file only; stash how many
        *other* indexed files drifted (246 residue). Unnameable + multiple dirty → ``stale``
        without spending the cap (073). Requires git ``dirty_paths``; outside a repo returns ``ok``.
        """
        self.other_indexed_files_drifted = 0
        candidates = dirty_indexed_paths(self.store, self.config)
        if not candidates:
            return "ok"
        if subject_path is not None:
            others = [p for p in candidates if p != subject_path]
            self.other_indexed_files_drifted = len(others)
            if subject_path not in candidates:
                return "ok"
            return self.ensure(subject_path)
        if len(candidates) > 1:
            return "stale"
        return self.ensure(candidates[0])

    def ensure_paths(self, paths: list[str]) -> EnsureResult:
        """Ensure each path in order; return ``stale`` if any drifted file cannot be repaired."""
        worst: EnsureResult = "ok"
        seen: set[str] = set()
        for path in paths:
            if not path or path in seen:
                continue
            seen.add(path)
            status = self.ensure(path)
            if status == "stale":
                return "stale"
            if status == "repaired":
                worst = "repaired"
        return worst


def attach_other_indexed_files_drifted(
    payload: dict[str, object], guard: FreshnessGuard
) -> dict[str, object]:
    """Omit-when-empty (061): name how many unrelated indexed files drifted (246)."""
    n = guard.other_indexed_files_drifted
    if n > 0:
        payload["other_indexed_files_drifted"] = n
    return payload


def finalize_subject_checked_miss(
    payload: dict[str, object], guard: FreshnessGuard
) -> dict[str, object]:
    """On a miss after a named subject check: weaker ``reason`` + residue count (246)."""
    if guard.other_indexed_files_drifted > 0:
        payload["reason"] = REASON_SUBJECT_FILE_CHECKED
        payload["other_indexed_files_drifted"] = guard.other_indexed_files_drifted
    return payload


def dirty_indexed_paths(store: GraphStore, config: Config) -> list[str]:
    """Sorted drifted tracked paths this index covers — empty when git cannot answer (073).

    Drift is measured against the **indexed commit**, not just the working tree: a file changed
    and committed after the index was built is not working-tree-dirty, yet the index still predates
    it (166). ``changed_paths`` unions ``indexed_commit..HEAD`` with the working tree, so both a
    ``git pull`` and an uncommitted edit are seen. No indexed commit (non-git / legacy) → the
    working-tree signal alone.
    """
    last_commit = store.get_meta(LAST_COMMIT_KEY)
    paths = (
        gitutil.changed_paths(config.root, last_commit)
        if last_commit
        else gitutil.dirty_paths(config.root)
    )
    if not paths:
        return []
    suffixes = store.get_meta(INDEXED_SUFFIXES_KEY)
    if not suffixes:
        return []
    return list(indexable(paths, config.root, suffixes.split(",")))


def unrepaired_subject_served(
    store: GraphStore,
    qname: str,
    *,
    serve_behind: bool,
    dirty_paths: Sequence[str],
) -> bool:
    """Whether a ``stale`` verdict may still be answered, labelled rather than refused (267).

    True only when the caller opted in and the subject's own file is one of the dirty paths the
    pre-call census named — the case 257 left refusing. Anything else keeps ``index_stale``.
    """
    if not serve_behind:
        return False
    rows = store.nodes_by_qualified_name(qname, limit=1)
    subject = str(rows[0]["file_path"]) if rows else nameable_subject_path(store, qname)
    return subject is not None and subject in set(dirty_paths)


def _refuse_as_stale(payload: dict[str, object]) -> dict[str, object]:
    """An unrepaired dirty subject with no revision to stamp is a refusal, not an answer (267)."""
    payload["reason"] = REASON_INDEX_STALE
    payload["results"] = []
    payload["total_count"] = 0
    payload.pop("last_commit", None)
    return payload


def label_serve_behind(
    payload: dict[str, object],
    *,
    serve_behind: bool,
    subject_path: str | None,
    revision: Mapping[str, object] | None,
    dirty_paths: Sequence[str],
    subject_unrepaired: bool = False,
) -> dict[str, object]:
    """When opt-in and the index is behind, label a served answer (257 / 267).

    Read-through repair (035) stays first. Repaired subjects stay ``reason: ok``.
    Unchanged subjects on a behind index → ``index_behind`` (257). When freshness
    declined on a dirty subject and the caller continued under ``serve_behind``,
    → ``index_behind_subject_changed`` (267). Never stamp without a revision; an
    unrepaired dirty subject that cannot be stamped is refused as ``index_stale``.
    """
    if not serve_behind:
        return payload
    subject_dirty = subject_path is not None and subject_path in set(dirty_paths)
    unrepaired = subject_unrepaired and subject_dirty
    commit = revision.get("last_commit") if revision is not None else None
    stampable = (
        revision is not None
        and revision.get("staleness") == BEHIND
        and isinstance(commit, str)
        and bool(commit)
    )
    if not stampable:
        return _refuse_as_stale(payload) if unrepaired else payload
    assert isinstance(commit, str)  # narrowed by `stampable`
    if payload.get("reason") == REASON_INDEX_STALE:
        return payload
    if unrepaired:
        payload["reason"] = REASON_INDEX_BEHIND_SUBJECT_CHANGED
    elif subject_dirty:
        # Still dirty in the pre-repair census but repaired this call — leave alone.
        return payload
    elif payload.get("reason") == REASON_OK:
        payload["reason"] = REASON_INDEX_BEHIND
    payload["last_commit"] = commit
    short = commit[:REV_CHARS]
    results = payload.get("results")
    if isinstance(results, list):
        for row in results:
            if isinstance(row, dict):
                row["index_revision"] = short
    return payload
