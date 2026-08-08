"""Task 057: page large nav/search answers with limit + offset."""

from __future__ import annotations

import json
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


def test_default_args_match_explicit_defaults(store: GraphStore, tmp_path: Path) -> None:
    """Omitting limit/offset matches today's common case (offset=0, limit=max_results)."""
    _plant_impls(store, tmp_path, n=3)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=2)
    tool = find_implementations.create(config)
    omitted = tool("\\Base", detail_level="minimal")
    explicit = tool("\\Base", detail_level="minimal", limit=None, offset=0)
    assert json.dumps(omitted, sort_keys=True) == json.dumps(explicit, sort_keys=True)
    assert omitted["truncated"] is True
    assert len(omitted["results"]) == 2


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
