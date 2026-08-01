"""Generic cross-file edge linking — FQN / name / path → node, no language branches (§8.2)."""

from pathlib import PurePosixPath

from code_atlas import contract
from code_atlas.store import GraphStore

# Structural edges whose target_raw is an FQN; path/name strategies handle the rest (§8.2).
_FQN_KINDS = frozenset(
    kind
    for kind in contract.EDGE_KINDS
    if kind != "CONTAINS"
    and kind != "IMPORTS"
    and kind != "INCLUDES"
    and kind != "REFERENCES"
)


def resolve_edges(store: GraphStore, *, max_candidates: int) -> None:
    """Link bare edges after every node exists; ``max_candidates`` caps multi-match HEURISTIC."""
    for edge in store.unresolved_edges():
        if edge["confidence_tier"] == "DYNAMIC":
            continue
        kind = str(edge["kind"])
        if kind == "INCLUDES":
            _resolve_include(store, edge)
        elif kind in _FQN_KINDS:
            _resolve_symbol(store, edge, max_candidates)


def _resolve_include(store: GraphStore, edge: dict[str, object]) -> None:
    path = _relative_to(str(edge["file_path"]), str(edge["target_raw"]))
    hits = store.nodes_by_qualified_name(path, kind="File", limit=1)
    if len(hits) == 1:
        store.link_edge(int(str(edge["id"])), str(hits[0]["qualified_name"]), "RESOLVED")


def _resolve_symbol(store: GraphStore, edge: dict[str, object], max_candidates: int) -> None:
    raw = str(edge["target_raw"])
    hits = store.nodes_by_qualified_name(raw, limit=max_candidates)
    if hits:
        _link_candidates(store, edge, hits, "RESOLVED" if len(hits) == 1 else "HEURISTIC")
        return
    if edge["kind"] == "CALLS" and edge["confidence_tier"] == "HEURISTIC":
        methods = store.nodes_by_name(raw, kind="Method", limit=max_candidates)
        if methods:
            _link_candidates(store, edge, methods, "HEURISTIC")


def _link_candidates(
    store: GraphStore,
    edge: dict[str, object],
    candidates: list[dict[str, object]],
    tier: str,
) -> None:
    """Update the original edge to the first candidate; insert siblings for the rest (top-N)."""
    first = str(candidates[0]["qualified_name"])
    store.link_edge(int(str(edge["id"])), first, tier)
    for candidate in candidates[1:]:
        sibling = {field: edge[field] for field in contract.EDGE_FIELDS if field in edge}
        sibling["target_qname"] = candidate["qualified_name"]
        sibling["confidence_tier"] = tier
        store.insert_edge(sibling)


def _relative_to(includer: str, raw: str) -> str:
    """Join ``raw`` onto the includer's directory; collapse ``.`` / ``..`` (POSIX)."""
    parts: list[str] = []
    for part in (PurePosixPath(includer).parent / raw).parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part not in ("", "."):
            parts.append(part)
    return str(PurePosixPath(*parts)) if parts else "."
