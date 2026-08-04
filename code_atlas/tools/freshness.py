"""Query-time read-through freshness — repair drifted files before shaping a response (035)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from code_atlas.config import Config
from code_atlas.indexer import file_is_current, reparse_file
from code_atlas.store import GraphStore

# Cap reparses per tool call (WANT-1 / Goal: one adapter call). Overflow → index_stale.
READ_THROUGH_CAP = 1

EnsureResult = Literal["ok", "repaired", "stale"]


@dataclass
class FreshnessGuard:
    """Per-call budget for inline reparses against one open store."""

    config: Config
    store: GraphStore
    cap: int = READ_THROUGH_CAP
    _used: int = field(default=0, init=False)

    def ensure(self, path: str) -> EnsureResult:
        """Return ``ok`` if current, ``repaired`` after a successful reparse, else ``stale``."""
        if not path:
            return "ok"
        # Planted-store tests and missing paths have nothing to hash — trust the index.
        if not (self.config.root / path).is_file():
            return "ok"
        if file_is_current(self.store, self.config.root, path):
            return "ok"
        if self._used >= self.cap:
            return "stale"
        if not reparse_file(self.config, self.store, path):
            return "stale"
        self._used += 1
        return "repaired"

    def ensure_qname(self, qname: str) -> EnsureResult:
        """Ensure the indexed file for ``qname`` when a node row exists."""
        rows = self.store.nodes_by_qualified_name(qname, limit=1)
        if not rows:
            return "ok"
        return self.ensure(str(rows[0]["file_path"]))

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
