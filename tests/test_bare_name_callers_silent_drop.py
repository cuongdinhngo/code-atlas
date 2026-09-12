"""Task 054 Part B: find_callers must not claim no_matches when bare-name resolve truncated."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.resolver import resolve_edges
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from code_atlas.tools.nav_result import (
    REASON_BARE_NAME_TRUNCATED,
    REASON_NO_MATCHES,
    REASON_PROXIMITY_CANDIDATES,
)
from tests.test_nav_tools import db_config, edge, node, seed_file


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def _plant_truncated_bare_calls(store: GraphStore, root: Path) -> None:
    """Three ``put`` Methods; multi-match stays one unresolved site (258).

    Part B still needs an outsider with zero *linked* inbound edges while a bare ``put``
    CALL site exists — that is now the unresolved row, not a capped sibling list.
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


def _tool(tmp_path: Path, *, max_results: int = 2):
    """Query-time cap for paging; no longer governs what the build stores (258)."""
    return find_callers.create(replace(db_config(tmp_path), max_results=max_results))


def test_the_fixture_really_leaves_multi_match_unlinked(
    store: GraphStore, tmp_path: Path
) -> None:
    """Guard: multi-match bare CALLS stay unresolved — no cartesian inbound edges."""
    _plant_truncated_bare_calls(store, tmp_path)
    assert store.nodes_by_qualified_name("\\C::put", kind="Method", limit=1)
    linked = store.edges_by_source("\\A::save", kinds=("CALLS",), limit=10)
    assert len(linked) == 1
    assert linked[0]["target_qname"] is None
    assert store.count_edges_by_target("\\C::put", kinds=("CALLS",)) == 0
    assert store.count_edges_by_target("\\A::put", kinds=("CALLS",)) == 0


def test_find_callers_reports_truncated_bare_name_not_no_matches(
    store: GraphStore, tmp_path: Path
) -> None:
    """When proximity cannot attach the site, truncation honesty still fires for outsiders.

    Force a subject file with no shared subtree vs the call site so query-time expansion
    does not recover the caller (the 054 empty-page case).
    """
    seed_file(
        store,
        "legacy/a.x",
        [
            node("Method", "save", "\\A::save", "legacy/a.x"),
            node("Method", "put", "\\A::put", "legacy/a.x"),
            node("Method", "put", "\\B::put", "legacy/a.x"),
        ],
        [edge("CALLS", "\\A::save", "put", "legacy/a.x", tier="HEURISTIC")],
        root=tmp_path,
    )
    seed_file(
        store,
        "other/c.x",
        [node("Method", "put", "\\C::put", "other/c.x")],
        [],
        root=tmp_path,
    )
    resolve_edges(store, max_candidates=2)
    result = _tool(tmp_path)("\\C::put", detail_level="minimal")
    assert result["results"] == []
    assert result["total_count"] == 0
    assert result["reason"] == REASON_BARE_NAME_TRUNCATED
    assert result["reason"] != REASON_NO_MATCHES
    assert result["unresolved_bare_calls"] == 1


def test_truncated_bare_count_is_deterministic(store: GraphStore, tmp_path: Path) -> None:
    seed_file(
        store,
        "legacy/a.x",
        [
            node("Method", "save", "\\A::save", "legacy/a.x"),
            node("Method", "put", "\\A::put", "legacy/a.x"),
            node("Method", "put", "\\B::put", "legacy/a.x"),
        ],
        [edge("CALLS", "\\A::save", "put", "legacy/a.x", tier="HEURISTIC")],
        root=tmp_path,
    )
    seed_file(
        store,
        "other/c.x",
        [node("Method", "put", "\\C::put", "other/c.x")],
        [],
        root=tmp_path,
    )
    resolve_edges(store, max_candidates=2)
    tool = _tool(tmp_path)
    first = tool("\\C::put", detail_level="minimal")
    second = tool("\\C::put", detail_level="minimal")
    assert first["unresolved_bare_calls"] == second["unresolved_bare_calls"] == 1
    assert first["reason"] == second["reason"] == REASON_BARE_NAME_TRUNCATED


def test_same_subtree_recovers_unresolved_site_as_caller(
    store: GraphStore, tmp_path: Path
) -> None:
    """258 query-time path: a same-subtree unresolved site is a HEURISTIC caller."""
    _plant_truncated_bare_calls(store, tmp_path)
    result = _tool(tmp_path, max_results=50)("\\A::put", detail_level="minimal")
    assert result["total_count"] >= 1
    assert result["results"]
    # 258 rows are candidates, not measured callers — the label is the point (R5.6).
    assert result["reason"] == REASON_PROXIMITY_CANDIDATES
    assert str(result["results"][0]["qname"]) == "\\A::save"


