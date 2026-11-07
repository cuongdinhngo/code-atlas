"""Where else the code a read names lives: overrides, aliases, other definitions (394, 403).

A body read can be correct and still be the wrong code — an empty base method whose behaviour sits
in two subclasses, a class a test bootstrap aliases to a stub, a function with test-bootstrap
copies. Each pointer is read from rows and edges the index already holds; none is a new relation.
"""

from __future__ import annotations

import fnmatch
import functools
import json
import re
from collections.abc import Mapping, Sequence

from code_atlas import contract
from code_atlas.config import VERSION_TOKEN
from code_atlas.enrichment import DEFINITION_ORDER_META_KEY, DEFINITION_PRECEDENCE_META_KEY
from code_atlas.store import GraphStore, Row
from code_atlas.symbol_role import path_indicates_test

IMPLEMENTED_BY_FIELD = "implemented_by"
IMPLEMENTED_BY_TRUNCATED_FIELD = "implemented_by_truncated"
ALIASES_FIELD = "aliases"
AMBIGUITY_FIELD = "ambiguity"
TEST_COPIES = "test_copies"
# Several migrations redefine one object; the highest version answers (403).
MIGRATION_REDEFINITIONS = "migration_redefinitions"
# The project's declared precedence picks the definition that answers (414).
DEFINITION_PRECEDENCE = "definition_precedence"
# A definition's place under the declared precedence (437); only `live` is the one that runs.
DEFINITION_LIVE = "live"
DEFINITION_SUPERSEDED = "superseded"
DEFINITION_UNRANKED = "unranked"
DEFINITION_TEST_COPY = "test_copy"
DEFINITION_STATE_FIELD = "definition_state"
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


def declared_precedence(store: GraphStore) -> tuple[str, ...]:
    """The declared path globs, most authoritative first: the toml's ``definition_order`` (437),
    then the rules file's ``definitions.precedence`` (414); empty when neither is declared."""
    globs: list[str] = []
    for key in (DEFINITION_ORDER_META_KEY, DEFINITION_PRECEDENCE_META_KEY):
        raw = store.get_meta(key)
        globs.extend(json.loads(raw) if raw else ())
    return tuple(dict.fromkeys(globs))


# What `fnmatch.translate` returns: `(?s:<body>)\Z`.
_TRANSLATED = re.compile(r"\(\?s:(.*)\)\\Z", re.DOTALL)


@functools.lru_cache(maxsize=256)
def _glob_pattern(glob: str) -> re.Pattern[str]:
    """``fnmatch`` semantics, plus one ``<n>`` capturing a ``1``, ``1.5`` or ``2_0_1`` version."""
    parts = []
    for part in glob.split(VERSION_TOKEN):
        body = _TRANSLATED.fullmatch(fnmatch.translate(part))
        if body is None:  # a Python whose fnmatch wraps its pattern differently: fail loud
            raise RuntimeError(f"fnmatch.translate({part!r}) has an unknown shape")
        parts.append(body.group(1))
    return re.compile(r"(\d+(?:[._]\d+)*)".join(parts), re.DOTALL)


def _rank(path: str, precedence: Sequence[str]) -> tuple[int, tuple[int, ...]] | None:
    """How authoritative a definition at ``path`` is: the first glob it matches, then its version.

    Higher is more authoritative; ``None`` when no glob matches. ``1.0`` and ``1`` tie (403).
    """
    for position, glob in enumerate(precedence):
        hit = _glob_pattern(glob).fullmatch(path)
        if hit is None:
            continue
        digits = re.split(r"[._]", hit.group(1)) if hit.groups() else []
        version = [int(part) for part in digits]
        while len(version) > 1 and version[-1] == 0:
            version.pop()
        return len(precedence) - position, tuple(version)
    return None


def _answering(
    rows: Sequence[Row], precedence: Sequence[str], *, complete: bool
) -> tuple[Row | None, dict[int, tuple[int, tuple[int, ...]]]]:
    """The one production row the precedence ranks highest, and every production row's rank.

    A tie at the top, no glob matching, or a cut fetch (an unseen row may rank higher): ``None``.
    """
    ranks: dict[int, tuple[int, tuple[int, ...]]] = {}
    for index, row in enumerate(rows):
        rank = None if row.get("is_test") else _rank(str(row["file_path"]), precedence)
        if rank is not None:
            ranks[index] = rank
    if not complete or not ranks:
        return None, ranks
    best = max(ranks.values())
    top = [index for index, rank in ranks.items() if rank == best]
    return (rows[top[0]] if len(top) == 1 else None), ranks


def precedence_first(
    rows: Sequence[Row], precedence: Sequence[str], *, complete: bool = True
) -> tuple[list[Row], bool]:
    """The one production definition the precedence ranks highest, then the rest (414, 437).

    The first glob any production row matches decides, and within a ``<n>`` glob the highest
    version: one row answers; a tie leaves the rows as they are, never a guess.
    """
    if len(rows) < 2 or not precedence:
        return list(rows), False
    answer, _ = _answering(rows, precedence, complete=complete)
    if answer is None:
        return list(rows), False
    return [answer, *(row for row in rows if row is not answer)], True


def definition_states(
    rows: Sequence[Row], precedence: Sequence[str], *, complete: bool = True
) -> list[dict[str, object]]:
    """Which of a qname's definitions is ``live`` and which are ``superseded`` by it (437).

    ``definition_ordinal`` counts up to the live one (ties share one); a row no glob ranks has
    none. No precedence, a tie or a cut fetch: every production row is ``unranked`` (R5.6).
    """
    answer, ranks = _answering(rows, precedence, complete=complete) if precedence else (None, {})
    ordinal = {rank: n for n, rank in enumerate(sorted(set(ranks.values())), start=1)}
    states: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        state = {**_site(row), "definition_ordinal": ordinal.get(ranks.get(index, (0, ())))}
        if row.get("is_test"):
            state["state"] = DEFINITION_TEST_COPY
        elif answer is None:
            state["state"] = DEFINITION_UNRANKED
        elif row is answer:
            state["state"] = DEFINITION_LIVE
        else:
            state["state"] = DEFINITION_SUPERSEDED
            state["superseded_by"] = _site(answer)
        states.append(state)
    return states


def one_definition_first(
    rows: Sequence[Row],
    *,
    complete: bool = True,
    every_version: bool = True,
    precedence: Sequence[str] = (),
) -> tuple[list[Row], str | None]:
    """The definition that answers first, and why the others do not compete — or ``None``.

    The one rule every reader of several definitions applies (R1.8): a production row over its test
    copies (394), then the project's declared precedence (414), then the latest of a migration's
    redefinitions (403). ``every_version=False`` (a page may hide a redefinition) never names a
    latest it cannot see, nor a preferred definition.
    """
    ordered, held = test_copies_first(rows, complete=complete)
    if held:
        return ordered, TEST_COPIES
    ordered, held = precedence_first(rows, precedence, complete=complete and every_version)
    if held:
        return ordered, DEFINITION_PRECEDENCE
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
