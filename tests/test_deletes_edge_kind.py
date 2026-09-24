"""328 — DELETE / TRUNCATE / MERGE-with-DELETE emit DELETES, not WRITES."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import check_column_defaults, find_references

NODE = shutil.which("node")
ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")

SCHEMA = """\
CREATE TABLE dbo.T (
    Id         int NOT NULL,
    ChangeUser nvarchar(128) NULL DEFAULT (suser_sname())
);
GO
"""

DELETE_PROC = """\
CREATE PROCEDURE dbo.Clear_T
AS
    DELETE FROM dbo.T WHERE Id > 0;
GO
"""

TRUNCATE_PROC = """\
CREATE PROCEDURE dbo.Wipe_T
AS
    TRUNCATE TABLE dbo.T;
GO
"""

MERGE_DELETE = """\
CREATE PROCEDURE dbo.Merge_Clear_T
AS
    MERGE dbo.T AS tgt
    USING (SELECT 0 AS Id) AS src ON tgt.Id = src.Id
    WHEN MATCHED THEN DELETE;
GO
"""

WRITER = """\
CREATE PROCEDURE dbo.Insert_T
AS
    INSERT INTO dbo.T (Id) VALUES (1);
GO
"""


def _index(tmp_path: Path, *bodies: str) -> Config:
    files: dict[str, str] = {"db/schema.sql": SCHEMA}
    for i, body in enumerate(bodies):
        files[f"db/proc_{i}.sql"] = body
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    assert NODE is not None
    config = load_config(tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])})
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
    return config


@needs_node
def test_delete_from_emits_deletes_edge(tmp_path: Path) -> None:
    """AC1 — DELETE FROM dbo.T → one DELETES edge onto dbo.T."""
    cfg = _index(tmp_path, DELETE_PROC)
    with GraphStore(cfg.db_path) as store:
        rows = store.edges_by_target("dbo.T", kinds=("DELETES",), limit=64)
    assert len(rows) == 1
    assert rows[0]["kind"] == "DELETES"
    assert rows[0]["source_qname"] == "dbo.Clear_T"
    assert rows[0]["confidence_tier"] == "RESOLVED"


@needs_node
def test_truncate_and_merge_delete_emit_deletes(tmp_path: Path) -> None:
    """AC2 — TRUNCATE and MERGE…DELETE each emit DELETES."""
    cfg = _index(tmp_path, TRUNCATE_PROC, MERGE_DELETE)
    with GraphStore(cfg.db_path) as store:
        rows = store.edges_by_target("dbo.T", kinds=("DELETES",), limit=64)
    sources = {str(r["source_qname"]) for r in rows}
    assert sources == {"dbo.Wipe_T", "dbo.Merge_Clear_T"}


@needs_node
def test_check_column_defaults_ignores_deletes(tmp_path: Path) -> None:
    """AC3 — check_column_defaults is byte-identical with or without a DELETE."""
    cfg_writer = _index(tmp_path / "w", WRITER)
    cfg_both = _index(tmp_path / "b", WRITER, DELETE_PROC)
    tool_w = check_column_defaults.create(cfg_writer)
    tool_b = check_column_defaults.create(cfg_both)
    left = tool_w(table="dbo.T")
    right = tool_b(table="dbo.T")
    for key in ("index_root", "db_path", "answered_about_ref"):
        left.pop(key, None)
        right.pop(key, None)
    assert left == right


@needs_node
def test_find_references_lists_deletes_with_kind(tmp_path: Path) -> None:
    """AC4 — find_references dbo.T lists the delete site with kind DELETES."""
    cfg = _index(tmp_path, WRITER, DELETE_PROC)
    payload = find_references.create(cfg)("dbo.T")
    kinds = {str(h.get("kind")) for h in payload["results"]}  # type: ignore[union-attr]
    assert "DELETES" in kinds
    assert "WRITES" in kinds
    delete_hits = [h for h in payload["results"] if h.get("kind") == "DELETES"]  # type: ignore[union-attr]
    assert any("Clear_T" in str(h.get("qname", h.get("source_qname", ""))) for h in delete_hits)


@needs_node
def test_deletes_is_contract_v12_vocabulary() -> None:
    assert contract.CONTRACT_VERSION == 12
    assert "DELETES" in contract.EDGE_KINDS
    assert "DELETES" in contract.FQN_EDGE_KINDS
    assert "DELETES" not in contract.IMPACT_KINDS
