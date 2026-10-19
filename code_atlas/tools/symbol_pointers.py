"""Where else the code a read names lives: overrides, aliases, other definitions (394, 403).

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
# Several migrations redefine one object; the highest version answers (403).
MIGRATION_REDEFINITIONS = "migration_redefinitions"
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


def _migration_version(row: Row) -> tuple[int, ...] | None:
    """The adapter-stamped migration version of a definition, trailing zero parts dropped (403).

    ``1.0`` and ``1`` are one version (trailing zero parts never count); ``None`` when unstamped.
    """
    raw = row.get("extra")
    try:
        extra = json.loads(raw) if isinstance(raw, str) and raw else {}
    except json.JSONDecodeError:
        return None
    version = extra.get(contract.MIGRATION_VERSION_KEY) if isinstance(extra, dict) else None
    if not isinstance(version, str):
        return None
    try:
        parts = [int(part) for part in version.split(".")]
    except ValueError:
        return None
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def latest_migration_first(
    rows: Sequence[Row], *, complete: bool = True
) -> tuple[list[Row], bool]:
    """The highest version first when every production definition is a redefinition in one
    migration directory; test copies follow them and never answer (403).

    An unversioned row, a tied version, two directories (two migration sets) or a cut fetch is a
    genuine ambiguity: the rows are left as they are.
    """
    production = [row for row in rows if not row.get("is_test")]
    copies = [row for row in rows if row.get("is_test")]
    if not complete or len(rows) < 2 or not production:
        return list(rows), False
    versions = [_migration_version(row) for row in production]
    known = [version for version in versions if version is not None]
    folders = {str(row["file_path"]).rpartition("/")[0] for row in production}
    if len(known) != len(production) or len(set(known)) != len(known) or len(folders) != 1:
        return list(rows), False
    ranked = sorted(zip(known, production, strict=True), key=lambda pair: pair[0], reverse=True)
    return [row for _, row in ranked] + copies, True


def one_definition_first(
    rows: Sequence[Row], *, complete: bool = True, every_version: bool = True
) -> tuple[list[Row], str | None]:
    """The definition that answers first, and why the others do not compete — or ``None``.

    The one rule every reader of several definitions applies (R1.8): a production row over its test
    copies (394), then the latest of a migration's redefinitions (403). ``every_version=False``
    (a page may hide a redefinition) never names a latest it cannot see.
    """
    ordered, held = test_copies_first(rows, complete=complete)
    if held:
        return ordered, TEST_COPIES
    ordered, held = latest_migration_first(rows, complete=complete and every_version)
    return ordered, MIGRATION_REDEFINITIONS if held else None


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
