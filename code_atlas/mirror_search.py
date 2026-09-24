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
    NO_COUNTERPART,
    OUTSIDE_MIRROR,
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
# Honest negative when the path sits on a stamped pair but the sibling is not indexed (286 / 282).
MIRROR_NO_COUNTERPART_FIELD = "mirror_no_counterpart"
# Twin file indexed but the hit's name segment is not defined there (331).
MIRROR_COUNTERPART_FILE_FIELD = "mirror_counterpart_file"
MIRROR_SYMBOL_ABSENT_FIELD = "mirror_symbol_absent"
_FILE_KIND = "File"

__all__ = [
    "MIRROR_COUNTERPART_FIELD",
    "MIRROR_COUNTERPART_FILE_FIELD",
    "MIRROR_NO_COUNTERPART_FIELD",
    "MIRROR_SYMBOL_ABSENT_FIELD",
    "MIRROR_SEARCH_KEY",
    "SEARCH_ORDER_FIELD",
    "SEARCH_ORDER_MIRROR",
    "build_mirror_search_stamp",
    "mirror_prefer_key",
    "load_mirror_search_stamp",
    "attach_mirror_search_fields",
    "attach_mirror_read_fields",
    "decorate_mirror_hits",
    "label_mirror_rows",
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
    *,
    store: GraphStore | None = None,
) -> str | None:
    """Mutate hits with indexed-only counterparts; return the order rule or ``None`` (277/282)."""
    return decorate_mirror_hits(results, stamp, indexed, store=store)


def attach_mirror_read_fields(
    payload: dict[str, object],
    file_path: str,
    stamp: Mapping[str, object] | None,
    indexed: Container[str],
    *,
    kind: str | None = None,
    name: str | None = None,
    store: GraphStore | None = None,
) -> bool:
    """Name an indexed twin on a ``read_symbol`` hit, or the honest negative (286/331).

    Returns True when the file sits on a stamped pair (so the caller can attach the
    dispatch-boundary caveat). No stamp / outside a pair → False and no new fields (061).
    Never asserts which twin a request reaches.
    """
    if not stamp or not stamp.get("pairs"):
        return False
    pairs = _pairs_from_stamp(stamp)
    answer = resolve_counterpart(file_path, pairs, indexed)
    if answer.status == OUTSIDE_MIRROR:
        return False
    if answer.status == COUNTERPART and answer.path:
        _attach_twin_fields(
            payload,
            twin=answer.path,
            kind=kind,
            name=name,
            presence=_presence_for_hits(
                store,
                [{"file": file_path, "kind": kind, "name": name}],
                pairs,
                indexed,
            ),
        )
    elif answer.status == NO_COUNTERPART:
        payload[MIRROR_NO_COUNTERPART_FIELD] = True
    return True


def decorate_mirror_hits(
    results: Sequence[Mapping[str, Any]],
    stamp: Mapping[str, object] | None,
    indexed: Container[str],
    *,
    store: GraphStore | None = None,
) -> str | None:
    """Mutate hit dicts with counterparts that exist in ``indexed``; return order or ``None``.

    Synthesized sibling paths that are not indexed are never named (282). On a non-File
    hit, ``mirror_counterpart`` requires the twin file to define the same name (331).
    """
    if not stamp or not stamp.get("pairs"):
        return None
    pairs = _pairs_from_stamp(stamp)
    presence = _presence_for_hits(store, results, pairs, indexed)
    identity = _identity_for_hits(store, results)
    for hit in results:
        if not isinstance(hit, dict):
            continue
        path = hit.get("file")
        if not isinstance(path, str):
            continue
        answer = resolve_counterpart(path, pairs, indexed)
        if answer.status == COUNTERPART and answer.path:
            kind, name = _hit_kind_name(hit, identity)
            _attach_twin_fields(
                hit, twin=answer.path, kind=kind, name=name, presence=presence
            )
    return SEARCH_ORDER_MIRROR


