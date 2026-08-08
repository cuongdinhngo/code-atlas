"""Task 054 Part B: find_callers must not claim no_matches when bare-name resolve truncated."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.resolver import resolve_edges
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from code_atlas.tools.nav_result import REASON_BARE_NAME_TRUNCATED, REASON_NO_MATCHES
from tests.test_nav_tools import db_config, edge, node, seed_file


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def _plant_truncated_bare_calls(store: GraphStore, root: Path) -> None:
    """Three ``put`` Methods; max_candidates=2 keeps A/B — ``\\C::put`` is outside the cap.

    Same shape as ``test_many_method_name_matches_respect_max_candidates``; the call site is
    HEURISTIC bare ``put``, so winners receive inbound edges and the outsider does not.
    """
    seed_file(
        store,
        "a.x",
        [
            node("Method", "save", "\\A::save", "a.x"),
            node("Method", "put", "\\A::put", "a.x"),
            node("Method", "put", "\\B::put", "a.x"),
            node("Method", "put", "\\C::put", "a.x"),
        ],
        [edge("CALLS", "\\A::save", "put", "a.x", tier="HEURISTIC")],
        root=root,
    )
    resolve_edges(store, max_candidates=2)


def test_the_fixture_really_drops_the_outsider(store: GraphStore, tmp_path: Path) -> None:
    """Guard cannot pass vacuously — outsider exists and is not among linked targets."""
    _plant_truncated_bare_calls(store, tmp_path)
    assert store.nodes_by_qualified_name("\\C::put", kind="Method", limit=1)
    linked = store.edges_by_source("\\A::save", kinds=("CALLS",), limit=10)
    targets = {str(row["target_qname"]) for row in linked}
    assert targets == {"\\A::put", "\\B::put"}
    assert "\\C::put" not in targets
    assert store.count_edges_by_target("\\C::put", kinds=("CALLS",)) == 0


def test_find_callers_reports_truncated_bare_name_not_no_matches(
    store: GraphStore, tmp_path: Path
) -> None:
    _plant_truncated_bare_calls(store, tmp_path)
    result = find_callers.create(db_config(tmp_path))("\\C::put", detail_level="minimal")
    assert result["results"] == []
    assert result["total_count"] == 0
    assert result["reason"] == REASON_BARE_NAME_TRUNCATED
    assert result["reason"] != REASON_NO_MATCHES
    assert result["unresolved_bare_calls"] == 1


def test_truncated_bare_count_is_deterministic(store: GraphStore, tmp_path: Path) -> None:
    _plant_truncated_bare_calls(store, tmp_path)
    tool = find_callers.create(db_config(tmp_path))
    first = tool("\\C::put", detail_level="minimal")
    second = tool("\\C::put", detail_level="minimal")
    assert first["unresolved_bare_calls"] == second["unresolved_bare_calls"] == 1
    assert first["reason"] == second["reason"] == REASON_BARE_NAME_TRUNCATED


def test_winner_still_reports_callers_and_may_omit_unresolved(
    store: GraphStore, tmp_path: Path
) -> None:
    _plant_truncated_bare_calls(store, tmp_path)
    result = find_callers.create(db_config(tmp_path))("\\A::put", detail_level="minimal")
    assert result["total_count"] >= 1
    assert result["results"]
    assert result["reason"] == "ok"
    # Every bare ``put`` site links to this winner, so the honesty field stays off.
    assert "unresolved_bare_calls" not in result


def test_unknown_qname_does_not_claim_bare_name_truncation(
    store: GraphStore, tmp_path: Path
) -> None:
    """A typo must stay no_such_symbol — not a graph-wide same-name hand-off (R5.3)."""
    from code_atlas.tools.nav_result import REASON_NO_SUCH_SYMBOL

    _plant_truncated_bare_calls(store, tmp_path)
    result = find_callers.create(db_config(tmp_path))("\\Typo::put", detail_level="minimal")
    assert result["reason"] == REASON_NO_SUCH_SYMBOL
    assert "unresolved_bare_calls" not in result
