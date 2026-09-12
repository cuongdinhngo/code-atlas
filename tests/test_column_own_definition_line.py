"""254 — each Column of a multi-line CREATE TABLE points at its own definition line."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol

NODE = shutil.which("node")
ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")


def _index(tmp_path: Path, files: dict[str, str]) -> GraphStore:
    src = tmp_path / "db"
    src.mkdir(exist_ok=True)
    for name, body in files.items():
        (src / name).write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])})
    store = GraphStore(config.db_path)
    report = full_build(config, store)
    assert report.failed == 0
    return store


def _lines(store: GraphStore) -> dict[str, int]:
    return {
        str(row["name"]): int(row["line_start"])
        for row in store.nodes_by_kind("Column", limit=50)
    }


@needs_node
def test_multiline_create_columns_get_own_lines(tmp_path: Path) -> None:
    """AC1: each column reports the line its definition begins on."""
    store = _index(
        tmp_path,
        {
            "t.sql": """\
CREATE TABLE dbo.T (
  a int,
  b int,
  c int
);
"""
        },
    )
    try:
        assert _lines(store) == {"a": 2, "b": 3, "c": 4}
    finally:
        store.close()


@needs_node
def test_multiline_create_paren_on_own_line(tmp_path: Path) -> None:
    """AC1 sibling: `(` after CREATE must not off-by-one the column lines (challenger 254)."""
    store = _index(
        tmp_path,
        {
            "t.sql": """\
CREATE TABLE dbo.T2
(
  x int,
  y int
);
"""
        },
    )
    try:
        assert _lines(store) == {"x": 3, "y": 4}
    finally:
        store.close()


@needs_node
def test_multiline_create_blank_line_inside_body(tmp_path: Path) -> None:
    """AC1 sibling: blank lines inside CREATE must not collapse column line_start."""
    store = _index(
        tmp_path,
        {
            "t.sql": """\
CREATE TABLE dbo.T3 (
  a int,

  b int
);
"""
        },
    )
    try:
        assert _lines(store) == {"a": 2, "b": 4}
    finally:
        store.close()


@needs_node
def test_single_line_create_keeps_create_line_for_all_columns(tmp_path: Path) -> None:
    """AC2: CREATE TABLE (a int, b int) — both columns share the CREATE line."""
    store = _index(tmp_path, {"t.sql": "CREATE TABLE dbo.T (a int, b int);\n"})
    try:
        lines = _lines(store)
        assert set(lines) == {"a", "b"}
        assert lines["a"] == lines["b"] == 1
    finally:
        store.close()


@needs_node
def test_alter_add_column_keeps_alter_line(tmp_path: Path) -> None:
    """AC3: ALTER TABLE … ADD keeps that statement's line."""
    store = _index(
        tmp_path,
        {
            "t.sql": """\
CREATE TABLE dbo.T (
  a int
);
ALTER TABLE dbo.T ADD b int;
"""
        },
    )
    try:
        lines = _lines(store)
        assert lines["a"] == 2
        assert lines["b"] == 4
    finally:
        store.close()


@needs_node
def test_read_symbol_on_column_returns_column_definition(tmp_path: Path) -> None:
    """AC4: read_symbol on a column returns that column's definition, not the CREATE header."""
    store = _index(
        tmp_path,
        {
            "t.sql": """\
CREATE TABLE dbo.T (
  a int,
  long_name_column varchar(50)
);
"""
        },
    )
    try:
        config = load_config(
            tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])}
        )
        payload = read_symbol.create(config)("dbo.T::long_name_column", detail_level="standard")
        assert payload["found"] is True
        assert payload["line_start"] == 3
        source = str(payload.get("source") or "")
        assert "long_name_column" in source
        first = source.strip().splitlines()[0] if source.strip() else ""
        assert "CREATE TABLE" not in first
        assert "long_name_column" in first
    finally:
        store.close()
