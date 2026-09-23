"""Task 315: path_prefix narrows search_symbol / find_references; fail-loud + path_excluded."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from code_atlas.main import build_server
from code_atlas.store import GraphStore
from code_atlas.tools import find_references, search_symbol
from code_atlas.tools.nav_result import REASON_PATH_EXCLUDED
from code_atlas.tools.search_symbol import NAME as SEARCH
from tests.test_mcp_server import raises_through_the_client
from tests.test_nav_tools import db_config, edge, node, seed_file
from tests.test_search_read_outline import db_config as search_db_config


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def _seed_common(store: GraphStore, tmp_path: Path) -> None:
    seed_file(
        store,
        "src/app.x",
        [node("Class", "Database", "\\App\\Database", "src/app.x")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "tests/test_app.x",
        [node("Class", "Database", "\\Test\\Database", "tests/test_app.x")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "src/consumer.x",
        [node("Function", "useIt", "\\App\\useIt", "src/consumer.x")],
        [
            edge(
                "REFERENCES",
                "\\App\\useIt",
                "\\App\\Database",
                "src/consumer.x",
                target_qname="\\App\\Database",
            )
        ],
        root=tmp_path,
    )
    seed_file(
        store,
        "tests/consumer_test.x",
        [node("Function", "testUse", "\\Test\\testUse", "tests/consumer_test.x")],
        [
            edge(
                "REFERENCES",
                "\\Test\\testUse",
                "\\App\\Database",
                "tests/consumer_test.x",
                target_qname="\\App\\Database",
            )
        ],
        root=tmp_path,
    )


def test_search_symbol_path_prefix_keeps_only_under_prefix(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC1 — filtered population only; tier order unchanged within the set."""
    _seed_common(store, tmp_path)
    config = replace(db_config(tmp_path), root=tmp_path)
    tool = search_symbol.create(config)
    result = tool("Database", path_prefix="src/", detail_level="minimal")
    assert result["reason"] == "ok"
    files = [hit["file"] for hit in result["results"]]
    assert files == ["src/app.x"]
    assert result["total_count"] == 1
    assert all(str(f).startswith("src/") for f in files)


def test_path_prefix_exclusion_is_not_absence(store: GraphStore, tmp_path: Path) -> None:
    """AC2 — exact hit outside the prefix answers path_excluded, not no_matches."""
    _seed_common(store, tmp_path)
    config = replace(db_config(tmp_path), root=tmp_path)
    tool = search_symbol.create(config)
    result = tool("Database", path_prefix="vendor/", detail_level="minimal")
    assert result["reason"] == REASON_PATH_EXCLUDED
    assert result["results"] == []
    assert result["total_count"] == 0
    assert result["path_excluded"] == ["src/app.x", "tests/test_app.x"]


def test_find_references_path_prefix_scopes_consumers(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC3 — consumer enumeration under subtree; truncated/total honest for filtered count."""
    _seed_common(store, tmp_path)
    config = replace(db_config(tmp_path), root=tmp_path)
    tool = find_references.create(config)
    result = tool("\\App\\Database", path_prefix="src/", detail_level="minimal")
    assert result["reason"] == "ok"
    files = [hit["file"] for hit in result["results"]]
    assert files == ["src/consumer.x"]
    assert result["total_count"] == 1
    assert result.get("truncated") is not True


def test_find_references_truncated_subtrees_honour_path_prefix(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC3 — truncated filtered page must not advertise out-of-prefix subtrees (315 review)."""
    seed_file(
        store,
        "src/a.x",
        [node("Class", "Target", "\\App\\Target", "src/a.x")],
        [],
        root=tmp_path,
    )
    for i, path in enumerate(("src/c1.x", "src/c2.x", "src/c3.x", "tests/t1.x", "tests/t2.x")):
        seed_file(
            store,
            path,
            [node("Function", f"c{i}", f"\\X\\c{i}", path)],
            [
                edge(
                    "REFERENCES",
                    f"\\X\\c{i}",
                    "\\App\\Target",
                    path,
                    target_qname="\\App\\Target",
                )
            ],
            root=tmp_path,
        )
    config = replace(db_config(tmp_path), root=tmp_path, page_limit=2)
    tool = find_references.create(config)
    result = tool("\\App\\Target", path_prefix="src/", detail_level="minimal")
    assert result["total_count"] == 3
    assert result["truncated"] is True
    files = [hit["file"] for hit in result["results"]]
    assert all(str(f).startswith("src/") for f in files)
    # Single remaining top-level segment → field omitted (067); must not advertise tests/.
    assert "tests" not in result.get("result_subtrees", {})
    assert sum(result.get("result_subtrees", {}).values()) <= result["total_count"]


def test_path_prefix_underscore_is_literal_not_wildcard(
    store: GraphStore, tmp_path: Path
) -> None:
    """315 review — a '_' in the prefix must match itself, not any char (LIKE ESCAPE)."""
    seed_file(
        store,
        "src/a_b/hit.x",
        [node("Class", "Widget", "\\App\\A_B\\Widget", "src/a_b/hit.x")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "src/axb/miss.x",
        [node("Class", "Widget", "\\App\\AxB\\Widget", "src/axb/miss.x")],
        [],
        root=tmp_path,
    )
    config = replace(db_config(tmp_path), root=tmp_path)
    tool = search_symbol.create(config)
    result = tool("Widget", path_prefix="src/a_b/", detail_level="minimal")
    assert result["reason"] == "ok"
    assert [hit["file"] for hit in result["results"]] == ["src/a_b/hit.x"]
    assert result["total_count"] == 1


def test_invalid_path_prefix_fails_loud(tmp_path: Path) -> None:
    """AC4 — empty / absolute / backslash / traversal fail loud (056 style)."""
    tool = search_symbol.create(search_db_config(tmp_path))
    with pytest.raises(ValueError, match="non-empty"):
        tool("User", path_prefix="", detail_level="minimal")
    with pytest.raises(ValueError, match="index-root-relative"):
        tool("User", path_prefix="/abs/src", detail_level="minimal")
    with pytest.raises(ValueError, match="POSIX"):
        tool("User", path_prefix="src\\app", detail_level="minimal")
    with pytest.raises(ValueError, match=r"'\.\.'"):
        tool("User", path_prefix="src/../etc", detail_level="minimal")


def test_path_prefix_published_on_search_and_references_schema(tmp_path: Path) -> None:
    """AC4 — param appears in the published MCP schema for both tools."""

    async def props() -> dict[str, Any]:
        async with Client(build_server(search_db_config(tmp_path))) as client:
            tools = {tool.name: tool.inputSchema for tool in await client.list_tools()}
            return {
                "search": tools["search_symbol"]["properties"],
                "refs": tools["find_references"]["properties"],
            }

    schemas = asyncio.run(props())
    assert "path_prefix" in schemas["search"]
    assert "path_prefix" in schemas["refs"]


def test_invalid_path_prefix_fails_loud_through_mcp(tmp_path: Path) -> None:
    message = raises_through_the_client(
        build_server(search_db_config(tmp_path)),
        SEARCH,
        {"query": "User", "path_prefix": "/abs"},
    )
    assert "index-root-relative" in message
    assert "no_matches" not in message
