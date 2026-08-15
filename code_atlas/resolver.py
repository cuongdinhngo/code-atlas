"""Generic cross-file edge linking — FQN / name / path → node, no language branches (§8.2)."""

from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath

from code_atlas import contract
from code_atlas.store import DeltaScope, GraphStore

# RESOLVED is strongest; DYNAMIC is weakest — never promote a weaker incoming claim (R5.2).
_TIER_STRENGTH = {tier: index for index, tier in enumerate(contract.CONFIDENCE_TIERS)}

# How many unresolved edges to pull into Python at once (M4 — avoid loading the whole table).
_RESOLVE_BATCH = 1000

# Path-shaped kinds must not also be FQN-resolved (would double-link the same edge id).
assert "INCLUDES" not in contract.FQN_EDGE_KINDS


_BARE_NAME_KIND = "Method"


def _alias_preimages(keys: set[str], aliases: Mapping[str, str]) -> set[str]:
    """Every ``target_raw`` whose alias-followed lookup key is in ``keys`` (096).

    ``_lookup_raw`` rewrites a raw through the alias map — whole name and container alike — so a
    scope compared against raw text alone would skip an edge naming the alias of a delta's class.
    """
    if not aliases:
        return set()
    inverse: dict[str, set[str]] = {}
    for alias, real in aliases.items():
        inverse.setdefault(real, set()).add(alias)

    def sources(real: str) -> set[str]:
        """Walk the alias map backwards; the ``found`` guard makes a cycle terminate."""
        found: set[str] = set()
        pending = [real]
        while pending:
            for alias in inverse.get(pending.pop(), ()):
                if alias not in found:
                    found.add(alias)
                    pending.append(alias)
        return found

    extra: set[str] = set()
    for key in keys:
        extra.update(sources(key))
        container, member = contract.split_qname(key)
        if container is not None:
            extra.update(contract.join_qname(alias, member) for alias in sources(container))
    return extra


def delta_scope(
    store: GraphStore, files: Sequence[str], *, aliases: Mapping[str, str] | None = None
) -> DeltaScope:
    """The keys a delta could newly satisfy: qnames it declares, plus bare method names (096).

    An FQN edge resolves by ``target_raw``; the unmatched-CALLS second pass resolves by bare
    name. Those two are the whole lookup surface, so they are the whole key set — widened by the
    aliases of each key, because ``_lookup_raw`` reaches a key through the alias map too.
    """
    keys = set(store.qnames_in_files(files))
    keys.update(store.node_names_in_files(files, kind=_BARE_NAME_KIND))
    keys.update(_alias_preimages(keys, store.alias_targets() if aliases is None else aliases))
    return DeltaScope(
        files=tuple(files),
        keys=tuple(sorted(keys)),
        scoped_kinds=tuple(sorted(contract.FQN_EDGE_KINDS)),
    )


