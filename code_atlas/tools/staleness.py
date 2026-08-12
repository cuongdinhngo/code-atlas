"""Shared commit/dirty staleness vocabulary (tasks 047, 072, 077).

One source for ``staleness`` / ``last_commit`` / ``head_commit`` / ``last_ref`` / ``head_ref`` so
``get_index_status`` and the ``build_or_update_index`` busy refusal speak one vocabulary, not two.
Staleness counts only files the index covers (047): a dirty README is not a stale graph. Refs name
the revision humans reason in without re-modelling ``current``/``behind``/``unknown`` (077).
"""

from __future__ import annotations

from code_atlas.config import Config
from code_atlas.gitutil import dirty_paths, head_commit_and_ref
from code_atlas.indexer import indexable
from code_atlas.store import INDEXED_SUFFIXES_KEY, LAST_COMMIT_KEY, LAST_REF_KEY, GraphStore

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


OMIT: object = object()


def last_ref_for_payload(store: GraphStore) -> str | None | object:
    """Value for ``last_ref``, or ``OMIT`` when the index predates 077 (key absent, SHA present).

    ``null`` means non-git / cleared — never "built before this field existed" (061 / 077).
    """
    if store.has_meta(LAST_REF_KEY):
        return store.get_meta(LAST_REF_KEY)
    if store.get_meta(LAST_COMMIT_KEY) is not None:
        return OMIT
    return None


def compute_staleness(
    store: GraphStore, config: Config, *, include_dirty_count: bool = False
) -> dict[str, object]:
    """Staleness fields for status and busy (072 / 077). One git HEAD read for SHA + ref.

    ``last_ref`` is omitted (not null) when the index predates 077 so agents do not read
    "non-git" off a current SHA index. Busy callers ignore ``dirty_indexed_files``.
    """
    last_commit = store.get_meta(LAST_COMMIT_KEY)
    head, href = head_commit_and_ref(config.root)
    dirty, dirty_count = dirty_indexed(store, config)
    fields: dict[str, object] = {
        "last_commit": last_commit,
        "head_commit": head,
        "head_ref": href,
        "staleness": staleness_of(last_commit, head, dirty=dirty),
    }
    ref = last_ref_for_payload(store)
    if ref is not OMIT:
        fields["last_ref"] = ref
    if include_dirty_count:
        fields["dirty_indexed_files"] = dirty_count
    return fields
