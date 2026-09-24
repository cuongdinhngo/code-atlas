"""Generic cross-file edge linking — FQN / name / path → node, no language branches (§8.2)."""

from collections.abc import Callable, Mapping, Sequence
from pathlib import PurePosixPath

from code_atlas import contract
from code_atlas.store import DeltaScope, GraphStore

# RESOLVED is strongest; DYNAMIC is weakest — never promote a weaker incoming claim (R5.2).
_TIER_STRENGTH = {tier: index for index, tier in enumerate(contract.CONFIDENCE_TIERS)}

# How many unresolved edges to pull into Python at once (M4 — avoid loading the whole table).
_RESOLVE_BATCH = 1000

# Path-shaped kinds must not also be FQN-resolved (would double-link the same edge id).
assert not (set(contract.PATH_EDGE_KINDS) & contract.FQN_EDGE_KINDS)


_BARE_NAME_KIND = "Method"
# Bare CALLS → unique same-language Function (214). Not the Method HEURISTIC fallback.
_UNIQUE_FUNCTION_KIND = "Function"
# WRITES CI targets (215). One name each — never a multi-kind vocab literal (R3.2).
_TABLE_KIND = "Table"
# Kinds whose exact-FQN miss retries T-SQL's case-insensitive, default-schema rule (215 / 321).
# The resolver's own set, not a contract subset: 022 AC3 keeps tier-2 words out of those (197-C3).
_SCHEMA_OBJECT_KINDS: tuple[str, ...] = (contract.WRITES, contract.ALTERS)
_COLUMN_KIND = "Column"

