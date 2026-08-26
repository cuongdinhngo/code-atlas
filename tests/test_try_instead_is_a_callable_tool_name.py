"""Task 093 — every ``try_instead`` value the core can emit is a tool the reader can call.

The field mixed two registers: `search_symbol` (a real tool) sat beside
`find_references_on_method_qname` (an instruction shaped like an identifier), so an agent could not
tell without trying whether a given value was a route or prose. The split is now a naming rule —
``TRY_INSTEAD_*`` is a registered tool name, ``TRY_INSTEAD_HINT_*`` is prose — and this is the gate
that holds it. Both sets are derived (module namespace + ``main.TOOL_NAMES``), never hand-kept: a
hand-kept list is what drifts (R1.1).

Two boundaries this file asserts but does not close, stated so neither reads as covered:
- Callability is checked against ``main.TOOL_NAMES``, the full surface. ``CA_TOOLS`` can serve a
  subset, and a deployment that drops ``search_symbol`` would still be offered it as a route. The
  routes are chosen in ``nav_result``, which has no ``Config``, so closing this means threading the
  allow-list into the payload layer — a change 093 did not buy (pre-existing, cf. ``file_outline``).
- A route is checked to EXIST, not to answer. Whether the tool can serve the question is judged per
  emitter: ``include_graph`` deliberately carries no route because none can (see below).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.build_info import server_provenance
from code_atlas.main import TOOL_NAMES
from code_atlas.store import GraphStore
from code_atlas.tools import find_references, include_graph, nav_result, search_symbol
from tests.test_nav_tools import db_config, edge, node, seed_file

_ROUTE_PREFIX = "TRY_INSTEAD_"
_HINT_PREFIX = "TRY_INSTEAD_HINT_"


def _constants(prefix: str, *, exclude: str | None = None) -> dict[str, str]:
    """Every ``str`` constant in ``nav_result`` under ``prefix``, minus ``exclude``'s namespace."""
    return {
        name: value
        for name, value in vars(nav_result).items()
        if name.startswith(prefix)
        and isinstance(value, str)
        and not (exclude is not None and name.startswith(exclude))
    }


def test_every_try_instead_route_is_a_registered_tool_name() -> None:
    routes = _constants(_ROUTE_PREFIX, exclude=_HINT_PREFIX)
    assert routes, "no try_instead routes found — the derivation broke, not the invariant"
    prose = {name: value for name, value in routes.items() if value not in TOOL_NAMES}
    assert not prose, (
        f"try_instead value(s) are not registered tools: {prose}. "
        f"A route must be callable; prose belongs in a {_HINT_PREFIX}* sibling."
    )


def test_the_two_field_reported_prose_values_are_gone() -> None:
    """The exact strings the field evaluator could not call (093 §4, §9 runner-up)."""
    values = set(_constants(_ROUTE_PREFIX).values())
    assert "find_references_on_method_qname" not in values
    assert "path_basename_search" not in values


def test_hints_are_prose_and_never_shadow_a_tool_name() -> None:
    """A hint equal to a tool name would re-create the ambiguity from the other side."""
    hints = _constants(_HINT_PREFIX)
    assert hints, "no try_instead hints found — the derivation broke, not the invariant"
    shadowing = {name: value for name, value in hints.items() if value in TOOL_NAMES}
    assert not shadowing, f"hint(s) shadow a tool name: {shadowing}"


def _route_use_counts() -> dict[str, int]:
    """Uses of each route constant across ``code_atlas/tools/``, NOT counting its own definition.

    ``nav_result`` is where every constant is defined, so counting a name's presence there as a
    use makes the guard vacuous — it would find every constant "used" by its own definition line.
    Assignment lines are skipped instead, leaving genuine in-module attachments counted.
    """
    from code_atlas.tools import nav_result as defining_module

    routes = _constants(_ROUTE_PREFIX, exclude=_HINT_PREFIX)
    counts = dict.fromkeys(routes, 0)
    for source in sorted(Path(defining_module.__file__).parent.glob("*.py")):
        for line in source.read_text(encoding="utf-8").splitlines():
            for name in routes:
                if line.startswith(f"{name} ="):
                    continue  # the assignment itself is a definition, never a use
                counts[name] += line.count(name)
    return counts


def test_every_route_constant_is_actually_emitted() -> None:
    """A route nobody emits is dead vocabulary — the R1 audit must stay exhaustive, not stale."""
    counts = _route_use_counts()
    assert counts, "no route constants found — the derivation broke, not the invariant"
    unused = sorted(name for name, uses in counts.items() if uses == 0)
    assert not unused, f"route constant(s) nothing emits: {unused}"


