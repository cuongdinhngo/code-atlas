"""392 — a bare table or procedure name answers as its qualified name does, or is refused with each.

The field typed `RefType`: a table, and a column of the same name on another table, so the
suffix match counted two and answered `name_not_qualified`.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references, impact
from code_atlas.tools.nav_result import REASON_SUBJECT_AMBIGUOUS

NODE = shutil.which("node")
ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
pytestmark = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")

SCHEMA = """\
CREATE TABLE dbo.Items (Id int NOT NULL);
CREATE TABLE dbo.Orders (Id int NOT NULL, Items int NULL);
CREATE TABLE dbo.Shared (Id int NOT NULL);
CREATE TABLE audit.Shared (Id int NOT NULL);
"""
ROUTINES = """\
CREATE PROCEDURE dbo.Add_Item
AS
    INSERT INTO dbo.Items (Id) VALUES (1);
GO
CREATE PROCEDURE dbo.Run_Add
AS
    EXEC dbo.Add_Item;
GO
CREATE TABLE dbo.Orders2 (Id int NOT NULL, Add_Item int NULL);
"""


@pytest.fixture
def config(tmp_path: Path) -> Config:
    (tmp_path / "db").mkdir()
    (tmp_path / "db" / "schema.sql").write_text(SCHEMA, encoding="utf-8")
    (tmp_path / "db" / "routines.sql").write_text(ROUTINES, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A")):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    built = load_config(tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])})
    with GraphStore(built.db_path) as store:
        assert full_build(built, store).failed == 0
    return built


def _rows(payload: dict[str, object]) -> str:
    return json.dumps(payload["results"], sort_keys=True)


def test_ac1_a_bare_table_answers_as_its_qualified_name(config: Config) -> None:
    refs = find_references.create(config)
    bare, exact = refs("Items"), refs("dbo.Items")
    assert bare["reason"] == exact["reason"] == "ok", bare
    assert _rows(bare) == _rows(exact) != "[]"
    assert bare["resolved_from"] == "bare"
    assert "resolved_from" not in exact


def test_a_bare_procedure_answers_find_callers_and_impact(config: Config) -> None:
    callers = find_callers.create(config)("Add_Item", detail_level="minimal")
    assert callers["resolved_from"] == "bare", callers
    rows = callers["results"]
    assert isinstance(rows, list)
    assert [row["qname"] for row in rows] == ["dbo.Run_Add"]
    radius = impact.create(config)(qnames=["Items"], detail_level="minimal")
    assert radius["resolved_from"] == "bare", radius
    exact = impact.create(config)(qnames=["dbo.Items"], detail_level="minimal")
    assert {**radius, "qname": exact["qname"]} == {**exact, "resolved_from": "bare"}


def test_ac2_two_schemas_refuse_with_both(config: Config) -> None:
    payload = find_references.create(config)("Shared")
    assert payload["reason"] == REASON_SUBJECT_AMBIGUOUS, payload
    sites = payload["ambiguous_definitions"]
    assert isinstance(sites, list)
    assert sorted(str(site["qname"]) for site in sites) == ["audit.Shared", "dbo.Shared"]
