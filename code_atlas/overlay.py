"""A worktree overlay: answer from the caller's checkout without building or storing it (389).

When the caller works in another checkout of the indexed repository (its MCP roots, or
``CA_CALLER_ROOT``), the files that differ between the built commit and that checkout —
``git diff <built>`` plus untracked files — are parsed through their adapters on demand and
never written (R1.4). Every other file's bytes equal the built commit's, so the graph answers for
it as built. The overlay is keyed on the worktree and the built commit, never on the index
checkout's HEAD, so switching that checkout changes nothing a worktree is told.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from code_atlas import gitutil
from code_atlas.adapter import ParseResult
from code_atlas.config import Config
from code_atlas.containment import resolves_inside
from code_atlas.contract import CONFIDENCE_TIERS, MEMBER_SEPARATOR, UNLINKED_EVIDENCE_KINDS
from code_atlas.indexer import file_is_current, indexable, parse_files
from code_atlas.ref_check import OVERLAY_FIELD, OVERLAY_WORKTREE, caller_checkout
from code_atlas.store import INDEXED_SUFFIXES_KEY, LAST_COMMIT_KEY, GraphStore, stored
from code_atlas.tools.nav_result import (
    REASON_INDEX_BEHIND,
    REASON_NO_MATCHES,
    REASON_OK,
    REASON_WORKTREE_OVERLAY,
    edge_hit,
)

OVERLAY_ROOT_FIELD = "overlay_root"
OVERLAY_TRUNCATED_FIELD = "overlay_truncated"
OVERLAY_UNLINKED_FIELD = "overlay_unlinked_same_name"
OVERLAY_FIRST_HOP_FIELD = "overlay_first_hop_only"
# Files one call may parse through an adapter; past it the answer says it stopped looking.
OVERLAY_PARSE_CAP = 25

Parsed = tuple[list[dict[str, object]], list[dict[str, object]]]


@dataclass
class Overlay:
    """The caller's worktree for one call: which files differ, and their parse, read once each."""

    config: Config
    changed: frozenset[str]
    truncated: bool = False
    _parsed: dict[str, Parsed | None] = field(default_factory=dict)
    # Unchanged in the worktree, yet its built rows were since re-read from another checkout.
    _drifted: set[str] = field(default_factory=set)
    _same: set[str] = field(default_factory=set)
    _parses: int = 0

    @property
    def root(self) -> Path:
        return self.config.root

    def parsed(self, rel: str) -> Parsed | None:
        """``rel``'s nodes and edges in the worktree; empty when deleted, None when unreadable."""
        if rel in self._parsed:
            return self._parsed[rel]
        if not (self.root / rel).is_file():
            self._parsed[rel] = ([], [])
            return self._parsed[rel]
        room = OVERLAY_PARSE_CAP - self._parses
        if room <= 0:
            self.truncated = True
            return None
        # One adapter start reads every changed file still unread, not one start per file.
        rest = sorted(r for r in self.changed - {rel} if r not in self._parsed)
        batch = [rel, *(r for r in rest if (self.root / r).is_file())][:room]
        self._parses += len(batch)
        try:
            found = parse_files(self.config, batch)
        except (OSError, TimeoutError):
            found = {}
        for path in batch:
            self._parsed[path] = _rows(found.get(path), path)
        return self._parsed[rel]

    def changes(self, rel: str) -> bool:
        """Do this worktree's bytes for ``rel`` differ from the rows the store holds for it?

        A file the worktree did not change can still differ: read-through repair in another
        checkout rewrites the shared store's rows for it (389 challenger F5).
        """
        if rel in self.changed or rel in self._drifted:
            return True
        if not rel or rel in self._same:
            return False
        if not resolves_inside(self.root, self.root / rel):
            self._same.add(rel)  # never read outside the worktree, as the build never does
            return False
        # Its own read: an answer is often finished after the tool's connection closed.
        with GraphStore(self.config.db_path) as store:
            drifted = store.file_hash(rel) is not None and not file_is_current(
                store, self.root, rel
            )
        (self._drifted if drifted else self._same).add(rel)
        return drifted

    @property
    def differing(self) -> list[str]:
        """Every file known to differ so far, sorted (R4.2)."""
        return sorted(self.changed | self._drifted)

    def unread(self, rel: str) -> bool:
        """A differing file whose worktree parse could not be had (adapter failure or the cap)."""
        return self.parsed(rel) is None

    def nodes(self, rel: str) -> list[dict[str, object]]:
        found = self.parsed(rel)
        return [] if found is None else found[0]

    def edges(self, rel: str) -> list[dict[str, object]]:
        found = self.parsed(rel)
        return [] if found is None else found[1]

    def find(self, qname: str, first: str | None = None) -> dict[str, object] | None:
        """The one worktree node named ``qname``: ``first``'s file, then every changed file."""
        differing = self.differing
        order = ([first] if first in differing else []) + [r for r in differing if r != first]
        for rel in order:
            hits = [n for n in self.nodes(rel) if n.get("qualified_name") == qname]
            if len(hits) == 1:
                return hits[0]
        return None

    def label(self, payload: dict[str, object]) -> dict[str, object]:
        """Say the worktree answered, and never claim the built ref for it.

        A worktree identical to the built commit changes no answer, so it labels none (366).
        """
        if not self.changed and not self._drifted:
            return payload
        payload[OVERLAY_FIELD] = OVERLAY_WORKTREE
        payload[OVERLAY_ROOT_FIELD] = str(self.root)
        if self.truncated:
            payload[OVERLAY_TRUNCATED_FIELD] = True
        if "answered_about_ref" in payload:
            payload["answered_about_ref"] = None
        return payload


