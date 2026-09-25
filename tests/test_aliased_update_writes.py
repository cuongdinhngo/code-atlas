"""333 — an aliased UPDATE writes to the table its alias names, never to the alias."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore

NODE = shutil.which("node")
ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")

SCHEMA = """\
CREATE TABLE dbo.T (
    Id int NOT NULL,
    X  int NULL
);
GO
CREATE TABLE dbo.U (
    Id int NOT NULL
);
GO
"""

ALIASED = """\
CREATE PROCEDURE dbo.Alias_Upd
AS
    UPDATE c SET X = 1 FROM dbo.T c JOIN dbo.U p ON p.Id = c.Id;
GO
"""

ALIASED_AS = """\
CREATE PROCEDURE dbo.Alias_As_Upd
AS
    UPDATE a SET a.X = 1 FROM dbo.T AS a WHERE a.Id > 0;
GO
"""

NESTED = """\
CREATE PROCEDURE dbo.Nested_Upd
AS
    UPDATE c SET X = (SELECT TOP 1 Id FROM dbo.U c WHERE c.Id > 0) FROM dbo.T c;
GO
CREATE PROCEDURE dbo.Derived_Upd
AS
    UPDATE c SET X = 1 FROM (SELECT Id FROM dbo.U c) sub JOIN dbo.T c ON c.Id = sub.Id;
GO
"""

PLAIN = """\
CREATE PROCEDURE dbo.Plain_Upd
AS
    UPDATE dbo.T SET X = 1 WHERE Id > 0;
GO
"""

UNRESOLVED = """\
CREATE PROCEDURE dbo.Orphan_Upd
AS
    UPDATE q SET X = 1 FROM dbo.T c;
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


def _writes(cfg: Config, source: str) -> list[tuple[str, str, str]]:
    with GraphStore(cfg.db_path) as store:
        rows = store.edges_by_source(source, limit=64)
    return sorted(
        (str(r["target_raw"]), str(r["target_qname"]), str(r["confidence_tier"]))
        for r in rows
        if r["kind"] == "WRITES"
    )


@needs_node
def test_aliased_update_writes_the_from_source(tmp_path: Path) -> None:
    """AC1 — `UPDATE c … FROM dbo.T c JOIN …` writes dbo.T::X, not c::X."""
    cfg = _index(tmp_path, ALIASED)
    assert _writes(cfg, "dbo.Alias_Upd") == [("dbo.T::X", "dbo.T::X", "RESOLVED")]


@needs_node
def test_explicit_as_alias_resolves_the_same(tmp_path: Path) -> None:
    """AC2 — `FROM dbo.T AS t` resolves the alias the same way."""
    cfg = _index(tmp_path, ALIASED_AS)
    assert _writes(cfg, "dbo.Alias_As_Upd") == [("dbo.T::X", "dbo.T::X", "RESOLVED")]


@needs_node
def test_a_subquery_alias_never_shadows_the_outer_source(tmp_path: Path) -> None:
    """A subquery or derived table reusing the alias scopes its own; the outer FROM source wins."""
    cfg = _index(tmp_path, NESTED)
    assert _writes(cfg, "dbo.Nested_Upd") == [("dbo.T::X", "dbo.T::X", "RESOLVED")]
    assert _writes(cfg, "dbo.Derived_Upd") == [("dbo.T::X", "dbo.T::X", "RESOLVED")]


@needs_node
def test_plain_update_is_unchanged(tmp_path: Path) -> None:
    """AC3 — a non-aliased UPDATE still writes its named table."""
    cfg = _index(tmp_path, PLAIN)
    assert _writes(cfg, "dbo.Plain_Upd") == [("dbo.T::X", "dbo.T::X", "RESOLVED")]


@needs_node
def test_unmatched_alias_keeps_the_named_target(tmp_path: Path) -> None:
    """Scope 2 — no FROM source carries the alias, so no table is guessed."""
    cfg = _index(tmp_path, UNRESOLVED)
    assert [raw for raw, _, _ in _writes(cfg, "dbo.Orphan_Upd")] == ["q::X"]


DERIVED_DELETE = """\
CREATE PROCEDURE dbo.Derived_Del
AS
    DELETE c FROM (SELECT Id FROM dbo.U c) sub JOIN dbo.T c ON c.Id = sub.Id;
GO
"""


@needs_node
def test_the_shared_resolver_scopes_a_derived_delete_alias_too(tmp_path: Path) -> None:
    """R6.7 — DELETE shares the resolver, so its derived-table alias no longer shadows dbo.T."""
    cfg = _index(tmp_path, DERIVED_DELETE)
    with GraphStore(cfg.db_path) as store:
        rows = store.edges_by_source("dbo.Derived_Del", limit=64)
    assert [str(r["target_qname"]) for r in rows if r["kind"] == "DELETES"] == ["dbo.T"]
