"""Task 373 — a Python module loaded by path or by a literal name is imported, or the file stamped.

``runpy.run_path``, ``spec_from_file_location`` and ``exec`` of a file's text load a module by
path: built from ``__file__``'s directory and literals it names the file exactly (353's treatment),
otherwise the file is stamped ``dynamic_import`` (295). A literal ``import_module('pkg.mod')`` or
``__import__('pkg.mod')`` is an ``IMPORTS`` of that module; a computed or relative one stamps.
"""

from __future__ import annotations

import dataclasses
import shlex
import sqlite3
import subprocess
import sys

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_orphans, find_references, include_graph
from tests.python_adapter_cli import ENTRY, needs_python

pytestmark = needs_python

LOADER = "tools/loader.py"
EXECER = "tools/execer.py"
FILES = {
    LOADER: (
        "import os\n"  # 1
        "import runpy\n"  # 2
        "from importlib import import_module\n"  # 3
        "from pathlib import Path\n"  # 4
        "runpy.run_path(os.path.join(os.path.dirname(__file__), 'plugin.py'))\n"  # 5
        "exec((Path(__file__).resolve().parent / 'script.py').read_text())\n"  # 6
        "runpy.run_path(os.path.dirname(os.path.dirname(__file__)) + '/shared.py')\n"  # 7
        "import_module('pkg.mod')\n"  # 8
    ),
    EXECER: (
        "import sys\n"  # 1
        "from importlib import import_module\n"  # 2
        "path = sys.argv[1]\n"  # 3
        "exec(open(path).read())\n"  # 4
        "import_module(sys.argv[2])\n"  # 5
        "exec('VALUE = 1')\n"  # 6
        "source = open(path).read()\n"  # 7
        "exec(source)\n"  # 8 — file text through a variable: stamps (F4)
    ),
    "tools/edges.py": (
        "import os\n"  # 1
        "import runpy as rp\n"  # 2
        "import importlib as il\n"  # 3
        "from pathlib import Path\n"  # 4
        "rp.run_path(os.path.dirname(__file__))\n"  # 5 — a directory: stamps
        "rp.run_path(os.path.join(os.path.dirname(__file__), '/abs/y.py'))\n"  # 6 — absolute
        "rp.run_path(os.path.join(os.path.dirname(__file__), '../../../out.py'))\n"  # 7 — leaves
        "rp.run_path(str(Path(__file__).parent / 'extra.py'))\n"  # 8 — exact, via str()
        "il.import_module('pkg.mod')\n"  # 9 — exact, via an alias
    ),
    "tools/plugin.py": "PLUGIN = 1\n",
    "tools/extra.py": "EXTRA = 1\n",
    "tools/script.py": "SCRIPT = 1\n",
    "shared.py": "SHARED = 1\n",
    "pkg/__init__.py": "",
    "pkg/mod.py": "MOD = 1\n",
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
        {"CA_WORKERS": "1", "CA_PYTHON_CMD": shlex.join([sys.executable, str(ENTRY), "--server"])},
    )
    with GraphStore(built.db_path) as store:
        assert full_build(built, store).failed == 0
    return built


def _rows(config: Config, sql: str, *params: str) -> list[tuple[object, ...]]:
    conn = sqlite3.connect(config.db_path)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def _importers(config: Config, path: str) -> list[str]:
    """`include_graph` routes a module import to `find_references` on the File (186/188)."""
    routed = include_graph.create(config)(path, direction="imported_by")
    assert routed["try_instead"] == "find_references", routed
    answer = find_references.create(config)(path)
    assert answer["reason"] == "ok", answer
    results = answer["results"]
    assert isinstance(results, list)
    return sorted({str(hit["qname"]) for hit in results})


@pytest.mark.parametrize("target", ["tools/plugin.py", "tools/script.py", "shared.py"])
def test_a_file_loaded_by_a_file_relative_path_is_imported_by_its_loader(
    config: Config, target: str
) -> None:
    """AC1 — `run_path`, `exec(….read_text())`, and a parent's parent, each name the file."""
    assert _importers(config, target) == [LOADER]


def test_a_literal_import_module_imports_its_module(config: Config) -> None:
    """AC3 — `import_module('pkg.mod')` is an IMPORTS linked to the module's file."""
    rows = _rows(
        config,
        "SELECT target_qname FROM edges WHERE kind = 'IMPORTS' AND source_qname = ? AND line = 8",
        LOADER,
    )
    assert rows == [("pkg/mod.py",)]


def test_an_exact_load_does_not_stamp_but_a_computed_one_does(config: Config) -> None:
    """AC2/AC3 — the loader names every file and is unstamped; `exec(open(path).read())` and a
    computed `import_module` stamp theirs, and `exec` of a code string stamps nothing more."""
    files = "SELECT qualified_name, extra FROM nodes WHERE qualified_name IN (?, ?)"
    stamps = {str(row[0]): row[1] for row in _rows(config, files, LOADER, EXECER)}
    assert stamps[LOADER] is None
    assert "dynamic_import" in str(stamps[EXECER])
    imports = _rows(
        config, "SELECT line FROM edges WHERE kind = 'IMPORTS' AND source_qname = ?", EXECER
    )
    assert sorted(imports) == [(1,), (2,)]
    rooted = dataclasses.replace(config, entry_points=(LOADER,))
    assert find_orphans.create(rooted)()["status"] == "resolution_unmodelled"


def test_only_a_file_inside_the_repo_is_read_exactly(config: Config) -> None:
    """Challenger F1/F2/F5 — a directory, an absolute part and a path leaving the repo stamp; a
    `str(…)` wrapper and an aliased module still read exactly."""
    rows = _rows(
        config,
        "SELECT line, target_qname FROM edges WHERE kind = 'IMPORTS' AND source_qname = ?"
        " AND line > 4 ORDER BY line",
        "tools/edges.py",
    )
    assert rows == [(8, "tools/extra.py"), (9, "pkg/mod.py")]
    (extra,) = _rows(config, "SELECT extra FROM nodes WHERE qualified_name = ?", "tools/edges.py")
    assert "dynamic_import" in str(extra[0])
