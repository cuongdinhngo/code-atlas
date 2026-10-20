"""Task 406 — a PHP template's `ctrl.X(` / `ng-model` references and an asset list, by rule."""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, ConfigError, load_config
from code_atlas.enrichment import load_indirection_rules
from code_atlas.indexer import BuildReport, full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references
from tests.php_adapter_cli import ENTRY as PHP_ENTRY
from tests.php_adapter_cli import PHP, needs_php
from tests.ts_adapter_cli import ENTRY as TS_ENTRY
from tests.ts_adapter_cli import NODE, needs_node

pytestmark = [needs_php, needs_node]

EDIT = (
    '<div ng-controller="EditCtrl as ctrl">\n'  # 1
    '  <button ng-click="ctrl.save()">Save</button>\n'  # 2
    '  <button ng-click="ctrl.missing()">Gone</button>\n'  # 3
    '  <input ng-model="ctrl.pick">\n'  # 4
    "</div>\n"  # 5
    "<script>\n"  # 6
    "function EditCtrl() {\n"  # 7
    "  var self = this;\n"  # 8
    "  self.save = function () {};\n"  # 9
    "  self.pick = function () {};\n"  # 10
    "}\n"  # 11
    "</script>\n"  # 12
)
# Two controllers bound to `ctrl` in one file: which one a reference names cannot be told.
TWO = (
    '<div ng-controller="ACtrl as ctrl"><a ng-click="ctrl.go()">a</a></div>\n'
    '<div ng-controller="BCtrl as ctrl"><a ng-click="ctrl.go()">b</a></div>\n'
    "<script>\n"
    "function ACtrl() { this.go = function () {}; }\n"
    "function BCtrl() { this.go = function () {}; }\n"
    "</script>\n"
)
PAGE = (
    "<?php\n"
    "class Page {\n"
    "  function head() {\n"
    "    $this->loadScripts(['js/app.js', $dynamic, 'js/' . $x, \"js/gone.js\"]);\n"
    "    $this->loadScripts(array('js/app.js'));\n"
    "  }\n"
    "}\n"
)
APP_JS = "function boot() {}\n"
PLAIN = "<?php\nfunction plain() { return 1; }\n"

CONTEXT = 'ng-controller="(?P<ctrl>[\\w$]+) as ctrl"'
RULES = {
    "template_refs": [
        {
            "files": ["web/*.php"],
            "context_pattern": CONTEXT,
            "pattern": "\\bctrl\\.(?P<member>[\\w$]+)\\(",
            "target_template": "{path}::{ctrl}::{member}",
        },
        {
            "files": ["web/*.php"],
            "context_pattern": CONTEXT,
            "pattern": 'ng-model="ctrl\\.(?P<member>[\\w$]+)',
            "target_template": "{path}::{ctrl}::{member}",
            "kind": "REFERENCES",
        },
    ],
    "keyed_calls": [
        {
            "setter": "loadScripts",
            "key_arg": 1,
            "key_from": "list",
            "target_template": "web/{key}",
        }
    ],
}
PHP_CMD = {"CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"])}
TS_CMD = {"CA_TYPESCRIPT_CMD": shlex.join([str(NODE), str(TS_ENTRY), "--server"])}


def _build(root: Path, rules: object | None) -> tuple[Config, BuildReport]:
    (root / "web" / "js").mkdir(parents=True)
    (root / "web" / "edit.php").write_text(EDIT, encoding="utf-8")
    (root / "web" / "two.php").write_text(TWO, encoding="utf-8")
    (root / "web" / "page.php").write_text(PAGE, encoding="utf-8")
    (root / "web" / "js" / "app.js").write_text(APP_JS, encoding="utf-8")
    (root / "lib.php").write_text(PLAIN, encoding="utf-8")
    env = {"CA_WORKERS": "1", **PHP_CMD, **TS_CMD}
    if rules is not None:
        (root / "rules.json").write_text(json.dumps(rules), encoding="utf-8")
        env["CA_INDIRECTION_RULES"] = "rules.json"
    for args in (("init", "-q"), ("add", "-A")):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    config = load_config(root, env)
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
    assert report.failed == 0
    return config, report


def _rows(answer: dict[str, object]) -> list[tuple[str, str, bool]]:
    rows = answer["results"]
    assert isinstance(rows, list)
    return sorted((str(r["qname"]), str(r["confidence_tier"]), bool(r.get("rule"))) for r in rows)


