"""Task 062: producer-side PROVIDES_VIEW_DATA edges from view_data rules."""

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
from code_atlas.tools import find_view_data

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
FIXTURES = REPO / "tests" / "fixtures" / "view_databag"

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

HANDLER = "\\App\\OrderController::index"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / ".code-atlas" / "graph.db") as opened:
        yield opened


def _plant(root: Path) -> None:
    src = root / "src"
    src.mkdir()
    shutil.copy(FIXTURES / "handler.php", src / "handler.php")
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


@needs_php
def test_handler_publish_keys_queryable_with_rules(tmp_path: Path, store: GraphStore) -> None:
    """Rules on ⇒ find_view_data returns planted keys (string + array_keys); HEURISTIC + rule."""
    _plant(tmp_path)
    config = load_config(tmp_path, _php_env(tmp_path, rules=True))
    assert full_build(config, store).failed == 0

    edges = store.edges_by_source(HANDLER, kinds=(contract.PROVIDES_VIEW_DATA,), limit=20)
    assert edges, "expected PROVIDES_VIEW_DATA edges from the view_data rules"
    # assign/put lines + setData array line: items/title each appear twice (different lines).
    keys = {
        contract.VIEW_DATA_PREFIX + "items",
        contract.VIEW_DATA_PREFIX + "title",
        contract.VIEW_DATA_PREFIX + "extra",
    }
    assert {row["target_raw"] for row in edges} == keys
    assert len(edges) == 5
    assert all(row["confidence_tier"] == "HEURISTIC" for row in edges)
    assert all(row["file_path"] == INDIRECTION_FILE for row in edges)

    tool = find_view_data.create(config)
    payload = tool(HANDLER)
    assert payload["reason"] == "ok"
    assert payload["total_count"] == 5
    assert {hit["key"] for hit in payload["results"]} == {"items", "title", "extra"}
    for hit in payload["results"]:
        assert hit[contract.RULE_FLAG] is True
        assert hit["confidence_tier"] == "HEURISTIC"
        assert hit["kind"] == contract.PROVIDES_VIEW_DATA
        assert isinstance(hit["line"], int) and hit["line"] >= 1
        assert hit.get("file") == "src/handler.php"


@needs_php
def test_without_rules_no_view_data_edges(tmp_path: Path, store: GraphStore) -> None:
    """AC5: no CA_INDIRECTION_RULES ⇒ graph has no PROVIDES_VIEW_DATA."""
    _plant(tmp_path)
    config = load_config(tmp_path, _php_env(tmp_path, rules=False))
    assert full_build(config, store).failed == 0

    edges = store.edges_matching_kind(contract.PROVIDES_VIEW_DATA, limit=20)
    assert edges == []
    payload = find_view_data.create(config)(HANDLER)
    assert payload["total_count"] == 0
    assert payload["results"] == []


@needs_php
def test_array_literal_keys_are_recorded_on_calls(tmp_path: Path, store: GraphStore) -> None:
    """Adapter emits arg_keys for top-level string keys; non-literal keys do not shift."""
    _plant(tmp_path)
    config = load_config(tmp_path, _php_env(tmp_path, rules=False))
    assert full_build(config, store).failed == 0

    calls = [
        row
        for row in store.edges_by_source(HANDLER, kinds=("CALLS",), limit=20)
        if row["target_raw"] == "setData" or str(row["target_raw"]).endswith("::setData")
    ]
    assert len(calls) == 1
    raw_keys = calls[0]["arg_keys"]
    if isinstance(raw_keys, str):
        import json

        raw_keys = json.loads(raw_keys)
    assert raw_keys == [["items", "title"]]
