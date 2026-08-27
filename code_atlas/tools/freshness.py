"""Query-time read-through freshness — repair drifted files before answering (035 / 073)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from code_atlas import gitutil
from code_atlas.config import Config
from code_atlas.indexer import file_is_current, indexable, reparse_file
from code_atlas.store import INDEXED_SUFFIXES_KEY, LAST_COMMIT_KEY, GraphStore

# Cap reparses per tool call (WANT-1 / Goal: one adapter call). Overflow → index_stale.
READ_THROUGH_CAP = 1

EnsureResult = Literal["ok", "repaired", "stale"]


@dataclass
class FreshnessGuard:
    """Per-call budget for inline reparses against one open store.

    Result-driven repair (035): paths already on the answer are hash-checked. Miss-driven
    repair (073): a zero-hit query may spend the same cap on the sole dirty indexed file.
    Multiple dirty indexed files cannot be chosen under the cap — callers get ``stale``.
    """

    config: Config
    store: GraphStore
    cap: int = READ_THROUGH_CAP
    _used: int = field(default=0, init=False)

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
        return self.ensure_miss()

    def ensure_miss(self) -> EnsureResult:
        """When a query matched nothing: repair the sole dirty indexed file, else signal.

        Zero dirty → ``ok`` (absence is as current as the index). Exactly one → ``ensure`` it.
        Multiple → ``stale`` without spending the cap (no deterministic single subject under
        ``READ_THROUGH_CAP``). Requires git ``dirty_paths``; outside a repo returns ``ok``.
        """
        candidates = dirty_indexed_paths(self.store, self.config)
        if not candidates:
            return "ok"
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
