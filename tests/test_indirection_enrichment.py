"""Task 040: framework indirection rules as data (core enrichment)."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import ConfigError, load_config
from code_atlas.enrichment import INDIRECTION_FILE, apply_indirection_rules
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
FIXTURES = REPO / "tests" / "fixtures" / "indirection"

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

NODE_COLUMNS = ", ".join(contract.NODE_FIELDS)
EDGE_COLUMNS = ", ".join(contract.EDGE_FIELDS)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / ".code-atlas" / "graph.db") as opened:
        yield opened


def _plant(root: Path) -> None:
    src = root / "src"
    src.mkdir()
    for name in ("app.php", "facade.php", "repository.php"):
        shutil.copy(FIXTURES / name, src / name)
    rules = root / "rules"
    rules.mkdir()
    shutil.copy(FIXTURES / "rules.json", rules / "rules.json")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)


def _php_env(root: Path, *, rules: bool) -> dict[str, str]:
    env = {
        "CA_WORKERS": "2",
        "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
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


@needs_php
def test_facade_rule_resolves_call_to_concrete_method(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1 proving: facade ALIASES remap Cache::get → Repository::get."""
    _plant(tmp_path)
    config = load_config(tmp_path, _php_env(tmp_path, rules=True))
    assert full_build(config, store).failed == 0

    calls = [
        row
        for row in store.edges_by_source("\\App\\Runner::run", kinds=("CALLS",), limit=20)
        if "get" in str(row["target_raw"]) or "get" in str(row["target_qname"] or "")
    ]
    assert calls, "expected a CALLS edge from Runner::run"
    assert any(
        row["target_qname"] == "\\Lib\\Cache\\Repository::get" for row in calls
    ), calls


@needs_php
def test_rules_synthesize_string_and_array_callable_calls(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1: rules `calls` entries yield HEURISTIC CALLS (string + array-callable shapes)."""
    _plant(tmp_path)
    config = load_config(tmp_path, _php_env(tmp_path, rules=True))
    assert full_build(config, store).failed == 0

    string_hits = store.edges_by_source(
        "\\App\\Hooks::register", kinds=("CALLS",), limit=20
    )
    targets = {(row["target_raw"], row["confidence_tier"]) for row in string_hits}
    assert ("\\App\\on_save", "HEURISTIC") in targets
    assert ("\\App\\Controller::store", "HEURISTIC") in targets
    linked = [row for row in string_hits if row["target_qname"]]
    assert any(row["target_qname"] == "\\App\\on_save" for row in linked)
    assert any(row["target_qname"] == "\\App\\Controller::store" for row in linked)


@needs_php
def test_rules_off_leaves_graph_unchanged(tmp_path: Path, store: GraphStore) -> None:
    """AC2: no rules ⇒ no synthetic file; two off builds match."""
    _plant(tmp_path)
    config = load_config(tmp_path, _php_env(tmp_path, rules=False))
    first = full_build(config, store)
    assert first.failed == 0
    assert INDIRECTION_FILE not in store.file_paths()
    snap = _graph_rows(store)

    with GraphStore(tmp_path / "second.db") as other:
        second = full_build(load_config(tmp_path, _php_env(tmp_path, rules=False)), other)
        assert second.failed == 0
        assert _graph_rows(other) == snap


@needs_php
def test_rule_edges_are_heuristic_not_resolved(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC3: rule-emitted edges stay HEURISTIC (never silent RESOLVED)."""
    _plant(tmp_path)
    config = load_config(tmp_path, _php_env(tmp_path, rules=True))
    assert full_build(config, store).failed == 0
    rule_edges = store._conn.execute(
        "SELECT kind, confidence_tier FROM edges WHERE file_path = ?",
        (INDIRECTION_FILE,),
    ).fetchall()
    assert rule_edges
    assert all(tier == "HEURISTIC" for _kind, tier in rule_edges)


def test_missing_rules_file_fails_loud(tmp_path: Path, store: GraphStore) -> None:
    config = load_config(
        tmp_path,
        {"CA_INDIRECTION_RULES": "missing/rules.json", "CA_WORKERS": "1"},
    )
    with pytest.raises(ConfigError, match="not a file"):
        apply_indirection_rules(config, store)
