"""215: partial writer sets say so; duplicate CONTAINS do not multiply rows; CI WRITES link."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.contract import CONTRACT_VERSION
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import check_column_defaults
from code_atlas.tools.nav_result import REASON_OK

NODE = shutil.which("node")
ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")

TABLE = "dbo.LedgerTrans"
COLUMN = f"{TABLE}::ChangeUser"


def _index(tmp_path: Path, *files: tuple[str, str]) -> Config:
    src = tmp_path / "db"
    src.mkdir()
    for name, body in files:
        (src / name).write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])})
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
    return config


SCHEMA = """\
CREATE TABLE dbo.LedgerTrans (
    TransId    int NOT NULL,
    Amount     decimal(18, 2) NOT NULL,
    ChangeUser varchar(50) NULL DEFAULT (user_name())
);
"""


@needs_node
def test_duplicate_contains_yields_one_row_and_surfaces_multiplicity(tmp_path: Path) -> None:
    """AC1 — two CONTAINS for one column → total_count 1 and declarations > 1."""
    schema_a = SCHEMA
    schema_b = """\
CREATE TABLE dbo.LedgerTrans (
    TransId    int NOT NULL,
    Amount     decimal(18, 2) NOT NULL,
    ChangeUser varchar(50) NULL DEFAULT (user_name())
);
"""
    writers = """\
CREATE PROCEDURE dbo.Insert_Ledger_TransA
AS
    INSERT INTO dbo.LedgerTrans (TransId, Amount) VALUES (1, 2);
GO
"""
    config = _index(
        tmp_path,
        ("001_schema.sql", schema_a),
        ("002_schema_again.sql", schema_b),
        ("003_writers.sql", writers),
    )
    # Two CONTAINS edges for the same column qname (one per declaring file).
    with GraphStore(config.db_path) as store:
        contains = store.edges_by_source(TABLE, kinds=("CONTAINS",), limit=50)
        change = [e for e in contains if str(e["target_raw"]) == COLUMN]
        assert len(change) >= 2, change

    payload = check_column_defaults.create(config)(table=TABLE, column="ChangeUser")
    assert payload["reason"] == REASON_OK
    assert payload["total_count"] == 1
    assert len(payload["results"]) == 1
    row = payload["results"][0]
    assert isinstance(row, dict)
    assert row["column"] == COLUMN
    assert row["declarations"] == len(change)


@needs_node
def test_complete_writer_set_carries_no_partial_marker(tmp_path: Path) -> None:
    """AC2 — every WRITES linked ⇒ no writers_partial keys."""
    writers = """\
CREATE PROCEDURE dbo.Insert_Ledger_TransA
AS
    INSERT INTO dbo.LedgerTrans (TransId, Amount) VALUES (1, 2);
GO
CREATE PROCEDURE dbo.Insert_Ledger_TransStamped
AS
    INSERT INTO dbo.LedgerTrans (TransId, ChangeUser) VALUES (4, 'x');
GO
"""
    config = _index(tmp_path, ("001_schema.sql", SCHEMA), ("002_writers.sql", writers))
    payload = check_column_defaults.create(config)(table=TABLE, column="ChangeUser")
    assert payload["reason"] == REASON_OK
    assert check_column_defaults.WRITERS_PARTIAL_KEY not in payload
    assert check_column_defaults.WRITERS_PARTIAL_HINT_KEY not in payload


@needs_node
def test_partial_writer_set_is_marked_and_names_forms(tmp_path: Path) -> None:
    """AC2/AC3 — linked writers + unlinked relating WRITES ⇒ marker + hint."""
    writers = """\
CREATE PROCEDURE dbo.Insert_Ledger_TransA
AS
    INSERT INTO dbo.LedgerTrans (TransId, Amount) VALUES (1, 2);
GO
"""
    # Twin table: unqualified INSERT cannot unique-link, so the WRITES stays bare but relates.
    twin = """\
CREATE TABLE other.LedgerTrans (
    TransId int NOT NULL,
    Amount  decimal(18, 2) NOT NULL
);
CREATE PROCEDURE dbo.Ambiguous_Write
AS
    INSERT INTO LedgerTrans (TransId, Amount) VALUES (9, 9);
