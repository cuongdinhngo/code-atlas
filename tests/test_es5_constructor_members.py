"""Task 395 — the ES5 constructor pattern declares Methods of the function that constructs."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import file_outline, find_callers, search_symbol
from tests.ts_adapter_cli import ENTRY as TS_ENTRY
from tests.ts_adapter_cli import NODE, needs_node

pytestmark = needs_node

CTRL = (
    "function EditCtrl($scope) {\n"  # 1
    "  var self = this;\n"  # 2
    "  self.save = function (item) { self.check(item); };\n"  # 3
    "  this.check = function () {};\n"  # 4
    "  $scope.reset = function () {};\n"  # 5
    "  function inner() { this.own = function () {}; }\n"  # 6
    "}\n"  # 7
    "var ListCtrl = function () { this.refresh = () => 1; };\n"  # 8
)


@pytest.fixture
def config(tmp_path: Path) -> Config:
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "ctrl.js").write_text(CTRL, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A")):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    built = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_TYPESCRIPT_CMD": shlex.join([str(NODE), str(TS_ENTRY), "--server"]),
        },
    )
    with GraphStore(built.db_path) as store:
        assert full_build(built, store).failed == 0
    return built


def test_ac1_a_member_assigned_on_self_is_a_method_of_the_function(config: Config) -> None:
    payload = search_symbol.create(config)("save", detail_level="standard")
    rows = payload["results"]
    assert isinstance(rows, list)
    assert [(row["qname"], row["kind"]) for row in rows] == [
        ("web/ctrl.js::EditCtrl::save", "Method")
    ]


def test_this_a_variable_bound_function_and_a_nested_function_own_their_members(
    config: Config,
) -> None:
    outline = file_outline.create(config)("web/ctrl.js")
    symbols = outline["results"]
    assert isinstance(symbols, list)
    methods = {(str(s["qname"]), int(s["line_start"])) for s in symbols if s["kind"] == "Method"}
    assert methods == {
        ("web/ctrl.js::EditCtrl::save", 3),
        ("web/ctrl.js::EditCtrl::check", 4),
        ("web/ctrl.js::EditCtrl::inner::own", 6),
        ("web/ctrl.js::ListCtrl::refresh", 8),
    }


def test_a_members_body_is_sourced_at_the_member(config: Config) -> None:
    payload = find_callers.create(config)("web/ctrl.js::EditCtrl::check", detail_level="minimal")
    rows = payload["results"]
    assert isinstance(rows, list)
    assert [row["qname"] for row in rows] == ["web/ctrl.js::EditCtrl::save"]
