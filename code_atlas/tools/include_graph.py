"""``include_graph`` — ``include``/``require`` neighbors for one path (§12)."""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Literal, NamedTuple

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools.coverage import relation_carried_by, relation_unmodelled_for_language
from code_atlas.tools.nav_result import (
    AUTHORITATIVE,
    REASON_NO_MATCHES,
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
    REASON_RELATIONSHIP_NOT_MODELLED,
    TRY_INSTEAD_FIND_REFERENCES,
    TRY_INSTEAD_HINT_PATH_BASENAME,
    TRY_INSTEAD_HINT_RELATION_CARRIED_BY_ANOTHER_KIND,
    TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE,
    answered_about_ref_for,
    apply_empty_inbound_honesty,
    attach_try_instead,
    edge_hit,
    edge_id,
    empty_nav,
    nav_result,
)

NAME = "include_graph"

DetailLevel = Literal["minimal", "standard"]
Direction = Literal["imports", "imported_by", "both"]

# Unlinked includes that could still be this file's includer, listed on a not-modelled zero (363).
UNLINKED_INCLUDES = "unlinked_includes"
# Same-named files that are included, named beside a positive inbound zero (363).
SAME_BASENAME_INCLUDED = "same_basename_included"
_QUOTED = re.compile(r"'([^']*)'|\"([^\"]*)\"")

_INCLUDE = ("INCLUDES",)
# The kind a module language carries the same relation under, linked since 188 — the route's premise
_MODULE_DEP = ("IMPORTS",)


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
        confident zero — 065). An empty inbound answer with unlinked includes whose path tail
        could be this file returns ``reason=relationship_not_modelled``, lists them in
        ``unlinked_includes``, and adds a ``try_instead_hint`` but deliberately NO ``try_instead`` —
        no registered tool reads unlinked include text (093). When none could, and another file of
        the same name is included, the zero is positive: ``no_matches``, ``authoritative: true``,
        ``same_basename_included`` (363).
        An empty inbound answer on a file whose **language** emits no ``INCLUDES`` at all returns
        ``reason=relation_unmodelled_for_language`` instead of a confident zero: the relation is
        carried under another edge kind here (186). Where that kind is ``IMPORTS``, which 188 links,
        ``try_instead`` names ``find_references``; where the language emits neither, it stays a hint
        with no route.
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
            answered_about_ref=None)
        limit = config.page_limit
        reason = None
        try_instead: str | None = None
        try_instead_hint: str | None = None
        could_name: list[dict[str, object]] = []
        alternatives: list[str] = []
        with GraphStore(config.db_path) as store:
            about_ref = answered_about_ref_for(store)
            outcome = _graph(store, rel, direction=direction, hops=depth, limit=limit)
            if direction in ("imported_by", "both") and not outcome.results:
                # Never a bare inbound zero (9-B, 160). Unlinked text that mentions this file ⇒ the
                # relationship exists but is not modelled, with a hint; otherwise it is a genuine
                # zero named no_matches — not "not modelled" (065 keeps that distinction).
                # Only an unlinked include whose path tail fits this file could include it (363).
                basename = PurePosixPath(rel).name
                could_name = [
                    {"file": row["file_path"], "line": row["line"], "target_raw": row["target_raw"]}
                    for row in store.unlinked_includes_mentioning(basename, limit=limit)
                    if _tail_fits(str(row["target_raw"]), rel)
                ]
                if could_name:
                    reason = REASON_RELATIONSHIP_NOT_MODELLED
                    try_instead_hint = TRY_INSTEAD_HINT_PATH_BASENAME
                elif relation_unmodelled_for_language(store, file_path=rel, kinds=_INCLUDE):
                    # This file's language emits no INCLUDES at all, so there is no unlinked
                    # evidence either and the arm above cannot fire — 186's inversion: the better
                    # the adapter, the more confident the wrong zero.
                    reason = REASON_RELATION_UNMODELLED_FOR_LANGUAGE
                    if relation_carried_by(store, file_path=rel, kinds=_MODULE_DEP):
                        # 188 linked IMPORTS, so a registered tool can now enumerate the relation
                        # from the same File qname — clause (c) says name it.
                        try_instead = TRY_INSTEAD_FIND_REFERENCES
                        try_instead_hint = TRY_INSTEAD_HINT_RELATION_CARRIED_BY_ANOTHER_KIND
                    else:
                        # No carrying kind either: hint, and NO route (R5.4c, 186's original case).
                        try_instead_hint = TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE
                else:
                    # Shared predicate (264) before a bare no_matches — File subject, path qname.
                    reason, _unlinked = apply_empty_inbound_honesty(
                        REASON_NO_MATCHES,
                        store,
                        subject_kind="File",
                        raws=(rel,),
                    )
                    if reason == REASON_NO_MATCHES:
                        # A positive zero: every include of this name reached another copy (363).
                        alternatives = [
                            path for path in store.included_files_named(basename) if path != rel
                        ]
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
            answered_about_ref=about_ref)
        if outcome.unresolved_includes is not None:
            payload["unresolved_includes"] = outcome.unresolved_includes
        if could_name:
            payload[UNLINKED_INCLUDES] = could_name
        if alternatives:
            payload[AUTHORITATIVE] = True
            payload[SAME_BASENAME_INCLUDED] = alternatives
        return attach_try_instead(payload, try_instead, try_instead_hint)

    return include_graph


def _tail_fits(target_raw: str, rel: str) -> bool:
    """Could an include written as ``target_raw`` reach ``rel``? Its path tail must be rel's (363).

    `target_raw` is the literal as written, so its last quoted string is the path when there is one.
    `..`/`.` drop out; a tail naming another directory, or a longer name, cannot be this file.
    """
    quoted = _QUOTED.findall(target_raw)
    path = next((a or b for a, b in reversed(quoted)), target_raw) if quoted else target_raw
    parts = [part for part in path.replace("\\", "/").split("/") if part not in ("", ".", "..")]
    subject = rel.split("/")
    return bool(parts) and len(parts) <= len(subject) and subject[-len(parts) :] == parts


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
