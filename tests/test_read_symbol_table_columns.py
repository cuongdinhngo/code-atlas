"""Task 248 — ``read_symbol`` on a Table returns its columns via CONTAINS."""

from __future__ import annotations

import hashlib
import shlex
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.main import TOOL_NAMES
from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol


def _plant_table(
    store: GraphStore,
    root: Path,
    *,
    path: str,
    table: str,
    columns: list[tuple[str, str, str | None]],
) -> None:
    """Plant one Table + Columns + CONTAINS edges; column order is DDL emission order."""
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    body = b"CREATE TABLE planted (\n"
    for name, typ, dflt in columns:
        line = f"  {name} {typ}"
        if dflt is not None:
            line += f" DEFAULT {dflt}"
        body += (line + ",\n").encode()
    body += b");\n"
    target.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    store.upsert_file(path, digest, "sql")
    nodes: list[dict[str, object]] = [
        {
            "kind": "Table",
            "name": table.split(".")[-1],
            "qualified_name": table,
            "file_path": path,
            "line_start": 1,
            "line_end": 1,
        }
    ]
    edges: list[dict[str, object]] = []
    for name, typ, dflt in columns:
        qname = f"{table}::{name}"
        extra: dict[str, str] = {"type": typ, "data_type": typ}
        if dflt is not None:
            extra["default"] = dflt
        nodes.append(
            {
                "kind": "Column",
                "name": name,
                "qualified_name": qname,
                "file_path": path,
                "line_start": 1,
                "line_end": 1,
                "extra": extra,
            }
        )
        edges.append(
            {
                "kind": "CONTAINS",
                "source_qname": table,
                "target_raw": qname,
                "target_qname": qname,
                "file_path": path,
                "line": 1,
                "confidence_tier": "RESOLVED",
            }
        )
    store.replace_file_rows(path, nodes, edges)


def _tool(tmp_path: Path, db: Path, *, page_limit: int = 50):
    return read_symbol.create(
        replace(load_config(tmp_path, {}), db_path=db, page_limit=page_limit)
    )


def test_table_read_returns_columns_in_ddl_order_without_source(tmp_path: Path) -> None:
    """AC1: columns name/type/DEFAULT in DDL order; CREATE header is not the product."""
    db = tmp_path / "graph.db"
    # Non-alphabetical DDL order so alpha sort by target_raw would fail.
    cols = [
        ("zeta", "int", None),
        ("alpha", "varchar(8)", "'x'"),
        ("mid", "datetime", None),
    ]
    with GraphStore(db) as store:
        _plant_table(store, tmp_path, path="s.sql", table="dbo.Assets", columns=cols)
    out = _tool(tmp_path, db)("dbo.Assets")
    assert out["found"] is True
    assert out["reason"] == "ok"
    assert out["source"] == ""
    assert [c["name"] for c in out["columns"]] == ["zeta", "alpha", "mid"]  # type: ignore[index]
    assert out["columns"][0] == {"name": "zeta", "type": "int"}  # type: ignore[index]
    assert out["columns"][1] == {
        "name": "alpha",
        "type": "varchar(8)",
        "default": "'x'",
    }  # type: ignore[index]
    assert out["total_count"] == 3
    assert out["truncated"] is False


