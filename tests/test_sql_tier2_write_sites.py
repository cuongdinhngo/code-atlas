"""022 G1: field retro round 12 §15's question, answered from the graph in one pass.

    "Which writers of LedgerTrans omit ChangeUser, and what is that column's DEFAULT?"
    Answer: all 20 Insert_*_Trans* procs omit it; DEFAULT (user_name()).

The retro needed four grep passes, a purpose-built `dbsweep.php` mapping each write to its enclosing
proc, and two `sqlcmd` round-trips to establish that. The proof is integration — adapter through
the resolver to the store — because a write site that never links is the failure mode that matters,
and a unit test over the scanner's return value cannot see it. Ticket 194 builds the tool; this
pins that the graph carries the facts it will read.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore

NODE = shutil.which("node")
ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")

TABLE = "dbo.LedgerTrans"
COLUMN = f"{TABLE}::ChangeUser"

SCHEMA = """\
CREATE TABLE dbo.LedgerTrans (
    TransId    int NOT NULL,
    MemberId int NOT NULL,
    Amount     decimal(18, 2) NOT NULL,
    ChangeUser varchar(50) NULL DEFAULT (user_name()),
    CONSTRAINT PK_LedgerTrans PRIMARY KEY (TransId)
);
"""

# Three shapes on purpose: two writers that omit the column, one that names it, and one that names
# no columns at all — the last is *unmeasured*, not an omitter, and the proof turns on that.
WRITERS = """\
CREATE PROCEDURE dbo.Insert_Ledger_TransA
AS
    INSERT INTO dbo.LedgerTrans (TransId, MemberId, Amount) VALUES (1, 2, 3);
GO
CREATE PROCEDURE dbo.Insert_Ledger_TransB
AS
    INSERT dbo.LedgerTrans (TransId, Amount) VALUES (4, 5);
GO
CREATE PROCEDURE dbo.Insert_Ledger_TransStamped
AS
    INSERT INTO dbo.LedgerTrans (TransId, ChangeUser) VALUES (6, 'x');
GO
CREATE PROCEDURE dbo.Bulk_Ledger
AS
    INSERT INTO dbo.LedgerTrans SELECT * FROM staging.Rows;
GO
"""


@pytest.fixture
def indexed(tmp_path: Path) -> Iterator[tuple[GraphStore, Path]]:
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
        yield store, tmp_path


def _write_sites(store: GraphStore, table: str) -> dict[str, set[str]]:
    """Every routine writing `table`, mapped to the columns it NAMED — empty means it named none.

    This is the shape 194 will query: the target kind is the discriminator, so a writer reaches
    this map through the table itself (named no columns) or through each column it named.
    """
    sites: dict[str, set[str]] = {}
    for row in store.edges_by_target(table, kinds=("WRITES",), limit=200):
        sites.setdefault(str(row["source_qname"]), set())
    for contained in store.edges_by_source(table, kinds=("CONTAINS",), limit=200):
        column = str(contained["target_raw"])
        for row in store.edges_by_target(column, kinds=("WRITES",), limit=200):
            sites.setdefault(str(row["source_qname"]), set()).add(column)
    return sites


@needs_node
def test_the_column_carries_its_declared_default(indexed) -> None:
    """AC1's second half: the DEFAULT expression is a graph fact, not a second sqlcmd round-trip."""
    store, _ = indexed
    rows = store.nodes_by_qualified_name(COLUMN, kind="Column", limit=2)

    assert len(rows) == 1
    extra = json.loads(str(rows[0]["extra"]))
    assert extra["default"] == "(user_name())"
    assert extra["data_type"] == "varchar(50)"


@needs_node
def test_writers_omitting_a_defaulted_column_are_derivable(indexed) -> None:
    """G1 — the retro's question, in one pass over the graph."""
    store, _ = indexed
    sites = _write_sites(store, TABLE)

    named = {source for source, cols in sites.items() if COLUMN in cols}
    omitted = {source for source, cols in sites.items() if cols and COLUMN not in cols}

    assert named == {"dbo.Insert_Ledger_TransStamped"}
    assert omitted == {"dbo.Insert_Ledger_TransA", "dbo.Insert_Ledger_TransB"}


@needs_node
def test_a_writer_that_names_no_columns_is_unmeasured_not_an_omitter(indexed) -> None:
    """AC6 / R5.6 — the shape that would otherwise inflate the omitters by one."""
    store, _ = indexed

    sites = _write_sites(store, TABLE)

    assert {source for source, cols in sites.items() if not cols} == {"dbo.Bulk_Ledger"}
    # It is a writer, so it must not vanish from the total either.
    assert set(sites) == {
        "dbo.Insert_Ledger_TransA", "dbo.Insert_Ledger_TransB",
        "dbo.Insert_Ledger_TransStamped", "dbo.Bulk_Ledger",
    }


@needs_node
def test_the_write_edges_resolve_onto_the_column_they_name(indexed) -> None:
    """The edge is linked, not left bare: a write site that never links answers nothing (H7)."""
    store, _ = indexed
    rows = store.edges_by_target(COLUMN, kinds=("WRITES",), limit=10)

    assert rows and all(row["target_qname"] == COLUMN for row in rows)