def label_mirror_rows(
    rows: Sequence[dict[str, object]],
    stamp: Mapping[str, object] | None,
    indexed: Container[str],
    *,
    store: GraphStore | None = None,
) -> None:
    """Name each row's indexed twin, or the honest negative, as ``read_symbol`` does (286/313/331).

    Rows off every stamped pair — and every row when there is no stamp — gain nothing (061).
    """
    if not stamp or not stamp.get("pairs"):
        return
    pairs = _pairs_from_stamp(stamp)
    presence = _presence_for_hits(store, rows, pairs, indexed)
    identity = _identity_for_hits(store, rows)
    for row in rows:
        path = row.get("file")
        if not isinstance(path, str):
            continue
        answer = resolve_counterpart(path, pairs, indexed)
        if answer.status == COUNTERPART and answer.path:
            kind, name = _hit_kind_name(row, identity)
            _attach_twin_fields(
                row, twin=answer.path, kind=kind, name=name, presence=presence
            )
        elif answer.status == NO_COUNTERPART:
            row[MIRROR_NO_COUNTERPART_FIELD] = True


def _attach_twin_fields(
    target: dict[str, object],
    *,
    twin: str,
    kind: str | None,
    name: str | None,
    presence: frozenset[tuple[str, str]] | None,
) -> None:
    """File hits keep today's path claim; symbols require presence when it was computed (331)."""
    if kind == _FILE_KIND or not name or presence is None:
        target[MIRROR_COUNTERPART_FIELD] = twin
        return
    if (twin, name) in presence:
        target[MIRROR_COUNTERPART_FIELD] = twin
        return
    target[MIRROR_COUNTERPART_FILE_FIELD] = twin
    target[MIRROR_SYMBOL_ABSENT_FIELD] = True


def _identity_for_hits(
    store: GraphStore | None, hits: Sequence[Mapping[str, Any]]
) -> dict[str, tuple[str, str]]:
    """qname → ``(name, kind)`` for hits that omit either — one batch when ``store`` is present."""
    if store is None:
        return {}
    need: list[str] = []
    for hit in hits:
        has_name = isinstance(hit.get("name"), str) and bool(hit["name"])
        has_kind = isinstance(hit.get("kind"), str) and bool(hit["kind"])
        if has_name and has_kind:
            continue
        qname = hit.get("qname")
        if isinstance(qname, str) and qname:
            need.append(qname)
    if not need:
        return {}
    found = store.nodes_by_qualified_names(need, limit=1)
    return {
        qname: (str(rows[0]["name"]), str(rows[0]["kind"]))
        for qname, rows in found.items()
        if rows
    }


def _hit_kind_name(
    hit: Mapping[str, Any], identity: Mapping[str, tuple[str, str]]
) -> tuple[str | None, str | None]:
    kind = hit.get("kind") if isinstance(hit.get("kind"), str) else None
    name = hit.get("name") if isinstance(hit.get("name"), str) else None
    if (not kind or not name) and isinstance(hit.get("qname"), str):
        found = identity.get(str(hit["qname"]))
        if found:
            if not name:
                name = found[0]
            if not kind:
                kind = found[1]
    return kind, name


def _presence_for_hits(
    store: GraphStore | None,
    hits: Sequence[Mapping[str, Any]],
    pairs: tuple[MirrorPair, ...],
    indexed: Container[str],
) -> frozenset[tuple[str, str]] | None:
    """One page-level presence set, or ``None`` when no store (legacy file-level claim)."""
    if store is None:
        return None
    identity = _identity_for_hits(store, hits)
    twin_paths: list[str] = []
    name_list: list[str] = []
    for hit in hits:
        path = hit.get("file")
        if not isinstance(path, str):
            continue
        kind, name = _hit_kind_name(hit, identity)
        if kind == _FILE_KIND or not name:
            continue
        answer = resolve_counterpart(path, pairs, indexed)
        if answer.status == COUNTERPART and answer.path:
            twin_paths.append(answer.path)
            name_list.append(name)
    return store.names_defined_in_files(twin_paths, name_list)


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
