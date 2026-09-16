"""Task 287 — ``Class::method`` is a direct match on a separator boundary, not a substring."""

from __future__ import annotations

from pathlib import Path

from code_atlas.store import GraphStore, is_direct_match
from code_atlas.tools import search_symbol
from code_atlas.tools.nav_result import REASON_OK, REASON_SUBSTRING_MATCH
from tests.test_nav_tools import db_config, node, seed_file
from tests.test_nav_tools import store as store  # noqa: F401 — pytest fixture


def test_class_method_query_is_direct_on_boundary() -> None:
    """Predicate: Class::method suffixes a qname on a non-alnum boundary."""
    assert is_direct_match(
        "EntityPlan::getItem",
        "getItem",
        "\\App\\EntityPlan::getItem",
    )
    assert is_direct_match(
        "EntityPlan::getItem",
        "getItem",
        "App\\EntityPlan::getItem",
    )


def test_bare_method_and_cross_class_are_not_accidentally_direct() -> None:
    """AC2/AC3: bare method still exact-on-name; other class is not a Class::method hit."""
    assert is_direct_match("getItem", "getItem", "\\App\\Other::getItem")
    assert not is_direct_match(
        "EntityPlan::getItem",
        "getItem",
        "\\App\\OtherClass::getItem",
    )
    assert not is_direct_match(
        "EntityPlan::getItem",
        "getItem",
        "\\App\\FooEntityPlan::getItem",
    )
    assert not is_direct_match(
        "EntityPlan::getItem",
        "getItem",
        "\\App\\Foo_EntityPlan::getItem",
    )


def test_search_class_method_reason_ok_and_exact_first(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1: Class::method → reason ok, exact member first."""
    seed_file(
        store,
        "a.php",
        [
            node("Method", "getItem", "\\App\\EntityPlan::getItem", "a.php"),
            node("Method", "getItemX", "\\App\\EntityPlan::getItemX", "a.php"),
            node("Method", "getItem", "\\App\\Other::getItem", "a.php"),
        ],
        [],
        root=tmp_path,
    )
    payload = search_symbol.create(db_config(tmp_path))(
        query="EntityPlan::getItem", kind="Method", limit=10
    )
    assert payload["reason"] == REASON_OK
    first = payload["results"][0]  # type: ignore[index]
    assert first["qname"] == "\\App\\EntityPlan::getItem"


def test_query_without_separator_byte_identical_band(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC4: no member separator → same reason band as before for a substring near-miss."""
    seed_file(
        store,
        "a.php",
        [node("Method", "preloadReport", "\\App\\Doc::preloadReport", "a.php")],
        [],
        root=tmp_path,
    )
    payload = search_symbol.create(db_config(tmp_path))(query="loadReport", limit=10)
    assert payload["reason"] == REASON_SUBSTRING_MATCH
