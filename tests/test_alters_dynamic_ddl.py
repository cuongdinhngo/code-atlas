"""321 — a migration that alters an object, literally or through ``sp_executesql``, names it.

The field shape: a DEFAULT re-pointed by ``ALTER TABLE …`` built into ``@sql`` inside a cursor and
run by ``sp_executesql``. The table name lived only in a string literal, so no edge reached it and
"has this object already been migrated?" had no graph answer — a byte-identical migration shipped.
"""

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
from code_atlas.tools import check_column_defaults, search_symbol

NODE = shutil.which("node")
ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")

SCHEMA = """\
CREATE TABLE dbo.UserNotes (
    Id         int NOT NULL,
    ChangeUser nvarchar(128) NULL DEFAULT (suser_sname())
);
GO
CREATE PROCEDURE dbo.Insert_Note
AS
    INSERT INTO dbo.UserNotes (Id) VALUES (1);
GO
"""
# The field migration's shape: drop every DEFAULT in a cursor, then add the new one (line 8, 14).
DYNAMIC_MIGRATION = """\
DECLARE @name sysname, @sql nvarchar(max);
DECLARE c CURSOR FOR
    SELECT name FROM sys.default_constraints WHERE parent_object_id = OBJECT_ID(N'dbo.UserNotes');
OPEN c;
FETCH NEXT FROM c INTO @name;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = N'ALTER TABLE dbo.UserNotes DROP CONSTRAINT ' + QUOTENAME(@name);
    EXEC sp_executesql @sql;
    FETCH NEXT FROM c INTO @name;
END
CLOSE c;
DEALLOCATE c;
SET @sql = N'ALTER TABLE [dbo].[UserNotes] ADD CONSTRAINT DF_UserNotes_ChangeUser
    DEFAULT (CAST(SESSION_CONTEXT(N''app_user'') AS nvarchar(128))) FOR ChangeUser';
EXEC sp_executesql @sql;
"""
STATIC_MIGRATION = "ALTER TABLE dbo.UserNotes ADD Archived bit NULL;\n"
# A DDL verb in a string, but nothing here executes it — a message, not a migration.
PRINTED_DDL = "PRINT 'ALTER TABLE dbo.UserNotes needs a new DEFAULT';\n"
MENTION_ONLY = "EXEC (N'SELECT * FROM dbo.UserNotes');\n"
ROUTINE_DDL = "EXEC (N'CREATE OR ALTER PROCEDURE dbo.Insert_Note AS SELECT 1');\n"
# The file runs dynamic SQL, but not these strings: a printed DDL line, and a DDL variable no EXEC
# runs (the challenger's shape). Only `@run` executes, and it holds no DDL.
MIXED = """\
PRINT 'ALTER TABLE dbo.UserNotes needs a new DEFAULT';
DECLARE @ddl nvarchar(max) = N'ALTER TABLE dbo.UserNotes ADD Unused bit NULL';
DECLARE @run nvarchar(max) = N'UPDATE dbo.UserNotes SET ChangeUser = NULL';
EXEC sp_executesql @run;
"""
# A statement built across lines, then run through `EXEC (@v)`.
CONTINUED = """\
DECLARE @sql nvarchar(max);
SET @sql = N'PRINT 1;'
    + N'ALTER TABLE dbo.UserNotes ADD Continued bit NULL';
EXEC (@sql);
"""
UNQUALIFIED_DDL = "EXEC sp_executesql N'ALTER TABLE UserNotes ADD Flag bit NULL';\n"

FILES = {
    "db/001_schema.sql": SCHEMA,
    "db/migrations/V128__notes_author.sql": DYNAMIC_MIGRATION,
    "db/migrations/V130__notes_archived.sql": STATIC_MIGRATION,
    "db/scripts/print_ddl.sql": PRINTED_DDL,
    "db/scripts/report.sql": MENTION_ONLY,
    "db/scripts/redefine.sql": ROUTINE_DDL,
    "db/scripts/mixed.sql": MIXED,
    "db/scripts/continued.sql": CONTINUED,
}
V128 = "db/migrations/V128__notes_author.sql"

# check_column_defaults on dbo.UserNotes, captured on main before 321 (host-shaped keys stripped).
_PRE_321_DEFAULTS = (
    '{"indexed": true, "reason": "ok", "results": [{"column": "dbo.UserNotes::ChangeUser", '
    '"default": "(suser_sname())", "named_by": [], "omitted_by": ["dbo.Insert_Note"], '
    '"omitted_count": 1, "status": "checked", "writers_total": 1}], "table": "dbo.UserNotes", '
    '"total_count": 1, "truncated": false}'
)


