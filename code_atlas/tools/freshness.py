"""Query-time read-through freshness — repair drifted files before answering (035 / 073 / 246)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from code_atlas import gitutil
from code_atlas.config import Config
from code_atlas.contract import MEMBER_SEPARATOR
from code_atlas.indexer import file_is_current, indexable, reparse_file
from code_atlas.store import INDEXED_SUFFIXES_KEY, LAST_COMMIT_KEY, GraphStore
from code_atlas.tools.nav_result import REASON_SUBJECT_FILE_CHECKED

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
        if not reparse_file(self.config, self.store, path):
            return "stale"
        self._used += 1
        return "repaired"

    def ensure_qname(self, qname: str) -> EnsureResult:
        """Ensure the indexed file for ``qname``, or miss-repair when no node row exists (073)."""
        rows = self.store.nodes_by_qualified_name(qname, limit=1)
        if rows:
            return self.ensure(str(rows[0]["file_path"]))
        return self.ensure_miss(nameable_subject_path(self.store, qname))

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
