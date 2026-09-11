"""247 — Column.extra captures nullability, IDENTITY and PRIMARY KEY ordinals.

Proving path is integration (adapter → store): the defect is that the reader drops the clauses,
so a unit assertion over a helper cannot see the graph the tools will read. R6.5 — the proving
test is red before the capture lands.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.indexer import full_build, incremental_update
from code_atlas.store import GraphStore

NODE = shutil.which("node")
ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")


def _extra(store: GraphStore, qname: str) -> dict[str, object]:
    rows = store.nodes_by_qualified_name(qname, kind="Column", limit=5)
    assert len(rows) == 1, f"expected one Column for {qname}, got {len(rows)}"
    raw = rows[0]["extra"]
    data = json.loads(str(raw)) if raw else {}
    assert isinstance(data, dict)
    return data


def _index(tmp_path: Path, files: dict[str, str]) -> GraphStore:
    src = tmp_path / "db"
    src.mkdir(exist_ok=True)
    for name, body in files.items():
        (src / name).write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])})
    store = GraphStore(config.db_path)
    report = full_build(config, store)
    assert report.failed == 0
    return store


@needs_node
def test_inline_identity_not_null_primary_key(tmp_path: Path) -> None:
    """AC1 — ``[ID] int IDENTITY(1,1) NOT NULL PRIMARY KEY`` carries all three facts."""
    store = _index(
        tmp_path,
        {
            "t.sql": """\
CREATE TABLE dbo.Items (
    [ID] int IDENTITY(1,1) NOT NULL PRIMARY KEY,
    [Name] varchar(50)
);
"""
        },
    )
    try:
        extra = _extra(store, "dbo.Items::ID")
        assert extra["nullable"] is False
        assert extra["identity"] == {"increment": 1, "seed": 1}
        assert extra["primary_key"] == 1
        name = _extra(store, "dbo.Items::Name")
        assert "nullable" not in name
        assert "identity" not in name
        assert "primary_key" not in name
    finally:
        store.close()


@needs_node
def test_table_level_composite_primary_key_ordinals(tmp_path: Path) -> None:
    """AC2 — table-level CONSTRAINT PK marks A=1, B=2; constraint entry is not a Column."""
    store = _index(
        tmp_path,
        {
            "t.sql": """\
CREATE TABLE dbo.Pair (
    [A] int NOT NULL,
    [B] int NOT NULL,
    [C] int,
    CONSTRAINT PK_Pair PRIMARY KEY ([A] ASC, [B] ASC)
);
"""
        },
    )
    try:
        assert _extra(store, "dbo.Pair::A")["primary_key"] == 1
        assert _extra(store, "dbo.Pair::B")["primary_key"] == 2
        assert "primary_key" not in _extra(store, "dbo.Pair::C")
        columns = [r["name"] for r in store.nodes_by_kind("Column", limit=50)]
        assert "PK_Pair" not in columns
        assert set(columns) == {"A", "B", "C"}
    finally:
        store.close()


@needs_node
def test_alter_primary_key_reaches_create_columns_across_files(tmp_path: Path) -> None:
    """AC3 — ALTER ADD CONSTRAINT PRIMARY KEY folds onto the CREATE Column nodes."""
    store = _index(
        tmp_path,
        {
            "create.sql": """\
CREATE TABLE dbo.Pair (
    [A] int NOT NULL,
    [B] int NOT NULL,
    [C] int
);
""",
            "pk.sql": """\
ALTER TABLE dbo.Pair ADD CONSTRAINT PK_Pair PRIMARY KEY ([A] ASC, [B] ASC);
""",
        },
    )
    try:
        assert _extra(store, "dbo.Pair::A")["primary_key"] == 1
        assert _extra(store, "dbo.Pair::B")["primary_key"] == 2
        assert "primary_key" not in _extra(store, "dbo.Pair::C")
        # One typed Column per qname after the fold — not a sparse ALTER twin.
        for qn in ("dbo.Pair::A", "dbo.Pair::B", "dbo.Pair::C"):
            assert len(store.nodes_by_qualified_name(qn, kind="Column", limit=5)) == 1
    finally:
        store.close()


@needs_node
def test_omitted_nullability_carries_no_nullable_key(tmp_path: Path) -> None:
    """AC4 — neither NULL nor NOT NULL ⇒ no ``nullable`` key (R5.6 / 061)."""
    store = _index(
        tmp_path,
        {
            "t.sql": """\
CREATE TABLE dbo.Loose (
    [X] int,
    [Y] int NOT NULL
);
"""
        },
    )
    try:
        assert "nullable" not in _extra(store, "dbo.Loose::X")
        assert _extra(store, "dbo.Loose::Y")["nullable"] is False
    finally:
        store.close()


@needs_node
def test_default_null_does_not_invent_nullable(tmp_path: Path) -> None:
    """Nullability is a column attribute — DEFAULT NULL / DEFAULT (NULL) are not (challenger R1)."""
    store = _index(
        tmp_path,
        {
            "t.sql": """\
CREATE TABLE dbo.D (
    [X] int DEFAULT (NULL),
    [Z] int DEFAULT NULL,
    [Y] int NULL DEFAULT (NULL)
);
"""
        },
    )
    try:
        assert "nullable" not in _extra(store, "dbo.D::X")
        assert "nullable" not in _extra(store, "dbo.D::Z")
        assert _extra(store, "dbo.D::Z")["default"] == "NULL"
        assert _extra(store, "dbo.D::Y")["nullable"] is True
    finally:
        store.close()


@needs_node
def test_generated_as_identity_is_not_tsql_identity(tmp_path: Path) -> None:
    """228 — Postgres GENERATED … AS IDENTITY must not become T-SQL identity (challenger R7)."""
    store = _index(
        tmp_path,
        {
            "t.sql": """\
