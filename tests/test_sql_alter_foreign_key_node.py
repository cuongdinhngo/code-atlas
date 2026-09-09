"""236 — a standalone ``ALTER … ADD … FOREIGN KEY`` is a ForeignKey node, not a second Table row.

The incident: a table's DDL lives in one file and its foreign keys in a separate
``_fk_constraints`` file. Before the fix the constraint file re-emitted a ``kind:"Table"`` node for
the referenced table, so ``search_symbol(kind:"Table")`` returned two indistinguishable rows and
the correct FK answer was re-derived wrong. AC4 pins the shape: one Table row, one ForeignKey.

R6.5 (prove-the-guard-fails): on the pre-fix adapter the second file emits a Table node and zero
ForeignKey nodes, so every assertion below is red before the change.
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

# The table is defined in one file …
CREATE = """\
CREATE TABLE [dbo].[MemberType] (
    [Id] int NOT NULL,
    [MemberParentTypeId] int NOT NULL
);
"""

# … and altered to add its foreign key in another (the `_fk_constraints.sql` shape).
FK_CONSTRAINTS = """\
ALTER TABLE [dbo].[MemberType]
    ADD CONSTRAINT [FK_MemberType_MemberParentTypeID]
    FOREIGN KEY ([MemberParentTypeId]) REFERENCES [dbo].[MemberParentType] ([Id]);
"""

_FK_QNAME = "dbo.MemberType::FK_MemberType_MemberParentTypeID"


@pytest.fixture
def indexed(tmp_path: Path) -> Iterator[GraphStore]:
    src = tmp_path / "db"
    src.mkdir()
    (src / "MemberType.sql").write_text(CREATE, encoding="utf-8")
    (src / "_fk_constraints.sql").write_text(FK_CONSTRAINTS, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])})
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
        yield store


@needs_node
def test_one_table_row_not_two(indexed: GraphStore) -> None:
    """AC4: the referenced table resolves to its single DDL site, not the constraint line too."""
    tables = indexed.nodes_by_qualified_name("dbo.MemberType", kind="Table", limit=50)
    assert len(tables) == 1
    assert str(tables[0]["file_path"]).endswith("MemberType.sql")


@needs_node
def test_foreign_key_is_its_own_node(indexed: GraphStore) -> None:
    """AC1/AC2: the constraint is one ForeignKey node carrying parent/referenced/columns."""
    fks = indexed.nodes_by_kind("ForeignKey", limit=50)
    assert len(fks) == 1
    node = fks[0]
    assert str(node["qualified_name"]) == _FK_QNAME
    assert str(node["file_path"]).endswith("_fk_constraints.sql")
    extra = json.loads(str(node["extra"]))
    assert extra["parent_table"] == "dbo.MemberType"
    assert extra["referenced_table"] == "dbo.MemberParentType"
    assert extra["columns"] == "MemberParentTypeId"


@needs_node
def test_constraint_file_emits_no_table_row(indexed: GraphStore) -> None:
    """The whole defect in one line: the constraint file contributes no Table node at all."""
    from_constraints = [
        row
        for row in indexed.nodes_by_kind("Table", limit=200)
        if str(row["file_path"]).endswith("_fk_constraints.sql")
    ]
    assert from_constraints == []