def test_column_rows_omit_uncaptured_247_fields(tmp_path: Path) -> None:
    """AC2 without 247: no nullability / identity / primary-key keys (R5.6)."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        _plant_table(
            store,
            tmp_path,
            path="s.sql",
            table="dbo.T",
            columns=[("id", "int", None)],
        )
    out = _tool(tmp_path, db)("dbo.T")
    row = out["columns"][0]  # type: ignore[index]
    assert set(row) <= {"name", "type", "default"}
    for banned in ("nullable", "nullability", "identity", "primary_key", "pk", "is_nullable"):
        assert banned not in row


def test_wide_table_is_bounded_with_next_page(tmp_path: Path) -> None:
    """AC3: default page capped; truncated + total_count + offset route the next page."""
    db = tmp_path / "graph.db"
    cols = [(f"c{i:02d}", "int", None) for i in range(5)]
    with GraphStore(db) as store:
        _plant_table(store, tmp_path, path="s.sql", table="dbo.Wide", columns=cols)
    tool = _tool(tmp_path, db, page_limit=2)
    page1 = tool("dbo.Wide")
    assert page1["truncated"] is True
    assert page1["total_count"] == 5
    assert page1["results_offset"] == 0
    assert [c["name"] for c in page1["columns"]] == ["c00", "c01"]  # type: ignore[index]
    page2 = tool("dbo.Wide", offset=2)
    assert page2["results_offset"] == 2
    assert [c["name"] for c in page2["columns"]] == ["c02", "c03"]  # type: ignore[index]
    assert page2["truncated"] is True
    page3 = tool("dbo.Wide", offset=4)
    assert [c["name"] for c in page3["columns"]] == ["c04"]  # type: ignore[index]
    assert page3["truncated"] is False


def test_no_columns_distinguishable_from_empty_page(tmp_path: Path) -> None:
    """AC4: no CONTAINS → no_indexed_columns; offset past end → empty page + total_count."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        _plant_table(store, tmp_path, path="empty.sql", table="dbo.Empty", columns=[])
        _plant_table(
            store,
            tmp_path,
            path="full.sql",
            table="dbo.Full",
            columns=[("a", "int", None), ("b", "int", None)],
        )
    tool = _tool(tmp_path, db, page_limit=2)
    empty = tool("dbo.Empty")
    assert empty.get("no_indexed_columns") is True
    assert "columns" not in empty
    assert "total_count" not in empty
    past = tool("dbo.Full", offset=10)
    assert past.get("no_indexed_columns") is not True
    assert past["columns"] == []
    assert past["total_count"] == 2
    assert past["truncated"] is False


def test_non_table_payload_unchanged(tmp_path: Path) -> None:
    """AC5: a Function hit carries none of the Table column keys."""
    db = tmp_path / "graph.db"
    path = "f.php"
    target = tmp_path / path
    target.write_bytes(b"<?php function f() {}\n")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    with GraphStore(db) as store:
        store.upsert_file(path, digest, "php")
        store.replace_file_rows(
            path,
            [
                {
                    "kind": "Function",
                    "name": "f",
                    "qualified_name": "f",
                    "file_path": path,
                    "line_start": 1,
                    "line_end": 1,
                    "params": [],
                }
            ],
            [],
        )
    out = _tool(tmp_path, db)("f")
    for key in ("columns", "no_indexed_columns", "total_count", "truncated", "results_offset"):
        assert key not in out


def test_foreign_key_contains_do_not_inflate_column_paging(tmp_path: Path) -> None:
    """AC3/AC4: Table→ForeignKey CONTAINS must not inflate total_count or fake pages."""
    db = tmp_path / "graph.db"
    path = "s.sql"
    target = tmp_path / path
    target.write_bytes(b"-- planted\n")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    table = "dbo.Mixed"
    with GraphStore(db) as store:
        store.upsert_file(path, digest, "sql")
        nodes: list[dict[str, object]] = [
            {
                "kind": "Table",
                "name": "Mixed",
                "qualified_name": table,
                "file_path": path,
                "line_start": 1,
                "line_end": 1,
            },
            {
                "kind": "Column",
                "name": "id",
                "qualified_name": f"{table}::id",
                "file_path": path,
                "line_start": 1,
                "line_end": 1,
                "extra": {"type": "int", "data_type": "int"},
            },
            {
                "kind": "ForeignKey",
                "name": "FK_id_Other",
                "qualified_name": f"{table}::FK_id_Other",
                "file_path": path,
                "line_start": 1,
                "line_end": 1,
                "extra": {"parent_table": table, "referenced_table": "dbo.Other"},
            },
        ]
        edges = [
            {
                "kind": "CONTAINS",
                "source_qname": table,
                "target_raw": f"{table}::id",
                "target_qname": f"{table}::id",
                "file_path": path,
                "line": 1,
                "confidence_tier": "RESOLVED",
            },
            {
                "kind": "CONTAINS",
                "source_qname": table,
                "target_raw": f"{table}::FK_id_Other",
                "target_qname": f"{table}::FK_id_Other",
                "file_path": path,
                "line": 1,
                "confidence_tier": "RESOLVED",
            },
        ]
        store.replace_file_rows(path, nodes, edges)
    out = _tool(tmp_path, db, page_limit=50)(table)
    assert out["total_count"] == 1
    assert [c["name"] for c in out["columns"]] == ["id"]  # type: ignore[index]
    assert out["truncated"] is False
    assert "no_indexed_columns" not in out