# ``\A::m()::b()::c`` is m's type, then b on that, then c on that — the separator between steps.
_CHAIN_STEP = contract.TYPE_OF_SUFFIX + contract.MEMBER_SEPARATOR
# How many member types one receiver may be walked through. Real chains are a handful long; the
# bound is what stops a pathological or cyclic one from costing a round per element.
_MAX_CHAIN_STEPS = 8
# How wide a subtype fan-out may go before the answer stops being worth the rows it costs.
_MAX_SUBTYPES = 64


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
    on_batch: Callable[[], None] | None = None,
) -> int:
    """Link bare edges after every node exists; ``max_candidates`` caps multi-match HEURISTIC.

    When ``file_path`` is set, only unresolved edges from that file are considered (read-through
    reparse). Full builds omit it so the whole unresolved set is linked.

    ``delta`` narrows the FQN-resolved kinds to the edges an incremental could have changed the
    answer for (096). It is equivalent to a full pass only while the alias map is unchanged —
    the caller owns that check, because only it can snapshot the map before the parse.

    ``on_batch`` fires once per streamed batch after it is applied (290). Coarse throttle is the
    batch itself (``_RESOLVE_BATCH``); the sink does not time-throttle when ``total`` is unset.

    Returns the number of **sibling rows inserted**. They are rows this run wrote, and the build
    report has to count them or it reports a graph smaller than the one it just made (task 051).
    """
    inserted = 0
    # Alias FQN → real FQN from ALIASES edges (source → target_raw); remaps CALLS/NEW (task 030).
    # Built once: every ALIASES row is in the store before resolve runs (full parse first).
    alias_map = store.alias_targets()
    # Same reason as the alias map: every hierarchy edge is in the store before resolve runs.
    parent_map = store.hierarchy_parents()
    # The call site's language, for the bare-name fallback below (204). Same one-map-per-run shape.
    file_languages = store.file_languages()
    for batch in store.iter_unresolved_edges(
        batch_size=_RESOLVE_BATCH, skip_dynamic=True, file_path=file_path, delta=delta
    ):
        links: list[tuple[int, str, str]] = []
        siblings: list[dict[str, object]] = []
        paths: list[dict[str, object]] = []
        symbols: list[dict[str, object]] = []
        for edge in batch:
            kind = str(edge["kind"])
            if kind in contract.PATH_EDGE_KINDS:
                paths.append(edge)
            elif kind in contract.FQN_EDGE_KINDS:
                symbols.append(edge)

        path_keys = [_path_key(edge) for edge in paths]
        file_hits = store.nodes_by_qualified_names(
            path_keys, kind="File", limit=2
        )
        for edge, path in zip(paths, path_keys, strict=True):
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
        by_name: list[tuple[dict[str, object], str]] = []
        bare_calls: list[tuple[dict[str, object], str, str]] = []
        inherited: list[tuple[dict[str, object], str, str]] = []
        deferred: list[tuple[dict[str, object], str, str]] = []
        writes_misses: list[dict[str, object]] = []
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
            if edge["kind"] in _SCHEMA_OBJECT_KINDS:
                # Case / schema mismatch: exact FQN missed; unique CI link is T-SQL's rule (215).
                writes_misses.append(edge)
                continue
            if edge["kind"] != "CALLS":
                continue
            container, member = contract.split_qname(lookup)
            if container is None:
                # Bare: unique Function first (214); HEURISTIC Method is the leftover.
                bare_calls.append((edge, member, incoming))
                continue
            if (source := contract.split_type_of(container)) is not None:
                # The receiver is whatever ``source`` was declared to return, which lives in
                # another file — the one thing a single file cannot know (R3.3 / 137).
                deferred.append((edge, source, member))
            else:
                # A class does not have to declare what it inherits: the call names the class it
                # was made on, and an ancestor or trait declares the method (137).
                inherited.append((edge, container, member))

        unlinked = _resolve_inherited(
            store, inherited, parent_map, max_candidates, links, siblings
        )
        unlinked.extend(
            _resolve_deferred(store, deferred, parent_map, max_candidates, links, siblings)
        )
        by_name.extend(
            _resolve_subtypes(store, unlinked, parent_map, max_candidates, links, siblings)
        )
        for edge, name, incoming in _link_by_unique_function(
            store, bare_calls, file_languages, links, siblings
        ):
            if incoming == "HEURISTIC":
                by_name.append((edge, name))

        _link_by_bare_name(store, by_name, file_languages, max_candidates, links, siblings)
        _link_writes_casefold(store, writes_misses, links, siblings)

        # One txn: kill between link and sibling insert must not leave under-linked parents.
        store.apply_resolution(links, siblings)
        inserted += len(siblings)
        if on_batch is not None:
            on_batch()
    return inserted


