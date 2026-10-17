"""Task 398 — a keyed_calls string key is read from the edge, not from the call's first line.

The adapters capture a plain string literal's value beside its `args` category (contract v16), so a
call wrapped after `(`, two calls on one line, and a PHP 8 named argument all name their key. A
site that passed a string literal where the key is, yet named none, is counted in `keys_unread`.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from code_atlas import contract
from code_atlas.config import Config, ConfigError, load_config
from code_atlas.enrichment import load_indirection_rules
from code_atlas.indexer import BuildReport, full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_references, get_index_status
from tests.php_adapter_cli import CLI as PHP_CLI
from tests.php_adapter_cli import ENTRY as PHP_ENTRY
from tests.php_adapter_cli import PHP, needs_php
from tests.python_adapter_cli import CLI as PY_CLI
from tests.sql_adapter_cli import CLI as SQL_CLI
from tests.ts_adapter_cli import CLI as TS_CLI

NODE = shutil.which("node")
SQL_ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {SQL_ENTRY}")

SCHEMA = """\
CREATE TABLE dbo.Items (Id int NOT NULL, Name varchar(50) NOT NULL);
GO
CREATE TABLE dbo.Orders (Id int NOT NULL);
GO
CREATE TABLE dbo.Lines (Id int NOT NULL);
GO
"""

PAGE = """\
<?php
function wrapped($row) {
    insertRow(
        'Items',
        $row
    );
}
function twoOnALine($a, $b) { insertRow('Orders', $a); insertRow('Lines', $b); }
function fromVar($table, $row) { insertRow($table, $row); }
function named($row) { insertRow(row: $row, table: 'Lines'); }
function interpolated($id, $row) { insertRow("Items_$id", $row); }
"""

RULES = {
    "keyed_calls": [
        {
            "setter": "\\insertRow",
            "key_arg": 1,
            "key_kw": "table",
            "kind": "WRITES",
            "target_template": "dbo.{key}",
        }
    ]
}


def _build(root: Path, rules: dict[str, Any] = RULES) -> tuple[Config, BuildReport]:
    (root / "db").mkdir()
    (root / "db" / "001_items.sql").write_text(SCHEMA, encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "page.php").write_text(PAGE, encoding="utf-8")
    (root / "rules.json").write_text(json.dumps(rules), encoding="utf-8")
    env = {
        "CA_WORKERS": "1",
        "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"]),
        "CA_INDIRECTION_RULES": "rules.json",
    }
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    config = load_config(root, env)
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
    assert report.failed == 0
    return config, report


def _writers(config: Config, table: str) -> set[str]:
    payload = find_references.create(config)(table)
    return {str(hit["qname"]) for hit in payload["results"] if hit.get("rule") is True}


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Config, BuildReport]:
    return _build(tmp_path_factory.mktemp("repo"))


@needs_php
@needs_node
def test_ac1_a_wrapped_call_names_its_table(built: tuple[Config, BuildReport]) -> None:
    """AC1 (proving test): the key sits two lines below the call's `(`, and still links."""
    assert "\\wrapped" in _writers(built[0], "dbo.Items")


@needs_php
@needs_node
def test_ac2_two_calls_on_one_line_both_link(built: tuple[Config, BuildReport]) -> None:
    """AC2: 352's skip is gone — each call's own literal names its own table."""
    config, _ = built
    assert "\\twoOnALine" in _writers(config, "dbo.Orders")
    assert "\\twoOnALine" in _writers(config, "dbo.Lines")


@needs_php
@needs_node
def test_ac3_a_variable_key_links_nothing_and_is_not_unread(
    built: tuple[Config, BuildReport],
) -> None:
    """AC3: `$table` is no literal, so nothing links and only the interpolated site is unread."""
    config, report = built
    every = set().union(*(_writers(config, t) for t in ("dbo.Items", "dbo.Orders", "dbo.Lines")))
    assert "\\fromVar" not in every
    [census] = report.keys_unread
    assert census == {
        "setter": "\\insertRow",
        "kind": "WRITES",
        "key_arg": 1,
        "key_kw": "table",
        "keys_unread": 1,  # `"Items_$id"`: a string literal with no value, on one line or many
    }
    status = get_index_status.create(config, (get_index_status.NAME,))()
    assert status["keys_unread"] == [census]


@needs_php
@needs_node
def test_ac4_a_named_argument_names_its_table(built: tuple[Config, BuildReport]) -> None:
    """AC4: `insertRow(row: $row, table: 'Lines')` under `key_kw: "table"` links."""
    assert "\\named" in _writers(built[0], "dbo.Lines")


@needs_php
def test_the_php_adapter_captures_values_and_named_arguments(tmp_path: Path) -> None:
    """The edge carries what the rule reads; a named argument leaves the positional list."""
    page = tmp_path / "p.php"
    page.write_text(
        "<?php\nf(\n  'a',\n  \"b$x\",\n  3\n);\ng(1, key: 'k', other: $v);\n", encoding="utf-8"
    )
    edges = {e["target_raw"]: e for e in PHP_CLI.parse_file(str(page))["edges"]}

    assert edges["\\f"]["args"] == ["string", "string", "number"]
    assert edges["\\f"][contract.ARG_STRINGS_FIELD] == ["a", None, None]
    assert edges["\\f"][contract.KWARGS_FIELD] == {}
    assert edges["\\g"]["args"] == ["number"]
    assert edges["\\g"][contract.KWARGS_FIELD] == {"key": "string", "other": None}
    assert edges["\\g"][contract.KWARG_STRINGS_FIELD] == {"key": "k"}
    assert contract.ARG_STRINGS_FIELD not in edges["\\g"]  # no positional string to capture


