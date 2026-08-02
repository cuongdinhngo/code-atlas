"""``include_graph`` — ``include``/``require`` neighbors for one path (§12)."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Literal, NamedTuple

from code_atlas.config import Config
from code_atlas.contract import CONFIDENCE_TIERS
from code_atlas.store import GraphStore

NAME = "include_graph"

DetailLevel = Literal["minimal", "standard"]
Direction = Literal["imports", "imported_by", "both"]

_RESOLVED = CONFIDENCE_TIERS[0]
_INCLUDE = ("INCLUDES",)


class _GraphOutcome(NamedTuple):
    results: list[dict[str, object]]
    truncated: bool


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def include_graph(
        path: str,
        direction: Direction = "both",
        depth: int = 1,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """``include``/``require`` neighbors of ``path``.

        ``direction`` is ``imports`` (what this file includes), ``imported_by`` (who includes it),
        or ``both``. ``depth`` defaults to 1 (direct); deeper values BFS over linked ``INCLUDES``
        only, capped by ``CA_MAX_RESULTS``.
        """
        if depth < 1:
            raise ValueError(f"depth must be >= 1, got {depth}")
        if direction not in ("imports", "imported_by", "both"):
            raise ValueError(f"direction must be imports|imported_by|both, got {direction!r}")
        rel = _repo_relative(config.root, path)
        if not config.db_path.is_file():
            return _empty(rel, detail_level=detail_level, db_path=str(config.db_path))
        limit = config.max_results
        with GraphStore(config.db_path) as store:
            outcome = _graph(store, rel, direction=direction, hops=depth, limit=limit)
        return _result(
            rel,
            outcome.results,
            detail_level=detail_level,
            db_path=str(config.db_path),
            truncated=outcome.truncated,
            direction=direction,
            depth=depth,
        )

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

    while queue and len(results) < limit:
        current, hop = queue.popleft()
        if hop >= hops:
            continue
        neighbors = _neighbors(store, current, direction=direction, limit=limit)
        for edge_id, neighbor, hit in neighbors:
            if edge_id in seen_edge_ids:
                continue
            seen_edge_ids.add(edge_id)
            hit = {**hit, "depth": hop + 1}
            results.append(hit)
            if len(results) >= limit:
                break
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, hop + 1))

    return _GraphOutcome(results=results, truncated=len(results) >= limit and bool(queue))


def _neighbors(
    store: GraphStore, path: str, *, direction: Direction, limit: int
) -> list[tuple[int, str, dict[str, object]]]:
    out: list[tuple[int, str, dict[str, object]]] = []
    if direction in ("imports", "both"):
        for edge in store.edges_by_source(path, kinds=_INCLUDE, limit=limit):
            target = edge.get("target_qname")
            if not isinstance(target, str) or not target:
                continue
            out.append((_edge_id(edge), target, _hit(neighbor=target, edge=edge)))
    if direction in ("imported_by", "both"):
        for edge in store.edges_by_target(path, kinds=_INCLUDE, limit=limit):
            source = str(edge["source_qname"])
            out.append((_edge_id(edge), source, _hit(neighbor=source, edge=edge)))
    return out


def _edge_id(edge: dict[str, object]) -> int:
    raw = edge["id"]
    if not isinstance(raw, int):
        raise TypeError(f"edge id must be int, got {type(raw).__name__}")
    return raw


def _hit(*, neighbor: str, edge: dict[str, object]) -> dict[str, object]:
    hit: dict[str, object] = {}
    hit["path"] = neighbor
    hit["file"] = edge["file_path"]
    hit["line"] = edge["line"]
    hit["kind"] = edge["kind"]
    hit["confidence_tier"] = edge.get("confidence_tier") or _RESOLVED
    return hit


def _repo_relative(root: Path, path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return PurePosixPath(path).as_posix()
    return PurePosixPath(path).as_posix()


def _empty(path: str, *, detail_level: str, db_path: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "indexed": False,
        "path": path,
        "results": [],
        "truncated": False,
    }
    if detail_level == "standard":
        payload["db_path"] = db_path
    return payload


def _result(
    path: str,
    results: list[dict[str, object]],
    *,
    detail_level: str,
    db_path: str,
    truncated: bool,
    **extra: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "indexed": True,
        "path": path,
        "results": results,
        "truncated": truncated,
        **extra,
    }
    if detail_level == "standard":
        payload["db_path"] = db_path
    return payload
