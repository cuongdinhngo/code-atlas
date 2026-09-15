"""Build-time mirror facts for name-search ordering (277) — same 115 computation, stamped once.

Prefers paths outside any mirror pair, then the side with more inbound edges from *outside*
the pair (measurable, no directory names — R2). Empty stamp ⇒ search order unchanged (061).
"""

from __future__ import annotations

import json
from collections.abc import Container, Mapping, Sequence
from typing import TYPE_CHECKING, Any

from code_atlas.onboarding.mirrors import (
    COUNTERPART,
    MirrorPair,
    find_mirror_subtrees,
    resolve_counterpart,
)

if TYPE_CHECKING:
    from code_atlas.store import GraphStore

MIRROR_SEARCH_KEY = "mirror_search"
# Payload field naming the within-band rule (265 / 277) — omit when the stamp is absent.
SEARCH_ORDER_MIRROR = "exact_band_then_outside_mirror_then_external_inbound"
SEARCH_ORDER_FIELD = "search_order"
MIRROR_COUNTERPART_FIELD = "mirror_counterpart"

__all__ = [
    "MIRROR_COUNTERPART_FIELD",
    "MIRROR_SEARCH_KEY",
    "SEARCH_ORDER_FIELD",
    "SEARCH_ORDER_MIRROR",
    "build_mirror_search_stamp",
    "mirror_prefer_key",
    "load_mirror_search_stamp",
    "attach_mirror_search_fields",
    "decorate_mirror_hits",
]


def build_mirror_search_stamp(
    store: GraphStore,
    *,
    sample_limit: int = 3,
    min_shared: int | None = None,
    min_overlap: float | None = None,
) -> dict[str, object]:
    """Compute the search stamp from the indexed path set — called once per build."""
    paths = list(store.file_paths())
    kwargs: dict[str, object] = {"sample_limit": sample_limit}
    if min_shared is not None:
        kwargs["min_shared"] = min_shared
    if min_overlap is not None:
        kwargs["min_overlap"] = min_overlap
    report = find_mirror_subtrees(paths, **kwargs)  # type: ignore[arg-type]
    pairs = [
        {"left": pair.left, "right": pair.right, "shared": pair.shared, "overlap": pair.overlap}
        for pair in report.pairs
    ]
    inbound = _external_inbound_by_prefix(store, report.pairs)
    return {"pairs": pairs, "external_inbound": inbound}


def load_mirror_search_stamp(store: GraphStore) -> dict[str, object] | None:
    """The stamped mirror-search facts, or ``None`` when absent (pre-277 / no mirrors)."""
    raw = store.get_meta(MIRROR_SEARCH_KEY)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def mirror_prefer_key(path: str, stamp: Mapping[str, object] | None) -> int:
    """Sort key within an exactness band: outside mirrors first, then higher external inbound.

    Lower is preferred. Deterministic when inbound ties (prefix string).
    """
    if not stamp:
        return 0
    pairs = stamp.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        return 0
    inbound = stamp.get("external_inbound")
    inbound_map = inbound if isinstance(inbound, dict) else {}
    matched: list[tuple[str, str, str]] = []
    for pair in pairs:
        if not isinstance(pair, Mapping):
            continue
        left, right = str(pair.get("left", "")), str(pair.get("right", ""))
        for prefix in (left, right):
            if prefix and (path == prefix or path.startswith(prefix + "/")):
                matched.append((prefix, left, right))
    if not matched:
        return 0  # outside every mirror — preferred
    # Longest prefix wins when nested (stable).
    matched.sort(key=lambda row: (-len(row[0]), row[0]))
    prefix, left, right = matched[0]
    other = right if prefix == left else left
    mine = int(inbound_map.get(prefix) or 0)
    theirs = int(inbound_map.get(other) or 0)
    # Prefer the side with more external inbound; tie → lexicographic prefix.
    side_rank = 0 if mine > theirs else (1 if mine < theirs else (0 if prefix <= other else 1))
    return 1 + side_rank  # 1 or 2 — always after outside (0)


def attach_mirror_search_fields(
    results: Sequence[Mapping[str, Any]],
    stamp: Mapping[str, object] | None,
    indexed: Container[str],
) -> str | None:
    """Mutate hits with indexed-only counterparts; return the order rule or ``None`` (277/282)."""
    return decorate_mirror_hits(results, stamp, indexed)


def decorate_mirror_hits(
    results: Sequence[Mapping[str, Any]],
    stamp: Mapping[str, object] | None,
    indexed: Container[str],
) -> str | None:
    """Mutate hit dicts with counterparts that exist in ``indexed``; return order or ``None``.

    Synthesized sibling paths that are not indexed are never named (282) — that is
    ``NO_COUNTERPART``, not a confident ``mirror_counterpart``.
    """
    if not stamp or not stamp.get("pairs"):
        return None
    pairs = _pairs_from_stamp(stamp)
    for hit in results:
        path = hit.get("file")
        if not isinstance(path, str):
            continue
        answer = resolve_counterpart(path, pairs, indexed)
        if answer.status == COUNTERPART and answer.path:
            # Mapping may be a plain dict from _hit.
            if isinstance(hit, dict):
                hit[MIRROR_COUNTERPART_FIELD] = answer.path
    return SEARCH_ORDER_MIRROR


def _pairs_from_stamp(stamp: Mapping[str, object]) -> tuple[MirrorPair, ...]:
    rows = stamp.get("pairs")
    if not isinstance(rows, list):
        return ()
    out: list[MirrorPair] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        out.append(
            MirrorPair(
                left=str(row["left"]),
                right=str(row["right"]),
                shared=int(row.get("shared") or 0),
                left_only=0,
                right_only=0,
                overlap=float(row.get("overlap") or 0.0),
                sample=(),
            )
        )
    return tuple(out)


def _external_inbound_by_prefix(
    store: GraphStore, pairs: Sequence[MirrorPair]
) -> dict[str, int]:
    """Inbound edges whose source is outside both sides of the pair, counted per prefix."""
    counts: dict[str, int] = {}
    for pair in pairs:
        counts[pair.left] = 0
        counts[pair.right] = 0
    if not pairs:
        return counts
    for src, tgt in store.resolved_edge_file_pairs():
        for pair in pairs:
            tgt_side = _side(tgt, pair)
            if tgt_side is None:
                continue
            if _side(src, pair) is not None:
                continue  # internal to the pair
            counts[tgt_side] = counts.get(tgt_side, 0) + 1
    return counts


def _side(path: str, pair: MirrorPair) -> str | None:
    for prefix in (pair.left, pair.right):
        if path == prefix or path.startswith(prefix + "/"):
            return prefix
    return None
