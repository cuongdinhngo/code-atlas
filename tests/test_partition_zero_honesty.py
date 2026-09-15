"""272 — a production_count 0 partition is as honest as an empty answer."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references
from code_atlas.tools.nav_result import (
    REASON_BARE_NAME_TRUNCATED,
    REASON_OK,
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
    REASON_RELATIONSHIP_NOT_MODELLED,
    escalate_zero_production,
)
from tests.test_nav_tools import db_config, edge, node, seed_file


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def _seed_method(
    store: GraphStore,
    root: Path,
    *,
    production_linked: bool,
    with_unlinked_production: bool,
) -> None:
    seed_file(
        store,
        "src/App.php",
        [
            node("Class", "App", "App", "src/App.php"),
            node("Method", "getPath", "App::getPath", "src/App.php"),
        ],
        [],
        root=root,
    )
    seed_file(
        store,
        "tests/AppTest.php",
        [node("Method", "t", "AppTest::t", "tests/AppTest.php")],
        [
            edge(
                "CALLS",
                "AppTest::t",
                "App::getPath",
                "tests/AppTest.php",
                target_qname="App::getPath",
            )
        ],
        root=root,
    )
    if with_unlinked_production or production_linked:
        prod_edge = edge(
            "CALLS",
            "Caller::run",
            "App::getPath",
            "src/Caller.php",
            target_qname="App::getPath" if production_linked else None,
        )
        seed_file(
            store,
            "src/Caller.php",
            [node("Method", "run", "Caller::run", "src/Caller.php")],
            [prod_edge],
            root=root,
        )


def _seed_class_refs(
    store: GraphStore,
    root: Path,
    *,
    production_linked: bool,
    with_unlinked_production: bool,
) -> None:
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
        [
            edge(
                "REFERENCES",
                "FooTest::t",
                "Foo",
                "tests/FooTest.php",
                target_qname="Foo",
            )
        ],
        root=root,
    )
    if with_unlinked_production or production_linked:
        prod_edge = edge(
            "REFERENCES",
            "Caller::run",
            "Foo",
            "src/Caller.php",
            target_qname="Foo" if production_linked else None,
        )
        seed_file(
            store,
            "src/Caller.php",
            [node("Method", "run", "Caller::run", "src/Caller.php")],
            [prod_edge],
            root=root,
        )


def test_escalate_zero_production_only_from_ok_with_unlinked() -> None:
    assert (
        escalate_zero_production(REASON_OK, production_count=0, unlinked_same_name_sites=1)
        == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
    )
    assert (
        escalate_zero_production(REASON_OK, production_count=0, unlinked_same_name_sites=0)
        == REASON_OK
    )
    assert (
        escalate_zero_production(REASON_OK, production_count=1, unlinked_same_name_sites=1)
        == REASON_OK
    )
    assert (
        escalate_zero_production(
            REASON_RELATIONSHIP_NOT_MODELLED,
            production_count=0,
            unlinked_same_name_sites=1,
        )
        == REASON_RELATIONSHIP_NOT_MODELLED
    )
    assert (
        escalate_zero_production(
            REASON_OK,
            production_count=0,
            unlinked_same_name_sites=0,
            unresolved_bare=1,
        )
        == REASON_BARE_NAME_TRUNCATED
    )
    assert (
        escalate_zero_production(
            REASON_OK,
            production_count=0,
            unlinked_same_name_sites=1,
            unresolved_bare=1,
        )
        == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
    )
    assert (
        escalate_zero_production(
            REASON_OK,
            production_count=0,
            unlinked_same_name_sites=0,
            shared_honesty_reason=REASON_RELATIONSHIP_NOT_MODELLED,
        )
        == REASON_RELATIONSHIP_NOT_MODELLED
    )


def test_unlinked_production_plus_test_caller_is_not_ok(store: GraphStore, tmp_path: Path) -> None:
    _seed_method(store, tmp_path, production_linked=False, with_unlinked_production=True)
    payload = find_callers.create(db_config(tmp_path))("App::getPath", depth=1)
    assert payload["production_count"] == 0
    assert payload["test_count"] == 1
    assert payload["reason"] != REASON_OK
    assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
    assert payload["unlinked_same_name_sites"] == 1


def test_linked_production_stays_ok(store: GraphStore, tmp_path: Path) -> None:
    _seed_method(store, tmp_path, production_linked=True, with_unlinked_production=True)
    payload = find_callers.create(db_config(tmp_path))("App::getPath", depth=1)
    assert payload["reason"] == REASON_OK
    assert payload["production_count"] == 1
    assert "unlinked_same_name_sites" not in payload


def test_true_zero_partition_stays_ok(store: GraphStore, tmp_path: Path) -> None:
    _seed_method(store, tmp_path, production_linked=False, with_unlinked_production=False)
    payload = find_callers.create(db_config(tmp_path))("App::getPath", depth=1)
    assert payload["production_count"] == 0
    assert payload["test_count"] == 1
    assert payload["reason"] == REASON_OK
    assert "unlinked_same_name_sites" not in payload


def test_depth_above_one_does_not_escalate(store: GraphStore, tmp_path: Path) -> None:
    """061: partition fields (and this honesty gate) exist only at depth 1."""
    _seed_method(store, tmp_path, production_linked=False, with_unlinked_production=True)
    payload = find_callers.create(db_config(tmp_path))("App::getPath", depth=2)
    assert payload["reason"] == REASON_OK
    assert "production_count" not in payload
    assert "unlinked_same_name_sites" not in payload


def test_find_references_unlinked_production_plus_test_is_not_ok(
    store: GraphStore, tmp_path: Path
) -> None:
    _seed_class_refs(store, tmp_path, production_linked=False, with_unlinked_production=True)
    payload = find_references.create(db_config(tmp_path))("Foo")
    assert payload["production_count"] == 0
    assert payload["test_count"] == 1
    assert payload["reason"] != REASON_OK
    assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
    assert payload["unlinked_same_name_sites"] == 1


def test_find_references_true_zero_partition_stays_ok(store: GraphStore, tmp_path: Path) -> None:
    _seed_class_refs(store, tmp_path, production_linked=False, with_unlinked_production=False)
    payload = find_references.create(db_config(tmp_path))("Foo")
    assert payload["production_count"] == 0
    assert payload["reason"] == REASON_OK
    assert "unlinked_same_name_sites" not in payload


def test_empty_unmodelled_class_refs_unchanged(store: GraphStore, tmp_path: Path) -> None:
    """AC5: an existing empty relation_unmodelled / relationship_not_modelled case is untouched."""
    seed_file(
        store,
        "a.php",
        [node("Class", "RegionManager", "\\Src\\System\\RegionManager", "a.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "b.php",
        [node("Class", "Caller", "\\App\\Caller", "b.php")],
        [
            edge(
                "REFERENCES",
                "\\App\\Caller",
                "\\Src\\System\\RegionManager",
                "b.php",
            ),
        ],
        root=tmp_path,
    )
    payload = find_references.create(db_config(tmp_path))(
        "\\Src\\System\\RegionManager", detail_level="minimal"
    )
    assert payload["total_count"] == 0
    assert payload["reason"] == REASON_RELATIONSHIP_NOT_MODELLED
    assert payload["reason"] != REASON_OK