def test_ac1_a_template_call_is_a_heuristic_caller_and_a_miss_is_counted(tmp_path: Path) -> None:
    config, report = _build(tmp_path, RULES)
    callers = find_callers.create(config)("web/edit.php::EditCtrl::save", detail_level="minimal")
    assert callers["reason"] == "ok", callers
    assert _rows(callers) == [("web/edit.php", "HEURISTIC", True)]
    # `ctrl.missing(` names no member; `two.php`'s two `ctrl.go(` name no single controller;
    # `js/gone.js` names no file. Each is a site no rule linked.
    assert report.rule_keys_unresolved == 4
    assert report.rules_unresolved == 0


def test_a_model_binding_is_a_reference_of_the_member(tmp_path: Path) -> None:
    config, _ = _build(tmp_path, RULES)
    refs = find_references.create(config)("web/edit.php::EditCtrl::pick", detail_level="minimal")
    assert _rows(refs) == [("web/edit.php", "HEURISTIC", True)]
    callers = find_callers.create(config)("web/edit.php::EditCtrl::pick", detail_level="minimal")
    assert callers["results"] == []


def test_an_undecidable_controller_links_neither(tmp_path: Path) -> None:
    config, _ = _build(tmp_path, RULES)
    for qname in ("web/two.php::ACtrl::go", "web/two.php::BCtrl::go"):
        callers = find_callers.create(config)(qname, detail_level="minimal")
        assert callers["results"] == [], (qname, callers)


def test_a_list_of_asset_paths_names_each_file_once_per_site(tmp_path: Path) -> None:
    config, _ = _build(tmp_path, RULES)
    refs = find_references.create(config)("web/js/app.js", detail_level="standard")
    assert refs["reason"] == "ok", refs
    rows = refs["results"]
    assert isinstance(rows, list)
    assert _rows(refs) == [("\\Page::head", "HEURISTIC", True)] * 2
    with GraphStore(config.db_path) as store:
        lines = store._conn.execute(
            "SELECT line FROM edges WHERE target_qname = 'web/js/app.js' ORDER BY line"
        ).fetchall()
    # `[…]` and `array(…)` each name it once; `$dynamic`, a concatenation and `gone.js` do not.
    assert [row[0] for row in lines] == [4, 5]


def test_ac2_no_rule_writes_the_same_rows(tmp_path: Path) -> None:
    def rows(root: Path, rules: object | None) -> list[tuple[object, ...]]:
        config, _ = _build(root, rules)
        with GraphStore(config.db_path) as store:
            edges = store._conn.execute(
                "SELECT kind, source_qname, target_raw, target_qname, file_path, line "
                "FROM edges ORDER BY 1, 2, 3, 4, 5, 6"
            ).fetchall()
            nodes = store._conn.execute(
                "SELECT qualified_name, kind, file_path, line_start FROM nodes ORDER BY 1, 2, 3"
            ).fetchall()
        return [tuple(row) for row in (*edges, *nodes)]

    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    # A rule file with only an empty template_refs list is the off state too.
    assert rows(tmp_path / "a", None) == rows(tmp_path / "b", {"template_refs": []})


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ({"files": [], "pattern": "x(?P<m>y)", "target_template": "{m}"}, "files"),
        ({"files": ["*.php"], "pattern": "(", "target_template": "x"}, "pattern"),
        ({"files": ["*.php"], "pattern": "x(?P<m>y)", "target_template": "{n}"}, "placeholder"),
        (
            {
                "files": ["*.php"],
                "context_pattern": "(?P<m>z)",
                "pattern": "x(?P<m>y)",
                "target_template": "{m}",
            },
            "both",
        ),
        (
            {"files": ["*.php"], "pattern": "x(?P<m>y)", "target_template": "{m}", "kind": "NEW"},
            "kind",
        ),
    ],
)
def test_a_bad_template_rule_fails_loud(
    tmp_path: Path, entry: dict[str, object], message: str
) -> None:
    (tmp_path / "rules.json").write_text(json.dumps({"template_refs": [entry]}), encoding="utf-8")
    config = load_config(tmp_path, {"CA_INDIRECTION_RULES": "rules.json"})
    with pytest.raises(ConfigError, match=message):
        load_indirection_rules(config)
