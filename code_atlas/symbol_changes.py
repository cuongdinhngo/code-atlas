"""Has this symbol changed since revision X — per symbol, not per file (task 384).

A snapshot records, per symbol, its signature (params, modifiers, declared type) and the
``body_hash`` its adapter stamped — tokens only, so a comment or whitespace edit does not move it.
The consumer keeps the snapshot; ``compare`` judges named qnames or paths against the current
index. A symbol the snapshot never held is ``unknown_at_base``, never ``unchanged`` (R5.6).
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass

from code_atlas import contract
from code_atlas.store import GraphStore

SNAPSHOT_FORMAT = "code-atlas-symbols/1"

UNCHANGED = "unchanged"
BODY_CHANGED = "body_changed"
SIGNATURE_CHANGED = "signature_changed"
MOVED = "moved"
REMOVED = "removed"
UNKNOWN_AT_BASE = "unknown_at_base"
UNKNOWN = "unknown"

# A File or Namespace spans unrelated symbols, so it is no symbol's body.
_UNSNAPSHOTTED = frozenset({"File", "Namespace"})
# Twins of one qname, or same-named candidates for a move — more than this is not one symbol.
_LOOKUP_LIMIT = 50


@dataclass(frozen=True)
class Symbol:
    """One symbol as a snapshot records it."""

    qname: str
    file: str
    kind: str
    name: str
    signature: str
    body_hash: str | None


def _json(raw: object) -> object:
    if isinstance(raw, str) and raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


def symbol_of(row: Mapping[str, object]) -> Symbol | None:
    """The snapshot form of a node row; ``None`` for a kind that is no symbol's body."""
    kind = str(row["kind"])
    if kind in _UNSNAPSHOTTED:
        return None
    extra = _json(row.get("extra"))
    extra = extra if isinstance(extra, dict) else {}
    signature = {
        "params": _json(row.get("params")),
        "modifiers": _json(row.get("modifiers")),
        "type": extra.get("type"),
    }
    body_hash = extra.get(contract.BODY_HASH)
    return Symbol(
        qname=str(row["qualified_name"]),
        file=str(row["file_path"]),
        kind=kind,
        name=str(row["name"]),
        signature=json.dumps(signature, sort_keys=True, separators=(",", ":")),
        body_hash=body_hash if isinstance(body_hash, str) else None,
    )


def snapshot(rows: Iterable[Mapping[str, object]], *, rev: str | None, ref: str | None) -> dict:
    """Every symbol in the index at one revision, in a stable order (R4.2)."""
    symbols = [asdict(symbol) for symbol in map(symbol_of, rows) if symbol is not None]
    return {"format": SNAPSHOT_FORMAT, "rev": rev, "ref": ref, "symbols": symbols}


def read_snapshot(data: object) -> tuple[dict[str, object], list[Symbol]]:
    """The snapshot's revision fields and symbols; ``ValueError`` for anything else."""
    if not isinstance(data, dict) or data.get("format") != SNAPSHOT_FORMAT:
        raise ValueError(f"not a {SNAPSHOT_FORMAT} snapshot")
    try:
        symbols = [Symbol(**entry) for entry in data["symbols"]]
    except (KeyError, TypeError) as error:
        raise ValueError(f"malformed {SNAPSHOT_FORMAT} snapshot: {error}") from None
    return {"rev": data.get("rev"), "ref": data.get("ref")}, symbols


def compare(
    store: GraphStore,
    base: Sequence[Symbol],
    *,
    qnames: Sequence[str] = (),
    paths: Sequence[str] = (),
    drifted: Collection[str] = (),
) -> list[dict[str, object]]:
    """One verdict per base symbol a subject names, in subject order.

    ``drifted`` lists files changed since the index was built: a symbol in one is ``unknown``,
    since the index cannot see the edit and would otherwise answer ``unchanged``.
    """
    by_qname: dict[str, list[Symbol]] = defaultdict(list)
    by_file: dict[str, list[Symbol]] = defaultdict(list)
    for symbol in base:
        by_qname[symbol.qname].append(symbol)
        by_file[symbol.file].append(symbol)
    verdicts: list[dict[str, object]] = []
    for qname in qnames:
        if qname not in by_qname:
            now = _current(store, qname)
            verdicts.append(_verdict(qname, qname, UNKNOWN_AT_BASE, None, now[0] if now else None))
            continue
        verdicts.extend(_judge(store, qname, symbol, drifted) for symbol in by_qname[qname])
    for path in paths:
        held = {symbol.qname for symbol in by_file.get(path, [])}
        verdicts.extend(_judge(store, path, symbol, drifted) for symbol in by_file.get(path, []))
        for row in store.nodes_by_file_all(path):
            fresh = symbol_of(row)
            if fresh is not None and fresh.qname not in held:
                verdicts.append(_verdict(path, fresh.qname, UNKNOWN_AT_BASE, None, fresh))
    return verdicts


def _current(store: GraphStore, qname: str) -> list[Symbol]:
    rows = store.nodes_by_qualified_names([qname], limit=_LOOKUP_LIMIT).get(qname, [])
    return [symbol for symbol in map(symbol_of, rows) if symbol is not None]


def _judge(
    store: GraphStore, subject: str, base: Symbol, drifted: Collection[str]
) -> dict[str, object]:
    now = _current(store, base.qname)
    here = next((symbol for symbol in now if symbol.file == base.file), None)
    if here is None and base.body_hash is not None:
        # A move keeps the body: the same qname in another file, or the same name and kind.
        moved = next((symbol for symbol in now if symbol.body_hash == base.body_hash), None)
        if moved is None:
            rows = store.nodes_by_names([base.name], kind=base.kind, limit=_LOOKUP_LIMIT)
            candidates = (symbol_of(row) for row in rows.get(base.name, []))
            moved = next(
                (s for s in candidates if s is not None and s.body_hash == base.body_hash), None
            )
        if moved is not None:
            return _checked(subject, base, MOVED, moved, drifted)
    if here is None and now:
        here = now[0]
    if here is None:
        return _checked(subject, base, REMOVED, None, drifted)
    if here.signature != base.signature:
        return _checked(subject, base, SIGNATURE_CHANGED, here, drifted)
    if here.body_hash is None or base.body_hash is None:
        verdict = _verdict(subject, base.qname, UNKNOWN, base, here)
        verdict["reason"] = "no_body_hash"
        return verdict
    status = UNCHANGED if here.body_hash == base.body_hash else BODY_CHANGED
    return _checked(subject, base, status, here, drifted)


def _checked(
    subject: str, base: Symbol, status: str, now: Symbol | None, drifted: Collection[str]
) -> dict[str, object]:
    files = {base.file} | ({now.file} if now is not None else set())
    if files & set(drifted):
        verdict = _verdict(subject, base.qname, UNKNOWN, base, now)
        verdict["reason"] = "file_changed_since_index"
        return verdict
    return _verdict(subject, base.qname, status, base, now)


def _verdict(
    subject: str, qname: str, status: str, base: Symbol | None, now: Symbol | None
) -> dict[str, object]:
    verdict: dict[str, object] = {"subject": subject, "qname": qname, "status": status}
    if base is not None:
        verdict["file_base"] = base.file
    if now is not None:
        verdict["file_now"] = now.file
        if now.qname != qname:
            verdict["qname_now"] = now.qname
    return verdict
