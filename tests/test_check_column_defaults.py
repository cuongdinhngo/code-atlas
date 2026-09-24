"""194: field retro round 12 §15's question, answered in one call.

    "Which writers of LedgerTrans omit ChangeUser, and what is that column's DEFAULT?"
    Answer: all 20 Insert_*_Trans* procs omit it; DEFAULT (user_name()).

The retro established that by hand with four grep passes, a purpose-built `dbsweep.php` mapping each
write to its enclosing proc, and two `sqlcmd` round-trips. Proof is integration — index, then call —
because the arithmetic is over what the resolver linked, not over what the adapter returned.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.contract import CONTRACT_VERSION
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import check_column_defaults
from code_atlas.tools.nav_result import REASON_NO_MATCHES, REASON_NO_SUCH_SYMBOL, REASON_OK

NODE = shutil.which("node")
ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")

TABLE = "dbo.LedgerTrans"
COLUMN = f"{TABLE}::ChangeUser"

SCHEMA = """\
CREATE TABLE dbo.LedgerTrans (
    TransId    int NOT NULL,
    Amount     decimal(18, 2) NOT NULL,
    ChangeUser varchar(50) NULL DEFAULT (user_name())
);
CREATE TABLE dbo.Untouched (
    Id      int NOT NULL,
    Stamped datetime2 NULL DEFAULT (sysdatetime())
);
"""

# Two omitters, one that names the column, one that names no columns at all. The fourth is the
# shape the answer turns on: it is UNMEASURED, and counting it as an omitter inflates the class.
WRITERS = """\
CREATE PROCEDURE dbo.Insert_Ledger_TransA
AS
    INSERT INTO dbo.LedgerTrans (TransId, Amount) VALUES (1, 2);
GO
CREATE PROCEDURE dbo.Insert_Ledger_TransB
AS
    INSERT dbo.LedgerTrans (TransId) VALUES (3);
GO
CREATE PROCEDURE dbo.Insert_Ledger_TransStamped
AS
    INSERT INTO dbo.LedgerTrans (TransId, ChangeUser) VALUES (4, 'x');
GO
CREATE PROCEDURE dbo.Bulk_Ledger
AS
    INSERT INTO dbo.LedgerTrans SELECT * FROM staging.Rows;
GO
"""


@pytest.fixture
def indexed(tmp_path: Path) -> Iterator[Config]:
    src = tmp_path / "db"
    src.mkdir()
    (src / "001_schema.sql").write_text(SCHEMA, encoding="utf-8")
    (src / "002_writers.sql").write_text(WRITERS, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])})
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
        assert report.parsed == 2 and report.failed == 0
    yield config


def _only(payload: dict[str, object]) -> dict[str, object]:
    results = payload["results"]
    assert isinstance(results, list) and len(results) == 1, results
    row = results[0]
    assert isinstance(row, dict)
    return row


@needs_node
def test_the_one_call_answers_round_12s_question(indexed: Config) -> None:
    """G1 / AC1 — the omitters, the total, and the DEFAULT, from a single call."""
    payload = check_column_defaults.create(indexed)(table=TABLE, column="ChangeUser")

    assert payload["reason"] == REASON_OK
    row = _only(payload)
    assert row["default"] == "(user_name())"
    assert row["omitted_by"] == ["dbo.Insert_Ledger_TransA", "dbo.Insert_Ledger_TransB"]
    assert row["named_by"] == ["dbo.Insert_Ledger_TransStamped"]
    assert (row["omitted_count"], row["writers_total"]) == (2, 4)


@needs_node
def test_a_writer_that_named_no_columns_is_unmeasured_not_an_omitter(indexed: Config) -> None:
    """R5.6 — counting it as an omitter would inflate the class by one on this fixture alone."""
    row = _only(check_column_defaults.create(indexed)(table=TABLE, column=COLUMN))

    assert row["unmeasured"] == ["dbo.Bulk_Ledger"]
    assert "dbo.Bulk_Ledger" not in row["omitted_by"]


@needs_node
def test_a_table_with_no_writers_answers_unmeasured_not_zero(indexed: Config) -> None:
    """AC2 — pinned by its own test: the absence of a claim, not a claim of absence."""
    row = _only(check_column_defaults.create(indexed)(table="dbo.Untouched"))

    assert row["status"] == check_column_defaults.STATUS_NO_WRITERS
    assert row["writers_total"] == 0
    # The keys are ABSENT, not empty: `omitted_by: []` would read as "no writer omits it".
    assert "omitted_by" not in row and "omitted_count" not in row


@needs_node
def test_the_scan_finds_the_class_without_being_told_which_column(indexed: Config) -> None:
    """AC3 — the rule flags the shape; only defaulted columns are candidates."""
    payload = check_column_defaults.create(indexed)(table=TABLE)

    assert [row["column"] for row in payload["results"]] == [COLUMN]
    assert payload["total_count"] == 1


@needs_node
def test_two_runs_over_one_index_are_identical(indexed: Config) -> None:
    """C1 / R4.2 — identical graph, identical rows, including every list's order."""
    call = check_column_defaults.create(indexed)

    assert call(table=TABLE) == call(table=TABLE)


@needs_node
def test_an_unknown_table_and_an_undefaulted_column_answer_differently(indexed: Config) -> None:
    """A table nobody indexed is not the same fact as a table with no defaulted column."""
    call = check_column_defaults.create(indexed)

    assert call(table="dbo.NoSuchTable")["reason"] == REASON_NO_SUCH_SYMBOL
    assert call(table=TABLE, column="TransId")["reason"] == REASON_NO_MATCHES


def test_the_answer_costs_no_further_contract_vocabulary() -> None:
    """AC4 — everything this reads was already spent by 022."""
    assert CONTRACT_VERSION == 11
