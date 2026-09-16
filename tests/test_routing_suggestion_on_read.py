"""Task 158 — a successful read_symbol of a callable earns the next mechanism step.

The routing surface was state-reactive (build when stale) and miss-reactive (try_instead on a zero),
never question-reactive: a successful body read of a method carried no pointer to find_callers /
impact — the pivotal "who calls this?" call the field retro never made. The suggestion is earned by
node kind (callable), never universal (061), and names registered tools (093).
"""

from __future__ import annotations

from pathlib import Path

from code_atlas.main import TOOL_NAMES
from code_atlas.tools import read_symbol
from code_atlas.tools.nav_result import NEXT_TOOLS_FOR_CALLABLE, NEXT_TOOLS_FOR_TYPE
from tests.test_nav_tools import (  # noqa: F401 — store is a fixture
    db_config,
    node,
    seed_file,
    store,
)


def test_read_symbol_of_a_method_suggests_find_callers_and_impact(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """AC1: a method body read names the next mechanism step for that symbol."""
    seed_file(
        store, "a.php", [node("Method", "save", "\\App\\Doc::save", "a.php")], [], root=tmp_path
    )
    result = read_symbol.create(db_config(tmp_path))("\\App\\Doc::save")
    assert result["found"] is True
    assert result["next_tool_suggestions"] == ["find_callers", "impact"]


def test_read_symbol_of_a_function_also_earns_the_suggestion(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """AC1: functions are callable too."""
    seed_file(store, "a.php", [node("Function", "helper", "\\helper", "a.php")], [], root=tmp_path)
    result = read_symbol.create(db_config(tmp_path))("\\helper")
    assert result["next_tool_suggestions"] == ["find_callers", "impact"]


def test_read_symbol_of_a_class_suggests_find_implementations(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """285: a Class hit names find_implementations; Const still earns nothing."""
    seed_file(store, "a.php", [node("Class", "Doc", "\\App\\Doc", "a.php")], [], root=tmp_path)
    result = read_symbol.create(db_config(tmp_path))("\\App\\Doc")
    assert result["found"] is True
    assert result["next_tool_suggestions"] == ["find_implementations"]

    seed_file(store, "b.php", [node("Const", "X", "\\App\\X", "b.php")], [], root=tmp_path)
    const = read_symbol.create(db_config(tmp_path))("\\App\\X")
    assert "next_tool_suggestions" not in const


def test_the_suggested_tools_are_registered_callable_names(tmp_path: Path) -> None:
    """AC2: every suggested name is a real tool the client can call (093), not a string literal."""
    for name in (*NEXT_TOOLS_FOR_CALLABLE, *NEXT_TOOLS_FOR_TYPE):
        assert name in TOOL_NAMES


def test_the_suggestion_is_deterministic(tmp_path: Path, store) -> None:  # noqa: F811
    """AC5 / R4.2: the same answer yields the same suggestion."""
    seed_file(
        store, "a.php", [node("Method", "save", "\\App\\Doc::save", "a.php")], [], root=tmp_path
    )
    tool = read_symbol.create(db_config(tmp_path))
    assert tool("\\App\\Doc::save") == tool("\\App\\Doc::save")