def test_foreign_key_only_table_reports_no_indexed_columns(tmp_path: Path) -> None:
    """AC4: CONTAINS that are only ForeignKey → no_indexed_columns, not an empty page."""
    db = tmp_path / "graph.db"
    path = "fk.sql"
    target = tmp_path / path
    target.write_bytes(b"-- planted\n")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    table = "dbo.FkOnly"
    with GraphStore(db) as store:
        store.upsert_file(path, digest, "sql")
        store.replace_file_rows(
            path,
            [
                {
                    "kind": "Table",
                    "name": "FkOnly",
                    "qualified_name": table,
                    "file_path": path,
                    "line_start": 1,
                    "line_end": 1,
                },
                {
                    "kind": "ForeignKey",
                    "name": "FK_x",
                    "qualified_name": f"{table}::FK_x",
                    "file_path": path,
                    "line_start": 1,
                    "line_end": 1,
                },
            ],
            [
                {
                    "kind": "CONTAINS",
                    "source_qname": table,
                    "target_raw": f"{table}::FK_x",
                    "target_qname": f"{table}::FK_x",
                    "file_path": path,
                    "line": 1,
                    "confidence_tier": "RESOLVED",
                },
            ],
        )
    out = _tool(tmp_path, db)(table)
    assert out.get("no_indexed_columns") is True
    assert "columns" not in out


def test_tool_count_stays_at_twenty_four() -> None:
    """AC6: extending read_symbol keeps the documented tool count at 24."""
    assert len(TOOL_NAMES) == 24
    assert "read_symbol" in TOOL_NAMES
    assert "table_columns" not in TOOL_NAMES


NODE = shutil.which("node")
SQL_ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {SQL_ENTRY}")

# Deliberately not alphabetical and not reverse-alphabetical, so neither `_NODE_ORDER` nor a
# reversed scan can pass this by accident.
DDL = """\
CREATE TABLE dbo.Ledger (
    zeta int NOT NULL,
    alpha varchar(8) NULL,
    mid datetime NULL,
    beta int NULL,
    CONSTRAINT PK_Ledger PRIMARY KEY (zeta)
);
"""


@needs_node
def test_ddl_order_holds_through_a_real_index_not_only_planted_rows(tmp_path: Path) -> None:
    """AC1: the order claim is about the adapter's emission order, so prove it end to end.

    Planted rows only show that insertion order survives one batch. What the payload claims is
    that insertion order *is* the DDL's order — which lives in the `CONTAINS` edge ids and in
    `_insert` keeping every same-shaped edge in one statement. Nothing else pins that (R5.2).
    """
    (tmp_path / "db").mkdir()
    (tmp_path / "db" / "schema.sql").write_text(DDL, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(
        tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"])}
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    out = read_symbol.create(config)("dbo.Ledger")
    assert out["found"] is True
    assert [c["name"] for c in out["columns"]] == ["zeta", "alpha", "mid", "beta"]  # type: ignore[index]
    assert out["columns"][0]["type"] == "int"  # type: ignore[index]
    assert out["source"] == ""
    assert out["total_count"] == 4


def test_a_capped_contains_scan_says_so_rather_than_reading_as_the_whole_table(
    tmp_path: Path,
) -> None:
    """Review: past one CONTAINS walk both the page and `total_count` are short (R5.6)."""
    db = tmp_path / "graph.db"
    cols = [(f"c{i:02d}", "int", None) for i in range(5)]
    with GraphStore(db) as store:
        _plant_table(store, tmp_path, path="s.sql", table="dbo.Wide", columns=cols)
    with patch.object(read_symbol, "_CONTAINS_WALK", 3):
        out = _tool(tmp_path, db)("dbo.Wide")
    assert out["columns_scan_capped_to"] == 3
    assert out["total_count"] == 3
    uncapped = _tool(tmp_path, db)("dbo.Wide")
    assert "columns_scan_capped_to" not in uncapped
    assert uncapped["total_count"] == 5