def _link_writes_casefold(
    store: GraphStore,
    writes_misses: Sequence[dict[str, object]],
    links: list[tuple[int, str, str]],
    siblings: list[dict[str, object]],
) -> None:
    """Link WRITES / ALTERS whose exact FQN missed via a unique case-insensitive match (215/321).

    Zero or two-or-more candidates leave the edge unlinked — ambiguity must not pick a twin.
    Uses Table/Column kinds only (contract vocabulary); never a language branch (R1.1).
    """
    if not writes_misses:
        return
    raws = [str(edge["target_raw"]) for edge in writes_misses]
    # Pass 1: unique casefold of the whole target_raw (schema.table or schema.table::col).
    ci_hits = store.nodes_by_qualified_names_casefold(raws, limit=2)
    remaining: list[dict[str, object]] = []
    for edge, raw in zip(writes_misses, raws, strict=True):
        hits = ci_hits.get(raw, [])
        if len(hits) == 1 and str(hits[0]["kind"]) in (_TABLE_KIND, _COLUMN_KIND):
            tier = _weaker_tier(str(edge["confidence_tier"]), "RESOLVED")
            _queue_candidates(edge, hits, tier, links, siblings)
            continue
        remaining.append(edge)
    if not remaining:
        return
    # Pass 2: unqualified / schema-mismatched table (::column) → unique Table by bare name.
    containers: list[str] = []
    members: list[str | None] = []
    for edge in remaining:
        container, member = contract.split_qname(str(edge["target_raw"]))
        if container is None:
            containers.append(member)
            members.append(None)
        else:
            bare = container.rsplit(".", 1)[-1]
            containers.append(bare)
            members.append(member)
    table_hits = store.nodes_by_names_casefold(containers, kind=_TABLE_KIND, limit=2)
    column_lookups: list[str] = []
    column_owners: list[tuple[dict[str, object], str]] = []
    for edge, bare, col in zip(remaining, containers, members, strict=True):
        tables = table_hits.get(bare, [])
        if len(tables) != 1:
            continue
        table_qname = str(tables[0]["qualified_name"])
        if col is None:
            tier = _weaker_tier(str(edge["confidence_tier"]), "RESOLVED")
            _queue_candidates(edge, tables, tier, links, siblings)
            continue
        column_lookups.append(contract.join_qname(table_qname, col))
        column_owners.append((edge, table_qname))
    if not column_lookups:
        return
    # Prefer exact declared column qname under the unique table; fall back to CI on that join.
    exact = store.nodes_by_qualified_names(column_lookups, kind=_COLUMN_KIND, limit=2)
    need_ci = [
        qname for qname in column_lookups if len(exact.get(qname, [])) != 1
    ]
    ci_cols = (
        store.nodes_by_qualified_names_casefold(need_ci, kind=_COLUMN_KIND, limit=2)
        if need_ci
        else {}
    )
    for (edge, _), qname in zip(column_owners, column_lookups, strict=True):
        hits = exact.get(qname, [])
        if len(hits) != 1:
            hits = ci_cols.get(qname, [])
        if len(hits) != 1:
            continue
        tier = _weaker_tier(str(edge["confidence_tier"]), "RESOLVED")
        _queue_candidates(edge, hits, tier, links, siblings)


def _link_by_unique_function(
    store: GraphStore,
    bare_calls: Sequence[tuple[dict[str, object], str, str]],
    file_languages: Mapping[str, str],
    links: list[tuple[int, str, str]],
    siblings: list[dict[str, object]],
) -> list[tuple[dict[str, object], str, str]]:
    """Link a bare CALLS to the sole same-language Function of that name (214).

    Zero or two-or-more candidates leave the edge unlinked — ambiguity must not pick a twin.
    Returns every edge this pass did not claim, for the HEURISTIC Method fallback.
    """
    # HEURISTIC bare calls belong to the Method fallback (054/204); only a claimed (non-guess)
    # bare target may bind to a unique Function (schema-unqualified EXEC — 214). An
    # all-HEURISTIC batch must cost no store query — the budget is O(1) per batch (027).
    grouped: dict[str | None, list[str]] = {}
    for edge, name, incoming in bare_calls:
        if incoming != "HEURISTIC":
            grouped.setdefault(file_languages.get(str(edge["file_path"])), []).append(name)
    if not grouped:
        return list(bare_calls)
    hits_by_language = {
        language: store.nodes_by_names(
            names, kind=_UNIQUE_FUNCTION_KIND, limit=2, language=language
        )
        for language, names in grouped.items()
    }
    leftovers: list[tuple[dict[str, object], str, str]] = []
    for edge, name, incoming in bare_calls:
        language = file_languages.get(str(edge["file_path"]))
        candidates = hits_by_language.get(language, {}).get(name, [])
        if incoming != "HEURISTIC" and len(candidates) == 1:
            _queue_candidates(
                edge, candidates, _weaker_tier(incoming, "RESOLVED"), links, siblings
            )
        else:
            leftovers.append((edge, name, incoming))
    return leftovers


