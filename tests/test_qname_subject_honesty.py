"""Tasks 075 + 076: a malformed or under-qualified subject is not reported as absence.

One language-agnostic classifier (``nav_result.classify_missing_subject``) serves both: a
leading-anchor difference (``Ns\\Sub\\Enum`` vs the stored ``\\Ns\\Sub\\Enum``) resolves as a
single candidate; a bare member name (``isEnabled``) surfaces as many → ``name_not_qualified``.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools import (
    explain_path,
    file_outline,
    find_callers,
    find_implementations,
    find_references,
    find_view_data,
    impact,
    read_symbol,
    search_symbol,
)
from code_atlas.tools.nav_result import (
    REASON_NAME_NOT_QUALIFIED,
    REASON_NO_SUCH_SYMBOL,
    REASON_OK,
    TRY_INSTEAD_SEARCH_SYMBOL,
)
from tests.test_nav_tools import db_config, edge, node, seed_file

# One indexed file. `\Ns\Sub\Enum` is unique (leading-anchor case); `isEnabled` is a member name
# two classes carry (bare/under-qualified case); one caller targets the qualified `isEnabled`.
_NODES = [
    node("Class", "Enum", "\\Ns\\Sub\\Enum", "app.php"),
    node("Class", "Flags", "\\Ns\\Sub\\Flags", "app.php"),
    node("Method", "isEnabled", "\\Ns\\Sub\\Flags::isEnabled", "app.php"),
    node("Class", "Toggle", "\\Ns\\Other\\Toggle", "app.php"),
    node("Method", "isEnabled", "\\Ns\\Other\\Toggle::isEnabled", "app.php"),
    node("Function", "caller", "\\Ns\\caller", "app.php"),
]
_EDGES = [
    edge(
        "CALLS",
        "\\Ns\\caller",
        "\\Ns\\Sub\\Flags::isEnabled",
        "app.php",
        target_qname="\\Ns\\Sub\\Flags::isEnabled",
    ),
]


@pytest.fixture
def config(tmp_path: Path) -> Iterator[Config]:
    with GraphStore(tmp_path / "graph.db") as store:
        seed_file(store, "app.php", _NODES, _EDGES, root=tmp_path)
    yield db_config(tmp_path)


# --- 075: read_symbol -------------------------------------------------------------------------

def test_read_symbol_normalises_leading_anchor(config: Config) -> None:
    """PROVING TEST — both forms return the same found answer (pre-change: found:false/ok)."""
    tool = read_symbol.create(config)
    anchored = tool("\\Ns\\Sub\\Enum")
    bare_anchor = tool("Ns\\Sub\\Enum")
    assert anchored["found"] is True
    assert bare_anchor == anchored  # byte-identical (AC75.1)


def test_read_symbol_absent_is_no_such_symbol_never_ok(config: Config) -> None:
    result = read_symbol.create(config)("\\Nope\\Missing")
    assert result["found"] is False
    assert result["reason"] == REASON_NO_SUCH_SYMBOL  # never REASON_OK (075)


def test_read_symbol_ambiguous_bare_name_is_name_not_qualified(config: Config) -> None:
    result = read_symbol.create(config)("isEnabled")
    assert result["found"] is False
    assert result["reason"] == REASON_NAME_NOT_QUALIFIED
    assert result["candidate_count"] == 2
    assert result["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL


# --- 076: bare subject on the find_* family ---------------------------------------------------

def test_bare_name_subject_is_name_not_qualified(config: Config) -> None:
    result = find_callers.create(config)("isEnabled", detail_level="minimal")
    assert result["reason"] == REASON_NAME_NOT_QUALIFIED
    assert result["results"] == []
    assert result["candidate_count"] == 2
    assert result["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL


def test_bare_name_zero_candidates_stays_no_such_symbol(config: Config) -> None:
    result = find_callers.create(config)("totallyAbsentXyz", detail_level="minimal")
    assert result["reason"] == REASON_NO_SUCH_SYMBOL
    assert "candidate_count" not in result


def test_try_instead_route_reaches_the_symbol(config: Config) -> None:
    """AC75.3 — the named route (search_symbol) actually finds the candidates."""
    missed = find_callers.create(config)("isEnabled", detail_level="minimal")
    assert missed["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL
    found = search_symbol.create(config)("isEnabled", detail_level="minimal")
    assert found["total_count"] >= 2


def test_qualified_form_unchanged(config: Config) -> None:
    """AC76.3 — the fully-qualified subject answers exactly as before, no extra fields."""
    result = find_callers.create(config)(
        "\\Ns\\Sub\\Flags::isEnabled", detail_level="minimal"
    )
    assert result["reason"] == REASON_OK
    assert result["total_count"] == 1
    assert "candidate_count" not in result
    assert "try_instead" not in result


@pytest.mark.parametrize("factory", [find_references.create, find_implementations.create])
def test_refs_and_impls_bare_name_is_name_not_qualified(config: Config, factory: object) -> None:
    result = factory(config)("isEnabled", detail_level="minimal")  # type: ignore[operator]
    assert result["reason"] == REASON_NAME_NOT_QUALIFIED
    assert result["candidate_count"] == 2
    assert result["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL


def test_find_view_data_bare_name_is_name_not_qualified(config: Config) -> None:
    result = find_view_data.create(config)("isEnabled", detail_level="minimal")
    assert result["reason"] == REASON_NAME_NOT_QUALIFIED
    assert result["candidate_count"] == 2


# --- 075/076 surface sweep: no tool pairs an empty answer with reason:ok ----------------------

def test_no_tool_returns_absence_with_reason_ok(config: Config) -> None:
    """AC75.2 — a not-found / empty answer never carries reason:ok anywhere on the surface."""
    absent = "\\Nope\\Missing"
    payloads = [
        read_symbol.create(config)(absent),
        find_callers.create(config)(absent, detail_level="minimal"),
        find_references.create(config)(absent, detail_level="minimal"),
        find_implementations.create(config)(absent, detail_level="minimal"),
        find_view_data.create(config)(absent, detail_level="minimal"),
        file_outline.create(config)("no/such/file.php"),
    ]
    for payload in payloads:
        empty = payload.get("found") is False or payload.get("results") == []
        if empty:
            assert payload.get("reason") != REASON_OK, payload


# --- 075/076: multi-subject tools re-point a uniquely-resolvable under-anchored subject --------

def test_impact_seeds_repoint_unique_and_drop_ambiguous(config: Config) -> None:
    with GraphStore(config.db_path) as store:
        assert impact._seeds(
            store, paths=[], qnames=["Ns\\Sub\\Enum"], max_results=50
        ) == ["\\Ns\\Sub\\Enum"]
        assert impact._seeds(store, paths=[], qnames=["isEnabled"], max_results=50) == []


def test_explain_path_endpoint_repoints_unique_only(config: Config) -> None:
    with GraphStore(config.db_path) as store:
        assert explain_path._resolve_endpoint(store, "Ns\\Sub\\Enum", 50) == "\\Ns\\Sub\\Enum"
        assert explain_path._resolve_endpoint(store, "\\Ns\\Sub\\Enum", 50) == "\\Ns\\Sub\\Enum"
        assert explain_path._resolve_endpoint(store, "isEnabled", 50) == "isEnabled"
