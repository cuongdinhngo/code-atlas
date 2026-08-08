"""Task 056: unknown search_symbol kind fails loud; schema publishes NODE_KINDS."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from code_atlas.contract import NODE_KINDS
from code_atlas.main import build_server
from code_atlas.store import GraphStore
from code_atlas.tools import search_symbol
from code_atlas.tools.search_symbol import NAME as SEARCH
from tests.test_mcp_server import raises_through_the_client
from tests.test_nav_tools import db_config, node, seed_file
from tests.test_search_read_outline import db_config as search_db_config


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def _kind_enum(kind_prop: Mapping[str, Any]) -> list[str]:
    """``NodeKind | None`` publishes enum on the string branch of ``anyOf``, not as a sibling."""
    raw = kind_prop.get("enum")
    if isinstance(raw, list):
        return [str(item) for item in raw]
    for branch in kind_prop.get("anyOf", []):
        if isinstance(branch, dict) and isinstance(branch.get("enum"), list):
            return [str(item) for item in branch["enum"]]
    raise AssertionError(f"no enum in kind schema: {kind_prop}")


def test_unknown_kind_raises_naming_accepted_values(tmp_path: Path) -> None:
    """Proving test: ``kind='class'`` must not look like ``no_matches``."""
    tool = search_symbol.create(search_db_config(tmp_path))
    with pytest.raises(ValueError, match="unknown kind 'class'") as caught:
        tool("User", kind="class", detail_level="minimal")  # type: ignore[arg-type]
    message = str(caught.value)
    for accepted in NODE_KINDS:
        assert accepted in message, accepted


def test_capitalised_kind_class_is_unchanged(store: GraphStore, tmp_path: Path) -> None:
    seed_file(
        store,
        "a.x",
        [node("Class", "User", "\\App\\User", "a.x")],
        [],
        root=tmp_path,
    )
    config = replace(db_config(tmp_path), root=tmp_path)
    result = search_symbol.create(config)("User", kind="Class", detail_level="minimal")
    assert result["reason"] == "ok"
    assert "\\App\\User" in [hit["qname"] for hit in result["results"]]


def test_published_kind_schema_enumerates_node_kinds(tmp_path: Path) -> None:
    """``list_tools`` must show the vocabulary — same style as the 050 schema-guard test."""

    async def kind_schema() -> dict[str, Any]:
        async with Client(build_server(search_db_config(tmp_path))) as client:
            tools = {tool.name: tool.inputSchema for tool in await client.list_tools()}
            prop = tools["search_symbol"]["properties"]["kind"]
            assert isinstance(prop, dict)
            return prop

    kind_prop = asyncio.run(kind_schema())
    assert _kind_enum(kind_prop) == list(NODE_KINDS)
    assert {"type": "null"} in kind_prop.get("anyOf", [])


def test_kind_schema_enum_is_node_kinds_not_a_hand_copy(tmp_path: Path) -> None:
    """Drift guard: published enum must be exactly ``list(NODE_KINDS)``."""

    async def published_enum() -> list[str]:
        async with Client(build_server(search_db_config(tmp_path))) as client:
            tools = {tool.name: tool.inputSchema for tool in await client.list_tools()}
            prop = tools["search_symbol"]["properties"]["kind"]
            assert isinstance(prop, dict)
            return _kind_enum(prop)

    assert asyncio.run(published_enum()) == list(NODE_KINDS)


def test_unknown_kind_fails_loud_through_mcp(tmp_path: Path) -> None:
    """The agent must see a ToolError, not an empty ``results`` list (056 premise)."""
    message = raises_through_the_client(
        build_server(search_db_config(tmp_path)),
        SEARCH,
        {"query": "User", "kind": "class"},
    )
    for accepted in NODE_KINDS:
        assert accepted in message, accepted
    assert "no_matches" not in message
