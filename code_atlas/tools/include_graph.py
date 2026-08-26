"""``include_graph`` — ``include``/``require`` neighbors for one path (§12)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Literal, NamedTuple

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_RELATIONSHIP_NOT_MODELLED,
    TRY_INSTEAD_HINT_PATH_BASENAME,
    attach_try_instead,
    edge_hit,
    edge_id,
    empty_nav,
    nav_result,
)

NAME = "include_graph"

DetailLevel = Literal["minimal", "standard"]
Direction = Literal["imports", "imported_by", "both"]

_INCLUDE = ("INCLUDES",)


class _GraphOutcome(NamedTuple):
    results: list[dict[str, object]]
    truncated: bool
    unresolved_includes: int | None


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def include_graph(
        path: str,
        direction: Direction = "both",
        depth: int = 1,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """What does this file pull in, and what pulls it in?

        ``direction`` is ``imports`` (what this file includes), ``imported_by`` (who includes it),
        or ``both``. ``depth`` defaults to 1 (direct); deeper values BFS over linked ``INCLUDES``
        only, capped by ``CA_MAX_RESULTS``. ``unresolved_includes`` counts bare/dynamic includes on
        the seed's ``imports`` side and is omitted for ``imported_by`` (inbound unresolved is not a
        confident zero — 065). An empty inbound answer with unlinked includes mentioning the
        basename returns ``reason=relationship_not_modelled`` plus a ``try_instead_hint`` and
        deliberately NO ``try_instead`` — no registered tool reads unlinked include text (093).
        """
        if depth < 1:
            raise ValueError(f"depth must be >= 1, got {depth}")
        if direction not in ("imports", "imported_by", "both"):
            raise ValueError(f"direction must be imports|imported_by|both, got {direction!r}")
        rel = _repo_relative(config.root, path)
        if not config.db_path.is_file():
            return empty_nav(
                rel, detail_level=detail_level, db_path=str(config.db_path), subject_key="path",
                index_root=config.index_root,
            )
        limit = config.max_results
        reason = None
        try_instead: str | None = None
        try_instead_hint: str | None = None
        with GraphStore(config.db_path) as store:
            outcome = _graph(store, rel, direction=direction, hops=depth, limit=limit)
            if direction in ("imported_by", "both") and not outcome.results:
                # Never a bare inbound zero (9-B, 160). Unlinked text that mentions this file ⇒ the
                # relationship exists but is not modelled, with a hint; otherwise it is a genuine
                # zero named no_matches — not "not modelled" (065 keeps that distinction).
                if store.count_unlinked_includes_mentioning(PurePosixPath(rel).name) > 0:
                    reason = REASON_RELATIONSHIP_NOT_MODELLED
                    try_instead_hint = TRY_INSTEAD_HINT_PATH_BASENAME
                else:
                    reason = REASON_NO_MATCHES
        payload = nav_result(
            rel,
            outcome.results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            index_root=config.index_root,
            truncated=outcome.truncated,
            subject_key="path",
            reason=reason,
            direction=direction,
            depth=depth,
        )
        if outcome.unresolved_includes is not None:
            payload["unresolved_includes"] = outcome.unresolved_includes
        return attach_try_instead(payload, try_instead, try_instead_hint)

    return include_graph


def _graph(
    store: GraphStore,
    path: str,
    *,
    direction: Direction,
    hops: int,
    limit: int,
) -> _GraphOutcome:
    results: list[dict[str, object]] = []
    seen_edge_ids: set[int] = set()
    visited: set[str] = {path}
    queue: deque[tuple[str, int]] = deque([(path, 0)])
    truncated = False
    unresolved: int | None = (
        _count_unresolved_imports(store, path) if direction in ("imports", "both") else None
    )

    while queue and len(results) < limit:
        current, hop = queue.popleft()
        if hop >= hops:
            continue
        neighbors = _neighbors(store, current, direction=direction, limit=limit)
        for index, (eid, neighbor, hit) in enumerate(neighbors):
            if eid in seen_edge_ids:
                continue
            seen_edge_ids.add(eid)
            hit = {**hit, "depth": hop + 1}
            results.append(hit)
            if len(results) >= limit:
                # Exact fill with no further neighbors and no deeper queue ⇒ not truncated.
                truncated = index + 1 < len(neighbors) or bool(queue)
                break
            if hop + 1 >= hops or neighbor in visited:
                continue
            visited.add(neighbor)
            queue.append((neighbor, hop + 1))

    return _GraphOutcome(
        results=results, truncated=truncated, unresolved_includes=unresolved
    )


def _count_unresolved_imports(store: GraphStore, path: str) -> int:
    """Bare/dynamic INCLUDES from ``path`` — linked-only results hide these otherwise."""
    count = 0
    for edge in store.edges_by_source(path, kinds=_INCLUDE, limit=10_000):
        target = edge.get("target_qname")
        if not isinstance(target, str) or not target:
            count += 1
    return count


def _neighbors(
    store: GraphStore, path: str, *, direction: Direction, limit: int
) -> list[tuple[int, str, dict[str, object]]]:
    out: list[tuple[int, str, dict[str, object]]] = []
    if direction in ("imports", "both"):
        for edge in store.edges_by_source(path, kinds=_INCLUDE, limit=limit):
            target = edge.get("target_qname")
            if not isinstance(target, str) or not target:
                continue
            out.append(
                (
                    edge_id(edge),
                    target,
                    edge_hit(edge, subject=target, subject_key="path"),
                )
            )
    if direction in ("imported_by", "both"):
        for edge in store.edges_by_target(path, kinds=_INCLUDE, limit=limit):
            source = str(edge["source_qname"])
            out.append(
                (
                    edge_id(edge),
                    source,
                    edge_hit(edge, subject=source, subject_key="path"),
                )
            )
    return out


def _repo_relative(root: Path, path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return PurePosixPath(path).as_posix()
    return PurePosixPath(path).as_posix()
