"""Task 329 — Table find_references pages writing statements, not per-column edges."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from code_atlas.store import COVERED_LANGUAGES_KEY, EMITTED_KINDS_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import find_references
from code_atlas.tools.nav_result import REASON_OK
from tests.test_nav_tools import db_config, edge, node
from tests.test_nav_tools import store as store  # noqa: F401

TABLE = "dbo.Orders"
COL_A = "dbo.Orders::A"
COL_B = "dbo.Orders::B"
COL_C = "dbo.Orders::C"
COL_D = "dbo.Orders::D"
COL_E = "dbo.Orders::E"
INS1 = "dbo.usp_Ins1"
INS2 = "dbo.usp_Ins2"
INS3 = "dbo.usp_Ins3"


def _seed(graph: GraphStore, root: Path, path: str, nodes: list, edges: list) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    body = b"# planted\n"
    target.write_bytes(body)
    graph.upsert_file(path, hashlib.sha256(body).hexdigest(), "sql")
    graph.replace_file_rows(path, nodes, edges)


def _stamp(graph: GraphStore) -> None:
    graph.set_meta(COVERED_LANGUAGES_KEY, "sql")
    graph.set_meta(
        EMITTED_KINDS_BY_LANGUAGE_KEY,
        json.dumps({"sql": ["WRITES"]}, sort_keys=True),
    )


def _multi_column_fixture(graph: GraphStore, root: Path) -> None:
    """Two INSERTs (3 + 2 cols) + one column-less table write → 3 statements / 6 edges."""
    cols = [
        node("Column", name, qn, "schema.sql")
        for name, qn in (
            ("A", COL_A),
            ("B", COL_B),
            ("C", COL_C),
            ("D", COL_D),
            ("E", COL_E),
        )
    ]
    _seed(
        graph,
        root,
        "schema.sql",
        [
            node("Table", "Orders", TABLE, "schema.sql"),
            *cols,
            node("Function", "usp_Ins1", INS1, "schema.sql"),
            node("Function", "usp_Ins2", INS2, "schema.sql"),
            node("Function", "usp_Ins3", INS3, "schema.sql"),
        ],
        [
            edge("CONTAINS", TABLE, COL_A, "schema.sql", target_qname=COL_A),
            edge("CONTAINS", TABLE, COL_B, "schema.sql", target_qname=COL_B),
            edge("CONTAINS", TABLE, COL_C, "schema.sql", target_qname=COL_C),
            edge("CONTAINS", TABLE, COL_D, "schema.sql", target_qname=COL_D),
            edge("CONTAINS", TABLE, COL_E, "schema.sql", target_qname=COL_E),
            # INSERT 1 naming A,B,C at line 10
            edge("WRITES", INS1, COL_A, "writers.sql", target_qname=COL_A, line=10),
            edge("WRITES", INS1, COL_B, "writers.sql", target_qname=COL_B, line=10),
            edge("WRITES", INS1, COL_C, "writers.sql", target_qname=COL_C, line=10),
            # INSERT 2 naming D,E at line 20
            edge("WRITES", INS2, COL_D, "writers.sql", target_qname=COL_D, line=20),
            edge("WRITES", INS2, COL_E, "writers.sql", target_qname=COL_E, line=20),
            # column-less write at line 30
            edge("WRITES", INS3, TABLE, "writers.sql", target_qname=TABLE, line=30),
        ],
    )
    _stamp(graph)


def test_table_groups_writes_by_statement(tmp_path: Path, store: GraphStore) -> None:
    """AC1: two INSERTs + one column-less write → 3 rows, not 6."""
    _multi_column_fixture(store, tmp_path)
    payload = find_references.create(db_config(tmp_path))(TABLE)
    assert payload["reason"] == REASON_OK
    assert payload["total_count"] == 3
    assert len(payload["results"]) == 3  # type: ignore[arg-type]
    by_q = {str(h["qname"]): h for h in payload["results"]}  # type: ignore[union-attr]
    assert by_q[INS1]["columns"] == ["A", "B", "C"]
    assert by_q[INS2]["columns"] == ["D", "E"]
    assert "columns" not in by_q[INS3]


def test_table_paging_walks_statements(tmp_path: Path, store: GraphStore) -> None:
    """AC2: total_count is 3; limit=2 returns 2 statements and truncated."""
    _multi_column_fixture(store, tmp_path)
    payload = find_references.create(db_config(tmp_path))(TABLE, limit=2)
    assert payload["total_count"] == 3
    assert len(payload["results"]) == 2  # type: ignore[arg-type]
    assert payload["truncated"] is True


def test_column_subject_is_byte_identical(tmp_path: Path, store: GraphStore) -> None:
    """AC3: find_references on a Column is unchanged (per-edge, no columns fold)."""
    _multi_column_fixture(store, tmp_path)
    payload = find_references.create(db_config(tmp_path))(COL_A)
    assert payload["total_count"] == 1
    assert len(payload["results"]) == 1  # type: ignore[arg-type]
    hit = payload["results"][0]  # type: ignore[index]
    assert hit["qname"] == INS1
    assert "columns" not in hit
