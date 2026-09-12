"""Task 256 — keyed_calls target_template may resolve to a File node.

Field shape: a .js file holding a bare filename string, a PHP file of that name, no
symbol relation. Zero hits before the rule; the dispatch site after (AC1/AC2).
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import load_config
from code_atlas.enrichment import INDIRECTION_FILE
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
TS_ENTRY = REPO / "adapters" / "typescript" / "index.js"
FIXTURES = REPO / "tests" / "fixtures" / "dispatch_file"

PHP = shutil.which("php")
NODE = shutil.which("node")
needs_adapters = pytest.mark.skipif(
    PHP is None or NODE is None or not PHP_AUTOLOAD.is_file(),
    reason="needs php+composer vendor and node for the TS adapter",
)

TARGET = "getMemberEvacReport.php"
NODE_COLUMNS = ", ".join(contract.NODE_FIELDS)
EDGE_COLUMNS = ", ".join(contract.EDGE_FIELDS)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / ".code-atlas" / "graph.db") as opened:
        yield opened


def _plant(root: Path, *, rules: str | None, missing: bool = False) -> None:
    src = root / "src"
    src.mkdir()
    js = FIXTURES / ("dispatch_missing.js" if missing else "dispatch.js")
    shutil.copy(js, src / "dispatch.js")
    if not missing:
        shutil.copy(FIXTURES / TARGET, root / TARGET)
    if rules is not None:
        rules_dir = root / "rules"
        rules_dir.mkdir()
        shutil.copy(FIXTURES / rules, rules_dir / "rules.json")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)


def _env(root: Path, *, rules: bool) -> dict[str, str]:
    env = {
        "CA_WORKERS": "2",
        "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        "CA_TS_CMD": shlex.join([str(NODE), str(TS_ENTRY), "--server"]),
    }
    if rules:
        env["CA_INDIRECTION_RULES"] = "rules/rules.json"
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


@needs_adapters
def test_file_shaped_rule_find_callers_and_references(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1/AC2/AC5 — after the rule, File subject returns HEURISTIC rule:true dispatch site."""
    _plant(tmp_path, rules="rules.json")
    config = load_config(tmp_path, _env(tmp_path, rules=True))
    report = full_build(config, store)
    assert report.failed == 0
    assert report.rules_unresolved == 0

    files = store.nodes_by_qualified_names([TARGET], kind="File", limit=2)
    assert len(files.get(TARGET, [])) == 1

    callers = find_callers.create(config)(TARGET, detail_level="minimal")
    assert callers["reason"] == "ok", callers
    assert callers["total_count"] >= 1
    hit = next(
        (
            row
            for row in callers["results"]
            if row.get(contract.RULE_FLAG) is True
            and row.get("confidence_tier") == "HEURISTIC"
        ),
        None,
    )
    assert hit is not None, callers["results"]
    assert hit.get("confidence_tier") != "RESOLVED"

    refs = find_references.create(config)(TARGET, detail_level="minimal")
    assert refs["reason"] == "ok", refs
    assert refs["total_count"] >= 1
    assert any(row.get(contract.RULE_FLAG) is True for row in refs["results"]), refs


@needs_adapters
def test_file_shaped_without_rule_is_zero(tmp_path: Path, store: GraphStore) -> None:
    """AC2 before — no rule ⇒ no edge between the JS string and the PHP File."""
    _plant(tmp_path, rules=None)
    config = load_config(tmp_path, _env(tmp_path, rules=False))
    assert full_build(config, store).failed == 0

    callers = find_callers.create(config)(TARGET, detail_level="minimal")
    assert callers["total_count"] == 0, callers
    refs = find_references.create(config)(TARGET, detail_level="minimal")
    assert refs["total_count"] == 0, refs


@needs_adapters
def test_file_shaped_off_is_byte_identical(tmp_path: Path, store: GraphStore) -> None:
    """AC3 — no CA_INDIRECTION_RULES ⇒ two builds produce identical rows (222 AC2 re-pin)."""
    _plant(tmp_path, rules=None)
    config = load_config(tmp_path, _env(tmp_path, rules=False))
    first = full_build(config, store)
    assert first.failed == 0
    assert first.rules_unresolved == 0
    assert INDIRECTION_FILE not in store.file_paths()
    snap = _graph_rows(store)

    with GraphStore(tmp_path / "second.db") as other:
        second = full_build(load_config(tmp_path, _env(tmp_path, rules=False)), other)
        assert second.failed == 0
        assert _graph_rows(other) == snap


@needs_adapters
def test_file_shaped_unresolved_reported_on_build_report(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC4 — file-shaped template matching nothing is loud on BuildReport."""
    _plant(tmp_path, rules="rules.json", missing=True)
    config = load_config(tmp_path, _env(tmp_path, rules=True))
    report = full_build(config, store)
    assert report.failed == 0
    assert report.rules_unresolved >= 1, report

    rule_calls = [
        row
        for row in store.calls_by_target_raw("noSuchDispatchTarget.php")
        if row.get("file_path") == INDIRECTION_FILE
    ]
    assert rule_calls, "expected synthetic CALLS edges from the misconfigured rule"
    assert all(not row.get("target_qname") for row in rule_calls)
