"""Task 353: an include built as a head plus a literal path links to its file.

``__DIR__`` / ``dirname(…)`` heads are language spec, so the adapter turns them into an exact
includer-relative path. Any other head (a ``define()``d root) leaves a ``/…`` tail at HEURISTIC,
which the core links only when exactly one indexed file ends with it.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import include_graph
from tests.php_adapter_cli import ENTRY, PHP, needs_php

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "include_concat"
HOME = "src/pages/home.php"


@pytest.fixture
def built(tmp_path: Path) -> Iterator[tuple[Config, GraphStore]]:
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_PHP_CMD": shlex.join([str(PHP), str(ENTRY), "--server"]),
            "CA_DB_PATH": str(tmp_path / ".code-atlas" / "graph.db"),
        },
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
        yield config, store


def includes(store: GraphStore) -> dict[int, tuple[str, str | None, str]]:
    """``line → (target_raw, target_qname, tier)`` for every include in home.php."""
    rows = store._conn.execute(
        "SELECT line, target_raw, target_qname, confidence_tier FROM edges "
        "WHERE kind = 'INCLUDES' AND file_path = ?",
        (HOME,),
    ).fetchall()
    return {line: (raw, qname, tier) for line, raw, qname, tier in rows}


@needs_php
def test_a_dir_head_links_resolved_to_the_file_beside_the_includer(built: tuple) -> None:
    """AC1: ``__DIR__``, ``dirname(__DIR__)`` and ``dirname(__FILE__, 3)`` are exact paths."""
    _, store = built
    edges = includes(store)

    assert edges[2][1:] == ("src/pages/partials/header.php", "RESOLVED")
    assert edges[3][1:] == ("src/lib/util.php", "RESOLVED")
    assert edges[4][1:] == ("a/dup/x.php", "RESOLVED")


@needs_php
def test_a_constant_head_links_its_unique_tail_at_heuristic(built: tuple) -> None:
    """AC2 (proving test): ``ROOT_DIR . '/src/partials/select.php'`` links HEURISTIC, and
    ``include_graph imported_by`` on the partial lists the includer."""
    config, store = built

    assert includes(store)[5][1:] == ("src/partials/select.php", "HEURISTIC")
    answer = include_graph.create(config)("src/partials/select.php", direction="imported_by")
    assert answer.get("reason", "ok") == "ok", answer
    assert [hit["path"] for hit in answer["results"]] == [HOME], answer


@needs_php
def test_a_tail_two_files_end_with_stays_unlinked_and_counted(built: tuple) -> None:
    """AC3: ``/dup/x.php`` ends both ``a/dup/x.php`` and ``b/dup/x.php`` — no pick, counted."""
    config, store = built

    assert includes(store)[6] == ("/dup/x.php", None, "HEURISTIC")
    answer = include_graph.create(config)(HOME, direction="imports")
    # The ambiguous tail, `$path`, and the two paths with a variable in them are unresolved.
    assert answer["unresolved_includes"] == 4, answer


@needs_php
def test_a_fully_dynamic_include_is_unchanged(built: tuple) -> None:
    """AC4: ``$path``, and a path with a variable in it, stay ``(dynamic)``."""
    _, store = built
    edges = includes(store)

    assert edges[7] == ("(dynamic)", None, "DYNAMIC")
    assert edges[8] == ("(dynamic)", None, "DYNAMIC")
    # A variable mid-path would leave `/select.php`, a bare basename match (the challenger's F2).
    assert edges[9] == ("(dynamic)", None, "DYNAMIC")
