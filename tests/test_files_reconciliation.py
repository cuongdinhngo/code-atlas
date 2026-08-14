"""Task 082 Part A: verbose ``get_index_status`` lets an outsider reconcile ``files``.

Round 4 saw ``files: 18,888`` against a tree of 28,425 ``.php`` and could not tell 18,888 from
18,889 without the denominator. This publishes it: a ``collection`` block whose terms an outsider
reconciles against their own ``git ls-files`` — ``collected - skipped(suffix, ignore) = kept`` and
``kept + stubs = files`` — so 068's ±1 synthetic-bookmark exclusion becomes checkable arithmetic.

The fake-adapter tree (``.aa``) proves the arithmetic term by term. The PHP fixture proves it holds
with the indirection-rules channel on and off, and that the bookmark never inflates ``files``.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status
from tests.test_incremental import committed, fake_env, git

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
FIXTURES = REPO / "tests" / "fixtures" / "view_databag"

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)


def _verbose(root: Path, config_env: dict[str, str]) -> dict[str, object]:
    config = load_config(root, config_env)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    served = (get_index_status.NAME, get_index_status.BUILD_TOOL)
    return get_index_status.create(config, served)(detail_level="verbose")


def test_verbose_status_reconciles_files_end_to_end(tmp_path: Path) -> None:
    """Proving test (AC1): every term of the reconciliation is published and closes.

    Fails pre-082 (no ``collection`` block on verbose); passes after.
    """
    committed(
        tmp_path,
        {
            "src/a.aa": "class A {}\n",  # kept
            "src/b.aa": "class B {}\n",  # kept
            "src/notes.txt": "not a claimed suffix\n",  # skipped: suffix
            "vendor/lib.aa": "class V {}\n",  # skipped: ignore (built-in vendor/)
        },
    )
    db = tmp_path / ".code-atlas" / "graph.db"
    status = _verbose(tmp_path, {**fake_env(workers=1), "CA_DB_PATH": str(db)})

    col = status["collection"]
    assert isinstance(col, dict)
    # The outsider's own denominator — every tracked path, all suffixes (incl. .gitignore).
    tracked = [line for line in git(tmp_path, "ls-files").splitlines() if line]
    assert col["collected"] == len(tracked)
    assert col["skipped"]["ignore"] == 1  # vendor/lib.aa
    assert col["kept"] == 2  # src/a.aa, src/b.aa
    # collected - skipped(suffix, ignore) = kept, and kept + stubs = files (the reconciliation).
    assert col["collected"] - col["skipped"]["suffix"] - col["skipped"]["ignore"] == col["kept"]
    assert col["kept"] + status["stubs"] == status["files"]
    assert ".aa" in col["indexed_suffixes"]
    assert col["skipped"]["untracked"] == 0


def test_collection_absent_before_first_build_and_omitted_pre_082(tmp_path: Path) -> None:
    """061: no fake denominator — an unbuilt index carries no ``collection`` block."""
    committed(tmp_path, {"src/a.aa": "class A {}\n"})
    db = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(tmp_path, {**fake_env(workers=1), "CA_DB_PATH": str(db)})
    served = (get_index_status.NAME, get_index_status.BUILD_TOOL)
    status = get_index_status.create(config, served)(detail_level="verbose")
    assert status["indexed"] is False
    assert "collection" not in status


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
        "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
    }
    if rules:
        env["CA_INDIRECTION_RULES"] = "rules/rules.json"
    return env


@needs_php
def test_arithmetic_closes_and_bookmark_excluded_with_rules_on_and_off(tmp_path: Path) -> None:
    """AC2: rules on/off leaves the census and ``files`` identical; the bookmark is never a file.

    The rules channel adds a synthetic bookmark node (068), but ``collection`` is a collect-walk
    artifact computed before enrichment, so both the denominator and ``files`` are unchanged.
    """
    off_root, on_root = tmp_path / "off", tmp_path / "on"
    off_root.mkdir()
    on_root.mkdir()
    _plant(off_root)
    _plant(on_root)

    off = _verbose(off_root, _php_env(off_root, rules=False))
    on = _verbose(on_root, _php_env(on_root, rules=True))

    # The rules channel actually fired on the "on" build (else the test proves nothing).
    with GraphStore(on_root / ".code-atlas" / "graph.db") as store:
        assert store.edges_matching_kind(contract.PROVIDES_VIEW_DATA, limit=20)

    assert on["collection"] == off["collection"]  # denominator unchanged by the rules channel
    assert on["files"] == off["files"]  # the bookmark is not a file (068)
    for status in (on, off):
        col = status["collection"]
        assert col["collected"] - col["skipped"]["suffix"] - col["skipped"]["ignore"] == col["kept"]
        assert col["kept"] + status["stubs"] == status["files"]
