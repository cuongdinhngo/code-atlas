"""239 — a Column search hit names its FK target from existing REFERENCES edges.

The field trap: two same-prefixed columns on one table, one pointing at a differently-named
table — the sweep distinguishes them in one call. AC2 pins byte-identity for no-FK Columns and
non-Column kinds. No adapter or CONTRACT_VERSION change.
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
from code_atlas.store import GraphStore
from code_atlas.tools import search_symbol

NODE = shutil.which("node")
ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")

# Field shape: two Region* columns; RegionID is the trap (points at OperationalRegion, not Region).
TRAP_SCHEMA = """\
CREATE TABLE dbo.Region (
    RegionId int NOT NULL,
    Code varchar(16) NOT NULL,
    CONSTRAINT PK_Region PRIMARY KEY (RegionId)
);
GO
CREATE TABLE dbo.OperationalRegion (
    OperationalRegionId int NOT NULL,
    CONSTRAINT PK_OperationalRegion PRIMARY KEY (OperationalRegionId)
);
GO
CREATE TABLE dbo.Authen (
    AuthenId int NOT NULL,
    RegionCode varchar(16) NOT NULL,
    RegionID int NOT NULL,
    PlainNote varchar(40) NULL,
    CONSTRAINT PK_Authen PRIMARY KEY (AuthenId),
    CONSTRAINT FK_Authen_RegionCode FOREIGN KEY (RegionCode) REFERENCES dbo.Region (Code),
    CONSTRAINT FK_Authen_RegionID FOREIGN KEY (RegionID)
        REFERENCES dbo.OperationalRegion (OperationalRegionId)
);
GO
CREATE TABLE dbo.SelfRef (
    Id int NOT NULL,
    ParentId int NULL,
    CONSTRAINT PK_SelfRef PRIMARY KEY (Id),
    CONSTRAINT FK_SelfRef_Parent FOREIGN KEY (ParentId) REFERENCES dbo.SelfRef (Id)
);
GO
CREATE TABLE dbo.ImpliedPK (
    Id int NOT NULL,
    RegionId int NOT NULL,
    CONSTRAINT PK_ImpliedPK PRIMARY KEY (Id),
    CONSTRAINT FK_ImpliedPK_Region FOREIGN KEY (RegionId) REFERENCES dbo.Region
);
GO
CREATE TABLE dbo.Composite (
    A int NOT NULL,
    B int NOT NULL,
    CONSTRAINT PK_Composite PRIMARY KEY (A, B)
);
GO
CREATE TABLE dbo.UsesComposite (
    Id int NOT NULL,
    A int NOT NULL,
    B int NOT NULL,
    CONSTRAINT PK_UsesComposite PRIMARY KEY (Id),
    CONSTRAINT FK_UsesComposite_AB FOREIGN KEY (A, B) REFERENCES dbo.Composite (A, B)
);
"""


@pytest.fixture
def indexed(tmp_path: Path) -> Iterator[tuple[GraphStore, Path]]:
    src = tmp_path / "db"
    src.mkdir()
    (src / "schema.sql").write_text(TRAP_SCHEMA, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])})
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
        yield store, tmp_path


def _search(tmp_path: Path, *args: object, **kwargs: object) -> dict[str, object]:
    config = load_config(tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])})
    return search_symbol.create(config)(*args, **kwargs)  # type: ignore[arg-type]


@needs_node
def test_column_hit_carries_fk_target_self_fk_and_composite(indexed) -> None:
    """AC1 / AC4: FK, self-FK, and multi-column FK targets ride the Column row; order is stable."""
    _, root = indexed
    region_code = _search(root, "RegionCode", kind="Column")
    code_hits = [h for h in region_code["results"] if h["qname"] == "dbo.Authen::RegionCode"]
    assert code_hits and code_hits[0]["references"] == ["dbo.Region::Code"]

    self_hit = _search(root, "ParentId", kind="Column")
    parent = [h for h in self_hit["results"] if h["qname"] == "dbo.SelfRef::ParentId"]
    assert parent and parent[0]["references"] == ["dbo.SelfRef::Id"]

    a_hit = _search(root, query="A", kind="Column")
    uses_a = [h for h in a_hit["results"] if h["qname"] == "dbo.UsesComposite::A"]
    assert uses_a and uses_a[0]["references"] == ["dbo.Composite::A"]
    b_hit = _search(root, query="B", kind="Column")
    uses_b = [h for h in b_hit["results"] if h["qname"] == "dbo.UsesComposite::B"]
    assert uses_b and uses_b[0]["references"] == ["dbo.Composite::B"]

    # Determinism: identical call → identical references list.
    again = _search(root, "RegionCode", kind="Column")
    assert again["results"] == region_code["results"]


@needs_node
def test_no_fk_column_and_non_column_stay_byte_identical(indexed) -> None:
    """AC2: no-FK Column and non-Column kinds omit `references`; minimal is a subset."""
    _, root = indexed
    plain = _search(root, "PlainNote", kind="Column")
    note = [h for h in plain["results"] if h["qname"] == "dbo.Authen::PlainNote"]
    assert note and "references" not in note[0]
    assert set(note[0]) <= {"qname", "kind", "file", "line"}

    table = _search(root, "Authen", kind="Table")
    assert table["results"]
    assert all("references" not in h for h in table["results"])

    std = _search(root, "RegionID", kind="Column", detail_level="standard")
    mini = _search(root, "RegionID", kind="Column", detail_level="minimal")
    trap = next(h for h in std["results"] if h["qname"] == "dbo.Authen::RegionID")
    assert "references" in trap
    mini_trap = next(h for h in mini["results"] if h["qname"] == "dbo.Authen::RegionID")
    assert "references" not in mini_trap
    assert set(mini_trap) <= {"qname", "kind", "file", "line"}


@needs_node
def test_trap_sweep_distinguishes_same_prefix_columns(indexed) -> None:
    """AC3 proving test: RegionCode vs RegionID name different targets in one sweep."""
    _, root = indexed
    sweep = _search(root, queries=["RegionCode", "RegionID"], kind="Column")
    by_q: dict[str, dict[str, object]] = {}
    for subject in sweep["subjects"]:
        for hit in subject["results"]:
            by_q[str(hit["qname"])] = hit
    assert by_q["dbo.Authen::RegionCode"]["references"] == ["dbo.Region::Code"]
    assert by_q["dbo.Authen::RegionID"]["references"] == [
        "dbo.OperationalRegion::OperationalRegionId"
    ]


@needs_node
def test_contract_version_unchanged_and_r1_1_surface() -> None:
    """AC5: no contract bump; enrichment keys off kind + REFERENCES, not a language branch."""
    assert CONTRACT_VERSION == 10
    src = Path(__file__).resolve().parent.parent / "code_atlas" / "tools" / "search_symbol.py"
    text = src.read_text(encoding="utf-8")
    assert 'if language ==' not in text
    assert 'kind"] == "Column"' in text or "kind'] == 'Column'" in text or '== "Column"' in text


@needs_node
def test_payload_cost_of_the_addition_is_bounded(indexed) -> None:
    """AC6: nine-column-shaped sweep grows only by the references facts, recorded for 223."""
    _, root = indexed
    # Measure: trap table's two FK columns vs the same call at minimal (no references).
    std = _search(root, queries=["RegionCode", "RegionID"], kind="Column", detail_level="standard")
    mini = _search(root, queries=["RegionCode", "RegionID"], kind="Column", detail_level="minimal")
    std_bytes = len(json.dumps(std, sort_keys=True))
    mini_bytes = len(json.dumps(mini, sort_keys=True))
    delta = std_bytes - mini_bytes
    # Two short target strings + key overhead — well under a kilobyte for this fixture.
    assert 0 < delta < 500, f"unexpected envelope delta {delta} (std={std_bytes} mini={mini_bytes})"


@needs_node
def test_table_only_fk_is_never_signed_as_a_resolved_column_target(indexed) -> None:
    """R5.6: both states in one test — a resolved column target and a table-only one differ."""
    _, root = indexed
    resolved = _search(root, "RegionCode", kind="Column")
    hit = next(h for h in resolved["results"] if h["qname"] == "dbo.Authen::RegionCode")
    assert hit["references"] == ["dbo.Region::Code"]
    assert "references_unresolved" not in hit

    implied = _search(root, "RegionId", kind="Column")
    table_only = next(h for h in implied["results"] if h["qname"] == "dbo.ImpliedPK::RegionId")
    # The FK omits its column list, so only the table is known — never signed under `references`.
    assert table_only["references_unresolved"] == ["dbo.Region"]
    assert "references" not in table_only
