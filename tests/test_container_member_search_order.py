"""Task 292 — a container's own hits outrank Columns it CONTAINS for the same query."""

from __future__ import annotations

from pathlib import Path

from code_atlas.store import GraphStore
from code_atlas.tools import search_symbol
from tests.test_nav_tools import db_config, edge, node, seed_file
from tests.test_nav_tools import store as store  # noqa: F401 — pytest fixture


def _plant_orders_with_crowding_columns(store: GraphStore, root: Path) -> None:
    """One Table + 40 Columns share a file; five Table twins sit behind them on BM25 alone."""
    path = "t.sql"
    cols = [node("Column", f"col_{i:02d}", f"Orders::col_{i:02d}", path) for i in range(40)]
    contains = [
        edge(
            "CONTAINS",
            "Orders",
            c["qualified_name"],
            path,
            target_qname=str(c["qualified_name"]),
        )
        for c in cols
    ]
    seed_file(
        store,
        path,
        [node("Table", "Orders", "Orders", path), *cols],
        contains,
        root=root,
    )
    for i in range(5):
        p = f"migration/{i:03d}_orders.sql"
        seed_file(
            store,
            p,
            [node("Table", "Orders", f"legacy{i}.Orders", p)],
            [],
            root=root,
        )
    seed_file(
        store,
        "procs/Orders.sql",
        [node("Function", "Orders", "dbo.Orders", "procs/Orders.sql")],
        [],
        root=root,
    )


def test_table_and_twins_outrank_contained_columns(tmp_path: Path, store: GraphStore) -> None:
    """AC1 / AC3 — Table definitions (including twins) beat CONTAINS Columns on page 1."""
    _plant_orders_with_crowding_columns(store, tmp_path)
    page = store.search_nodes("Orders", limit=10)
    kinds = [str(r["kind"]) for r in page]
    first_col = next((i for i, k in enumerate(kinds) if k == "Column"), len(kinds))
    assert all(k in ("Table", "Function") for k in kinds[:first_col])
    assert first_col == 7  # 1 primary + 5 twins + 1 Function — none truncated
    assert str(page[0]["qualified_name"]) == "Orders"


def test_procedure_definitions_before_same_named_table_columns(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2 — Function hits for the query name precede Columns of a same-named Table."""
    _plant_orders_with_crowding_columns(store, tmp_path)
    rows = store.search_nodes("Orders", limit=50)
    first_col = next(i for i, r in enumerate(rows) if r["kind"] == "Column")
    fn_idxs = [i for i, r in enumerate(rows) if r["kind"] == "Function"]
    table_idxs = [i for i, r in enumerate(rows) if r["kind"] == "Table"]
    assert fn_idxs and all(i < first_col for i in fn_idxs)
    assert table_idxs and all(i < first_col for i in table_idxs)


def test_no_contains_pair_is_byte_identical(tmp_path: Path, store: GraphStore) -> None:
    """AC4 / 061 — no container/member CONTAINS among hits ⇒ same order as pre-292 keys."""
    seed_file(
        store,
        "a.php",
        [
            node("Class", "Widget", "App\\Widget", "a.php"),
            node("Class", "WidgetFactory", "App\\WidgetFactory", "a.php"),
        ],
        [],
        root=tmp_path,
    )
    rows = store.search_nodes("Widget", limit=10)
    assert [r["qualified_name"] for r in rows] == ["App\\Widget", "App\\WidgetFactory"]


def test_column_kind_filter_does_not_demote_without_parent_hit(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC4 — CONTAINS parent outside the filtered hit set must not reorder Columns."""
    path = "t.sql"
    cols = [node("Column", f"col_{i:02d}", f"Orders::col_{i:02d}", path) for i in range(5)]
    seed_file(
        store,
        path,
        [node("Table", "Orders", "Orders", path), *cols],
        [
            edge(
                "CONTAINS",
                "Orders",
                c["qualified_name"],
                path,
                target_qname=str(c["qualified_name"]),
            )
            for c in cols
        ],
        root=tmp_path,
    )
    with_filter = [
        r["qualified_name"] for r in store.search_nodes("Orders", kind="Column", limit=20)
    ]
    # Same Columns, no Table row in the store at all → no parent hit possible.
    store2_path = tmp_path / "solo.db"
    with GraphStore(store2_path) as solo:
        seed_file(solo, path, cols, [], root=tmp_path / "solo_root")
        without_parent = [
            r["qualified_name"] for r in solo.search_nodes("Orders", kind="Column", limit=20)
        ]
    assert with_filter == without_parent


def test_search_symbol_page_keeps_container_definitions(
    tmp_path: Path, store: GraphStore
) -> None:
    """Tool surface: page limit no longer truncates Table/Function defs behind Columns."""
    _plant_orders_with_crowding_columns(store, tmp_path)
    out = search_symbol.create(db_config(tmp_path))(query="Orders", limit=7)
    kinds = [h["kind"] for h in out["results"]]  # type: ignore[index]
    assert "Column" not in kinds
    assert kinds.count("Table") == 6 and kinds.count("Function") == 1


def _plant_class_with_methods(
    store: GraphStore, root: Path, *, class_qname: str, path: str
) -> None:
    """Class + many Methods sharing a CONTAINS parent — the 297 band-collision shape."""
    methods = [
        node("Method", f"m_{i:02d}", f"{class_qname}::m_{i:02d}", path) for i in range(20)
    ]
    contains = [
        edge(
            "CONTAINS",
            class_qname,
            m["qualified_name"],
            path,
            target_qname=str(m["qualified_name"]),
        )
        for m in methods
    ]
    bare = class_qname.rsplit("\\", 1)[-1].rsplit("::", 1)[-1]
    seed_file(
        store,
        path,
        [node("Class", bare, class_qname, path), *methods],
        contains,
        root=root,
    )


def test_php_class_outranks_its_methods(tmp_path: Path, store: GraphStore) -> None:
    """297 AC1 — qualified Class query ranks Class above its Methods."""
    qn = "App\\UserService"
    _plant_class_with_methods(store, tmp_path, class_qname=qn, path="UserService.php")
    page = store.search_nodes(qn, limit=10)
    assert str(page[0]["qualified_name"]) == qn
    assert str(page[0]["kind"]) == "Class"
    assert all(r["kind"] != "Class" or r["qualified_name"] == qn for r in page[1:])


def test_ts_class_outranks_its_methods(tmp_path: Path, store: GraphStore) -> None:
    """297 AC1 — TypeScript Class::Method qnames demote the same way."""
    qn = "src/user.ts::UserService"
    _plant_class_with_methods(store, tmp_path, class_qname=qn, path="src/user.ts")
    page = store.search_nodes(qn, limit=10)
    assert str(page[0]["qualified_name"]) == qn
    assert str(page[0]["kind"]) == "Class"


def test_python_class_outranks_its_methods(tmp_path: Path, store: GraphStore) -> None:
    """297 AC1 — Python Class qname ranks above Methods."""
    qn = "pkg.user::UserService"
    _plant_class_with_methods(store, tmp_path, class_qname=qn, path="pkg/user.py")
    page = store.search_nodes(qn, limit=10)
    assert str(page[0]["qualified_name"]) == qn
    assert str(page[0]["kind"]) == "Class"


def test_demote_term_has_no_column_kind_literal() -> None:
    """297 AC3 — demote is containment-keyed, not COLUMN_KIND."""
    from code_atlas import contract
    from code_atlas.store import _search_contains_demote

    sql, _ = _search_contains_demote("Orders", kind=None, namespace=None)
    assert contract.COLUMN_KIND not in sql
    assert "nodes.kind =" not in sql

