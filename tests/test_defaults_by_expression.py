"""Task 391 — check_column_defaults takes a DEFAULT expression as its subject."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

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


@needs_node
def test_an_expression_answer_pages(tmp_path: Path) -> None:
    """Scope 2 — paged like the other tools: limit/offset over the matched columns."""
    tool = check_column_defaults.create(_built(tmp_path))
    first = tool(default_expr="user_name()", limit=1)
    second = tool(default_expr="user_name()", limit=1, offset=1)
    assert first["total_count"] == second["total_count"] == 2
    assert first["truncated"] is True and second["truncated"] is False
    assert first["results"][0]["column"] != second["results"][0]["column"]
    with pytest.raises(ValueError, match="blank"):
        tool(default_expr="  ")


def test_a_parenthesis_inside_a_literal_does_not_block_stripping() -> None:
    assert normalise_default("('(')") == "'('"


def _expr_tool(root: Path, extra: dict[str, str]) -> Callable[..., dict[str, Any]]:
    for name, text in extra.items():
        (root / name).write_text(text, encoding="utf-8")
    return check_column_defaults.create(_built(root))


@needs_node
def test_a_column_declared_in_two_files_is_one_row_and_not_unowned(tmp_path: Path) -> None:
    """Review — two Column nodes for one qname must not double-append nor count as tableless."""
    again = "CREATE TABLE dbo.Orders (Id INT, ChangeUser VARCHAR(50) DEFAULT (user_name()));\n"
    payload = _expr_tool(tmp_path, {"again.sql": again})(default_expr="user_name()")
    columns = [row["column"] for row in payload["results"]]
    assert columns.count("dbo.Orders::ChangeUser") == 1
    assert "columns_without_table" not in payload


@needs_node
def test_a_default_added_only_by_alter_is_reported_with_that_default(tmp_path: Path) -> None:
    """Review — CREATE without DEFAULT, then ALTER ... DEFAULT FOR in another file."""
    alter = "ALTER TABLE dbo.Stamps ADD CONSTRAINT DF_s DEFAULT (user_name()) FOR Id;\n"
    payload = _expr_tool(tmp_path, {"zz.sql": alter})(default_expr="user_name()")
    rows = {row["column"]: row for row in payload["results"]}
    assert rows["dbo.Stamps::Id"]["default"] == "(user_name())"
    assert "columns_without_table" not in payload


@needs_node
def test_the_scan_cap_is_silent_on_an_exact_fit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _built(tmp_path)
    with GraphStore(config.db_path) as store:
        total = len(store.nodes_by_kind("Column", limit=1_000))
    tool = check_column_defaults.create(config)
    monkeypatch.setattr(check_column_defaults, "_COLUMN_SCAN", total)
    assert "columns_scan_capped" not in tool(default_expr="user_name()")
    monkeypatch.setattr(check_column_defaults, "_COLUMN_SCAN", total - 1)
    assert tool(default_expr="user_name()")["columns_scan_capped"] == total - 1


def test_empty_parentheses_are_blank_and_unbuilt_echoes_the_normalised_form(
    tmp_path: Path,
) -> None:
    tool = check_column_defaults.create(load_config(tmp_path, {}))
    with pytest.raises(ValueError, match="blank"):
        tool(default_expr="()")
    unbuilt = tool(default_expr="(USER_NAME())")
    assert unbuilt["reason"] == "not_indexed"
    assert unbuilt["default_expr_normalised"] == "user_name()"
