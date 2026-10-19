"""Task 399 — a PHP view's inline ``<script>`` is read by the JS adapter, at the view's own lines."""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import file_outline, find_callers
from tests.php_adapter_cli import ENTRY as PHP_ENTRY
from tests.php_adapter_cli import PHP, needs_php
from tests.ts_adapter_cli import ENTRY as TS_ENTRY
from tests.ts_adapter_cli import NODE, needs_node

pytestmark = [needs_php, needs_node]

VIEW = (
    "<?php $title = 'Pick'; ?>\n"  # 1
    "<html><head>\n"  # 2
    '<script type="text/ng-template" id="t">function notCode(){}</script>\n'  # 3
    "<script>\n"  # 4
    "var base = <?= json_encode($title) ?>;\n"  # 5
    "function onPick(item) {\n"  # 6
    "  helper(item);\n"  # 7
    "}\n"  # 8
    "</script>\n"  # 9
    '<script src="x.js">function external(){}</script>\n'  # 10
    '<script type="module">export function fromModule() {}</script>\n'  # 11
    "<!-- <script>function commented(){}</script> -->\n"  # 12
    "</head></html>\n"  # 13
    "<?php function render() { onPick(); echo '<script>function inString(){}</script>'; } ?>\n"  # 14
)
LIB_JS = "function helper(x) { return x; }\n"
LIB_PHP = "<?php\nfunction helper($x) { return $x; }\nfunction caller() { helper(1); }\n"
PLAIN = "<?php\nfunction plain() { return 1; }\n"


def _build(tmp_path: Path, env: dict[str, str]) -> Config:
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "view.php").write_text(VIEW, encoding="utf-8")
    (tmp_path / "web" / "lib.js").write_text(LIB_JS, encoding="utf-8")
    (tmp_path / "web" / "lib.php").write_text(LIB_PHP, encoding="utf-8")
    (tmp_path / "web" / "plain.php").write_text(PLAIN, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A")):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    built = load_config(tmp_path, {"CA_WORKERS": "1", **env})
    with GraphStore(built.db_path) as store:
        assert full_build(built, store).failed == 0
    return built


PHP_CMD = {"CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"])}
TS_CMD = {"CA_TYPESCRIPT_CMD": shlex.join([str(NODE), str(TS_ENTRY), "--server"])}


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return _build(tmp_path, {**PHP_CMD, **TS_CMD})


def _outline(config: Config, path: str) -> list[tuple[str, str, int]]:
    symbols = file_outline.create(config)(path)["results"]
    assert isinstance(symbols, list)
    return [(str(s["qname"]), str(s["kind"]), int(s["line_start"])) for s in symbols]


def _callers(config: Config, qname: str) -> list[str]:
    rows = find_callers.create(config)(qname, detail_level="minimal")["results"]
    assert isinstance(rows, list)
    return sorted(str(row["qname"]) for row in rows)


def test_ac1_a_script_function_is_a_symbol_of_the_view_at_its_true_line(config: Config) -> None:
    rows = _outline(config, "web/view.php")
    functions = {(qname, line) for qname, kind, line in rows if kind == "Function"}
    assert functions == {
        ("web/view.php::onPick", 6),
        ("web/view.php::fromModule", 11),
        ("\\render", 14),
    }


def test_a_script_call_links_in_its_own_language_and_a_php_call_never_reaches_it(
    config: Config,
) -> None:
    assert _callers(config, "web/lib.js::helper") == ["web/view.php::onPick"]
    assert _callers(config, "\\helper") == ["\\caller"]
    assert _callers(config, "web/view.php::onPick") == []


def test_ac2_a_view_with_no_script_carries_no_region() -> None:
    from tests.php_adapter_cli import parse_file

    result = parse_file("tests/fixtures/php/global.php")
    assert result["ok"] is True
    assert "embedded" not in result


def test_a_region_nothing_reads_is_named_on_the_file(tmp_path: Path) -> None:
    built = _build(tmp_path, PHP_CMD)
    with GraphStore(built.db_path) as store:
        files = store.nodes_by_qualified_name("web/view.php", kind="File", limit=5)
    assert [json.loads(str(row["extra"])) for row in files] == [{"embedded_unread": [".js", ".mjs"]}]


def test_the_js_adapter_reads_only_the_spans_at_the_files_own_lines(tmp_path: Path) -> None:
    view = tmp_path / "v.php"
    view.write_text("<?php $a; ?>\n<script>\nfunction a(){}\n</script>\n<?php function b(){} ?>\n")
    source = view.read_bytes()
    start = source.index(b"<script>") + len(b"<script>")
    spans = [[start, source.index(b"</script>")]]
    request = json.dumps({"path": "v.php", "spans": spans, "suffix": ".js"})
    out = subprocess.run(
        [str(NODE), str(TS_ENTRY), "--server"],
        cwd=tmp_path,
        input=request + "\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    result = json.loads(out[1])
    rows = {(n["qualified_name"], n["line_start"]) for n in result["nodes"] if n["kind"] != "File"}
    assert rows == {("v.php::a", 3)}
