"""Task 364 — a PHP write that names its table as a bare string argument is a writer of that table.

`queryInsert('Items', $row)` carries no T-SQL text for 278/281 to read, so the table had SQL writers
only. A `keyed_calls` rule now declares `kind: WRITES` (or `DELETES`) and spells the stored qname
in its template; the rule edge is a HEURISTIC writer with `rule: true`, and a name that matches no
table links nothing and is counted.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, ConfigError, load_config
from code_atlas.enrichment import INDIRECTION_FILE, load_indirection_rules
from code_atlas.indexer import BuildReport, full_build
from code_atlas.store import GraphStore
from code_atlas.tools import check_column_defaults, find_references
from tests.php_adapter_cli import ENTRY as PHP_ENTRY
from tests.php_adapter_cli import PHP, needs_php

NODE = shutil.which("node")
SQL_ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {SQL_ENTRY}")

SCHEMA = """\
CREATE TABLE dbo.Items (
    Id      int NOT NULL,
    Name    varchar(50) NOT NULL,
    Stamped datetime2 NULL DEFAULT (sysdatetime())
);
GO
CREATE PROCEDURE dbo.Insert_Item
AS
    INSERT INTO dbo.Items (Id, Name) VALUES (1, 'x');
GO
"""

PAGE = """\
<?php
function addItem($row) { queryInsert('Items', $row); }
function dropItem($id) { queryDelete('Items', $id); }
function addWidget($row) { queryInsert('Widgetz', $row); }
function addFromVar($row, $table) { queryInsert($table, $row); }
"""

TABLE = "dbo.{key}"
RULES = {
    "keyed_calls": [
        {"setter": "\\queryInsert", "key_arg": 1, "kind": "WRITES", "target_template": TABLE},
        {"setter": "\\queryDelete", "key_arg": 1, "kind": "DELETES", "target_template": TABLE},
    ]
}


def _build(root: Path, *, rules: bool) -> tuple[Config, BuildReport]:
    (root / "db").mkdir()
    (root / "db" / "001_items.sql").write_text(SCHEMA, encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "page.php").write_text(PAGE, encoding="utf-8")
    env = {
        "CA_WORKERS": "1",
        "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"]),
    }
    if rules:
        (root / "rules.json").write_text(json.dumps(RULES), encoding="utf-8")
        env["CA_INDIRECTION_RULES"] = "rules.json"
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    config = load_config(root, env)
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
    assert report.failed == 0
    return config, report


@needs_php
@needs_node
def test_a_table_named_by_a_string_lists_its_php_writer(tmp_path: Path) -> None:
    """AC1 — `find_references dbo.Items` lists `addItem` beside the SQL writer, rule-flagged."""
    config, _ = _build(tmp_path, rules=True)
    payload = find_references.create(config)("dbo.Items")
    by_source = {str(hit["qname"]): hit for hit in payload["results"]}
    assert "dbo.Insert_Item" in by_source
    assert "\\addItem" in by_source, sorted(by_source)
    php = by_source["\\addItem"]
    assert php["kind"] == "WRITES"
    assert php["confidence_tier"] == "HEURISTIC"
    assert php["rule"] is True
    deleter = by_source["\\dropItem"]
    assert deleter["kind"] == "DELETES"
    assert "\\addFromVar" not in by_source  # a variable names no table


@needs_php
@needs_node
def test_a_rule_writer_without_columns_is_unmeasured_not_an_omitter(tmp_path: Path) -> None:
    """AC2 — the rule edge names no column, so it never reads as omitting `Stamped`."""
    config, _ = _build(tmp_path, rules=True)
    payload = check_column_defaults.create(config)(table="dbo.Items", column="Stamped")
    [row] = payload["results"]
    assert "\\addItem" not in row.get("omitted_by", [])
    assert row["omitted_by"] == ["dbo.Insert_Item"]
    assert row["unmeasured"] == ["\\addItem"]


@needs_php
@needs_node
def test_a_name_that_matches_no_table_links_nothing_and_is_counted(tmp_path: Path) -> None:
    """Scope 2 — `queryInsert('Widgetz')` stays an unlinked rule writer, counted once."""
    config, report = _build(tmp_path, rules=True)
    assert report.rule_keys_unresolved == 1
    with GraphStore(config.db_path) as store:
        rows = [
            row
            for row in store.edges_matching_kind("WRITES", limit=100)
            if row.get("file_path") == INDIRECTION_FILE
        ]
    assert {(row["target_raw"], bool(row["target_qname"])) for row in rows} == {
        ("dbo.Items", True),
        ("dbo.Widgetz", False),
    }


@needs_php
@needs_node
def test_without_the_rule_the_table_has_sql_writers_only(tmp_path: Path) -> None:
    """AC3 — no rule, no rule writer; the graph is what it was."""
    config, report = _build(tmp_path, rules=False)
    payload = find_references.create(config)("dbo.Items")
    assert sorted(str(hit["qname"]) for hit in payload["results"]) == ["dbo.Insert_Item"]
    assert report.rule_keys_unresolved == 0


@pytest.mark.parametrize(
    ("kind", "template", "message"),
    [
        ("ALTERS", "dbo.{key}", "kind"),
        ("WRITES", "dbo.{key}::Name", "Table"),
        ("DELETES", "dbo.T::{key}", "Table"),
    ],
)
def test_a_malformed_write_rule_fails_loud(
    tmp_path: Path, kind: str, template: str, message: str
) -> None:
    """R5.3 — only CALLS/WRITES/DELETES, and a write rule names a Table, never a column."""
    rule = {"setter": "q", "key_arg": 1, "kind": kind, "target_template": template}
    (tmp_path / "rules.json").write_text(json.dumps({"keyed_calls": [rule]}), encoding="utf-8")
    config = load_config(tmp_path, {"CA_INDIRECTION_RULES": "rules.json"})
    with pytest.raises(ConfigError, match=message):
        load_indirection_rules(config)


def _build_with(root: Path, page: str, rules: dict) -> tuple[Config, BuildReport]:
    (root / "db").mkdir()
    (root / "db" / "001_items.sql").write_text(SCHEMA, encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "page.php").write_text(page, encoding="utf-8")
    (root / "rules.json").write_text(json.dumps(rules), encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    config = load_config(
        root,
        {
            "CA_WORKERS": "1",
            "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
            "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"]),
            "CA_INDIRECTION_RULES": "rules.json",
        },
    )
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
    return config, report


@needs_php
@needs_node
def test_a_linked_rule_of_one_kind_does_not_hide_an_unlinked_one_of_another(
    tmp_path: Path,
) -> None:
    """Challenger F2 — `dbo.items`: WRITES links case-insensitively (215), CALLS does not."""
    rules = {
        "keyed_calls": [
            {"setter": "\\queryInsert", "key_arg": 1, "kind": "WRITES", "target_template": TABLE},
            {"setter": "\\queryInsert", "key_arg": 1, "target_template": TABLE},
        ]
    }
    page = "<?php\nfunction addItem($row) { queryInsert('items', $row); }\n"
    _, report = _build_with(tmp_path, page, rules)
    assert report.rules_unresolved == 1  # the CALLS rule's own row never linked
    assert report.rule_keys_unresolved == 0  # the site linked under the WRITES rule


@needs_php
@needs_node
def test_a_key_that_names_a_member_writes_nothing(tmp_path: Path) -> None:
    """Challenger F6 — a pattern capturing `Items::Name` would name a column: no edge at all."""
    rules = {
        "keyed_calls": [
            {
                "setter": "\\queryInsert",
                "key_arg": 1,
                "kind": "WRITES",
                "key_pattern": "(.+)",
                "target_template": TABLE,
            }
        ]
    }
    page = "<?php\nfunction addName($row) { queryInsert('Items::Name', $row); }\n"
    config, _ = _build_with(tmp_path, page, rules)
    payload = find_references.create(config)("dbo.Items")
    assert "\\addName" not in {str(hit["qname"]) for hit in payload["results"]}


@needs_php
@needs_node
def test_a_write_key_in_another_case_links_like_any_writer(tmp_path: Path) -> None:
    """215's case-insensitive arm applies to a rule WRITES too, as TOOLS.md says."""
    rules = {
        "keyed_calls": [
            {"setter": "\\queryInsert", "key_arg": 1, "kind": "WRITES", "target_template": TABLE}
        ]
    }
    page = "<?php\nfunction addItem($row) { queryInsert('items', $row); }\n"
    config, report = _build_with(tmp_path, page, rules)
    payload = find_references.create(config)("dbo.Items")
    assert "\\addItem" in {str(hit["qname"]) for hit in payload["results"]}
    assert report.rule_keys_unresolved == 0