def resolve_edges(
    store: GraphStore,
    *,
    max_candidates: int,
    file_path: str | None = None,
    delta: DeltaScope | None = None,
) -> int:
    """Link bare edges after every node exists; ``max_candidates`` caps multi-match HEURISTIC.

    When ``file_path`` is set, only unresolved edges from that file are considered (read-through
    reparse). Full builds omit it so the whole unresolved set is linked.

    ``delta`` narrows the FQN-resolved kinds to the edges an incremental could have changed the
    answer for (096). It is equivalent to a full pass only while the alias map is unchanged —
    the caller owns that check, because only it can snapshot the map before the parse.

    Returns the number of **sibling rows inserted**. They are rows this run wrote, and the build
    report has to count them or it reports a graph smaller than the one it just made (task 051).
    """
    inserted = 0
    # Alias FQN → real FQN from ALIASES edges (source → target_raw); remaps CALLS/NEW (task 030).
    # Built once: every ALIASES row is in the store before resolve runs (full parse first).
    alias_map = store.alias_targets()
    for batch in store.iter_unresolved_edges(
        batch_size=_RESOLVE_BATCH, skip_dynamic=True, file_path=file_path, delta=delta
    ):
        links: list[tuple[int, str, str]] = []
        siblings: list[dict[str, object]] = []
        includes: list[dict[str, object]] = []
        symbols: list[dict[str, object]] = []
        for edge in batch:
            kind = str(edge["kind"])
            if kind == "INCLUDES":
                includes.append(edge)
            elif kind in contract.FQN_EDGE_KINDS:
                symbols.append(edge)

        include_paths = [
            _relative_to(str(edge["file_path"]), str(edge["target_raw"]))
            for edge in includes
        ]
        file_hits = store.nodes_by_qualified_names(
            include_paths, kind="File", limit=2
        )
        for edge, path in zip(includes, include_paths, strict=True):
            hits = file_hits.get(path, [])
            if len(hits) != 1:
                continue
            tier = _weaker_tier(str(edge["confidence_tier"]), "RESOLVED")
            links.append((int(str(edge["id"])), str(hits[0]["qualified_name"]), tier))

        lookup_raws = [
            _lookup_raw(str(edge["target_raw"]), edge["kind"], alias_map)
            for edge in symbols
        ]
        qname_hits = store.nodes_by_qualified_names(lookup_raws, limit=max_candidates)
        unmatched_calls: list[dict[str, object]] = []
        for edge, lookup in zip(symbols, lookup_raws, strict=True):
            incoming = str(edge["confidence_tier"])
            hits = qname_hits.get(lookup, [])
            if hits:
                # The lookup key IS the qname, so a hit means the name resolved; N hits only means
                # N files declare it, which an edge storing a qname cannot record anyway (046).
                _queue_candidates(
                    edge, hits, _weaker_tier(incoming, "RESOLVED"), links, siblings
                )
                continue
            if edge["kind"] == "CALLS" and incoming == "HEURISTIC":
                unmatched_calls.append(edge)

        if unmatched_calls:
            call_raws = [str(edge["target_raw"]) for edge in unmatched_calls]
            method_hits = store.nodes_by_names(
                call_raws, kind="Method", limit=max_candidates
            )
            for edge in unmatched_calls:
                methods = method_hits.get(str(edge["target_raw"]), [])
                if methods:
                    _queue_candidates(edge, methods, "HEURISTIC", links, siblings)

        # One txn: kill between link and sibling insert must not leave under-linked parents.
        store.apply_resolution(links, siblings)
        inserted += len(siblings)
    return inserted


def _follow_aliases(raw: str, alias_map: dict[str, str]) -> str:
    """Follow ALIASES transitively; cycle-safe (Aka2→Aka→Real)."""
    seen = {raw}
    target = raw
    while target in alias_map and alias_map[target] not in seen:
        target = alias_map[target]
        seen.add(target)
    return target


def _lookup_raw(raw: str, kind: object, alias_map: dict[str, str]) -> str:
    """ALIASES targets the real class; other FQN kinds may name an alias (task 030)."""
    if str(kind) == "ALIASES":
        return raw
    followed = _follow_aliases(raw, alias_map)
    if followed != raw:
        return followed
    container, member = contract.split_qname(raw)
    if container is not None:
        mapped = _follow_aliases(container, alias_map)
        if mapped != container:
            return contract.join_qname(mapped, member)
    return raw


def _weaker_tier(left: str, right: str) -> str:
    """Return the less-certain of two tiers so a guess is never promoted to RESOLVED (R5.2)."""
    return left if _TIER_STRENGTH[left] >= _TIER_STRENGTH[right] else right


def _distinct_qnames(candidates: list[dict[str, object]]) -> list[str]:
    """The candidates' qualified names, deduped in source order (``dict.fromkeys``, so R4 holds).

    An FQN lookup is keyed by qname, so its candidates differ only by file — and an edge cannot
    record a file. A sibling per node would be an exact duplicate row (046).
    """
    return list(dict.fromkeys(str(candidate["qualified_name"]) for candidate in candidates))


def _queue_candidates(
    edge: dict[str, object],
    candidates: list[dict[str, object]],
    tier: str,
    links: list[tuple[int, str, str]],
    siblings: list[dict[str, object]],
) -> None:
    """Update the original edge to the first candidate; queue siblings for the rest (top-N)."""
    qnames = _distinct_qnames(candidates)
    links.append((int(str(edge["id"])), qnames[0], tier))
    for qname in qnames[1:]:
        sibling = {field: edge[field] for field in contract.EDGE_FIELDS if field in edge}
        sibling["target_qname"] = qname
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
