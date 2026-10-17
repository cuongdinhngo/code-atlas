"""Task 391 — check_column_defaults takes a DEFAULT expression as its subject."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import check_column_defaults
from code_atlas.tools.check_column_defaults import normalise_default

REPO = Path(__file__).resolve().parent.parent
SQL_ENTRY = REPO / "adapters" / "sql" / "index.js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="needs node for the SQL adapter")

SCHEMA = """CREATE TABLE dbo.Orders (Id INT NOT NULL, ChangeUser VARCHAR(50) DEFAULT (user_name()));
GO
CREATE TABLE audit.Notes (Id INT NOT NULL, ChangeUser VARCHAR(50) NULL);
GO
ALTER TABLE audit.Notes ADD CONSTRAINT DF_n DEFAULT ([USER_NAME]()) FOR ChangeUser;
GO
CREATE TABLE dbo.Stamps (Id INT NOT NULL, Created DATETIME DEFAULT (getdate()));
GO
CREATE PROCEDURE dbo.AddOrder AS
    INSERT INTO dbo.Orders (Id) VALUES (1);
GO
CREATE PROCEDURE dbo.AddNote AS
    INSERT INTO audit.Notes (Id, ChangeUser) VALUES (1, 'app');
GO
"""


def _built(root: Path) -> Config:
    (root / "db").mkdir()
    (root / "db" / "schema.sql").write_text(SCHEMA, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "init")):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=root,
            check=True,
            capture_output=True,
        )
    config = load_config(
        root,
        {"CA_WORKERS": "2", "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"])},
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    return config


@needs_node
def test_ac1_an_expression_lists_every_column_defaulting_to_it_with_omitters(
    tmp_path: Path,
) -> None:
    payload = check_column_defaults.create(_built(tmp_path))(default_expr="user_name()")
    rows = {row["column"]: row for row in payload["results"]}
    assert sorted(rows) == ["audit.Notes::ChangeUser", "dbo.Orders::ChangeUser"]
    assert rows["dbo.Orders::ChangeUser"]["table"] == "dbo.Orders"
    assert rows["dbo.Orders::ChangeUser"]["omitted_by"] == ["dbo.AddOrder"]
    assert rows["audit.Notes::ChangeUser"]["omitted_count"] == 0
    assert rows["audit.Notes::ChangeUser"]["named_by"] == ["dbo.AddNote"]
    assert payload["total_count"] == 2


@needs_node
def test_ac2_spellings_of_one_expression_match_the_same_columns(tmp_path: Path) -> None:
    tool = check_column_defaults.create(_built(tmp_path))
    columns = [
        sorted(row["column"] for row in tool(default_expr=spelling)["results"])
        for spelling in ("user_name()", "[USER_NAME]()", "user_name ( )", "(USER_NAME())")
    ]
    assert all(found == columns[0] for found in columns) and len(columns[0]) == 2


@needs_node
def test_ac3_a_table_call_is_unchanged_and_one_subject_is_required(tmp_path: Path) -> None:
    tool = check_column_defaults.create(_built(tmp_path))
    by_table = tool(table="dbo.Orders")
    assert "default_expr" not in by_table and by_table["table"] == "dbo.Orders"
    assert all("table" not in row for row in by_table["results"])
    with pytest.raises(ValueError, match="exactly one"):
        tool()
    with pytest.raises(ValueError, match="exactly one"):
        tool(table="dbo.Orders", default_expr="getdate()")
    with pytest.raises(ValueError, match="column"):
        tool(default_expr="getdate()", column="Created")
    assert tool(default_expr="newid()")["reason"] == "no_matches"


def test_a_quoted_literal_keeps_its_case_and_spaces() -> None:
    """Exposure #1 — `'N'` and `'n'` are two defaults; folding a literal would merge them."""
    assert normalise_default("('N')") != normalise_default("('n')")
    assert normalise_default("('a b')") != normalise_default("('ab')")
    assert normalise_default(" ( [User_Name] ( ) ) ") == "user_name()"
