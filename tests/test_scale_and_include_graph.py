"""Task 015: include_graph + global/PSR-0 resolution + resolver batching (§6, §8, §12)."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.resolver import resolve_edges
from code_atlas.store import GraphStore
from code_atlas.tools import include_graph

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PSR0_FIXTURES = REPO / "tests" / "fixtures" / "php" / "psr0_resolve"
INCLUDE_FIXTURES = REPO / "tests" / "fixtures" / "php" / "include_graph"

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


def seed_file(store: GraphStore, path: str, nodes: list[dict], edges: list[dict]) -> None:
    store.upsert_file(path, "h", "lang")
    store.replace_file_rows(path, nodes, edges)


def node(kind: str, name: str, qname: str, path: str) -> dict[str, object]:
    return {
        "kind": kind,
        "name": name,
        "qualified_name": qname,
        "file_path": path,
        "line_start": 1,
    }


def edge(
    kind: str,
    source: str,
    target_raw: str,
    path: str,
    *,
    tier: str | None = None,
    target_qname: str | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "kind": kind,
        "source_qname": source,
        "target_raw": target_raw,
        "file_path": path,
        "line": 1,
    }
    if tier is not None:
        row["confidence_tier"] = tier
    if target_qname is not None:
        row["target_qname"] = target_qname
    return row


def php_cmd() -> str:
    return shlex.join([PHP or "php", str(PHP_ENTRY), "--server"])


@needs_php
def test_underscore_global_symbols_resolve_by_fqn(tmp_path: Path) -> None:
    """AC1: underscore/global FQNs link (layout is realistic set-dressing, not load-bearing)."""
    root = tmp_path / "repo"
    shutil.copytree(PSR0_FIXTURES, root)
    cfg = replace(
        load_config(root, {"CA_PHP_CMD": php_cmd()}),
        db_path=tmp_path / "graph.db",
        root=root,
    )
    with GraphStore(cfg.db_path) as store:
        full_build(cfg, store)
        extends = store.edges_by_source("\\Foo_Bar_Baz", kinds=("EXTENDS",), limit=10)
        news = store.edges_by_source("\\Foo_Bar_Baz::fetch", kinds=("NEW",), limit=10)
    assert extends and extends[0]["target_qname"] == "\\Legacy_Table"
    assert extends[0]["confidence_tier"] == "RESOLVED"
    assert news and news[0]["target_qname"] == "\\Legacy_Table"
    assert any(
        n["qualified_name"] == "\\Foo_Bar_Baz" and n["file_path"] == "Foo/Bar/Baz.php"
        for n in _all_classes(cfg)
    )


def _all_classes(cfg: Config) -> list[dict[str, object]]:
    with GraphStore(cfg.db_path) as store:
        return store.nodes_by_kind("Class", limit=50)


@needs_php
def test_include_graph_imports_and_imported_by(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    shutil.copytree(INCLUDE_FIXTURES, root)
    cfg = replace(
        load_config(root, {"CA_PHP_CMD": php_cmd()}),
        db_path=tmp_path / "graph.db",
        root=root,
    )
    with GraphStore(cfg.db_path) as store:
        full_build(cfg, store)
    tool = include_graph.create(cfg)
    imports = tool("app.php", direction="imports")
    imported_by = tool("Legacy/Registry.php", direction="imported_by")
    assert imports["indexed"] is True
    assert {hit["path"] for hit in imports["results"]} == {"Legacy/Registry.php"}
    assert {hit["path"] for hit in imported_by["results"]} == {"app.php"}
    assert imports["unresolved_includes"] == 0
    assert "unresolved_includes" not in imported_by


@needs_php
def test_include_graph_answers_for_a_namespaced_file(tmp_path: Path) -> None:
    """Task 129: an INCLUDES edge anchors on the file, so a namespaced includer is answerable.

    Fails pre-129, and silently: the edge's source was the enclosing container, which inside a
    namespaced file is the namespace. `imports` returned `[]` **with** `unresolved_includes: 0` —
    an affirmative claim that nothing was dropped — while two `require_once` lines sat in the file.
    In a PSR-4 repo every file declares a namespace, so this was every file.
    """
    root = tmp_path / "repo"
    shutil.copytree(INCLUDE_FIXTURES, root)
    cfg = replace(
        load_config(root, {"CA_PHP_CMD": php_cmd()}),
        db_path=tmp_path / "graph.db",
        root=root,
    )
    with GraphStore(cfg.db_path) as store:
        full_build(cfg, store)
        # The anchor itself, not only what the tool makes of it.
        assert store.edges_by_source("\\Shop", kinds=("INCLUDES",), limit=10) == []
        anchored = store.edges_by_source("Shop/Bootstrap.php", kinds=("INCLUDES",), limit=10)
    assert len(anchored) == 2, anchored

    tool = include_graph.create(cfg)
    imports = tool("Shop/Bootstrap.php", direction="imports")
    assert {hit["path"] for hit in imports["results"]} == {"helpers.php"}
    # The dynamic require is unanswerable, and the payload says so instead of claiming zero.
    assert imports["unresolved_includes"] == 1

    imported_by = tool("helpers.php", direction="imported_by")
    assert {hit["path"] for hit in imported_by["results"]} == {"Shop/Bootstrap.php"}
    # `path` carries a path, not the includer's namespace.
    assert all(not str(hit["path"]).startswith("\\") for hit in imported_by["results"])


def test_include_graph_exact_fill_at_depth_one_is_not_truncated(tmp_path: Path) -> None:
    """Regression: depth=1 with exactly max_results neighbors must not set truncated."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        for i in range(3):
            path = f"f{i}.php"
            seed_file(store, path, [node("File", path, path, path)], [])
        seed_file(
            store,
            "app.php",
            [node("File", "app.php", "app.php", "app.php")],
            [
                edge(
                    "INCLUDES",
                    "app.php",
                    f"f{i}.php",
                    "app.php",
                    target_qname=f"f{i}.php",
                )
                for i in range(3)
            ],
        )
    tool = include_graph.create(
        replace(load_config(tmp_path, {}), db_path=db, page_limit=3, root=tmp_path)
    )
    payload = tool("app.php", direction="imports", depth=1)
    assert len(payload["results"]) == 3
    assert payload["truncated"] is False