def _index(tmp_path: Path, files: dict[str, str]) -> Config:
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(tmp_path, {"CA_SQL_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])})
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
        assert report.parsed == len(files) and report.failed == 0
    return config


@pytest.fixture
def indexed(tmp_path: Path) -> Iterator[Config]:
    yield _index(tmp_path, FILES)


def _alters_into(config: Config, qname: str) -> list[tuple[str, int, str]]:
    with GraphStore(config.db_path) as store:
        rows = store.edges_by_target(qname, kinds=("ALTERS",), limit=64)
    return sorted(
        (str(r["file_path"]), int(str(r["line"])), str(r["confidence_tier"])) for r in rows
    )


@needs_node
def test_a_cursor_built_alter_through_sp_executesql_alters_the_table(indexed: Config) -> None:
    """AC1 — both string-built statements reach dbo.UserNotes, at DYNAMIC."""
    dynamic = [row for row in _alters_into(indexed, "dbo.UserNotes") if row[0] == V128]
    assert dynamic == [(V128, 8, "DYNAMIC"), (V128, 14, "DYNAMIC")]


@needs_node
def test_asking_about_the_table_names_the_migration_apart_from_resolved_ones(
    indexed: Config,
) -> None:
    """AC2 — the dynamic claim rides its own field; the literal ALTER rides `altered_by`."""
    payload = search_symbol.create(indexed)(query="UserNotes", kind="Table")
    # One row per declaring file (the schema, and V130's ADD); the relation is the qname's.
    hits = payload["results"]
    assert {hit["qname"] for hit in hits} == {"dbo.UserNotes"} and len(hits) == 2
    for hit in hits:
        assert hit["altered_by"] == [{"file": "db/migrations/V130__notes_archived.sql", "line": 1}]
        assert hit["altered_by_dynamic"] == [
            {"file": "db/migrations/V128__notes_author.sql", "line": 8},
            {"file": "db/migrations/V128__notes_author.sql", "line": 14},
            {"file": "db/scripts/continued.sql", "line": 3},
        ]
    minimal = search_symbol.create(indexed)(query="UserNotes", kind="Table", detail_level="minimal")
    assert not any(key.startswith("altered_by") for hit in minimal["results"] for key in hit)


@needs_node
def test_a_literal_alter_table_alters_the_same_node_at_resolved(indexed: Config) -> None:
    """AC3 — the static spelling is the same relation, one tier stronger."""
    static = [row for row in _alters_into(indexed, "dbo.UserNotes") if row[2] == "RESOLVED"]
    assert static == [("db/migrations/V130__notes_archived.sql", 1, "RESOLVED")]


@needs_node
def test_ddl_never_counts_as_a_writer(indexed: Config) -> None:
    """AC4 — three migrations alter the table; the writer census still sees the one proc."""
    payload = check_column_defaults.create(indexed)(table="dbo.UserNotes")
    payload.pop("index_root")
    payload.pop("unconfigured_adapters")
    assert json.dumps(payload, sort_keys=True) == _PRE_321_DEFAULTS


def test_alters_is_contract_vocabulary_at_version_eleven() -> None:
    """AC5 — a new word is an R3 bump, and the resolver looks it up by FQN."""
    assert contract.CONTRACT_VERSION == 12
    assert "ALTERS" in contract.EDGE_KINDS
    assert "ALTERS" in contract.FQN_EDGE_KINDS
    assert "ALTERS" not in contract.IMPACT_KINDS


@needs_node
def test_a_mention_or_an_unexecuted_string_alters_nothing(indexed: Config) -> None:
    """AC6 — "altered by", never "mentioned near": no DDL verb, or nothing runs the string."""
    files = {row[0] for row in _alters_into(indexed, "dbo.UserNotes")}
    assert "db/scripts/report.sql" not in files
    assert "db/scripts/print_ddl.sql" not in files
    assert "db/scripts/mixed.sql" not in files


@needs_node
def test_a_string_assigned_to_a_variable_an_exec_runs_alters(indexed: Config) -> None:
    """The claim follows the string to the EXEC that runs it, across a `+` continuation."""
    rows = _alters_into(indexed, "dbo.UserNotes")
    assert ("db/scripts/continued.sql", 3, "DYNAMIC") in rows


@needs_node
def test_create_or_alter_in_a_string_alters_the_routine(indexed: Config) -> None:
    """Scope 3 — `CREATE OR ALTER` names a Function node, at DYNAMIC."""
    assert _alters_into(indexed, "dbo.Insert_Note") == [("db/scripts/redefine.sql", 1, "DYNAMIC")]
    payload = search_symbol.create(indexed)(query="Insert_Note", kind="Function")
    [hit] = payload["results"]
    assert hit["altered_by_dynamic"] == [{"file": "db/scripts/redefine.sql", "line": 1}]
    assert "altered_by" not in hit


@needs_node
def test_an_unqualified_name_links_by_the_writes_rule(tmp_path: Path) -> None:
    """T-SQL's default-schema rule (215) applies to DDL as it does to a write: one table, linked."""
    config = _index(tmp_path, {"db/001_schema.sql": SCHEMA, "db/fix.sql": UNQUALIFIED_DDL})
    assert _alters_into(config, "dbo.UserNotes") == [("db/fix.sql", 1, "DYNAMIC")]