def _link_by_bare_name(
    store: GraphStore,
    by_name: Sequence[tuple[dict[str, object], str]],
    file_languages: Mapping[str, str],
    max_candidates: int,
    links: list[tuple[int, str, str]],
    siblings: list[dict[str, object]],
) -> None:
    """Last chance: link a `CALLS` whose receiver is unknown to a same-named method (R5.2).

    Candidates are restricted to the CALL SITE's own language. A bare name is never evidence of a
    cross-language call, so there is DELIBERATELY no escape hatch — not even a configured language
    pair: a real FFI edge is a relation with its own evidence, not a widening of this guess (204).
    """
    grouped: dict[str | None, list[tuple[dict[str, object], str]]] = {}
    for edge, name in by_name:
        # An unattributed call site is not KNOWN to cross a boundary, so it keeps the old,
        # unfiltered set rather than silently losing edges this ticket never measured.
        language = file_languages.get(str(edge["file_path"]))
        grouped.setdefault(language, []).append((edge, name))
    for language, pairs in grouped.items():
        # Uniqueness from the batched fetch (283) — never one COUNT per edge. Probe at least
        # 2 so max_candidates=1 cannot treat a truncated prefix as a unique hit (258).
        probe_limit = max(max_candidates, 2)
        method_hits = store.nodes_by_names(
            [name for _, name in pairs],
            kind=_BARE_NAME_KIND,
            limit=probe_limit,
            language=language,
        )
        for edge, name in pairs:
            methods = method_hits.get(name, [])
            if len(methods) != 1:
                continue
            # Weaker than what the edge claimed, never stronger: the name matched, the
            # receiver did not (R5.2).
            _queue_candidates(edge, methods, "HEURISTIC", links, siblings)


class _Chain:
    """One call whose receiver is a chain of member types the graph has to walk (137)."""

    __slots__ = ("edge", "steps", "method", "receiver")

    def __init__(self, edge: dict[str, object], reference: str, method: str) -> None:
        head, *rest = reference.split(_CHAIN_STEP)
        self.edge = edge
        self.method = method
        # The head is a whole member qname; every later step is a member ON the previous type.
        self.steps: list[str] = [member_of(head), *rest]
        self.receiver: str | None = container_of(head)

    @property
    def walking(self) -> bool:
        return self.receiver is not None and bool(self.steps)


def _resolve_deferred(
    store: GraphStore,
    deferred: list[tuple[dict[str, object], str, str]],
    parent_map: Mapping[str, tuple[str, ...]],
    max_candidates: int,
    links: list[tuple[int, str, str]],
    siblings: list[dict[str, object]],
) -> list[tuple[dict[str, object], str, str]]:
    """Link a call whose receiver is the declared type of a member declared in another file.

    ``a()->b()->c()`` is one chain, so this walks it a step at a time — every step of every chain
    in one batched round, never one query per call. Returns what no step could answer; a chain
    that broke has no receiver type left to walk from, so it carries an empty container.
    """
    if not deferred:
        return []
    chains = [_Chain(edge, reference, method) for edge, reference, method in deferred]
    for _ in range(_MAX_CHAIN_STEPS):
        walking = [chain for chain in chains if chain.walking]
        if not walking:
            break
        ancestries = {
            chain.receiver: _ancestry(str(chain.receiver), parent_map) for chain in walking
        }
        declared = store.declared_types(
            sorted(
                contract.join_qname(ancestor, chain.steps[0])
                for chain in walking
                for ancestor in ancestries[chain.receiver]
            )
        )
        for chain in walking:
            found = _declared_class(
                str(chain.receiver), chain.steps[0], ancestries[chain.receiver], declared
            )
            chain.receiver = found
            if found is not None:
                chain.steps.pop(0)

    # Anything still walking ran past the step bound; treat it as unanswered, never as resolved.
    settled = [chain for chain in chains if chain.receiver is not None and not chain.steps]
    probes = {contract.join_qname(str(chain.receiver), chain.method) for chain in settled}
    # The receiver itself, because a declared type the graph holds no node for was never really
    # resolved — a nullable or union type reads as one name and names nothing (137).
    probes.update(str(chain.receiver) for chain in settled)
    resolved = store.nodes_by_qualified_names(sorted(probes), limit=max_candidates)

    unanswered: list[tuple[dict[str, object], str, str]] = [
        (chain.edge, "", chain.method)
        for chain in chains
        if chain.receiver is None or chain.steps
    ]
    walk: list[tuple[dict[str, object], str, str]] = []
    for chain in settled:
        if not resolved.get(str(chain.receiver)):
            unanswered.append((chain.edge, "", chain.method))
            continue
        hits = resolved.get(contract.join_qname(str(chain.receiver), chain.method), [])
        if hits:
            tier = _weaker_tier(str(chain.edge["confidence_tier"]), "RESOLVED")
            _queue_candidates(chain.edge, hits, tier, links, siblings)
        else:
            # The receiver is known but does not declare the method here — an ancestor may.
            walk.append((chain.edge, str(chain.receiver), chain.method))
    unanswered.extend(
        _resolve_inherited(store, walk, parent_map, max_candidates, links, siblings)
    )
    return unanswered


