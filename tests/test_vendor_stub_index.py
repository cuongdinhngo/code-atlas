"""Task 039: opt-in declarations-only indexing of dependency roots (vendor stubs)."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.adapter import ParseResult, SubprocessAdapter
from code_atlas.config import load_config
from code_atlas.indexer import (
    as_stub_result,
    collect_stubs,
    full_build,
    is_stub_path,
)
from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol, search_symbol

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

NODE_COLUMNS = ", ".join(contract.NODE_FIELDS)
EDGE_COLUMNS = ", ".join(contract.EDGE_FIELDS)

APP_PHP = """<?php
namespace App;
class User extends \\Lib\\Model
{
    public function save(): void
    {
        helper();
    }
}
"""

VENDOR_PHP = """<?php
namespace Lib;
class Model
{
    public function touch(): void
    {
        \\Lib\\Helper::ping();
        new \\Lib\\Other();
    }
}
class Helper
{
    public static function ping(): void {}
}
class Other {}
"""


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / ".code-atlas" / "graph.db") as opened:
        yield opened


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)


def _plant(root: Path) -> None:
    (root / "src").mkdir()
    (root / "src" / "User.php").write_text(APP_PHP, encoding="utf-8")
    vendor = root / "vendor" / "lib" / "src"
    vendor.mkdir(parents=True)
    (vendor / "Model.php").write_text(VENDOR_PHP, encoding="utf-8")
    _git_init(root)


def _php_env(root: Path, *, stubs: bool) -> dict[str, str]:
    env = {
        "CA_WORKERS": "2",
        "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
    }
    if stubs:
        env["CA_STUB_ROOTS"] = "vendor"
    return env


def _graph_rows(store: GraphStore) -> tuple[list[tuple], list[tuple]]:
    nodes = store._conn.execute(
        f"SELECT {NODE_COLUMNS} FROM nodes ORDER BY qualified_name, file_path, line_start"
    ).fetchall()
    edges = store._conn.execute(
        f"SELECT {EDGE_COLUMNS} FROM edges "
        "ORDER BY kind, source_qname, target_raw, file_path, line"
    ).fetchall()
    return nodes, edges


def test_collect_stubs_bypasses_ignore_and_is_stub_path(tmp_path: Path) -> None:
    (tmp_path / "vendor" / "pkg").mkdir(parents=True)
    (tmp_path / "vendor" / "pkg" / "A.php").write_text("<?php\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "App.php").write_text("<?php\n", encoding="utf-8")
    found = collect_stubs(tmp_path, ("vendor",), (".php",))
    assert found == ("vendor/pkg/A.php",)
    assert is_stub_path("vendor/pkg/A.php", ("vendor",))
    assert not is_stub_path("src/App.php", ("vendor",))
    assert not is_stub_path("vendor/pkg/A.php", None)


def test_as_stub_result_stamps_extra_and_drops_caller_kinds() -> None:
    result = ParseResult(
        path="vendor/x.php",
        ok=True,
        nodes=(
            {
                "kind": "Class",
                "name": "X",
                "qualified_name": "\\X",
                "file_path": "vendor/x.php",
                "line_start": 1,
                "extra": '{"attributes":[]}',
            },
        ),
        edges=(
            {
                "kind": "EXTENDS",
                "source_qname": "\\X",
                "target_raw": "\\Y",
                "file_path": "vendor/x.php",
                "line": 1,
            },
            {
                "kind": "CALLS",
                "source_qname": "\\X::m",
                "target_raw": "ping",
                "file_path": "vendor/x.php",
                "line": 2,
            },
            {
                "kind": "NEW",
                "source_qname": "\\X::m",
                "target_raw": "\\Z",
                "file_path": "vendor/x.php",
                "line": 3,
            },
        ),
    )
    stamped = as_stub_result(result)
    assert len(stamped.edges) == 1
    assert stamped.edges[0]["kind"] == "EXTENDS"
    extra = json.loads(str(stamped.nodes[0]["extra"]))
    assert extra["stub"] is True
    assert extra["attributes"] == []


@needs_php
def test_declarations_only_skips_body_calls_in_php_adapter(tmp_path: Path) -> None:
    """Adapter-side: declarations_only emits no CALLS/NEW from method bodies."""
    path = "body.php"
    (tmp_path / path).write_text(
        "<?php\nnamespace N;\nclass C {\n  public function m(): void {\n"
        "    \\N\\Helper::ping();\n    new \\N\\Other();\n  }\n}\n"
        "class Helper { public static function ping(): void {}\n}\n"
        "class Other {}\n",
        encoding="utf-8",
    )
    cmd = (str(PHP), str(PHP_ENTRY), "--server")
    adapter = SubprocessAdapter("php", cmd, tmp_path)
    adapter.start()
    try:
        full = adapter.parse(path)
        decls = adapter.parse(path, declarations_only=True)
    finally:
        adapter.stop()
    assert full.ok and decls.ok
    full_kinds = {str(e["kind"]) for e in full.edges}
    assert "CALLS" in full_kinds or "NEW" in full_kinds
    assert not any(str(e["kind"]) in contract.CALLER_KINDS for e in decls.edges)
    assert any(n.get("qualified_name") == "\\N\\C::m" for n in decls.nodes)


@needs_php
def test_stub_indexing_resolves_extends_and_marks_stubs(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1 proving: planted vendor EXTENDS becomes RESOLVED; stubs are marked."""
    _plant(tmp_path)
    config = load_config(tmp_path, _php_env(tmp_path, stubs=True))
    report = full_build(config, store)
    assert report.failed == 0
    assert "vendor/lib/src/Model.php" in store.file_paths()

    extends = store.edges_by_source("\\App\\User", kinds=("EXTENDS",), limit=10)
    assert len(extends) == 1
    assert extends[0]["target_qname"] == "\\Lib\\Model"
    assert extends[0]["confidence_tier"] == "RESOLVED"

    model = store.nodes_by_qualified_name("\\Lib\\Model", limit=1)[0]
    assert json.loads(str(model["extra"]))["stub"] is True

    vendor_edges = [
        row
        for row in store._conn.execute(
            "SELECT kind FROM edges WHERE file_path LIKE 'vendor/%'"
        ).fetchall()
    ]
    assert not any(kind[0] in contract.CALLER_KINDS for kind in vendor_edges)

    search = search_symbol.create(config)("Model", kind="Class", detail_level="minimal")
    stub_hits = [h for h in search["results"] if h["qname"] == "\\Lib\\Model"]
    assert stub_hits and stub_hits[0].get("stub") is True

    read = read_symbol.create(config)("\\Lib\\Model", detail_level="minimal")
    assert read["found"] is True and read.get("stub") is True


