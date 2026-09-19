"""Task 293 — ``Class.method`` is a direct match via the member-separator variant (249/287)."""

from __future__ import annotations

from pathlib import Path

from code_atlas.store import GraphStore, is_direct_match
from code_atlas.tools import search_symbol
from code_atlas.tools.nav_result import (
    REASON_OK,
    REASON_SEPARATOR_NORMALISED,
    REASON_SUBSTRING_MATCH,
)
from tests.test_nav_tools import db_config, node, seed_file
from tests.test_nav_tools import store as store  # noqa: F401 — pytest fixture


def test_dot_and_double_colon_are_direct_on_boundary() -> None:
    """AC1: Class.method and Class::method both direct-match the same qname shapes."""
    assert is_direct_match(
        "Class::method", "method", r"App\Svc\Class::method"
    )
    assert is_direct_match(
        "Class.method", "method", "src/svc.ts::Class::method"
    )
    assert is_direct_match(
        "Class.method", "method", "pkg/mod.py::Class::method"
    )


def test_double_colon_query_stays_off_path_shaped_qnames() -> None:
    """061: Class::method does not newly direct-match file::Class::method (challenger)."""
    assert not is_direct_match(
        "Class::method", "method", "src/svc.ts::Class::method"
    )
    assert is_direct_match(
        "Class.method", "method", "src/svc.ts::Class::method"
    )
    """AC3: `_` is an identifier character — Foo_EntityPlan.getItem is not direct."""
    assert not is_direct_match(
        "EntityPlan.getItem",
        "getItem",
        r"\App\Foo_EntityPlan::getItem",
    )
    assert not is_direct_match(
        "EntityPlan::getItem",
        "getItem",
        r"\App\Foo_EntityPlan::getItem",
    )


def test_search_dot_spelling_is_direct_band_with_separator_reason(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2: UserService.getUser → direct band, reason names the separator variant."""
    seed_file(
        store,
        "svc.ts",
        [
            node("Method", "getUser", "src/svc.ts::UserService::getUser", "svc.ts"),
            node("Method", "getUserX", "src/svc.ts::UserService::getUserX", "svc.ts"),
            node("Method", "getUser", "src/svc.ts::Other::getUser", "svc.ts"),
        ],
        [],
        root=tmp_path,
    )
    payload = search_symbol.create(db_config(tmp_path))(
        query="UserService.getUser", kind="Method", limit=10
    )
    assert payload["reason"] == REASON_SEPARATOR_NORMALISED
    assert payload["reason"] != REASON_SUBSTRING_MATCH
    first = payload["results"][0]  # type: ignore[index]
    assert first["qname"] == "src/svc.ts::UserService::getUser"


def test_no_separator_and_double_colon_unchanged(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC4/061: bare query and :: spelling keep today's reason bands."""
    seed_file(
        store,
        "a.php",
        [node("Method", "preloadReport", r"\App\Doc::preloadReport", "a.php")],
        [],
        root=tmp_path,
    )
    bare = search_symbol.create(db_config(tmp_path))(query="loadReport", kind="Method")
    assert bare["reason"] == REASON_SUBSTRING_MATCH

    seed_file(
        store,
        "b.php",
        [node("Method", "getItem", r"\App\EntityPlan::getItem", "b.php")],
        [],
        root=tmp_path,
    )
    colon = search_symbol.create(db_config(tmp_path))(
        query="EntityPlan::getItem", kind="Method"
    )
    assert colon["reason"] == REASON_OK
