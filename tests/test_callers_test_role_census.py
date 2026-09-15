"""262 — production vs test caller census and SQL-side exclude_tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references
from code_atlas.tools.nav_result import REASON_NO_MATCHES, REASON_OK
from tests.test_nav_tools import db_config, edge, node, seed_file


def _assert_partition(payload: dict[str, object]) -> None:
    prod = int(payload.get("production_count") or 0)
    test = int(payload.get("test_count") or 0)
    assert prod + test == payload["total_count"]


@pytest.fixture
def store(tmp_path: Path):
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def test_all_test_callers_not_no_matches(store: GraphStore, tmp_path: Path) -> None:
    root = tmp_path
    subject = "src/App.php"
    seed_file(
        store,
        subject,
        [node("Class", "App", "App", subject)],
        [],
        root=root,
    )
    seed_file(
        store,
        "tests/AppTest.php",
        [node("Method", "test_it", "AppTest::test_it", "tests/AppTest.php")],
        [
            edge("CALLS", "AppTest::test_it", "App", "tests/AppTest.php", target_qname="App"),
        ],
        root=root,
    )
    cfg = db_config(tmp_path)
    tool = find_callers.create(cfg)
    payload = tool("App", depth=1)
    assert payload["production_count"] == 0
    assert payload["test_count"] == 1
    assert payload["reason"] != REASON_NO_MATCHES
    assert payload["total_count"] == 1
    _assert_partition(payload)


def test_exclude_tests_pages_filtered_set(store: GraphStore, tmp_path: Path) -> None:
    root = tmp_path
    subject = "src/Target.php"
    prod_callers: list[dict] = []
    prod_edges: list[dict] = []
    for i in range(3):
        path = f"src/caller_{i}.php"
        qn = f"Caller{i}::run"
        prod_callers.append(node("Method", "run", qn, path))
        prod_edges.append(
            edge("CALLS", qn, "Target", path, target_qname="Target")
        )
    seed_file(store, subject, [node("Class", "Target", "Target", subject)], [], root=root)
    seed_file(store, "src/caller_0.php", [prod_callers[0]], [prod_edges[0]], root=root)
    seed_file(store, "src/caller_1.php", [prod_callers[1]], [prod_edges[1]], root=root)
    seed_file(store, "src/caller_2.php", [prod_callers[2]], [prod_edges[2]], root=root)
    test_edges = []
    for i in range(10):
        path = f"tests/t_{i}.php"
        qn = f"T{i}::t"
        test_edges.append(edge("CALLS", qn, "Target", path, target_qname="Target"))
        seed_file(
            store,
            path,
            [node("Method", "t", qn, path)],
            [test_edges[-1]],
            root=root,
        )
    cfg = db_config(tmp_path)
    tool = find_callers.create(cfg)
    filtered = tool("Target", depth=1, limit=2, exclude_tests=True)
    assert filtered["total_count"] == 3
    assert len(filtered["results"]) == 2
    assert all("tests/" not in str(h.get("file_path", "")) for h in filtered["results"])


def test_census_partitions_total(store: GraphStore, tmp_path: Path) -> None:
    root = tmp_path
    seed_file(
        store,
        "tests/x.php",
        [node("Method", "m", "T::m", "tests/x.php")],
        [edge("CALLS", "T::m", "Subj", "tests/x.php", target_qname="Subj")],
        root=root,
    )
    seed_file(store, "src/s.php", [node("Class", "Subj", "Subj", "src/s.php")], [], root=root)
    rows = store.inbound_test_rows("Subj", kinds=("CALLS", "NEW"))
    prod = sum(count for is_test, _path, count in rows if not is_test)
    test = sum(count for is_test, _path, count in rows if is_test)
    assert prod == 0 and test == 1
    assert prod + test == store.count_edges_by_target("Subj", kinds=("CALLS", "NEW"))


def test_find_references_carries_census(store: GraphStore, tmp_path: Path) -> None:
    root = tmp_path
    seed_file(
        store,
        "src/Foo.php",
        [node("Class", "Foo", "Foo", "src/Foo.php")],
        [],
        root=root,
    )
    seed_file(
        store,
        "tests/FooTest.php",
        [node("Method", "t", "FooTest::t", "tests/FooTest.php")],
        [edge("REFERENCES", "FooTest::t", "Foo", "tests/FooTest.php", target_qname="Foo")],
        root=root,
    )
    cfg = db_config(tmp_path)
    tool = find_references.create(cfg)
    payload = tool("Foo")
    assert payload["test_count"] == 1
    assert payload["production_count"] == 0
    assert payload["reason"] == REASON_OK
    _assert_partition(payload)


def test_excluding_every_caller_is_not_an_ok_answer(
    store: GraphStore, tmp_path: Path
) -> None:
    """An empty page is never `ok` (R5.6 / 264) — the census beside it says why it is empty."""
    root = tmp_path
    seed_file(store, "src/App.php", [node("Class", "App", "App", "src/App.php")], [], root=root)
    seed_file(
        store,
        "tests/AppTest.php",
        [node("Method", "t", "AppTest::t", "tests/AppTest.php")],
        [edge("CALLS", "AppTest::t", "App", "tests/AppTest.php", target_qname="App")],
        root=root,
    )
    payload = find_callers.create(db_config(tmp_path))("App", depth=1, exclude_tests=True)
    assert payload["results"] == []
    assert payload["total_count"] == 0
    assert payload["reason"] != REASON_OK
    assert payload["production_count"] == 0
    assert payload["test_count"] == 1


def test_census_is_omitted_above_depth_one(store: GraphStore, tmp_path: Path) -> None:
    """A depth-1 partition cannot add up to a BFS total, so it is not reported beside one."""
    root = tmp_path
    seed_file(store, "src/App.php", [node("Class", "App", "App", "src/App.php")], [], root=root)
    seed_file(
        store,
        "src/Caller.php",
        [node("Method", "run", "Caller::run", "src/Caller.php")],
        [edge("CALLS", "Caller::run", "App", "src/Caller.php", target_qname="App")],
        root=root,
    )
    tool = find_callers.create(db_config(tmp_path))
    shallow = tool("App", depth=1)
    assert shallow["production_count"] == 1
    _assert_partition(shallow)
    deep = tool("App", depth=2)
    assert "production_count" not in deep
    assert "test_count" not in deep


def test_test_role_source_names_the_path_convention(
    store: GraphStore, tmp_path: Path
) -> None:
    """No adapter emitted ``is_test`` here, so the label must say the path decided it."""
    root = tmp_path
    seed_file(store, "src/App.php", [node("Class", "App", "App", "src/App.php")], [], root=root)
    seed_file(
        store,
        "tests/AppTest.php",
        [node("Method", "t", "AppTest::t", "tests/AppTest.php")],
        [edge("CALLS", "AppTest::t", "App", "tests/AppTest.php", target_qname="App")],
        root=root,
    )
    payload = find_callers.create(db_config(tmp_path))("App", depth=1)
    assert payload["test_role_source"] == "path_convention"
    _assert_partition(payload)