@needs_php
def test_stubs_off_by_default_matches_build_without_vendor_rows(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC3: default (stubs off) leaves vendor unindexed; two off builds match."""
    _plant(tmp_path)
    config = load_config(tmp_path, _php_env(tmp_path, stubs=False))
    first = full_build(config, store)
    assert first.failed == 0
    assert all(not p.startswith("vendor/") for p in store.file_paths())
    extends = store.edges_by_source("\\App\\User", kinds=("EXTENDS",), limit=10)
    assert extends[0]["target_qname"] is None
    snap = _graph_rows(store)

    with GraphStore(tmp_path / "second.db") as other:
        second = full_build(load_config(tmp_path, _php_env(tmp_path, stubs=False)), other)
        assert second.failed == 0
        assert _graph_rows(other) == snap


def test_fake_adapter_stub_root_stamps_nodes(tmp_path: Path, store: GraphStore) -> None:
    """Core path: stub walk + stamp works with the language-agnostic fake adapter."""
    import sys

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.aa").write_text("app\n", encoding="utf-8")
    (tmp_path / "vendor" / "pkg").mkdir(parents=True)
    (tmp_path / "vendor" / "pkg" / "lib.aa").write_text("lib\n", encoding="utf-8")
    _git_init(tmp_path)

    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
            "CA_STUB_ROOTS": "vendor",
        },
    )
    report = full_build(config, store)
    assert report.failed == 0
    assert "vendor/pkg/lib.aa" in store.file_paths()
    node = store.nodes_by_qualified_name("vendor/pkg/lib.aa::Thing", limit=1)[0]
    assert json.loads(str(node["extra"]))["stub"] is True