def _resolve_subtypes(
    store: GraphStore,
    unlinked: list[tuple[dict[str, object], str, str]],
    parent_map: Mapping[str, tuple[str, ...]],
    max_candidates: int,
    links: list[tuple[int, str, str]],
    siblings: list[dict[str, object]],
) -> list[tuple[dict[str, object], str]]:
    """A receiver whose own type does not declare the member — a subtype does (137).

    ``f(Shape $s)`` narrowed to a concrete one and then asked for a method only that one declares
    is ordinary code, so walking up cannot be the whole answer. Which subtype runs is a runtime
    question, so this links at HEURISTIC no matter how certain the receiver was: the *receiver*
    was known, the *target* is a guess among the subtypes, and R5.2 grades the target.

    Bounded to types the graph actually holds below the receiver — never a same-named method
    anywhere, which is the name-match path this deliberately narrows.
    """
    # Only a broken chain falls back to the name-match path: it never had a receiver type, so a
    # same-named method is all that is left. A call that names a type the graph simply does not
    # hold stays unlinked, exactly as an unindexed static call always has — guessing there would
    # trade a precise unlinked claim for an imprecise linked one (136's vendor cap).
    def unmatched(entries: list[tuple[dict[str, object], str, str]]) -> list[
        tuple[dict[str, object], str]
    ]:
        return [(edge, member) for edge, container, member in entries if not container]

    candidates = [entry for entry in unlinked if entry[1]]
    if not candidates:
        return unmatched(unlinked)
    children: dict[str, list[str]] = {}
    for child, parents in parent_map.items():
        for parent in parents:
            children.setdefault(parent, []).append(child)
    chains = {
        container: _descendants(container, children) for _, container, _ in candidates
    }
    probes = {
        contract.join_qname(subtype, member)
        for _, container, member in candidates
        for subtype in chains[container]
    }
    hits = store.nodes_by_qualified_names(sorted(probes), limit=max_candidates)

    settled: set[int] = set()
    for edge, container, member in candidates:
        found = [
            node
            for subtype in chains[container]
            for node in hits.get(contract.join_qname(subtype, member), [])
        ]
        if found:
            _queue_candidates(
                edge, found, _weaker_tier(str(edge["confidence_tier"]), "HEURISTIC"),
                links, siblings,
            )
            settled.add(id(edge))
    return unmatched([entry for entry in unlinked if id(entry[0]) not in settled])


def _descendants(container: str, children: Mapping[str, list[str]]) -> list[str]:
    """Every type below ``container``, breadth-first; ``seen`` makes a cycle terminate."""
    order: list[str] = []
    seen = {container}
    queue = [container]
    while queue and len(order) < _MAX_SUBTYPES:
        for child in children.get(queue.pop(0), ()):
            if child not in seen:
                seen.add(child)
                order.append(child)
                queue.append(child)
    return order


