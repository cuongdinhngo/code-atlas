"""Generic cross-file edge linking — FQN / name / path → node, no language branches (§8.2)."""

from pathlib import PurePosixPath

from code_atlas import contract
from code_atlas.store import GraphStore

# RESOLVED is strongest; DYNAMIC is weakest — never promote a weaker incoming claim (R5.2).
_TIER_STRENGTH = {tier: index for index, tier in enumerate(contract.CONFIDENCE_TIERS)}

# How many unresolved edges to pull into Python at once (M4 — avoid loading the whole table).
_RESOLVE_BATCH = 1000


def resolve_edges(store: GraphStore, *, max_candidates: int) -> None:
    """Link bare edges after every node exists; ``max_candidates`` caps multi-match HEURISTIC."""
    for batch in store.iter_unresolved_edges(batch_size=_RESOLVE_BATCH, skip_dynamic=True):
        links: list[tuple[int, str, str]] = []
        siblings: list[dict[str, object]] = []
        for edge in batch:
            kind = str(edge["kind"])
            if kind == "INCLUDES":
                _resolve_include(store, edge, links)
            elif kind in contract.FQN_EDGE_KINDS:
                _resolve_symbol(store, edge, max_candidates, links, siblings)
        # One txn: kill between link and sibling insert must not leave under-linked parents.
        store.apply_resolution(links, siblings)


def _resolve_include(
    store: GraphStore, edge: dict[str, object], links: list[tuple[int, str, str]]
) -> None:
    path = _relative_to(str(edge["file_path"]), str(edge["target_raw"]))
    hits = store.nodes_by_qualified_name(path, kind="File", limit=2)
    if len(hits) != 1:
        return
    tier = _weaker_tier(str(edge["confidence_tier"]), "RESOLVED")
    links.append((int(str(edge["id"])), str(hits[0]["qualified_name"]), tier))


def _resolve_symbol(
    store: GraphStore,
    edge: dict[str, object],
    max_candidates: int,
    links: list[tuple[int, str, str]],
    siblings: list[dict[str, object]],
) -> None:
    raw = str(edge["target_raw"])
    incoming = str(edge["confidence_tier"])
    hits = store.nodes_by_qualified_name(raw, limit=max_candidates)
    if hits:
        computed = "RESOLVED" if len(hits) == 1 else "HEURISTIC"
        _queue_candidates(edge, hits, _weaker_tier(incoming, computed), links, siblings)
        return
    if edge["kind"] == "CALLS" and incoming == "HEURISTIC":
        methods = store.nodes_by_name(raw, kind="Method", limit=max_candidates)
        if methods:
            _queue_candidates(edge, methods, "HEURISTIC", links, siblings)


def _weaker_tier(left: str, right: str) -> str:
    """Return the less-certain of two tiers so a guess is never promoted to RESOLVED (R5.2)."""
    return left if _TIER_STRENGTH[left] >= _TIER_STRENGTH[right] else right


def _queue_candidates(
    edge: dict[str, object],
    candidates: list[dict[str, object]],
    tier: str,
    links: list[tuple[int, str, str]],
    siblings: list[dict[str, object]],
) -> None:
    """Update the original edge to the first candidate; queue siblings for the rest (top-N)."""
    first = str(candidates[0]["qualified_name"])
    links.append((int(str(edge["id"])), first, tier))
    for candidate in candidates[1:]:
        sibling = {field: edge[field] for field in contract.EDGE_FIELDS if field in edge}
        sibling["target_qname"] = candidate["qualified_name"]
        sibling["confidence_tier"] = tier
        siblings.append(sibling)


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
