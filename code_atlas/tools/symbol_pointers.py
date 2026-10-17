"""Where else the code a read names lives: overrides, aliases, test copies (394).

A body read can be correct and still be the wrong code — an empty base method whose behaviour sits
in two subclasses, a class a test bootstrap aliases to a stub, a function with test-bootstrap
copies. Each pointer is read from rows and edges the index already holds; none is a new relation.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from code_atlas import contract
from code_atlas.store import GraphStore, Row
from code_atlas.symbol_role import path_indicates_test

IMPLEMENTED_BY_FIELD = "implemented_by"
IMPLEMENTED_BY_TRUNCATED_FIELD = "implemented_by_truncated"
ALIASES_FIELD = "aliases"
AMBIGUITY_FIELD = "ambiguity"
TEST_COPIES = "test_copies"
# Overrides named per read, and subtype levels walked to find them: a pointer, not a hierarchy.
IMPLEMENTED_BY_CAP = 20
_DESCENT_LEVELS = 4


def implemented_by(store: GraphStore, node: Mapping[str, object] | Row) -> dict[str, object]:
    """The overriding callables of an empty or abstract method, from its class's stored subtypes.

    Read from linked ``EXTENDS`` / ``IMPLEMENTS`` edges and the subtypes' own member rows, nearest
    level first, so an adapter that links no inheritance yields nothing — never a guessed override.
    """
    qname = str(node["qualified_name"])
    if str(node["kind"]) not in contract.CALLABLE_KINDS or contract.MEMBER_SEPARATOR not in qname:
        return {}
    if not _bodiless(store, node):
        return {}
    owner, member = qname.rsplit(contract.MEMBER_SEPARATOR, 1)
    found: list[dict[str, object]] = []
    seen = {owner}
    level = [owner]
    truncated = False
    for _ in range(_DESCENT_LEVELS):
        children = []
        for parent in level:
            edges = store.edges_by_target(
                parent, kinds=contract.IMPL_KINDS, limit=IMPLEMENTED_BY_CAP + 1
            )
            truncated = truncated or len(edges) > IMPLEMENTED_BY_CAP  # subtypes went unread
            for edge in edges[:IMPLEMENTED_BY_CAP]:
                child = str(edge["source_qname"])
                if child not in seen:
                    seen.add(child)
                    children.append(child)
        for child in sorted(children):
            for row in store.nodes_by_qualified_name(
                f"{child}{contract.MEMBER_SEPARATOR}{member}", limit=1
            ):
                if len(found) >= IMPLEMENTED_BY_CAP:
                    truncated = True
                    break
                found.append(_site(row))
        level = sorted(children)
        if not level:
            break
    if not found:
        return {}
    pointer: dict[str, object] = {IMPLEMENTED_BY_FIELD: found}
    if truncated:
        pointer[IMPLEMENTED_BY_TRUNCATED_FIELD] = True
    return pointer


def _bodiless(store: GraphStore, node: Mapping[str, object] | Row) -> bool:
    """Abstract, or a body that reaches nothing: the graph's own cue, never a body grammar (R1.1).

    A declared ``abstract`` modifier, or no edge leaving the method but containment — what an
    empty ``{}`` emits in every language, and what F1's empty base method did.
    """
    if "abstract" in _modifiers(node.get("modifiers")):
        return True
    leaving = store.count_edges_by_source(
        str(node["qualified_name"]), kinds=contract.UNLINKED_EVIDENCE_KINDS
    )
    return leaving == 0


def _modifiers(raw: object) -> list[str]:
    """A stored modifier list (JSON text) or a parsed one, as strings."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return []
    return [str(item) for item in raw] if isinstance(raw, list) else []


def aliases(store: GraphStore, qname: str) -> list[dict[str, object]]:
    """The names an ``ALIASES`` edge ties to ``qname``, either way, with the declaring file.

    ``alias_of``: ``qname`` is an alias of the named class. ``aliased_as``: the named alias points
    at ``qname``. An alias declared in a file the index classes as a test is a ``test_double``.
    """
    entries: list[dict[str, object]] = []
    for edge in store.edges_by_source(qname, kinds=(contract.ALIASES,), limit=IMPLEMENTED_BY_CAP):
        entries.append(_alias(store, edge, str(edge["target_raw"]), "alias_of"))
    for edge in store.edges_by_target_raw(
        qname, kinds=(contract.ALIASES,), limit=IMPLEMENTED_BY_CAP
    ):
        entries.append(_alias(store, edge, str(edge["source_qname"]), "aliased_as"))
    return entries


def test_copies_first(rows: Sequence[Row], *, complete: bool = True) -> tuple[list[Row], bool]:
    """Production first when it is the one definition and every other is a test copy.

    Returns the rows in that order, and whether the case held; any other mix is left as it is.
    ``complete=False`` (a fetch that hit its limit) never holds: an unseen row may be production.
    """
    if not complete:
        return list(rows), False
    production = [row for row in rows if not row.get("is_test")]
    copies = [row for row in rows if row.get("is_test")]
    if len(rows) > 1 and len(production) == 1 and copies:
        return [production[0], *copies], True
    return list(rows), False


def _alias(
    store: GraphStore, edge: Mapping[str, object] | Row, name: str, relation: str
) -> dict[str, object]:
    path = str(edge["file_path"])
    entry: dict[str, object] = {
        "qname": name,
        "relation": relation,
        "file": path,
        "line": edge["line"],
    }
    if _is_test_file(store, path):
        entry["test_double"] = True
    return entry


def _is_test_file(store: GraphStore, path: str) -> bool:
    """The index's own verdict on the file — its rows' role — else the path convention."""
    rows = store.nodes_by_file(path, limit=1)
    if rows:
        return bool(rows[0].get("is_test"))
    return path_indicates_test(path)


def _site(row: Mapping[str, object] | Row) -> dict[str, object]:
    return {"qname": row["qualified_name"], "file": row["file_path"], "line": row["line_start"]}