def test_the_dead_route_guard_can_actually_fail() -> None:
    """The guard above is only worth having if a dead constant trips it — so prove one does.

    Injecting a route no module references must be reported. Without this, a guard that counts
    the definition site as a use passes forever and the audit rots silently (093 review).
    """
    injected = "TRY_INSTEAD_NOBODY_EMITS_THIS"
    setattr(nav_result, injected, "search_symbol")
    try:
        counts = _route_use_counts()
        assert counts.get(injected) == 0
        with pytest.raises(AssertionError, match=injected):
            test_every_route_constant_is_actually_emitted()
    finally:
        delattr(nav_result, injected)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def test_the_field_reported_payload_is_pinned_whole(tmp_path: Path, store: GraphStore) -> None:
    """§4 row 2 verbatim: `find_references` on a class consumed via a ``::class`` constant.

    Pinned as a whole dict, not field-by-field — 093's defect was the payload read as a set of
    callable routes, so what the reader sees in full is the thing under test.
    """
    seed_file(
        store,
        "a.php",
        [node("Class", "RegionManager", "\\Src\\System\\RegionManager", "a.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "b.php",
        [],
        [edge("REFERENCES", "\\Other", "RegionManager", "b.php", tier="BARE_NAME")],
        root=tmp_path,
    )
    payload = find_references.create(db_config(tmp_path))(
        "\\Src\\System\\RegionManager", detail_level="minimal"
    )
    assert payload == {
        "indexed": True,
        "qname": "\\Src\\System\\RegionManager",
        "results": [],
        "truncated": False,
        "index_root": str(tmp_path),
        "reason": nav_result.REASON_RELATIONSHIP_NOT_MODELLED,
        "total_count": 0,
        "try_instead": nav_result.TRY_INSTEAD_SEARCH_SYMBOL,
        "try_instead_hint": nav_result.TRY_INSTEAD_HINT_METHOD_QNAME,
        **server_provenance(),
    }
    assert payload["try_instead"] in TOOL_NAMES


def test_include_graph_offers_a_hint_and_deliberately_no_route(
    tmp_path: Path, store: GraphStore
) -> None:
    """The second prose value became a hint with NO route, because no tool can answer it.

    The evidence is unlinked include text in ``edges.target_raw``; ``nodes_fts`` indexes
    name/qname/file_path/params only. Routing to ``search_symbol`` returned ``reason=ok`` with the
    symbols declared IN the file and no includer — a confident wrong answer is worse than none.
    """
    seed_file(
        store,
        "app.php",
        [node("File", "app.php", "app.php", "app.php")],
        [edge("INCLUDES", "app.php", "dirname(__DIR__) . '/lib.php'", "app.php", tier="DYNAMIC")],
        root=tmp_path,
    )
    payload = include_graph.create(db_config(tmp_path))("lib.php", direction="imported_by")
    assert payload["reason"] == nav_result.REASON_RELATIONSHIP_NOT_MODELLED
    assert payload["try_instead_hint"] == nav_result.TRY_INSTEAD_HINT_PATH_BASENAME
    assert "try_instead" not in payload


def test_no_route_points_a_tool_back_at_itself(tmp_path: Path, store: GraphStore) -> None:
    """A self-route loops for the mechanical reader `try_instead` exists for (093 review).

    ``find_references`` on a class used to answer ``try_instead=find_references``: following it
    re-ran the same qname and returned a byte-identical payload, hint included, forever.
    """
    seed_file(
        store,
        "a.php",
        [
            node("Class", "RegionManager", "\\Src\\System\\RegionManager", "a.php"),
            node("Method", "load", "\\Src\\System\\RegionManager::load", "a.php"),
        ],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "b.php",
        [],
        [edge("REFERENCES", "\\Other", "RegionManager", "b.php", tier="BARE_NAME")],
        root=tmp_path,
    )
    payload = find_references.create(db_config(tmp_path))(
        "\\Src\\System\\RegionManager", detail_level="minimal"
    )
    assert payload["try_instead"] != find_references.NAME
    # The route must make progress: search_symbol lists the method qnames the hint asks for.
    assert payload["try_instead"] == nav_result.TRY_INSTEAD_SEARCH_SYMBOL
    hits = search_symbol.create(db_config(tmp_path))("RegionManager", detail_level="minimal")
    assert any("::load" in str(hit["qname"]) for hit in hits["results"])
