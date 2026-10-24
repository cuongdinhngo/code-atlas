"""Task 402 — a T-SQL view is a ``View`` node: found, read, a reader of its tables, and altered.

On ``main`` no node stood for ``CREATE VIEW``: its reads were the file's (390) and a question about
what filters a view, or which migration redefines it, went to the live DB or ``git grep``.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_references, read_symbol, search_symbol

REPO = Path(__file__).resolve().parent.parent
SQL_ENTRY = REPO / "adapters" / "sql" / "index.js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="needs node (SQL adapter)")

SCHEMA = """CREATE TABLE dbo.Orders (Id INT NOT NULL, Active BIT NULL);
GO
CREATE VIEW dbo.ActiveOrders
AS
SELECT Id
  FROM dbo.Orders
 WHERE Active = 1;
GO
CREATE VIEW dbo.Recent
AS
WITH c AS (
    SELECT Id FROM dbo.Orders
)
SELECT Id FROM c;
GO
CREATE TABLE dbo.Cust (Id INT NOT NULL);
GO
CREATE VIEW dbo.Labelled WITH SCHEMABINDING AS
SELECT CASE WHEN o.Active = 1 THEN 'x'
            ELSE 'y'
       END AS k
  FROM dbo.Orders o
  JOIN dbo.Cust c ON c.Id = o.Id;
GO
CREATE PROCEDURE dbo.Archive AS
    INSERT INTO dbo.activeorders SELECT Id FROM dbo.Orders;
GO
"""
# Two Flyway-style migrations redefine one view; neither is its first CREATE.
V1 = "CREATE OR ALTER VIEW dbo.OpenOrders AS SELECT Id FROM dbo.Orders WHERE Active = 1\nGO\n"
V7 = "ALTER VIEW dbo.OpenOrders\nAS\nSELECT Id FROM dbo.Orders WHERE Active = 0\nGO\n"


def _built(root: Path) -> Config:
    migrations = root / "db" / "migration"
    migrations.mkdir(parents=True)
    (root / "db" / "schema.sql").write_text(SCHEMA, encoding="utf-8")
    (migrations / "V1__open_orders.sql").write_text(V1, encoding="utf-8")
    (migrations / "V7__open_orders.sql").write_text(V7, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "init")):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=root,
            check=True,
            capture_output=True,
        )
    config = load_config(
        root,
        {"CA_WORKERS": "1", "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"])},
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    return config


@needs_node
def test_ac1_a_view_is_found_and_read(tmp_path: Path) -> None:
    config = _built(tmp_path)
    found = search_symbol.create(config)("ActiveOrders")
    top = found["results"][0]  # type: ignore[index]
    assert (top["qname"], top["kind"]) == ("dbo.ActiveOrders", "View"), found

    read = read_symbol.create(config)("dbo.ActiveOrders")
    assert read["reason"] == "ok", read
    assert "WHERE Active = 1" in str(read["source"]), "the predicate is the answer"


@needs_node
def test_ac2_a_table_lists_the_view_among_its_readers(tmp_path: Path) -> None:
    config = _built(tmp_path)
    payload = find_references.create(config)("dbo.Orders", kinds=["READS"])
    readers = {str(row["qname"]) for row in payload["results"]}  # type: ignore[union-attr]
    assert {"dbo.ActiveOrders", "dbo.OpenOrders"} <= readers, payload
    assert "db/schema.sql" not in readers, "the view reads, never the file (390's stand-in)"


@needs_node
def test_ac3_both_redefining_migrations_are_in_altered_by(tmp_path: Path) -> None:
    config = _built(tmp_path)
    found = search_symbol.create(config)("OpenOrders", kind="View")
    hits = found["results"]
    files = {str(hit["file"]) for hit in hits}  # type: ignore[union-attr]
    assert files == {"db/migration/V1__open_orders.sql", "db/migration/V7__open_orders.sql"}
    for hit in hits:  # type: ignore[union-attr]
        assert {str(row["file"]) for row in hit["altered_by"]} == files, hit


@needs_node
def test_a_cte_inside_a_view_is_never_read_as_a_table(tmp_path: Path) -> None:
    """The challenger's I1: the CTE closes its paren mid-body, and its name is not a source."""
    config = _built(tmp_path)
    with GraphStore(config.db_path) as store:
        reads = store.edges_by_source("dbo.Recent", kinds=("READS",), limit=10)
    assert {str(edge["target_raw"]) for edge in reads} == {"dbo.Orders"}


@needs_node
def test_a_line_leading_end_never_cuts_a_view_s_reads(tmp_path: Path) -> None:
    """Review of 402: a multi-line CASE's `END` at depth 0 flushed the body before its FROM."""
    config = _built(tmp_path)
    with GraphStore(config.db_path) as store:
        reads = store.edges_by_source("dbo.Labelled", kinds=("READS",), limit=10)
    tables = {str(edge["target_raw"]) for edge in reads if "::" not in str(edge["target_raw"])}
    assert tables == {"dbo.Orders", "dbo.Cust"}  # 410's column reads ride beside them


@needs_node
def test_a_case_mismatched_write_through_a_view_links_to_it(tmp_path: Path) -> None:
    """The challenger's I2: T-SQL's case-insensitive rule (215) reaches a View as a Table."""
    config = _built(tmp_path)
    with GraphStore(config.db_path) as store:
        writes = store.edges_by_target("dbo.ActiveOrders", kinds=("WRITES",), limit=10)
    assert [str(edge["source_qname"]) for edge in writes] == ["dbo.Archive"]