GO
"""
    config = _index(
        tmp_path,
        ("001_schema.sql", SCHEMA),
        ("002_writers.sql", writers),
        ("003_twin.sql", twin),
    )
    with GraphStore(config.db_path) as store:
        assert store.has_unlinked_writes_relating_to(TABLE)

    payload = check_column_defaults.create(config)(table=TABLE, column="ChangeUser")
    assert payload["reason"] == REASON_OK
    assert payload[check_column_defaults.WRITERS_PARTIAL_KEY] is True
    hint = payload[check_column_defaults.WRITERS_PARTIAL_HINT_KEY]
    assert isinstance(hint, str)
    assert "case or schema mismatch" in hint
    assert "CREATE-inside-string" in hint


@needs_node
def test_case_mismatched_table_name_links_and_counts(tmp_path: Path) -> None:
    """AC4 — INSERT INTO Ledgertrans links onto dbo.LedgerTrans columns (Scope 4)."""
    writers = """\
CREATE PROCEDURE dbo.Insert_AB_Trans_v1
AS
    INSERT INTO Ledgertrans (TransId, Amount) VALUES (1, 2);
GO
CREATE PROCEDURE dbo.Insert_Ledger_TransStamped
AS
    INSERT INTO dbo.LedgerTrans (TransId, ChangeUser) VALUES (4, 'x');
GO
"""
    config = _index(tmp_path, ("001_schema.sql", SCHEMA), ("002_writers.sql", writers))
    with GraphStore(config.db_path) as store:
        linked = store.edges_by_target(f"{TABLE}::TransId", kinds=("WRITES",), limit=20)
        sources = {str(row["source_qname"]) for row in linked}
        assert "dbo.Insert_AB_Trans_v1" in sources
        assert all(row["target_qname"] == f"{TABLE}::TransId" for row in linked)

    payload = check_column_defaults.create(config)(table=TABLE, column="ChangeUser")
    row = payload["results"][0]
    assert isinstance(row, dict)
    assert "dbo.Insert_AB_Trans_v1" in row["omitted_by"]
    assert row["writers_total"] == 2
    assert check_column_defaults.WRITERS_PARTIAL_KEY not in payload


@needs_node
def test_update_set_on_next_line_links(tmp_path: Path) -> None:
    """AC4 — UPDATE … SET on the following line already emits; CI links the table."""
    writers = """\
CREATE PROCEDURE dbo.Insert_AA_Trans_v1
AS
    UPDATE LedgerTrans
    SET ChangeUser = 'x'
    WHERE TransId = 1;
GO
"""
    config = _index(tmp_path, ("001_schema.sql", SCHEMA), ("002_writers.sql", writers))
    with GraphStore(config.db_path) as store:
        col = store.edges_by_target(COLUMN, kinds=("WRITES",), limit=10)
        assert any(str(r["source_qname"]) == "dbo.Insert_AA_Trans_v1" for r in col)

    payload = check_column_defaults.create(config)(table=TABLE, column="ChangeUser")
    row = payload["results"][0]
    assert isinstance(row, dict)
    assert row["named_by"] == ["dbo.Insert_AA_Trans_v1"]
    assert check_column_defaults.WRITERS_PARTIAL_KEY not in payload


@needs_node
def test_table_has_no_writers_stays_unmeasured_not_zero(tmp_path: Path) -> None:
    """AC5 — empty writer set is still table_has_no_writers, never a partial zero."""
    untouched = """\
CREATE TABLE dbo.Untouched (
    Id      int NOT NULL,
    Stamped datetime2 NULL DEFAULT (sysdatetime())
);
"""
    config = _index(tmp_path, ("001_schema.sql", SCHEMA + untouched))
    row = check_column_defaults.create(config)(table="dbo.Untouched")["results"][0]
    assert isinstance(row, dict)
    assert row["status"] == check_column_defaults.STATUS_NO_WRITERS
    assert "omitted_by" not in row
    payload = check_column_defaults.create(config)(table="dbo.Untouched")
    assert check_column_defaults.WRITERS_PARTIAL_KEY not in payload


def test_contract_version_unchanged() -> None:
    """AC6 — no contract bump beyond 022's v9."""
    assert CONTRACT_VERSION == 9
