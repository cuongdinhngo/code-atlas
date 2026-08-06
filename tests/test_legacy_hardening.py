"""Task 041: encoding fail-visible pin, Blade ignore, .phtml extension."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.ignore import load_ignore
from code_atlas.indexer import collect, collect_stubs, full_build
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

GOOD = b"<?php\nnamespace App;\nclass Ok {}\n"
PHTML = b"<?php\nnamespace App;\nclass View {}\n"
BLADE = b"<html><?php echo 1; ?></html>\n"
# Invalid bytes in a string literal → json_encode fails (same shape as adapter soft-fail test).
UNDEC = b'<?php\nrequire "\xff\xfe_broken.php";\n'
STUB_PHP = b"<?php\nnamespace Lib;\nclass Model {}\n"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / ".code-atlas" / "graph.db") as opened:
        yield opened


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)


def _php_env(**extra: str) -> dict[str, str]:
    env = {
        "CA_WORKERS": "2",
        "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
    }
    env.update(extra)
    return env


@needs_php
def test_non_utf8_file_surfaces_in_parse_failures(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1: pins existing fail-visible behaviour — files row + parse_failures, never absent."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.php").write_bytes(GOOD)
    (src / "bad.php").write_bytes(UNDEC)
    _git_init(tmp_path)

    config = load_config(tmp_path, _php_env())
    report = full_build(config, store)
    assert report.failed >= 1
    assert "src/bad.php" in store.file_paths()
    parsed_ok = store._conn.execute(
        "SELECT parsed_ok FROM files WHERE path = ?", ("src/bad.php",)
    ).fetchone()
    assert parsed_ok is not None and parsed_ok[0] == 0

    status = get_index_status.create(config, registered=["get_index_status"])()
    assert status["parse_failures"] >= 1
    assert status["indexed"] is True


@needs_php
def test_blade_php_is_ignored_and_not_indexed(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2: *.blade.* is a builtin ignore — not collected, not sent to the adapter."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.php").write_bytes(GOOD)
    (src / "page.blade.php").write_bytes(BLADE)
    _git_init(tmp_path)

    matcher = load_ignore(tmp_path)
    assert matcher.is_ignored("src/page.blade.php")
    assert not matcher.is_ignored("src/ok.php")

    paths = collect(tmp_path, (".php", ".phtml"))
    assert "src/ok.php" in paths
    assert "src/page.blade.php" not in paths

    config = load_config(tmp_path, _php_env())
    assert full_build(config, store).failed == 0
    assert "src/page.blade.php" not in store.file_paths()


@needs_php
def test_blade_under_stub_root_is_not_collected(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2 under 039: file-level builtins still apply inside CA_STUB_ROOTS."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.php").write_bytes(GOOD)
    vendor = tmp_path / "vendor" / "acme" / "views"
    vendor.mkdir(parents=True)
    (vendor / "Model.php").write_bytes(STUB_PHP)
    (vendor / "page.blade.php").write_bytes(BLADE)
    _git_init(tmp_path)

    stubs = collect_stubs(tmp_path, ("vendor",), (".php", ".phtml"))
    assert "vendor/acme/views/Model.php" in stubs
    assert "vendor/acme/views/page.blade.php" not in stubs

    config = load_config(tmp_path, _php_env(CA_STUB_ROOTS="vendor"))
    assert full_build(config, store).failed == 0
    assert "vendor/acme/views/page.blade.php" not in store.file_paths()
    assert store.nodes_by_qualified_name("\\Lib\\Model", limit=1)


@needs_php
def test_phtml_indexes_when_announced(tmp_path: Path, store: GraphStore) -> None:
    """AC3: .phtml indexes via handshake; collect omits it without that suffix."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.php").write_bytes(GOOD)
    (src / "view.phtml").write_bytes(PHTML)
    _git_init(tmp_path)

    assert "src/view.phtml" not in collect(tmp_path, (".php",))
    assert "src/view.phtml" in collect(tmp_path, (".php", ".phtml"))

    config = load_config(tmp_path, _php_env())
    assert full_build(config, store).failed == 0
    assert store.nodes_by_qualified_name("\\App\\View", limit=1)