def _declared_class(
    receiver: str, member: str, ancestry: Sequence[str], declared: Mapping[str, str]
) -> str | None:
    """The type ``receiver::member`` was declared to hold, relative ones read against their site.

    ``RELATIVE_TYPE_DECLARING`` is the type that declared the member; ``RELATIVE_TYPE_RECEIVER``
    is the one it was called on, which is why a fluent builder follows the caller and not the
    base class. Anything else is used as written — a name that is not a type simply never matches
    a node, so the core needs no reading of type syntax at all.
    """
    for ancestor in ancestry:
        found = declared.get(contract.join_qname(ancestor, member))
        if found is None:
            continue
        if found == contract.RELATIVE_TYPE_DECLARING:
            return ancestor
        if found == contract.RELATIVE_TYPE_RECEIVER:
            return receiver
        return found
    return None


def container_of(qname: str) -> str:
    """The container part of a member qname; a name with no member is its own container."""
    container, member = contract.split_qname(qname)
    return qname if container is None else container


def member_of(qname: str) -> str:
    return contract.split_qname(qname)[1]


def _ancestry(container: str, parents: Mapping[str, tuple[str, ...]]) -> list[str]:
    """``container`` then its ancestors, breadth-first in ``hierarchy_parents`` order.

    Breadth-first so the nearest declaration wins, and ``seen`` makes a cycle — which a broken
    or partially-indexed tree can hold — terminate instead of hanging the build.
    """
    order = [container]
    seen = {container}
    index = 0
    while index < len(order):
        for parent in parents.get(order[index], ()):
            if parent not in seen:
                seen.add(parent)
                order.append(parent)
        index += 1
    return order


def _resolve_inherited(
    store: GraphStore,
    inherited: list[tuple[dict[str, object], str, str]],
    parent_map: Mapping[str, tuple[str, ...]],
    max_candidates: int,
    links: list[tuple[int, str, str]],
    siblings: list[dict[str, object]],
) -> list[tuple[dict[str, object], str, str]]:
    r"""Link ``\C::m`` to the ancestor that actually declares ``m`` — one batched lookup (137).

    Nothing here reads a language: the walk is over ``INHERIT_KINDS``, which every adapter emits
    (R1.1). Returns the entries no ancestor declared, so a caller can decide what an unanswered
    receiver costs; for a call the adapter qualified itself, that is nothing — the claim stays
    the qualified name the receiver earned, which is what names what to stub (136).
    """
    if not inherited:
        return []
    chains = {container: _ancestry(container, parent_map) for _, container, _ in inherited}
    probes = {
        contract.join_qname(ancestor, member)
        for _, container, member in inherited
        for ancestor in chains[container]
    }
    hits = store.nodes_by_qualified_names(sorted(probes), limit=max_candidates)
    unlinked: list[tuple[dict[str, object], str, str]] = []
    for entry in inherited:
        edge, container, member = entry
        for ancestor in chains[container]:
            found = hits.get(contract.join_qname(ancestor, member))
            if found:
                tier = _weaker_tier(str(edge["confidence_tier"]), "RESOLVED")
                _queue_candidates(edge, found, tier, links, siblings)
                break
        else:
            unlinked.append(entry)
    return unlinked


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


def _path_key(edge: Mapping[str, object]) -> str:
    """The ``File`` qname a path-shaped edge names, per the contract's declared basis (188).

    ``repo-relative`` is the path the adapter resolved; ``includer-relative`` is joined onto the
    emitting file's directory. Either way the discriminator is the graph — a raw naming no indexed
    file does not link — so a symbol-shaped ``IMPORTS`` stays bare with no language branch.
    """
    raw = str(edge["target_raw"])
    if contract.PATH_TARGET_BASIS[str(edge["kind"])] == "repo-relative":
        return raw
    return _relative_to(str(edge["file_path"]), raw)


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
