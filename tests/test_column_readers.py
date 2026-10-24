"""Task 410 — `READS` onto a `Table::Column`: who reads this column, and what could not be told."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_references

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
SQL_ENTRY = REPO / "adapters" / "sql" / "index.js"
PHP = shutil.which("php")
NODE = shutil.which("node")
needs_adapters = pytest.mark.skipif(
    PHP is None or NODE is None or not PHP_AUTOLOAD.is_file(),
    reason="needs php+composer vendor and node for the SQL adapter",
)

SCHEMA = """CREATE TABLE dbo.T (Id int, Flag bit, Other int, Name nvarchar(10));
GO
CREATE VIEW dbo.vFlags AS SELECT t.Flag, t.Id FROM dbo.T t;
GO
CREATE PROCEDURE dbo.pFlag AS
BEGIN
  SELECT Id, Name FROM dbo.T WHERE Flag = 1 AND Name <> 'Flag' ORDER BY Id;
END
GO
CREATE PROCEDURE dbo.pOther AS
  SELECT a.Other FROM dbo.T a JOIN dbo.U u ON a.Id = u.TId WHERE Flag = 0;
GO
CREATE PROCEDURE dbo.pStar AS
  SELECT * FROM dbo.T WHERE Other > 1;
GO
CREATE PROCEDURE dbo.pWrite AS
  INSERT INTO dbo.T (Flag) SELECT Flag FROM dbo.Staging;
GO
"""
PAGE = """<?php
namespace App;

class Tiles
{
    public function load($db): array
    {
        return $db->query("SELECT Flag FROM dbo.T WHERE Id = ?");
    }
}
"""


def _built(root: Path) -> Config:
    _write(root / "db" / "schema.sql", SCHEMA)
    _write(root / "src" / "Tiles.php", PAGE)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    config = load_config(
        root,
        {
            "CA_WORKERS": "2",
            "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
            "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"]),
        },
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    return config


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _readers(answer: dict[str, object]) -> dict[str, str]:
    rows = answer["results"]
    assert isinstance(rows, list)
    return {str(row["qname"]): str(row["confidence_tier"]) for row in rows}


@needs_adapters
def test_ac1_ac2_a_column_lists_the_statements_that_read_it(tmp_path: Path) -> None:
    answer = find_references.create(_built(tmp_path))("dbo.T::Flag", kinds=["READS"])
    readers = _readers(answer)
    assert readers == {
        "dbo.vFlags": "RESOLVED",
        "dbo.pFlag": "RESOLVED",
        "\\App\\Tiles::load": "HEURISTIC",
    }, answer
    assert "kinds_ignored" not in answer
    # `pOther` names `Flag` bare beside two sources: not attributed (W2), nor counted unknown,
    # since the statement named other columns of the table.
    assert "dbo.pOther" not in readers


@needs_adapters
def test_ac3_select_star_is_counted_not_listed(tmp_path: Path) -> None:
    answer = find_references.create(_built(tmp_path))("dbo.T::Other", kinds=["READS"])
    assert set(_readers(answer)) == {"dbo.pOther"}
    assert answer["column_reads_unknown"] == 1  # `pStar`: `select *` names no column


@needs_adapters
def test_ac4_the_table_answer_folds_columns_into_one_row_per_statement(tmp_path: Path) -> None:
    answer = find_references.create(_built(tmp_path))("dbo.T", kinds=["READS"])
    rows = answer["results"]
    assert isinstance(rows, list)
    by_reader = {str(row["qname"]): row for row in rows}
    assert set(by_reader) == {
        "dbo.vFlags", "dbo.pFlag", "dbo.pOther", "dbo.pStar", "\\App\\Tiles::load"
    }
    assert answer["total_count"] == len(rows) == 5
    assert sorted(by_reader["dbo.vFlags"]["columns"]) == ["Flag", "Id"]
    assert "columns" not in by_reader["dbo.pStar"]


@needs_adapters
def test_a_written_table_and_a_string_literal_are_not_read_columns(tmp_path: Path) -> None:
    config = _built(tmp_path)
    flag = find_references.create(config)("dbo.T::Flag", kinds=["READS"])
    # `INSERT INTO dbo.T (Flag) SELECT Flag FROM dbo.Staging` reads Staging, not T's Flag;
    # `Name <> 'Flag'` compares to a literal.
    assert "dbo.pWrite" not in _readers(flag)
    name = find_references.create(config)("dbo.T::Name", kinds=["READS"])
    assert set(_readers(name)) == {"dbo.pFlag"}


@needs_adapters
def test_the_default_column_answer_is_still_its_writers(tmp_path: Path) -> None:
    answer = find_references.create(_built(tmp_path))("dbo.T::Flag")
    assert set(_readers(answer)) == {"dbo.pWrite"}
    assert "column_reads_unknown" not in answer


@needs_adapters
def test_review_names_a_keyword_list_would_drop_and_aliases_it_would_misread(
    tmp_path: Path,
) -> None:
    """410 review (challenger F1, F2, F5, F8): bind by place, never guess across scopes."""
    body = """CREATE PROCEDURE dbo.pDates AS
  SELECT Year, Path FROM dbo.S WHERE Day = 1 AND Rows > 2;
GO
CREATE PROCEDURE dbo.pReused AS
  SELECT a.Id FROM dbo.T a WHERE EXISTS (SELECT 1 FROM dbo.U a WHERE a.Flag = 1);
GO
CREATE PROCEDURE dbo.pAliases AS
  SELECT ROW_NUMBER() OVER (ORDER BY Id) rn, Other g, 1.5e3 FROM dbo.T;
GO
CREATE TRIGGER dbo.trT ON dbo.T AFTER UPDATE AS
  SELECT Name FROM inserted i JOIN dbo.T t ON t.Id = i.Id;
GO
CREATE PROCEDURE dbo.pSelf AS
  SELECT Status FROM dbo.Status WHERE DATEDIFF(day, Created, GETDATE()) > 1;
GO
"""
    _write(tmp_path / "db" / "more.sql", body)
    done = subprocess.run(
        [str(NODE), str(SQL_ENTRY), "--file", "db/more.sql"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    import json

    reads = {
        (edge["source_qname"], edge["target_raw"])
        for edge in json.loads(done.stdout)["edges"]
        if edge["kind"] == "READS" and "::" in edge["target_raw"]
    }
    assert reads == {
        ("dbo.pDates", "dbo.S::Year"),
        ("dbo.pDates", "dbo.S::Path"),
        ("dbo.pDates", "dbo.S::Day"),
        ("dbo.pDates", "dbo.S::Rows"),
        # `a` names two sources, so neither binds: no false RESOLVED `U::Id`.
        ("dbo.pAliases", "dbo.T::Id"),
        ("dbo.pAliases", "dbo.T::Other"),
        # `inserted` is a second item, so the trigger's bare `Name` binds to neither.
        ("dbo.trT", "dbo.T::Id"),
        ("dbo.pSelf", "dbo.Status::Status"),
        ("dbo.pSelf", "dbo.Status::Created"),
    }, reads
