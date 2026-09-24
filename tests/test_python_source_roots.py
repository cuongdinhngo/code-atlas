"""Task 230 — configured ``source_roots`` resolve absolute imports a climb cannot reach."""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

from code_atlas import contract
from code_atlas.adapter import SubprocessAdapter
from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status as status_mod
from tests.python_adapter_cli import ENTRY, needs_python

pytestmark = needs_python

REPO = Path(__file__).resolve().parents[1]


def _python_cmd() -> str:
    return shlex.join([sys.executable, str(ENTRY), "--server"])


def _seed_src_layout(root: Path) -> None:
    pkg = root / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "mod.py").write_text("class Thing:\n    pass\n", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "caller.py").write_text("from pkg.mod import Thing\n", encoding="utf-8")


def _seed_collision(root: Path) -> None:
    other = root / "other"
    other.mkdir()
    (other / "requests.py").write_text("def get():\n    pass\n", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "caller.py").write_text("import requests\n", encoding="utf-8")
    (root / "src").mkdir()


def _git_init(root: Path) -> None:
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)


def _build(tmp_path: Path, *, source_roots: str | None = None):
    _git_init(tmp_path)
    db_path = tmp_path / ".code-atlas" / "graph.db"
    env = {
        "CA_WORKERS": "1",
        "CA_DB_PATH": str(db_path),
        "CA_PYTHON_CMD": _python_cmd(),
    }
    if source_roots is not None:
        env["CA_SOURCE_ROOTS"] = source_roots
    config = load_config(tmp_path, env)
    store = GraphStore(db_path)
    report = full_build(config, store)
    assert report.failed == 0
    return config, store


def _imports(store: GraphStore) -> list[tuple[str, str, str | None, str | None]]:
    return [
        (
            str(row[0]),
            str(row[1]),
            None if row[2] is None else str(row[2]),
            None if row[3] is None else str(row[3]),
        )
        for row in store._conn.execute(
            "SELECT file_path, target_raw, target_qname, confidence_tier FROM edges "
            "WHERE kind = 'IMPORTS' ORDER BY id"
        )
    ]


def test_ac1_without_source_roots_import_stays_unlinked(tmp_path: Path) -> None:
    """R6.5 — climb from ``tests/`` cannot reach ``src/pkg``; IMPORTS stays unlinked."""
    _seed_src_layout(tmp_path)
    _config, store = _build(tmp_path)
    try:
        rows = _imports(store)
        assert any(
            path.endswith("tests/caller.py") and raw == "pkg.mod" and qname is None
            for path, raw, qname, _tier in rows
        ), rows
    finally:
        store.close()


def test_ac2_with_src_configured_import_links_resolved(tmp_path: Path) -> None:
    _seed_src_layout(tmp_path)
    _config, store = _build(tmp_path, source_roots="src")
    try:
        rows = [row for row in _imports(store) if row[0].endswith("tests/caller.py")]
        assert len(rows) == 1, rows
        _path, raw, qname, tier = rows[0]
        assert raw == "src/pkg/mod.py"
        assert qname == "src/pkg/mod.py"
        assert tier == "RESOLVED"
    finally:
        store.close()


def test_ac3_default_path_byte_identical_without_roots(tmp_path: Path) -> None:
    """Unset / empty ``source_roots`` must match climb-only adapter output (R4.2)."""
    _seed_src_layout(tmp_path)
    caller = "tests/caller.py"
    cmd = (sys.executable, str(ENTRY), "--server")
    with SubprocessAdapter("python", cmd, tmp_path) as adapter:
        without = adapter.parse(caller)
        empty = adapter.parse(caller, source_roots=None)
        empty_tuple = adapter.parse(caller, source_roots=())
    assert without.ok and empty.ok and empty_tuple.ok
    assert without.edges == empty.edges == empty_tuple.edges
    assert without.nodes == empty.nodes == empty_tuple.nodes
    imports = [e for e in without.edges if e.get("kind") == "IMPORTS"]
    assert imports and imports[0].get("target_raw") == "pkg.mod"


def test_ac4_unconfigured_collision_stays_unlinked(tmp_path: Path) -> None:
    """``import requests`` must not link to ``other/requests.py`` when ``other`` is not a root."""
    _seed_collision(tmp_path)
    _config, store = _build(tmp_path, source_roots="src")
    try:
        rows = _imports(store)
        assert any(
            path.endswith("tests/caller.py") and raw == "requests" and qname is None
            for path, raw, qname, _tier in rows
        ), rows
    finally:
        store.close()


def test_ac5_contract_version_unchanged_and_no_language_branch() -> None:
    """Optional request field mirrors ``declarations_only`` — response vocabulary untouched."""
    assert contract.CONTRACT_VERSION == 12
    hits: list[str] = []
    for path in (REPO / "code_atlas").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if 'language == "python"' in text or "language == 'python'" in text:
            hits.append(str(path.relative_to(REPO)))
    assert hits == []


def test_status_reports_source_root_hint_when_unlinked_matches_index(tmp_path: Path) -> None:
    _seed_src_layout(tmp_path)
    config, store = _build(tmp_path)
    try:
        assert store.count_source_root_hint_imports() >= 1
        tool = status_mod.create(config, ("get_index_status",))
        payload = tool(detail_level="standard")
        assert int(payload.get("source_root_hint_imports", 0)) >= 1
    finally:
        store.close()