def test_resolver_batches_unresolved_edges(store: GraphStore) -> None:
    """Streaming + batch link: many unresolved edges still resolve without one giant load."""
    for i in range(25):
        path = f"f{i}.x"
        seed_file(
            store,
            path,
            [
                node("Class", f"C{i}", f"\\C{i}", path),
                node("Class", f"P{i}", f"\\P{i}", path),
            ],
            [edge("EXTENDS", f"\\C{i}", f"\\P{i}", path)],
        )

    resolve_edges(store, max_candidates=50)

    for i in range(25):
        linked = store.edges_by_source(f"\\C{i}", kinds=("EXTENDS",), limit=5)
        assert linked[0]["target_qname"] == f"\\P{i}"
    assert store.unresolved_edges() == []


def test_iter_unresolved_edges_respects_batch_size(store: GraphStore) -> None:
    for i in range(5):
        path = f"b{i}.x"
        seed_file(
            store,
            path,
            [node("Class", f"A{i}", f"\\A{i}", path)],
            [edge("EXTENDS", f"\\A{i}", f"\\Missing{i}", path)],
        )
    batches = list(store.iter_unresolved_edges(batch_size=2))
    assert [len(batch) for batch in batches] == [2, 2, 1]


def test_iter_unresolved_edges_rejects_bad_batch_size_immediately(store: GraphStore) -> None:
    with pytest.raises(ValueError, match="batch_size"):
        store.iter_unresolved_edges(batch_size=0)


def test_iter_unresolved_edges_can_skip_dynamic(store: GraphStore) -> None:
    seed_file(
        store,
        "a.x",
        [node("Class", "A", "\\A", "a.x")],
        [
            edge("INCLUDES", "a.x", "(dynamic)", "a.x", tier="DYNAMIC"),
            edge("EXTENDS", "\\A", "\\Missing", "a.x"),
        ],
    )
    plain = [row for batch in store.iter_unresolved_edges(batch_size=10) for row in batch]
    skipped = [
        row
        for batch in store.iter_unresolved_edges(batch_size=10, skip_dynamic=True)
        for row in batch
    ]
    assert any(row["confidence_tier"] == "DYNAMIC" for row in plain)
    assert all(row["confidence_tier"] != "DYNAMIC" for row in skipped)


def test_scale_script_emits_timing_shape(tmp_path: Path) -> None:
    """Documented procedure: script writes a timing JSON artifact (sample path required)."""
    script = REPO / "scripts" / "scale_full_build.py"
    assert script.is_file()
    sample = tmp_path / "sample"
    sample.mkdir()
    (sample / "empty.php").write_text("<?php\n", encoding="utf-8")
    out = tmp_path / "timing.json"
    if PHP is None or not PHP_AUTOLOAD.is_file():
        pytest.skip("needs PHP to exercise the scale script end-to-end")
    env = {
        **os.environ,
        "CODE_ATLAS_SCALE_SAMPLE": str(sample),
        "CODE_ATLAS_SCALE_TIMING_OUT": str(out),
        "CA_PHP_CMD": php_cmd(),
    }
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "elapsed_seconds" in payload
    assert "files" in payload
    assert payload["sample_root"] == str(sample.resolve())
    assert "peak_rss_self_kb" in payload["host"]
    assert "peak_rss_children_kb" in payload["host"]
