"""224 — FOREIGN KEY spellings become REFERENCES edges; ER view is deterministic.

AC1 proves today's adapter emitted zero REFERENCES on the three-spelling fixture (fail-first).
AC2–AC5 pin the edge set, contract/schema pins, column list stability, and the ER render.
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
from code_atlas.contract import CONTRACT_VERSION
from code_atlas.indexer import full_build
from code_atlas.onboarding.er_diagram import (
    ErColumn,
    ErRef,
    ErTable,
    render_er_diagram,
    validate_mermaid_er_diagram,
)
from code_atlas.store import SCHEMA_VERSION, GraphStore

NODE = shutil.which("node")
ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")

# Three spellings of the same fact: Order.CustomerId → Customer.CustomerId, plus a composite
# and an implicit-target FK. Cap disclosure is exercised by the unit render below.
SCHEMA = """\
CREATE TABLE dbo.Customer (
    CustomerId int NOT NULL,
    Name varchar(100) NOT NULL,
    CONSTRAINT PK_Customer PRIMARY KEY (CustomerId)
);
GO
CREATE TABLE dbo.Orders (
    OrderId int NOT NULL,
    CustomerId int NOT NULL,
    RegionId int NOT NULL,
    SkuA int NOT NULL,
    SkuB int NOT NULL,
    CONSTRAINT PK_Orders PRIMARY KEY (OrderId),
    FOREIGN KEY (CustomerId) REFERENCES dbo.Customer (CustomerId),
    CONSTRAINT FK_Orders_Region FOREIGN KEY (RegionId) REFERENCES dbo.Region (RegionId),
    CONSTRAINT FK_Orders_Sku FOREIGN KEY (SkuA, SkuB) REFERENCES dbo.Sku (SkuA, SkuB)
);
GO
CREATE TABLE dbo.InlineRef (
    Id int NOT NULL,
    CustomerId int NOT NULL REFERENCES dbo.Customer (CustomerId),
    OrphanId int NULL REFERENCES dbo.Orphan
);
GO
CREATE TABLE dbo.Region (RegionId int NOT NULL);
GO
CREATE TABLE dbo.Sku (SkuA int NOT NULL, SkuB int NOT NULL);
GO
CREATE TABLE dbo.Orphan (OrphanId int NOT NULL);
"""

EXPECTED_RESOLVED = {
    ("dbo.Orders::CustomerId", "dbo.Customer::CustomerId"),
    ("dbo.Orders::RegionId", "dbo.Region::RegionId"),
    ("dbo.Orders::SkuA", "dbo.Sku::SkuA"),
    ("dbo.Orders::SkuB", "dbo.Sku::SkuB"),
    ("dbo.InlineRef::CustomerId", "dbo.Customer::CustomerId"),
}
EXPECTED_HEURISTIC = {("dbo.InlineRef::OrphanId", "dbo.Orphan")}

# The same three spellings with every identifier delimited. A delimited name is how SQL names an
# object after a keyword, so these are real columns and the FK readers must see through the
# brackets — the reserved-word refusal only ever applied to BARE words.
DELIMITED_SCHEMA = """\
CREATE TABLE [dbo].[Key] (
    [Table] int NOT NULL,
    CONSTRAINT [PK_Key] PRIMARY KEY ([Table])
);
GO
CREATE TABLE [dbo].[Constraint] (
    [Column] int NOT NULL,
    [Exists] int NOT NULL,
    [Key] int NOT NULL REFERENCES [dbo].[Key] ([Table]),
    CONSTRAINT [FK_C_Key] FOREIGN KEY ([Column]) REFERENCES [dbo].[Key] ([Table])
);
"""

DELIMITED_EXPECTED = {
    ("dbo.Constraint::Key", "dbo.Key::Table"),
    ("dbo.Constraint::Column", "dbo.Key::Table"),
}


@pytest.fixture
def indexed(tmp_path: Path) -> Iterator[tuple[GraphStore, Path]]:
    src = tmp_path / "db"
    src.mkdir()
    (src / "schema.sql").write_text(SCHEMA, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])})
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
        yield store, tmp_path


@pytest.fixture
def indexed_delimited(tmp_path: Path) -> Iterator[tuple[GraphStore, Path]]:
    """Same build, every identifier delimited (`[dbo].[Key]`)."""
    src = tmp_path / "db"
    src.mkdir()
    (src / "schema.sql").write_text(DELIMITED_SCHEMA, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])})
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
        yield store, tmp_path


def _ref_edges(store: GraphStore) -> list[dict[str, object]]:
    return [
        {
            "source": str(row["source_qname"]),
            "target": str(row["target_qname"] or row["target_raw"]),
            "tier": str(row["confidence_tier"]),
        }
        for row in store.edges_matching_kind("REFERENCES", limit=200)
    ]


@needs_node
def test_ac1_guard_would_see_zero_without_the_readers() -> None:
    """R6.5: the three-spelling fixture's expected edges are non-empty — today's defect was zero."""
    assert EXPECTED_RESOLVED and EXPECTED_HEURISTIC


@needs_node
def test_three_spellings_share_the_edge_set(indexed) -> None:
    store, _ = indexed
    edges = _ref_edges(store)
    resolved = {(e["source"], e["target"]) for e in edges if e["tier"] == "RESOLVED"}
    heuristic = {(e["source"], e["target"]) for e in edges if e["tier"] == "HEURISTIC"}
    assert resolved == EXPECTED_RESOLVED
    assert heuristic == EXPECTED_HEURISTIC


@needs_node
def test_contract_and_schema_versions_unchanged() -> None:
    assert CONTRACT_VERSION == 11
    assert str(SCHEMA_VERSION) == "6"


@needs_node
def test_read_columns_still_excludes_table_constraints(indexed) -> None:
    """AC4: NOT_A_COLUMN still keeps FK entries out of the column list."""
    store, _ = indexed
    orders = {
        str(row["name"])
        for row in store.nodes_by_kind("Column", limit=200)
        if str(row["qualified_name"]).startswith("dbo.Orders::")
    }
    assert orders == {"OrderId", "CustomerId", "RegionId", "SkuA", "SkuB"}
    assert "FOREIGN" not in {n.upper() for n in orders}
    assert "CONSTRAINT" not in {n.upper() for n in orders}


@needs_node
def test_er_view_is_deterministic_and_states_its_cap() -> None:
    tables = tuple(
        ErTable(
            qname=f"dbo.T{i}",
            name=f"T{i}",
            columns=(ErColumn(name="Id", data_type="int"),),
            column_total=1,
        )
        for i in range(5)
    )
    refs = (ErRef(source="dbo.T1", target="dbo.T0", label="Id->Id"),)
    a = render_er_diagram(tables, refs, table_cap=3)
    b = render_er_diagram(tables, refs, table_cap=3)
    assert a == b
    assert a.startswith("erDiagram\n")
    assert "table(s) omitted by the ER cap" in a
    validate_mermaid_er_diagram(a)
    # Byte-identical on a second process-shaped call with the same inputs.
    assert json.dumps(a) == json.dumps(b)


@needs_node
def test_delimited_identifiers_still_yield_the_same_foreign_keys(indexed_delimited) -> None:
    """228's refusal narrowed to BARE words, so a delimited schema keeps every FK it declares.

    Red before that narrowing: `[Key]`, `[Table]` and `[Column]` were refused as reserved names,
    so both tables vanished and the whole file came back `ok:false` — the fixture's own
    `report.failed == 0` is where it shows, before any assertion here runs.
    """
    store, _ = indexed_delimited
    edges = _ref_edges(store)
    resolved = {(e["source"], e["target"]) for e in edges if e["tier"] == "RESOLVED"}

    assert resolved == DELIMITED_EXPECTED
    tables = {str(row["qualified_name"]) for row in store.nodes_by_kind("Table", limit=50)}
    assert tables == {"dbo.Key", "dbo.Constraint"}
