"""Task 069: descriptions answer the caller's question; find_view_data says when it is inert.

The proving path is integration — it reads the descriptions the MCP client actually receives from a
built server, the same text a session routes on, not the raw source docstrings.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from fastmcp import Client

from code_atlas import contract
from code_atlas.main import build_server
from code_atlas.store import GraphStore
from code_atlas.tools import find_view_data
from code_atlas.tools.nav_result import (
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_NO_MATCHES,
)
from tests.test_nav_tools import db_config, node, seed_file

# Mechanism vocabulary an opener must not carry before the question it answers (AC4).
_EDGE_KINDS = contract.EDGE_KINDS
_CA_VAR = re.compile(r"\bCA_[A-Z_]+\b")
_EDGE_WORD = re.compile(r"\bedges?\b", re.IGNORECASE)
_LANGS = ("php", "javascript", "typescript", "csharp", "roslyn", "nikic")


def _descriptions(server: Any) -> dict[str, str]:
    async def once() -> dict[str, str]:
        async with Client(server) as client:
            return {t.name: (t.description or "") for t in await client.list_tools()}

    return asyncio.run(once())


def _opener(description: str) -> str:
    """The first line — the summary a caller reads when scanning the tool list."""
    return description.strip().splitlines()[0]


def test_each_tool_opens_with_the_question_not_the_mechanism(tmp_path: Path) -> None:
    """Proving (AC1/AC4): no opener leads with an edge kind, a config var, or a language."""
    descriptions = _descriptions(build_server(db_config(tmp_path)))
    assert len(descriptions) == 14
    for name, description in descriptions.items():
        opener = _opener(description)
        for kind in _EDGE_KINDS:
            assert kind not in opener, f"{name} opener names edge kind {kind}: {opener!r}"
        assert not _CA_VAR.search(opener), f"{name} opener names a CA_ config var: {opener!r}"
        assert not _EDGE_WORD.search(opener), f"{name} opener says 'edge(s)': {opener!r}"
        low = opener.lower()
        for lang in _LANGS:
            assert lang not in low, f"{name} opener names a language {lang}: {opener!r}"


def test_find_view_data_inert_without_rules_is_distinct_from_no_keys(tmp_path: Path) -> None:
    """AC3: no rules configured -> capability_not_configured; configured but empty -> no_matches."""
    with GraphStore(tmp_path / "graph.db") as store:
        seed_file(
            store,
            "h.php",
            [node("Method", "index", "\\Ctrl::index", "h.php")],
            [],
            root=tmp_path,
        )
    no_rules = db_config(tmp_path)
    assert no_rules.indirection_rules is None
    inert = find_view_data.create(no_rules)("\\Ctrl::index", detail_level="minimal")
    assert inert["reason"] == REASON_CAPABILITY_NOT_CONFIGURED
    assert inert["total_count"] == 0
    assert inert["results"] == []

    configured = replace(no_rules, indirection_rules=("view_data:with",))
    empty = find_view_data.create(configured)("\\Ctrl::index", detail_level="minimal")
    assert empty["reason"] == REASON_NO_MATCHES
    assert empty["total_count"] == 0