def test_unknown_qname_does_not_claim_bare_name_truncation(
    store: GraphStore, tmp_path: Path
) -> None:
    """A typo must stay no_such_symbol — not a graph-wide same-name hand-off (R5.3)."""
    from code_atlas.tools.nav_result import REASON_NO_SUCH_SYMBOL

    _plant_truncated_bare_calls(store, tmp_path)
    result = _tool(tmp_path)("\\Typo::put", detail_level="minimal")
    assert result["reason"] == REASON_NO_SUCH_SYMBOL
    assert "unresolved_bare_calls" not in result


def test_count_bare_calls_ignores_non_heuristic_tiers(store: GraphStore, tmp_path: Path) -> None:
    """Only HEURISTIC bare CALLS count — RESOLVED/DYNAMIC unlinked rows are not truncation."""
    seed_file(
        store,
        "a.x",
        [
            node("Method", "save", "\\A::save", "a.x"),
            node("Method", "put", "\\C::put", "a.x"),
        ],
        [
            edge("CALLS", "\\A::save", "put", "a.x", tier="RESOLVED", target_qname=None),
            edge("CALLS", "\\A::save", "put", "a.x", tier="DYNAMIC", target_qname=None),
        ],
        root=tmp_path,
    )
    assert store.count_bare_calls_not_targeting("\\C::put", bare_name="put") == 0


def test_method_count_at_or_below_cap_skips_expensive_scan(
    store: GraphStore, tmp_path: Path
) -> None:
    """Precondition: Method decls ≤ max_results ⇒ no honesty field (even with orphan HEURISTIC)."""
    seed_file(
        store,
        "a.x",
        [
            node("Method", "save", "\\A::save", "a.x"),
            node("Method", "put", "\\A::put", "a.x"),
            node("Method", "put", "\\C::put", "a.x"),
        ],
        [
            # Unlinked HEURISTIC bare call — 258 query-time proximity may still surface it.
            edge("CALLS", "\\A::save", "put", "a.x", tier="HEURISTIC", target_qname=None),
        ],
        root=tmp_path,
    )
    result = _tool(tmp_path, max_results=2)("\\C::put", detail_level="minimal")
    assert result["reason"] != REASON_BARE_NAME_TRUNCATED
    assert "unresolved_bare_calls" not in result


def test_function_subject_does_not_claim_bare_name_truncation(
    store: GraphStore, tmp_path: Path
) -> None:
    """Function ``\\App\\put`` must not collide with bare Method CALLS named ``put``."""
    seed_file(
        store,
        "a.x",
        [
            node("Method", "save", "\\A::save", "a.x"),
            node("Method", "put", "\\A::put", "a.x"),
            node("Method", "put", "\\B::put", "a.x"),
            node("Method", "put", "\\C::put", "a.x"),
            node("Function", "put", "\\App\\put", "a.x"),
        ],
        [edge("CALLS", "\\A::save", "put", "a.x", tier="HEURISTIC")],
        root=tmp_path,
    )
    resolve_edges(store, max_candidates=2)
    result = _tool(tmp_path)("\\App\\put", detail_level="minimal")
    # Function path may be no_matches or 214's unlinked-CALLS arm — never bare_name_truncated.
    assert result["reason"] != REASON_BARE_NAME_TRUNCATED
    assert "unresolved_bare_calls" not in result


def test_class_subject_does_not_claim_bare_name_truncation(
    store: GraphStore, tmp_path: Path
) -> None:
    seed_file(
        store,
        "a.x",
        [
            node("Class", "put", "\\Put", "a.x"),
            node("Method", "save", "\\A::save", "a.x"),
            node("Method", "put", "\\A::put", "a.x"),
            node("Method", "put", "\\B::put", "a.x"),
            node("Method", "put", "\\C::put", "a.x"),
        ],
        [edge("CALLS", "\\A::save", "put", "a.x", tier="HEURISTIC")],
        root=tmp_path,
    )
    resolve_edges(store, max_candidates=2)
    result = _tool(tmp_path)("\\Put", detail_level="minimal")
    assert result["reason"] == REASON_NO_MATCHES
    assert "unresolved_bare_calls" not in result


def test_edges_raw_index_exists(store: GraphStore) -> None:
    row = store._conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = 'idx_edges_raw'"
    ).fetchone()
    assert row is not None