def active_overlay(config: Config, store: GraphStore) -> Overlay | None:
    """The caller's worktree overlay, or None when the caller is in the index checkout (AC4)."""
    root = caller_checkout(config)
    if root is None:
        return None
    built = store.get_meta(LAST_COMMIT_KEY)
    suffixes = store.get_meta(INDEXED_SUFFIXES_KEY)
    if not built or not suffixes:
        return None
    diffs = gitutil.changed_paths(root, built, renames=False)
    if diffs is None:
        return None
    paths = sorted(set(diffs) | set(gitutil.ls_untracked(root) or ()))
    changed = frozenset(indexable(paths, root, suffixes.split(",")))
    return Overlay(replace(config, root=root), changed)


# The worktree's own edges are read, never linked by the resolver: HEURISTIC at best (389).
_HEURISTIC = CONFIDENCE_TIERS[1]
# Partitions computed over the built rows, which the swap below no longer matches (R5.5).
_BUILT_PARTITIONS = ("production_count", "test_count", "test_role_source", "tier_census")


def overlay_inbound(
    overlay: Overlay,
    payload: dict[str, object],
    subject: str,
    kinds: Sequence[str] | None,
    *,
    depth: int,
    offset: int,
) -> dict[str, object]:
    """Swap this page's rows from changed files for the worktree's own edges onto ``subject``.

    A worktree edge counts when its ``target_raw`` names the stored qname; at depth > 1 only the
    first hop is the worktree's; ``kinds=None`` reads every inbound kind but containment. Only
    the ``offset=0`` page carries the worktree's edges, ahead of the built page's full
    rows, so built paging never skips a row. The answer is labelled ``worktree_overlay``.
    """
    rows = payload.get("results")
    if not isinstance(rows, list):
        return overlay.label(payload)
    kinds = UNLINKED_EVIDENCE_KINDS if kinds is None else kinds
    # A deeper hop is the built graph's (the walk ran there); only first-hop rows swap.
    kept = [
        r
        for r in rows
        if not (
            isinstance(r, dict)
            and r.get("depth", 1) == 1
            and overlay.changes(str(r.get("file") or ""))
        )
    ]
    if not overlay.differing:
        return payload
    if depth > 1:
        payload[OVERLAY_FIRST_HOP_FIELD] = True
    added: list[dict[str, object]] = []
    for rel in overlay.differing:
        for edge in overlay.edges(rel):
            if edge.get("kind") in kinds and edge.get("target_raw") == subject:
                tiered = {**edge, "confidence_tier": _HEURISTIC}
                added.append(edge_hit(tiered, depth=1 if depth > 1 else None))
    bare = subject.rsplit(MEMBER_SEPARATOR, 1)[-1]
    unlinked = sum(
        1
        for rel in overlay.differing
        for edge in overlay.edges(rel)
        if edge.get("kind") in kinds and edge.get("target_raw") == bare
    )
    if unlinked:
        # Calls on an untyped receiver name only the member; the overlay does not guess (R5.6).
        payload[OVERLAY_UNLINKED_FIELD] = unlinked
    swapped = len(rows) - len(kept)
    if added or swapped:
        # Cutting page 0 to ``limit`` would drop built rows the next offset never returns.
        payload["results"] = added + kept if offset == 0 else kept
        total = payload.get("total_count")
        if isinstance(total, int):
            payload["total_count"] = max(total - swapped + len(added), len(added) + len(kept))
        for key in _BUILT_PARTITIONS:
            payload.pop(key, None)
    if payload.get("reason") in (REASON_OK, REASON_NO_MATCHES, REASON_INDEX_BEHIND):
        payload["reason"] = REASON_WORKTREE_OVERLAY
    return overlay.label(payload)


def _as_row(item: Mapping[str, object], rel: str) -> dict[str, object]:
    """An adapter dict shaped as a stored row (JSON text for structured values), file named."""
    row = {key: stored(value) for key, value in item.items()}
    row.setdefault("file_path", rel)
    return row


def _rows(found: tuple[str, ParseResult] | None, rel: str) -> Parsed | None:
    """A parse as stored-shaped rows, or None when it failed or no adapter read it."""
    if found is None or not found[1].ok:
        return None
    return [_as_row(n, rel) for n in found[1].nodes], [_as_row(e, rel) for e in found[1].edges]
