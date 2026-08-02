"""Task 018: cross-repo harness assert bar + parse isolation (Plan §16 / R6.3)."""

from __future__ import annotations

import importlib.util
import json
import shlex
import shutil
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.indexer import BuildReport, full_build
from code_atlas.store import GraphStore

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
MANIFEST = REPO / "scripts" / "cross_repo_samples.json"
HARNESS = REPO / "scripts" / "cross_repo_validate.py"
SYNTAX_ERROR = REPO / "tests" / "fixtures" / "php" / "syntax_error.php"
NAMESPACED = REPO / "tests" / "fixtures" / "php" / "namespaced.php"


def _load_harness():
    spec = importlib.util.spec_from_file_location("cross_repo_validate", HARNESS)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_harness = _load_harness()
PlausibleCountsError = _harness.PlausibleCountsError
assert_parse_isolation = _harness.assert_parse_isolation
assert_plausible_counts = _harness.assert_plausible_counts
load_manifest = _harness.load_manifest

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)


def test_manifest_lists_three_public_kinds() -> None:
    samples = load_manifest(MANIFEST)
    assert len(samples) == 3
    kinds = {s["kind"] for s in samples}
    assert kinds == {"laravel_app", "symfony_app", "psr4_library"}
    for sample in samples:
        assert sample["sha"]
        assert sample["url"].startswith("https://")
        assert "adapters/" not in str(MANIFEST.relative_to(REPO))


def test_assert_plausible_counts_rejects_empty() -> None:
    empty = BuildReport(files=0, parsed=0, failed=0, removed=0, nodes=0, edges=0)
    with pytest.raises(PlausibleCountsError, match="files"):
        assert_plausible_counts(empty, label="empty")


def test_assert_plausible_counts_accepts_positive() -> None:
    ok = BuildReport(files=2, parsed=1, failed=1, removed=0, nodes=3, edges=1)
    assert_plausible_counts(ok, label="ok")
    assert_parse_isolation(ok, label="ok", expect_failures=True)


@needs_php
def test_harness_plausible_counts_and_parse_isolation(tmp_path: Path) -> None:
    """Proving test: mini-repo with one good + one broken file (A2 + A5)."""
    (tmp_path / "src").mkdir()
    shutil.copy(NAMESPACED, tmp_path / "src" / "Good.php")
    shutil.copy(SYNTAX_ERROR, tmp_path / "src" / "Broken.php")

    php_cmd = shlex.join([PHP or "php", str(PHP_ENTRY), "--server"])
    config = load_config(
        tmp_path,
        {"CA_PHP_CMD": php_cmd, "CA_DB_PATH": str(tmp_path / "graph.db")},
    )
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)

    assert_plausible_counts(report, label="mini")
    assert_parse_isolation(report, label="mini", expect_failures=True)
    assert report.parsed >= 1
    assert report.failed >= 1


def test_manifest_is_valid_json_on_disk() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert "samples" in data
