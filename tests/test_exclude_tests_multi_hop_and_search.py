"""Task 332 — exclude_tests on multi-hop find_callers and on search_symbol."""

from __future__ import annotations

from pathlib import Path

from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, search_symbol
from tests.test_nav_tools import db_config, edge, node, seed_file
from tests.test_nav_tools import store as store  # noqa: F401 — pytest fixture


def test_find_callers_depth_two_exclude_tests(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1 — depth=2 + exclude_tests answers; no test-role site in the rows."""
    seed_file(
        store,
        "src/Leaf.php",
        [node("Function", "leaf", "leaf", "src/Leaf.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "src/Mid.php",
        [node("Function", "mid", "mid", "src/Mid.php")],
        [edge("CALLS", "mid", "leaf", "src/Mid.php", target_qname="leaf")],
        root=tmp_path,
    )
    seed_file(
        store,
        "src/Prod.php",
        [node("Function", "prod", "prod", "src/Prod.php")],
        [edge("CALLS", "prod", "mid", "src/Prod.php", target_qname="mid")],
        root=tmp_path,
    )
    seed_file(
        store,
        "tests/TestMid.php",
        [node("Method", "test_it", "TestMid::test_it", "tests/TestMid.php")],
        [
            edge(
                "CALLS",
                "TestMid::test_it",
                "mid",
                "tests/TestMid.php",
                target_qname="mid",
            )
        ],
        root=tmp_path,
    )
    tool = find_callers.create(db_config(tmp_path))
    # Would have raised on today's depth gate.
    payload = tool("leaf", depth=2, exclude_tests=True)
    files = [str(h.get("file", "")) for h in payload["results"]]  # type: ignore[index]
    assert files
    assert all(not f.startswith("tests/") for f in files)
    assert any("Prod.php" in f or "Mid.php" in f for f in files)


def test_search_symbol_exclude_tests_filters_total(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2 — class + three tests; exclude_tests keeps the class and drops tests from total."""
    seed_file(
        store,
        "src/Widget.php",
        [node("Class", "Widget", "App\\Widget", "src/Widget.php")],
        [],
        root=tmp_path,
    )
    for i in range(3):
        path = f"tests/WidgetTest{i}.php"
        seed_file(
            store,
            path,
            [node("Method", f"testWidget{i}", f"WidgetTest{i}::testWidget{i}", path)],
            [],
            root=tmp_path,
        )
    tool = search_symbol.create(db_config(tmp_path))
    filtered = tool(query="Widget", exclude_tests=True, limit=20)
    kinds = {str(h["kind"]) for h in filtered["results"]}  # type: ignore[index]
    assert "Class" in kinds
    assert "Method" not in kinds
    assert filtered["total_count"] == 1
    full = tool(query="Widget", limit=20)
    assert int(full["total_count"]) >= 4  # type: ignore[arg-type]


def test_exclude_tests_default_byte_identical(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC3 — default exclude_tests=false is byte-identical to omitting the argument."""
    seed_file(
        store,
        "src/A.php",
        [node("Function", "alpha", "alpha", "src/A.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "src/B.php",
        [node("Function", "beta", "beta", "src/B.php")],
        [edge("CALLS", "beta", "alpha", "src/B.php", target_qname="alpha")],
        root=tmp_path,
    )
    callers = find_callers.create(db_config(tmp_path))
    assert callers("alpha", depth=2) == callers("alpha", depth=2, exclude_tests=False)
    search = search_symbol.create(db_config(tmp_path))
    assert search(query="alpha") == search(query="alpha", exclude_tests=False)
