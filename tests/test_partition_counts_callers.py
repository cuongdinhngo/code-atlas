"""273 — the caller partition counts distinct sources, not edge rows."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references
from tests.test_nav_tools import db_config, edge, node, seed_file


def _assert_partition(payload: dict[str, object]) -> None:
    prod = int(payload.get("production_count") or 0)
    test = int(payload.get("test_count") or 0)
    assert prod + test == payload["total_count"]


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def _subject(store: GraphStore, root: Path) -> None:
    seed_file(
        store,
        "src/App.php",
        [node("Method", "run", "App::run", "src/App.php")],
        [],
        root=root,
    )


def test_three_call_sites_are_one_caller(store: GraphStore, tmp_path: Path) -> None:
    _subject(store, tmp_path)
    seed_file(
        store,
        "src/Caller.php",
        [node("Method", "go", "Caller::go", "src/Caller.php")],
        [
            edge(
                "CALLS", "Caller::go", "App::run", "src/Caller.php",
                target_qname="App::run", line=10,
            ),
            edge(
                "CALLS", "Caller::go", "App::run", "src/Caller.php",
                target_qname="App::run", line=20,
            ),
            edge(
                "CALLS", "Caller::go", "App::run", "src/Caller.php",
                target_qname="App::run", line=30,
            ),
        ],
        root=tmp_path,
    )
    payload = find_callers.create(db_config(tmp_path))("App::run", depth=1)
    assert payload["total_count"] == 1
    assert payload["production_count"] == 1
    assert payload["test_count"] == 0
    assert payload["production_count"] + payload["test_count"] == payload["total_count"]


def test_two_definition_files_are_one_caller(store: GraphStore, tmp_path: Path) -> None:
    _subject(store, tmp_path)
    seed_file(
        store,
        "src/a.php",
        [node("Method", "go", "Caller::go", "src/a.php")],
        [edge("CALLS", "Caller::go", "App::run", "src/a.php", target_qname="App::run")],
        root=tmp_path,
    )
    seed_file(
        store,
        "src/b.php",
        [node("Method", "go", "Caller::go", "src/b.php")],
        [],
        root=tmp_path,
    )
    payload = find_callers.create(db_config(tmp_path))("App::run", depth=1)
    assert payload["production_count"] == 1
    assert payload["total_count"] == 1
    assert payload["production_count"] + payload["test_count"] == payload["total_count"]


def test_depth_one_partition_sums_to_total(store: GraphStore, tmp_path: Path) -> None:
    _subject(store, tmp_path)
    seed_file(
        store,
        "src/Caller.php",
        [node("Method", "go", "Caller::go", "src/Caller.php")],
        [edge("CALLS", "Caller::go", "App::run", "src/Caller.php", target_qname="App::run")],
        root=tmp_path,
    )
    seed_file(
        store,
        "tests/AppTest.php",
        [node("Method", "t", "AppTest::t", "tests/AppTest.php")],
        [edge("CALLS", "AppTest::t", "App::run", "tests/AppTest.php", target_qname="App::run")],
        root=tmp_path,
    )
    payload = find_callers.create(db_config(tmp_path))("App::run", depth=1)
    _assert_partition(payload)
    assert payload["production_count"] + payload["test_count"] == payload["total_count"]
    assert payload["test_role_source"] in {"adapter", "path_convention", "mixed"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"confidence_tier": "RESOLVED"},
        {"confidence_tier": "HEURISTIC"},
    ],
)
def test_partition_sums_under_tier_filter(
    store: GraphStore, tmp_path: Path, kwargs: dict[str, str]
) -> None:
    _subject(store, tmp_path)
    seed_file(
        store,
        "src/Caller.php",
        [node("Method", "go", "Caller::go", "src/Caller.php")],
        [
            edge(
                "CALLS",
                "Caller::go",
                "App::run",
                "src/Caller.php",
                target_qname="App::run",
                tier="RESOLVED",
            )
        ],
        root=tmp_path,
    )
    seed_file(
        store,
        "src/Other.php",
        [node("Method", "go", "Other::go", "src/Other.php")],
        [
            edge(
                "CALLS",
                "Other::go",
                "App::run",
                "src/Other.php",
                target_qname="App::run",
                tier="HEURISTIC",
            )
        ],
        root=tmp_path,
    )
    payload = find_callers.create(db_config(tmp_path))("App::run", depth=1, **kwargs)
    _assert_partition(payload)


def test_partition_sums_under_arg_filter(store: GraphStore, tmp_path: Path) -> None:
    _subject(store, tmp_path)
    seed_file(
        store,
        "src/Caller.php",
        [
            node("Method", "a", "Caller::a", "src/Caller.php"),
            node("Method", "b", "Caller::b", "src/Caller.php"),
        ],
        [
            {
                **edge(
                    "CALLS",
                    "Caller::a",
                    "App::run",
                    "src/Caller.php",
                    target_qname="App::run",
                    line=1,
                ),
                "args": [None, "null"],
            },
            {
                **edge(
                    "CALLS",
                    "Caller::b",
                    "App::run",
                    "src/Caller.php",
                    target_qname="App::run",
                    line=2,
                ),
                "args": [None, "array"],
            },
        ],
        root=tmp_path,
    )
    tool = find_callers.create(db_config(tmp_path))
    _assert_partition(tool("App::run", depth=1))
    _assert_partition(tool("App::run", depth=1, arg_position=2, arg_is="null"))


def test_find_references_still_partitions_edge_rows(store: GraphStore, tmp_path: Path) -> None:
    """Hit set is edges; census stays edge rows (pinned, not callers)."""
    seed_file(
        store,
        "src/Foo.php",
        [node("Class", "Foo", "Foo", "src/Foo.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "src/Caller.php",
        [node("Method", "go", "Caller::go", "src/Caller.php")],
        [
            edge("REFERENCES", "Caller::go", "Foo", "src/Caller.php", target_qname="Foo", line=1),
            edge("REFERENCES", "Caller::go", "Foo", "src/Caller.php", target_qname="Foo", line=2),
            edge("REFERENCES", "Caller::go", "Foo", "src/Caller.php", target_qname="Foo", line=3),
        ],
        root=tmp_path,
    )
    payload = find_references.create(db_config(tmp_path))("Foo")
    assert payload["total_count"] == 3
    assert payload["production_count"] + payload["test_count"] == payload["total_count"]
