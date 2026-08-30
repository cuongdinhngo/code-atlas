"""Task 057: page large nav/search answers with limit + offset."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_implementations, find_references, search_symbol
from tests.test_nav_tools import db_config, edge, node, seed_file


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def _plant_impls(store: GraphStore, root: Path, *, n: int) -> None:
    """``n`` EXTENDS edges into ``\\Base``, ordered by source qname (then id)."""
    nodes = [node("Class", "Base", "\\Base", "a.x")]
    edges = []
    for i in range(n):
        qname = f"\\C{i:02d}"
        nodes.append(node("Class", f"C{i:02d}", qname, "a.x"))
        edges.append(
            edge("EXTENDS", qname, "\\Base", "a.x", target_qname="\\Base", tier="RESOLVED")
        )
    seed_file(store, "a.x", nodes, edges, root=root)


def test_paged_walk_visits_each_row_once_stable(store: GraphStore, tmp_path: Path) -> None:
    """Proving test: walk every page; two runs identical; no skip/repeat (R4.2)."""
    _plant_impls(store, tmp_path, n=5)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=2)
    tool = find_implementations.create(config)

    def walk() -> list[str]:
        seen: list[str] = []
        offset = 0
        while True:
            page = tool("\\Base", detail_level="minimal", limit=2, offset=offset)
            assert page["total_count"] == 5
            for hit in page["results"]:
                seen.append(str(hit["qname"]))
            if not page["truncated"]:
                break
            offset += len(page["results"])
            assert len(page["results"]) > 0
        return seen

    first = walk()
    second = walk()
    assert first == second
    assert first == [f"\\C{i:02d}" for i in range(5)]
    assert len(set(first)) == 5


def test_last_page_is_not_truncated(store: GraphStore, tmp_path: Path) -> None:
    _plant_impls(store, tmp_path, n=3)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=2)
    tool = find_implementations.create(config)
    first = tool("\\Base", detail_level="minimal", limit=2, offset=0)
    last = tool("\\Base", detail_level="minimal", limit=2, offset=2)
    assert first["truncated"] is True
    assert last["truncated"] is False
    assert len(last["results"]) == 1


def test_find_implementations_accepts_limit(store: GraphStore, tmp_path: Path) -> None:
    _plant_impls(store, tmp_path, n=3)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=50)
    result = find_implementations.create(config)(
        "\\Base", detail_level="minimal", limit=1
    )
    assert len(result["results"]) == 1
    assert result["total_count"] == 3
    assert result["truncated"] is True


def test_default_args_match_pre_pagination_shape(store: GraphStore, tmp_path: Path) -> None:
    """AC5: default call = first max_results page in store order (pre-057 common case)."""
    from code_atlas.contract import IMPL_KINDS

    _plant_impls(store, tmp_path, n=3)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=2)
    expected_sources = [
        str(row["source_qname"])
        for row in store.edges_by_target("\\Base", kinds=IMPL_KINDS, limit=2, offset=0)
    ]
    got = find_implementations.create(config)("\\Base", detail_level="minimal")
    assert set(got) == {
        "indexed",
        "qname",
        "results",
        "truncated",
        "reason",
        "total_count",
        "index_root",
        "server_version",
        "server_build",
        # 170: the divergence verdict rides unconditionally, so silence is not a clean answer.
        "server_stale_process",
        # 192: this fixture wires no adapter, so every answer — results or not — names the gap.
        "unconfigured_adapters",
    }
    assert got["qname"] == "\\Base"
    assert got["indexed"] is True
    assert got["truncated"] is True
    assert got["total_count"] == 3
    assert [hit["qname"] for hit in got["results"]] == expected_sources
    assert len(got["results"]) == 2


def test_find_callers_depth1_pages(store: GraphStore, tmp_path: Path) -> None:
    nodes = [
        node("Method", "put", "\\T::put", "a.x"),
        node("Method", "a", "\\A::a", "a.x"),
        node("Method", "b", "\\B::b", "a.x"),
        node("Method", "c", "\\C::c", "a.x"),
    ]
    edges = [
        edge(
            "CALLS", "\\A::a", "\\T::put", "a.x",
            target_qname="\\T::put", tier="RESOLVED", line=1,
        ),
        edge(
            "CALLS", "\\B::b", "\\T::put", "a.x",
            target_qname="\\T::put", tier="RESOLVED", line=2,
        ),
        edge(
            "CALLS", "\\C::c", "\\T::put", "a.x",
            target_qname="\\T::put", tier="RESOLVED", line=3,
        ),
    ]
    seed_file(store, "a.x", nodes, edges, root=tmp_path)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=2)
    tool = find_callers.create(config)
    page0 = tool("\\T::put", detail_level="minimal", limit=2, offset=0)
    page1 = tool("\\T::put", detail_level="minimal", limit=2, offset=2)
    assert page0["total_count"] == 3
    assert page0["truncated"] is True
    assert page1["truncated"] is False
    ids = {hit["qname"] for hit in page0["results"]} | {hit["qname"] for hit in page1["results"]}
    assert len(ids) == 3


def test_search_symbol_offset_pages(store: GraphStore, tmp_path: Path) -> None:
    nodes = [node("Class", f"Hit{i}", f"\\Hit{i}", "a.x") for i in range(4)]
    seed_file(store, "a.x", nodes, [], root=tmp_path)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=2)
    tool = search_symbol.create(config)
    page0 = tool("Hit", detail_level="minimal", limit=2, offset=0)
    page1 = tool("Hit", detail_level="minimal", limit=2, offset=2)
    assert page0["total_count"] == 4
    assert page0["truncated"] is True
    assert page1["truncated"] is False
    qnames = [hit["qname"] for hit in page0["results"]] + [
        hit["qname"] for hit in page1["results"]
    ]
    assert sorted(qnames) == [f"\\Hit{i}" for i in range(4)]
    assert len(set(qnames)) == 4


def test_find_references_offset(store: GraphStore, tmp_path: Path) -> None:
    nodes = [
        node("Method", "put", "\\T::put", "a.x"),
        node("Method", "a", "\\A::a", "a.x"),
        node("Method", "b", "\\B::b", "a.x"),
    ]
    edges = [
        edge(
            "CALLS", "\\A::a", "\\T::put", "a.x",
            target_qname="\\T::put", tier="RESOLVED", line=1,
        ),
        edge(
            "CALLS", "\\B::b", "\\T::put", "a.x",
            target_qname="\\T::put", tier="RESOLVED", line=2,
        ),
    ]
    seed_file(store, "a.x", nodes, edges, root=tmp_path)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=1)
    tool = find_references.create(config)
    first = tool("\\T::put", detail_level="minimal", limit=1, offset=0)
    second = tool("\\T::put", detail_level="minimal", limit=1, offset=1)
    assert first["truncated"] is True and second["truncated"] is False
    assert first["total_count"] == 2


def test_find_callers_depth2_offset_pages_bfs_stream(
    store: GraphStore, tmp_path: Path
) -> None:
    """Depth>1 applies offset to the BFS hit stream (review finding 3)."""
    nodes = [
        node("Method", "m", "\\A::m", "a.x"),
        node("Method", "b", "\\B::b", "a.x"),
        node("Method", "c", "\\C::c", "a.x"),
        node("Method", "d", "\\D::d", "a.x"),
    ]
    # D→B→A and C→A: depth=2 from A sees D (via B) and C (direct), plus B.
    edges = [
        edge(
            "CALLS", "\\B::b", "\\A::m", "a.x",
            target_qname="\\A::m", tier="RESOLVED", line=1,
        ),
        edge(
            "CALLS", "\\C::c", "\\A::m", "a.x",
            target_qname="\\A::m", tier="RESOLVED", line=2,
        ),
        edge(
            "CALLS", "\\D::d", "\\B::b", "a.x",
            target_qname="\\B::b", tier="RESOLVED", line=3,
        ),
    ]
    seed_file(store, "a.x", nodes, edges, root=tmp_path)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=10)
    tool = find_callers.create(config)
    page0 = tool("\\A::m", depth=2, detail_level="minimal", limit=1, offset=0)
    page1 = tool("\\A::m", depth=2, detail_level="minimal", limit=1, offset=1)
    assert page0["results"] and page1["results"]
    assert page0["results"][0]["qname"] != page1["results"][0]["qname"]
    assert page0["truncated"] is True


def test_search_offset_past_end_is_ok_not_no_matches(
    store: GraphStore, tmp_path: Path
) -> None:
    """Empty page with total_count > 0 must not read as proof of absence (PR #67)."""
    nodes = [node("Class", f"Hit{i}", f"\\Hit{i}", "a.x") for i in range(4)]
    seed_file(store, "a.x", nodes, [], root=tmp_path)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=2)
    result = search_symbol.create(config)(
        "Hit", detail_level="minimal", limit=2, offset=99
    )
    assert result["results"] == []
    assert result["total_count"] == 4
    assert result["truncated"] is False
    assert result["reason"] == "ok"
    assert result["reason"] != "no_matches"


@pytest.mark.parametrize(
    "factory",
    [
        find_implementations.create,
        find_references.create,
        search_symbol.create,
        find_callers.create,
    ],
    ids=["implementations", "references", "search", "callers"],
)
def test_bad_offset_fails_loud_when_unindexed(
    tmp_path: Path, factory: object
) -> None:
    """Caller errors must not hide behind ``not_indexed`` (PR #67 / #66 shape)."""
    config = replace(db_config(tmp_path), root=tmp_path)
    assert not config.db_path.is_file()
    tool = factory(config)  # type: ignore[operator]
    with pytest.raises(ValueError, match="offset"):
        if factory is search_symbol.create:
            tool("User", offset=-1, detail_level="minimal")
        else:
            tool("\\X", offset=-1, detail_level="minimal")
