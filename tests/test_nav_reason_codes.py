"""Task 033: reason codes + total_count on find_* / search (empty ≠ unknown)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_implementations, find_references, search_symbol
from code_atlas.tools.nav_result import (
    NAV_REASONS,
    REASON_BARE_NAME_TRUNCATED,
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_INDEX_STALE,
    REASON_NAME_NOT_QUALIFIED,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_NOT_INDEXED,
    REASON_OK,
    REASON_RELATIONSHIP_NOT_MODELLED,
    REASON_RULE_MATCHED_NO_FILES,
    REASON_SUBJECT_AMBIGUOUS,
)
from tests.test_nav_tools import db_config, edge, node, seed_file


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def test_find_callers_distinguishes_no_such_symbol_from_no_matches(
    tmp_path: Path, store: GraphStore
) -> None:
    seed_file(
        store,
        "a.x",
        [node("Function", "lonely", "\\lonely", "a.x")],
        [],
        root=tmp_path,
    )
    tool = find_callers.create(db_config(tmp_path))
    missing = tool("\\missing", detail_level="minimal")
    assert missing["reason"] == REASON_NO_SUCH_SYMBOL
    assert missing["results"] == []
    assert missing["total_count"] == 0
    assert missing["truncated"] is False

    empty = tool("\\lonely", detail_level="minimal")
    assert empty["reason"] == REASON_NO_MATCHES
    assert empty["results"] == []
    assert empty["total_count"] == 0


def test_unbuilt_index_returns_not_indexed(tmp_path: Path) -> None:
    config = load_config(tmp_path, {})
    assert not config.db_path.is_file()
    for factory in (
        find_callers.create,
        find_references.create,
        find_implementations.create,
    ):
        result = factory(config)("\\X", detail_level="minimal")
        assert result["reason"] == REASON_NOT_INDEXED
        assert result["indexed"] is False
        assert result["total_count"] == 0
        assert not config.db_path.is_file()
    search = search_symbol.create(config)("Anything", detail_level="minimal")
    assert search["reason"] == REASON_NOT_INDEXED
    assert search["indexed"] is False
    assert search["total_count"] == 0
    assert not config.db_path.is_file()


def test_truncation_sets_total_count_above_limit(tmp_path: Path, store: GraphStore) -> None:
    nodes = [node("Function", f"f{i}", f"\\f{i}", "a.x") for i in range(5)]
    nodes.append(node("Function", "t", "\\t", "a.x"))
    edges = [edge("CALLS", f"\\f{i}", "\\t", "a.x", target_qname="\\t") for i in range(5)]
    seed_file(store, "a.x", nodes, edges, root=tmp_path)
    config = replace(db_config(tmp_path), max_results=2)
    result = find_callers.create(config)("\\t", detail_level="minimal")
    assert result["reason"] == REASON_OK
    assert len(result["results"]) == 2
    assert result["truncated"] is True
    assert result["total_count"] == 5
    assert result["total_count"] > 2


def test_full_result_total_count_equals_returned_length(
    tmp_path: Path, store: GraphStore
) -> None:
    seed_file(
        store,
        "a.x",
        [
            node("Function", "a", "\\a", "a.x"),
            node("Function", "t", "\\t", "a.x"),
        ],
        [edge("CALLS", "\\a", "\\t", "a.x", target_qname="\\t")],
        root=tmp_path,
    )
    result = find_callers.create(db_config(tmp_path))("\\t", detail_level="minimal")
    assert result["reason"] == REASON_OK
    assert result["truncated"] is False
    assert result["total_count"] == len(result["results"]) == 1


def test_refs_and_impls_use_same_reason_vocabulary(
    tmp_path: Path, store: GraphStore
) -> None:
    seed_file(
        store,
        "a.x",
        [node("Class", "Base", "\\Base", "a.x")],
        [],
        root=tmp_path,
    )
    config = db_config(tmp_path)
    for factory in (find_references.create, find_implementations.create):
        missing = factory(config)("\\Nope", detail_level="minimal")
        assert missing["reason"] == REASON_NO_SUCH_SYMBOL
        empty = factory(config)("\\Base", detail_level="minimal")
        assert empty["reason"] == REASON_NO_MATCHES
        assert empty["total_count"] == 0


def test_search_symbol_reasons_and_total_count(tmp_path: Path, store: GraphStore) -> None:
    nodes = [
        node("Function", f"Alpha{i}", f"\\Alpha{i}", "a.x") for i in range(4)
    ]
    seed_file(store, "a.x", nodes, [], root=tmp_path)
    config = replace(db_config(tmp_path), max_results=2)
    tool = search_symbol.create(config)
    hits = tool("Alpha", detail_level="minimal")
    assert hits["reason"] == REASON_OK
    assert hits["truncated"] is True
    assert hits["total_count"] == 4
    assert hits["total_count"] > 2
    assert len(hits["results"]) == 2

    none = tool("ZzzNotHere", detail_level="minimal")
    assert none["reason"] == REASON_NO_MATCHES
    assert none["results"] == []
    assert none["total_count"] == 0


def test_reason_vocabulary_includes_index_stale_unused() -> None:
    assert REASON_INDEX_STALE in NAV_REASONS
    assert NAV_REASONS == (
        REASON_OK,
        REASON_NO_MATCHES,
        REASON_NO_SUCH_SYMBOL,
        REASON_NOT_INDEXED,
        REASON_INDEX_STALE,
        REASON_BARE_NAME_TRUNCATED,
        REASON_RELATIONSHIP_NOT_MODELLED,
        REASON_CAPABILITY_NOT_CONFIGURED,
        REASON_NAME_NOT_QUALIFIED,
        REASON_SUBJECT_AMBIGUOUS,
        REASON_RULE_MATCHED_NO_FILES,
    )


def test_edges_to_unindexed_target_are_not_swallowed_as_no_such_symbol(
    tmp_path: Path, store: GraphStore
) -> None:
    """Vendor/framework targets often have edges but no node row (default ignore / 039)."""
    seed_file(
        store,
        "a.php",
        [node("Class", "MyController", "\\App\\MyController", "a.php")],
        [
            edge(
                "EXTENDS",
                "\\App\\MyController",
                "\\Vendor\\BaseController",
                "a.php",
                target_qname="\\Vendor\\BaseController",
            ),
            edge(
                "CALLS",
                "\\App\\MyController",
                "\\Vendor\\Log::info",
                "a.php",
                target_qname="\\Vendor\\Log::info",
            ),
        ],
        root=tmp_path,
    )
    config = db_config(tmp_path)
    refs = find_references.create(config)("\\Vendor\\BaseController", detail_level="minimal")
    assert refs["reason"] == REASON_OK
    assert refs["total_count"] == 1
    assert refs["results"][0]["qname"] == "\\App\\MyController"

    impls = find_implementations.create(config)(
        "\\Vendor\\BaseController", detail_level="minimal"
    )
    assert impls["reason"] == REASON_OK
    assert impls["total_count"] == 1

    callers = find_callers.create(config)("\\Vendor\\Log::info", detail_level="minimal")
    assert callers["reason"] == REASON_OK
    assert callers["total_count"] == 1
    assert callers["results"][0]["qname"] == "\\App\\MyController"