CREATE TABLE dbo.Pg (
    id int GENERATED ALWAYS AS IDENTITY,
    n int IDENTITY(1,1)
);
"""
        },
    )
    try:
        assert "identity" not in _extra(store, "dbo.Pg::id")
        assert _extra(store, "dbo.Pg::n")["identity"] == {"increment": 1, "seed": 1}
    finally:
        store.close()


@needs_node
def test_primary_key_clustered_is_captured(tmp_path: Path) -> None:
    """T-SQL table_constraint may put CLUSTERED between KEY and the column list."""
    store = _index(
        tmp_path,
        {
            "t.sql": """\
CREATE TABLE dbo.Cl (
    [A] int NOT NULL,
    [B] int NOT NULL,
    CONSTRAINT PK_Cl PRIMARY KEY CLUSTERED ([A] ASC, [B] ASC)
);
"""
        },
    )
    try:
        assert _extra(store, "dbo.Cl::A")["primary_key"] == 1
        assert _extra(store, "dbo.Cl::B")["primary_key"] == 2
    finally:
        store.close()


@needs_node
def test_alter_pk_does_not_duplicate_contains(tmp_path: Path) -> None:
    """AC3 fold must not leave a second CONTAINS from the ALTER file."""
    store = _index(
        tmp_path,
        {
            "create.sql": "CREATE TABLE dbo.T ([A] int NOT NULL, [B] int NOT NULL);\n",
            "pk.sql": "ALTER TABLE dbo.T ADD CONSTRAINT PK_T PRIMARY KEY ([A], [B]);\n",
        },
    )
    try:
        edges = [
            e
            for e in store.edges_by_source("dbo.T", kinds=("CONTAINS",), limit=50)
            if str(e.get("target_qname") or e.get("target_raw") or "").endswith("::A")
        ]
        assert len(edges) == 1
    finally:
        store.close()


@needs_node
def test_existing_column_keys_unchanged_on_prior_fixture_shape(tmp_path: Path) -> None:
    """AC5 shape — prior keys (data_type / default) still land; new keys only when present."""
    store = _index(
        tmp_path,
        {
            "t.sql": """\
CREATE TABLE dbo.LedgerTrans (
    TransId    int NOT NULL,
    ChangeUser varchar(50) NULL DEFAULT (user_name()),
    CONSTRAINT PK_LedgerTrans PRIMARY KEY (TransId)
);
"""
        },
    )
    try:
        change = _extra(store, "dbo.LedgerTrans::ChangeUser")
        assert change["data_type"] == "varchar(50)"
        assert change["default"] == "(user_name())"
        assert change["nullable"] is True
        assert "primary_key" not in change
        tid = _extra(store, "dbo.LedgerTrans::TransId")
        assert tid["primary_key"] == 1
        assert tid["nullable"] is False
    finally:
        store.close()


@needs_node
def test_a_folded_key_survives_an_incremental_reindex_of_the_create_file(
    tmp_path: Path,
) -> None:
    """Review — the fold deletes the rows it consumes, so it owes the delta a way back.

    Nothing in the graph links the ALTER file to a column declared elsewhere once the sparse row
    is gone, so re-parsing only the CREATE file dropped ``primary_key`` for good — silently, and
    only a full rebuild brought it back (R5.6: a key that exists must not read as absent).
    """
    create = (
        "CREATE TABLE dbo.T (\n"
        "    Id int NOT NULL IDENTITY(1,1),\n"
        "    Name varchar(50) NULL\n);\n"
    )
    store = _index(
        tmp_path,
        {
            "a_create.sql": create,
            "b_alter.sql": "ALTER TABLE dbo.T ADD CONSTRAINT PK_T PRIMARY KEY (Id);\n",
        },
    )
    try:
        assert _extra(store, "dbo.T::Id")["primary_key"] == 1
        config = load_config(
            tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])}
        )
        (tmp_path / "db" / "a_create.sql").write_text(
            create.replace("varchar(50)", "varchar(60)"), encoding="utf-8"
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
        incremental_update(config, store, ["db/a_create.sql"])
        after = _extra(store, "dbo.T::Id")
        assert after["primary_key"] == 1
        assert after["identity"] == {"increment": 1, "seed": 1}
        assert _extra(store, "dbo.T::Name")["type"] == "varchar(60)"
    finally:
        store.close()


@needs_node
def test_a_primary_key_naming_the_column_in_another_case_still_folds(tmp_path: Path) -> None:
    """Review — SQL identifiers are case-insensitive, so the fold cannot match on spelling.

    ``PRIMARY KEY (ID)`` against a column declared ``Id`` used to leave a typeless phantom
    ``dbo.T::ID`` in the graph forever and drop the key from the real column.
    """
    store = _index(
        tmp_path,
        {
            "a_create.sql": "CREATE TABLE dbo.T (\n    Id int NOT NULL\n);\n",
            "b_alter.sql": "ALTER TABLE dbo.T ADD CONSTRAINT PK_T PRIMARY KEY (ID);\n",
        },
    )
    try:
        assert _extra(store, "dbo.T::Id")["primary_key"] == 1
        assert store.nodes_by_qualified_name("dbo.T::ID", kind="Column", limit=5) == []
    finally:
        store.close()
