"""Task 370 — a TS/JS ``require`` built from ``__dirname`` or a root plus a literal tail imports.

``__dirname`` joined to literals — by ``+``, a template, or ``path.join``/``path.resolve`` — names
a file exactly, as a ``./x`` literal does. Any other head with a ``/…`` literal is a ``HEURISTIC``
tail the core links by unique path suffix (353). ``require(name)`` stays a stamped load (294).
"""

from __future__ import annotations

import dataclasses
import shlex
import sqlite3
import subprocess

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_orphans, find_references, include_graph
from tests.ts_adapter_cli import ENTRY, NODE, needs_node

pytestmark = needs_node

LOADER = "src/loader.js"
FILES = {
    LOADER: (
        "const path = require('path');\n"  # 1
        "const { join } = require('node:path');\n"  # 2
        "const plus = require(__dirname + '/lib/plus');\n"  # 3
        "const tmpl = require(`${__dirname}/lib/tmpl`);\n"  # 4
        "const joined = require(path.join(__dirname, 'lib', 'joined'));\n"  # 5
        "const bare = require(join(__dirname, '..', 'shared', 'up.js'));\n"  # 6
        "const tail = require(ROOT + '/vendorless/tail');\n"  # 7
        "const twin = require(ROOT + '/dup/twin');\n"  # 8
        "const name = process.argv[2];\n"  # 9
        "const runtime = require(name);\n"  # 10
        "module.exports = { plus, tmpl, joined, bare, tail, twin, runtime };\n"  # 11
    ),
    "src/lib/plus.js": "module.exports = 1;\n",
    "src/lib/tmpl.js": "module.exports = 2;\n",
    "src/lib/joined.js": "module.exports = 3;\n",
    "shared/up.js": "module.exports = 4;\n",
    "pkg/vendorless/tail.js": "module.exports = 5;\n",
    "a/dup/twin.js": "module.exports = 6;\n",
    "b/dup/twin.js": "module.exports = 7;\n",
}


@pytest.fixture(scope="module")
def config(tmp_path_factory: pytest.TempPathFactory) -> Config:
    root = tmp_path_factory.mktemp("repo")
    for rel, body in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    built = load_config(
        root,
        {"CA_WORKERS": "1", "CA_TYPESCRIPT_CMD": shlex.join([str(NODE), str(ENTRY), "--server"])},
    )
    with GraphStore(built.db_path) as store:
        assert full_build(built, store).failed == 0
    return built


def _imports(config: Config) -> dict[int, tuple[str, str | None, str | None]]:
    conn = sqlite3.connect(config.db_path)
    rows = conn.execute(
        "SELECT line, target_raw, target_qname, confidence_tier FROM edges"
        " WHERE kind = 'IMPORTS' AND source_qname = ?",
        (LOADER,),
    ).fetchall()
    conn.close()
    return {row[0]: (row[1], row[2], row[3]) for row in rows}


def _importers(config: Config, path: str) -> list[str]:
    """`include_graph` routes a module import to `find_references` on the File (186/188)."""
    routed = include_graph.create(config)(path, direction="imported_by")
    assert routed["try_instead"] == "find_references", routed
    answer = find_references.create(config)(path)
    assert answer["reason"] == "ok", answer
    results = answer["results"]
    assert isinstance(results, list)
    return sorted({str(hit["qname"]) for hit in results})


@pytest.mark.parametrize(
    "target", ["src/lib/plus.js", "src/lib/tmpl.js", "src/lib/joined.js", "shared/up.js"]
)
def test_a_dirname_built_require_imports_its_file_exactly(config: Config, target: str) -> None:
    """AC1 — the `+`, template and `path.join` forms (and a `..` step) each name the file; the
    importer is read where `include_graph` routes an `IMPORTS` language (P3 deviation)."""
    assert _importers(config, target) == [LOADER]
    exact = [row for row in _imports(config).values() if row[1] == target]
    assert [row[2] for row in exact] == ["RESOLVED"]


def test_a_root_head_links_its_unique_tail_at_heuristic(config: Config) -> None:
    """AC2 — `ROOT + '/vendorless/tail'` completes with the requirer's extension and links by its
    unique suffix; a tail two files end with stays unlinked (no pick)."""
    edges = _imports(config)
    assert edges[7] == ("/vendorless/tail.js", "pkg/vendorless/tail.js", "HEURISTIC")
    assert edges[8] == ("/dup/twin.js", None, "HEURISTIC")
    assert _importers(config, "pkg/vendorless/tail.js") == [LOADER]


def test_a_require_with_no_literal_still_stamps_the_file(config: Config) -> None:
    """AC3 — `require(name)` imports nothing, the file stays stamped, orphans stay unmeasured."""
    assert 10 not in _imports(config)
    conn = sqlite3.connect(config.db_path)
    (extra,) = conn.execute(
        "SELECT extra FROM nodes WHERE kind = 'File' AND qualified_name = ?", (LOADER,)
    ).fetchone()
    conn.close()
    assert "dynamic_import" in extra
    rooted = dataclasses.replace(config, entry_points=(LOADER,))
    assert find_orphans.create(rooted)()["status"] == "resolution_unmodelled"