@needs_php
@needs_node
def test_an_interpolated_key_is_counted_unread(tmp_path: Path) -> None:
    """Scope 4: a string literal the adapter could not value is counted, wrapped or not."""
    rules = {"keyed_calls": [{**RULES["keyed_calls"][0], "key_kw": None}]}
    del rules["keyed_calls"][0]["key_kw"]
    page = "<?php\nfunction f($id, $row) {\n    insertRow(\n        \"Items_$id\", $row);\n}\n"
    (tmp_path / "x").mkdir()
    config, report = _build(tmp_path / "x", rules)
    (config.root / "src" / "page.php").write_text(page, encoding="utf-8")
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)

    assert report.keys_unread[0]["keys_unread"] == 1


def test_key_kw_needs_a_string_key(tmp_path: Path) -> None:
    rules = {"keyed_calls": [{**RULES["keyed_calls"][0], "key_from": "array_keys"}]}
    (tmp_path / "rules.json").write_text(json.dumps(rules), encoding="utf-8")
    config = load_config(tmp_path, {"CA_INDIRECTION_RULES": "rules.json"})
    with pytest.raises(ConfigError, match="key_kw"):
        load_indirection_rules(config)


def test_key_kw_alone_needs_no_key_arg(tmp_path: Path) -> None:
    rule = {k: v for k, v in RULES["keyed_calls"][0].items() if k != "key_arg"}
    (tmp_path / "rules.json").write_text(json.dumps({"keyed_calls": [rule]}), encoding="utf-8")
    config = load_config(tmp_path, {"CA_INDIRECTION_RULES": "rules.json"})
    payload = load_indirection_rules(config)
    assert payload is not None
    assert (payload.keyed_calls[0].key_arg, payload.keyed_calls[0].key_kw) == (0, "table")


@needs_php
@needs_node
def test_a_key_the_pattern_refuses_is_not_unread(tmp_path: Path) -> None:
    """Exposure-check 2: a key read and refused by `key_pattern` is no route, not a miss (361)."""
    rule = {**RULES["keyed_calls"][0], "key_pattern": "^(Items)$"}
    _, report = _build(tmp_path, {"keyed_calls": [rule]})

    assert report.keys_unread[0]["keys_unread"] == 1  # `"Items_$id"` only; Orders/Lines were read


def _edges_by_target(payload: dict[str, Any]) -> dict[str, Any]:
    return {str(e["target_raw"]).rsplit(".", 1)[-1]: e for e in payload["edges"] if e.get("args")}


def test_challenger_the_python_adapter_captures_values(tmp_path: Path) -> None:
    """Challenger M2: each `args` adapter emits the field; a null is a string with no value."""
    page = tmp_path / "p.py"
    source = "def run(v):\n    put(\n        'a',\n        f'b{v}',\n        key='k',\n    )\n"
    page.write_text(source)
    edge = _edges_by_target(PY_CLI.parse_file(str(page)))["put"]

    assert edge["args"] == ["string", "string"]
    assert edge[contract.ARG_STRINGS_FIELD] == ["a", None]
    assert edge[contract.KWARG_STRINGS_FIELD] == {"key": "k"}


@TS_CLI.availability
def test_challenger_the_typescript_adapter_captures_values(tmp_path: Path) -> None:
    page = tmp_path / "p.ts"
    page.write_text("function run(v: string) {\n  put(\n    'a',\n    `b${v}`,\n    3);\n}\n")
    edge = _edges_by_target(TS_CLI.parse_file(str(page)))["put"]

    assert edge[contract.ARG_STRINGS_FIELD] == ["a", None, None]


@SQL_CLI.availability
def test_challenger_the_sql_adapter_keeps_the_line_read(tmp_path: Path) -> None:
    """W6: the SQL scanner masks a literal's body before it reads EXEC args, so it captures none."""
    page = tmp_path / "p.sql"
    page.write_text("CREATE PROCEDURE dbo.A AS\n    EXEC dbo.B @name = N'x', @n = 3;\nGO\n")
    edge = _edges_by_target(SQL_CLI.parse_file(str(page)))["B"]

    assert edge["args"] == ["string", "number"]
    assert contract.ARG_STRINGS_FIELD not in edge  # absent: the core reads the line, as before


def test_challenger_ac5_an_edge_without_values_reads_the_line_as_before(tmp_path: Path) -> None:
    """AC5: a pre-bump edge (no `arg_strings`) still names a one-line key from its source line."""
    from code_atlas.enrichment import _keys_for_rule

    (tmp_path / "a.php").write_text("<?php\ninsertRow('Items', $row);\n", encoding="utf-8")
    config = load_config(tmp_path, {})
    edge: dict[str, object] = {"target_raw": "\\insertRow", "args": ["string", None]}

    keys = _keys_for_rule(config, edge, edge["args"], 1, "string", "a.php", 2, {})
    unvalued = {**edge, contract.ARG_STRINGS_FIELD: [None, None]}
    none = _keys_for_rule(config, unvalued, edge["args"], 1, "string", "a.php", 2, {})

    assert (keys, none) == (["Items"], [])  # a v16 null is never re-read from the line


@needs_php
def test_cross_repo_a_binary_literal_is_not_captured(tmp_path: Path) -> None:
    """P8 (brick_math): a non-UTF-8 literal has no JSON value; the file must still parse."""
    page = tmp_path / "b.php"
    page.write_text("<?php\nf(\"\\xff\\xfe\", 'ok');\n", encoding="utf-8")
    payload = PHP_CLI.parse_file(str(page))

    assert payload["ok"] is True
    [edge] = [e for e in payload["edges"] if e["target_raw"] == "\\f"]
    assert edge[contract.ARG_STRINGS_FIELD] == [None, "ok"]
