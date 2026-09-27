"""320 — a bare table name reaches the table it names, or is refused with the qualified candidates.

The field session typed `FormInstance` from a database mental model; the stored qname is
`dbo.FormInstance` (CONVENTION §3), so the exact lookup answered a dead-end `no_such_symbol`.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import check_column_defaults
from code_atlas.tools.nav_result import (
    REASON_NO_SUCH_SYMBOL,
    REASON_OK,
    REASON_SUBJECT_AMBIGUOUS,
    TRY_INSTEAD_SEARCH_SYMBOL,
)

NODE = shutil.which("node")
ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")

# Both DEFAULT spellings the adapter parses: inline, and ALTER … ADD CONSTRAINT … FOR (ddl.js).
SCHEMA = """\
CREATE TABLE dbo.FormInstance (
    Id           int NOT NULL,
    Status       int NULL DEFAULT ((1)),
    ModifiedDate datetime NULL
);
ALTER TABLE dbo.FormInstance
    ADD CONSTRAINT DF_FormInstance_Modified DEFAULT (getdate()) FOR ModifiedDate;
CREATE TABLE dbo.Shared (Id int NOT NULL, Flag bit NULL DEFAULT ((0)));
CREATE TABLE audit.Shared (Id int NOT NULL, Flag bit NULL DEFAULT ((1)));
"""
WRITERS = """\
CREATE PROCEDURE dbo.Insert_Form
AS
    INSERT INTO dbo.FormInstance (Id) VALUES (1);
GO
CREATE PROCEDURE dbo.Insert_Shared
AS
    INSERT INTO dbo.Shared (Id) VALUES (1);
GO
"""

# Captured on main before 320 (index_root stripped — it names the host, not the answer).
_PRE_320_EXACT_MINIMAL = (
    '{"indexed": true, "reason": "ok", "results": [{"column": "dbo.FormInstance::Status", '
    '"default": "((1))", "omitted_count": 1, "status": "checked", "writers_total": 1}], '
    '"table": "dbo.FormInstance", "total_count": 1, "truncated": false}'
)
_PRE_320_EXACT_STANDARD_ROWS = [
    {
        "column": "dbo.FormInstance::ModifiedDate",
        "default": "(getdate())",
        "named_by": [],
        "omitted_by": ["dbo.Insert_Form"],
        "omitted_count": 1,
        "status": "checked",
        "writers_total": 1,
    },
    {
        "column": "dbo.FormInstance::Status",
        "default": "((1))",
        "named_by": [],
        "omitted_by": ["dbo.Insert_Form"],
        "omitted_count": 1,
        "status": "checked",
        "writers_total": 1,
    },
]
_PRE_320_EXACT_STANDARD_KEYS = [
    "index_root",
    "indexed",
    "reason",
    "results",
    "table",
    "total_count",
    "truncated",
    "unconfigured_adapters",
]


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


@needs_node
def test_a_bare_name_with_one_candidate_answers_about_it_and_says_so(indexed: Config) -> None:
    """AC1 — the defaulted columns of dbo.FormInstance, and the envelope names that subject."""
    payload = check_column_defaults.create(indexed)(table="FormInstance")
    assert payload["reason"] == REASON_OK
    assert payload["table"] == "FormInstance"  # what was asked …
    assert payload["resolved_qname"] == "dbo.FormInstance"  # … is not what was measured (R5.6)
    assert payload["results"] == _PRE_320_EXACT_STANDARD_ROWS


@needs_node
def test_the_column_composes_against_the_resolved_table(indexed: Config) -> None:
    """Scope 2 — `column="Status"` means `dbo.FormInstance::Status`, not `FormInstance::Status`."""
    payload = check_column_defaults.create(indexed)(table="FormInstance", column="Status")
    assert [row["column"] for row in payload["results"]] == ["dbo.FormInstance::Status"]
    assert payload["results"][0]["default"] == "((1))"


@needs_node
def test_a_bare_name_two_schemas_hold_is_refused_with_both_candidates(indexed: Config) -> None:
    """AC2 — no rows at all: measuring dbo.Shared alone would leave audit.Shared unmentioned."""
    payload = check_column_defaults.create(indexed)(table="Shared")
    assert payload["reason"] == REASON_SUBJECT_AMBIGUOUS
    assert payload["results"] == []
    assert payload["total_count"] == 0
    assert "resolved_qname" not in payload
    sites = payload["ambiguous_definitions"]
    assert [site["qname"] for site in sites] == ["audit.Shared", "dbo.Shared"]
    assert all(site["kind"] == "Table" and site["file"] == "db/001_schema.sql" for site in sites)


@needs_node
def test_an_absent_table_keeps_no_such_symbol_and_gains_a_route(indexed: Config) -> None:
    """AC3 — still no_such_symbol, now with somewhere to go (search_symbol, kind=Table)."""
    call = check_column_defaults.create(indexed)
    for table in ("NoSuchTable", "dbo.NoSuchTable"):
        payload = call(table=table)
        assert payload["reason"] == REASON_NO_SUCH_SYMBOL
        assert payload["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL
        assert 'kind="Table"' in str(payload["try_instead_hint"])
        assert "resolved_qname" not in payload


@needs_node
def test_an_exactly_qualified_call_is_byte_identical(indexed: Config) -> None:
    """AC4 / 061 — the exact arm pays nothing and gains nothing."""
    call = check_column_defaults.create(indexed)
    minimal = call(table="dbo.FormInstance", column="Status", detail_level="minimal")
    minimal.pop("index_root")
    assert json.dumps(minimal, sort_keys=True) == _PRE_320_EXACT_MINIMAL
    standard = call(table="dbo.FormInstance")
    assert sorted(standard) == _PRE_320_EXACT_STANDARD_KEYS
    assert standard["results"] == _PRE_320_EXACT_STANDARD_ROWS
    assert standard["reason"] == REASON_OK
