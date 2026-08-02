"""Task 014: search / outline / read + trigram FTS (M3 ship).

Proving path is integration: index PHP fixtures, then call the tools — the layer where a missing
registration, a wrong FTS tokenizer, or a whole-file read would fail.
"""

from __future__ import annotations

import asyncio
import shlex
import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from fastmcp import Client

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.main import build_server
from code_atlas.store import GraphStore
from code_atlas.tools import file_outline, prompts, read_symbol, search_symbol
from code_atlas.tools.prompts import PROMPT_NAMES

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
NAMESPACED = REPO / "tests" / "fixtures" / "php" / "namespaced.php"

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def db_config(tmp_path: Path) -> Config:
    return replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")


def index_namespaced(tmp_path: Path, store: GraphStore) -> Path:
    """Copy namespaced.php into a tiny git repo and full_build it."""
    src = tmp_path / "src"
    src.mkdir()
    target = src / "namespaced.php"
    target.write_text(NAMESPACED.read_text(encoding="utf-8"), encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "2",
            "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        },
    )
    report = full_build(config, store)
    assert report.parsed == 1 and report.failed == 0
    return target


@needs_php
def test_search_symbol_returns_ranked_fixture_hits(tmp_path: Path, store: GraphStore) -> None:
    """Proving test: known fixture symbols appear within CA_MAX_RESULTS after index."""
    index_namespaced(tmp_path, store)
    config = replace(db_config(tmp_path), root=tmp_path)
    result = search_symbol.create(config)("User", detail_level="minimal")
    assert result["indexed"] is True
    qnames = [hit["qname"] for hit in result["results"]]
    assert "\\App\\Models\\User" in qnames
    assert len(result["results"]) <= config.max_results


@needs_php
def test_search_respects_namespace_prefix(tmp_path: Path, store: GraphStore) -> None:
    index_namespaced(tmp_path, store)
    config = replace(db_config(tmp_path), root=tmp_path)
    tool = search_symbol.create(config)
    inside = tool("User", namespace="\\App\\Models", detail_level="minimal")
    outside = tool("User", namespace="\\App\\Other", detail_level="minimal")
    assert "\\App\\Models\\User" in [hit["qname"] for hit in inside["results"]]
    assert outside["results"] == []


def test_namespace_filter_treats_underscore_literally(store: GraphStore) -> None:
    store.upsert_file("a.php", "h", "php")
    store.replace_file_rows(
        "a.php",
        [
            {
                "kind": "Class",
                "name": "Thing",
                "qualified_name": "\\My_App\\Thing",
                "file_path": "a.php",
                "line_start": 1,
            },
            {
                "kind": "Class",
                "name": "Thing",
                "qualified_name": "\\MyXApp\\Thing",
                "file_path": "a.php",
                "line_start": 2,
            },
        ],
        [],
    )
    hits = store.search_nodes("Thing", namespace="\\My_App", limit=10)
    assert [row["qualified_name"] for row in hits] == ["\\My_App\\Thing"]


@needs_php
def test_file_outline_lists_symbols_without_bodies(tmp_path: Path, store: GraphStore) -> None:
    index_namespaced(tmp_path, store)
    config = replace(db_config(tmp_path), root=tmp_path)
    # full_build stores repo-relative paths under the indexed root.
    path = "src/namespaced.php"
    result = file_outline.create(config)(path, detail_level="minimal")
    assert result["indexed"] is True
    assert result["results"]
    assert all("qname" in hit and "line_start" in hit for hit in result["results"])
    assert all("source" not in hit and "body" not in hit for hit in result["results"])


@needs_php
def test_read_symbol_returns_only_target_plus_docblock(tmp_path: Path, store: GraphStore) -> None:
    """Plant a docblock above a method; read_symbol must include it and not the whole file."""
    src = tmp_path / "src"
    src.mkdir()
    php = src / "Doc.php"
    php.write_text(
        "<?php\nnamespace App;\n\nclass Doc\n{\n"
        "    /**\n     * Saves the doc.\n     */\n"
        "    public function save(): void\n    {\n    }\n"
        "    public function other(): void\n    {\n    }\n}\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        },
    )
    report = full_build(config, store)
    assert report.parsed == 1 and report.failed == 0
    bound = replace(db_config(tmp_path), root=tmp_path)
    result = read_symbol.create(bound)("\\App\\Doc::save", detail_level="minimal")
    assert result["found"] is True
    source = str(result["source"])
    assert "Saves the doc" in source
    assert "function save" in source
    assert "function other" not in source
    whole = php.read_text(encoding="utf-8")
    assert len(source) < len(whole)


def test_trigram_fts_matches_camel_case(store: GraphStore) -> None:
    store.upsert_file("c.php", "h", "php")
    store.replace_file_rows(
        "c.php",
        [
            {
                "kind": "Function",
                "name": "findByEmail",
                "qualified_name": "\\App\\findByEmail",
                "file_path": "c.php",
                "line_start": 1,
            }
        ],
        [],
    )
    hits = store.search_nodes("email", limit=10)
    assert [row["name"] for row in hits] == ["findByEmail"]


def test_prompts_are_registered(tmp_path: Path) -> None:
    server = build_server(db_config(tmp_path))

    async def names() -> set[str]:
        async with Client(server) as client:
            return {prompt.name for prompt in await client.list_prompts()}

    assert set(PROMPT_NAMES) <= asyncio.run(names())
    assert prompts.EXPLORE_AREA in PROMPT_NAMES
