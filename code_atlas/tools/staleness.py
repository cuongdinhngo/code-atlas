"""Shared commit/dirty staleness vocabulary (tasks 047, 072).

One source for ``staleness`` / ``last_commit`` / ``head_commit`` so ``get_index_status`` and the
``build_or_update_index`` busy refusal speak one vocabulary, not two. Staleness counts only files
the index covers (047): a dirty README is not a stale graph.
"""

from __future__ import annotations

from code_atlas.config import Config
from code_atlas.gitutil import dirty_paths, head_commit
from code_atlas.indexer import indexable
from code_atlas.store import INDEXED_SUFFIXES_KEY, LAST_COMMIT_KEY, GraphStore

CURRENT = "current"
BEHIND = "behind"
UNKNOWN = "unknown"


def dirty_indexed(store: GraphStore, config: Config) -> tuple[bool | None, int | None]:
    """Are any *indexed* files dirty, and how many — a dirty README is not a stale graph (047).

    Falls back to the whole tracked tree when the index predates this key, which over-reports
    rather than promising freshness it cannot check (R5.2's spirit: never claim the stronger tier).
    """
    paths = dirty_paths(config.root)
    if paths is None:
        return None, None
    suffixes = store.get_meta(INDEXED_SUFFIXES_KEY)
    if not suffixes:
        return bool(paths), None
    hits = indexable(paths, config.root, suffixes.split(","))
    return bool(hits), len(hits)


def staleness_of(last_commit: str | None, head: str | None, *, dirty: bool | None) -> str:
    """``unknown`` unless both commits known; ``behind`` if HEAD moved or ``dirty`` (047)."""
    if last_commit is None or head is None:
        return UNKNOWN
    if last_commit != head:
        return BEHIND
    if dirty:
        return BEHIND
    return CURRENT


def compute_staleness(store: GraphStore, config: Config) -> dict[str, str | None]:
    """The three staleness fields ``get_index_status`` reports, reused on other payloads (072)."""
    last_commit = store.get_meta(LAST_COMMIT_KEY)
    head = head_commit(config.root)
    dirty, _ = dirty_indexed(store, config)
    return {
        "last_commit": last_commit,
        "head_commit": head,
        "staleness": staleness_of(last_commit, head, dirty=dirty),
    }
