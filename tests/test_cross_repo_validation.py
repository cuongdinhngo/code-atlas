"""Task 018: cross-repo harness assert bar + parse isolation (Plan §16 / R6.3)."""

from __future__ import annotations

import importlib.util
import json
import re
import shlex
import shutil
import subprocess
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
ADAPTERS = REPO / "adapters"


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


def test_manifest_covers_both_adapters_with_floors() -> None:
    """AC4: PHP+TS unchanged; Python+SQL shapes pinned with floors (233)."""
    samples = load_manifest(MANIFEST)
    by_lang: dict[str, set[str]] = {}
    for s in samples:
        by_lang.setdefault(str(s.get("language", "php")), set()).add(s["kind"])
    # PHP set is byte-identical to task 018 — this ticket must not perturb it.
    assert by_lang["php"] == {"laravel_app", "symfony_app", "psr4_library"}
    # TS/JS variety is the deliverable: a .ts-only lib, a mixed tree, a compiled-beside-source tree.
    assert {"ts_library", "ts_js_mixed", "compiled_beside_source"} <= by_lang["typescript"]
    assert sum(1 for s in samples if s.get("language") == "typescript") >= 3
    # 233: three Python shapes + at least one SQL pin.
    assert {
        "python_library",
        "python_src_layout",
        "python_flat_package",
    } <= by_lang["python"]
    assert sum(1 for s in samples if s.get("language") == "sql") >= 1
    assert "sql" in _harness._ADAPTERS
    assert not str(MANIFEST.resolve()).startswith(str(ADAPTERS.resolve()))
    for sample in samples:
        assert sample["sha"]
        assert sample["url"].startswith("https://")
        assert int(sample["min_files"]) >= 1
        assert int(sample["min_nodes"]) >= 1
        assert int(sample["min_edges"]) >= 1


def test_manifest_floor_bites_when_min_nodes_lowered() -> None:
    """AC2 / R6.5: a floor nobody has seen fail is not a gate — lowering min_nodes must fail."""
    samples = load_manifest(MANIFEST)
    py = next(s for s in samples if s.get("language") == "python")
    sql = next(s for s in samples if s.get("language") == "sql")
    for sample in (py, sql):
        floor = int(sample["min_nodes"])
        weak = BuildReport(
            files=max(int(sample["min_files"]), 1),
            parsed=1,
            failed=0,
            removed=0,
            nodes=max(floor - 1, 0),
            edges=max(int(sample["min_edges"]), 1),
        )
        with pytest.raises(PlausibleCountsError, match="nodes"):
            assert_plausible_counts(
                weak,
                label=str(sample["id"]),
                min_files=int(sample["min_files"]),
                min_nodes=floor,
                min_edges=int(sample["min_edges"]),
            )


def test_adapters_dict_names_python_and_sql() -> None:
    """R1: adding a language is a row in `_ADAPTERS`, never a code branch."""
    assert set(_harness._ADAPTERS) >= {"php", "typescript", "python", "sql"}
    assert _harness._ADAPTERS["sql"]["env"] == "CA_SQL_CMD"
    assert _harness._ADAPTERS["python"]["env"] == "CA_PYTHON_CMD"


def test_manifest_sample_names_absent_from_adapter_source() -> None:
    """R2.2: same denylist spirit as ci.yml — framework pins must not leak into adapters/."""
    # Match the CI gate's framework tokens; add brick (this ticket's library pin).
    pattern = re.compile(r"laravel|symfony|wordpress|drupal|magento|brick", re.I)
    hits: list[str] = []
    for path in ADAPTERS.rglob("*"):
        if not path.is_file():
            continue
        if "vendor" in path.parts or "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            hits.append(str(path.relative_to(REPO)))
    assert hits == [], f"framework/sample names leaked into adapters/: {hits}"


def test_assert_plausible_counts_rejects_empty() -> None:
    empty = BuildReport(files=0, parsed=0, failed=0, removed=0, nodes=0, edges=0)
    with pytest.raises(PlausibleCountsError, match="files"):
        assert_plausible_counts(empty, label="empty")


def test_assert_plausible_counts_rejects_zero_edges() -> None:
    nodes_only = BuildReport(files=2, parsed=2, failed=0, removed=0, nodes=3, edges=0)
    with pytest.raises(PlausibleCountsError, match="edges"):
        assert_plausible_counts(nodes_only, label="no-edges")


def test_assert_plausible_counts_respects_sample_floors() -> None:
    weak = BuildReport(files=10, parsed=10, failed=0, removed=0, nodes=50, edges=100)
    with pytest.raises(PlausibleCountsError, match="nodes"):
        assert_plausible_counts(weak, label="weak", min_files=5, min_nodes=60, min_edges=1)


def test_assert_parse_isolation_failure_ratio() -> None:
    mostly_ok = BuildReport(files=100, parsed=99, failed=1, removed=0, nodes=10, edges=10)
    assert_parse_isolation(mostly_ok, label="ok", max_failure_ratio=0.02)
    bad = BuildReport(files=100, parsed=90, failed=10, removed=0, nodes=10, edges=10)
    with pytest.raises(PlausibleCountsError, match="failure ratio"):
        assert_parse_isolation(bad, label="bad", max_failure_ratio=0.02)


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


def test_resolve_adapter_cmd_is_per_language(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC3: one code path, adapter argv as DATA — the command is keyed by language, not branched."""
    resolve_adapter_cmd = _harness.resolve_adapter_cmd
    monkeypatch.delenv("CA_PHP_CMD", raising=False)
    monkeypatch.delenv("CA_TYPESCRIPT_CMD", raising=False)

    php = resolve_adapter_cmd("php")
    ts = resolve_adapter_cmd("typescript")
    assert "adapters/php/index.php" in php.replace("\\", "/")
    assert "adapters/typescript/index.js" in ts.replace("\\", "/")
    assert ts.split()[0] == "node"
    # The back-compat wrapper is exactly the php branch (PHP path byte-identical).
    assert _harness.resolve_php_cmd() == php
    with pytest.raises(KeyError):
        resolve_adapter_cmd("cobol")


def test_sparse_paths_materializes_nested_git_repo(tmp_path: Path) -> None:
    """233: sparse_paths must not rely on a bare dir inside this worktree (parent git ls-files)."""
    # Use an existing local git repo as the "remote" so the test stays offline.
    remote = tmp_path / "remote"
    remote.mkdir()
    git = ["git", "-c", "advice.detachedHead=false"]
    subprocess.run([*git, "init", str(remote)], check=True)
    nested = remote / "schema"
    nested.mkdir()
    (nested / "t.sql").write_text("CREATE TABLE dbo.t (id INT);\n", encoding="utf-8")
    (remote / "other.sql").write_text("CREATE TABLE dbo.other (id INT);\n", encoding="utf-8")
    subprocess.run([*git, "-C", str(remote), "add", "-A"], check=True)
    subprocess.run(
        [
            *git,
            "-C",
            str(remote),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-m",
            "x",
        ],
        check=True,
    )
    sha = subprocess.check_output([*git, "-C", str(remote), "rev-parse", "HEAD"], text=True).strip()
    sample = {
        "id": "sparse_fixture",
        "url": str(remote),
        "sha": sha,
        "sparse_paths": ["schema"],
    }
    root = _harness.checkout_pinned(sample, tmp_path / "cache")
    assert (root / ".git").is_dir()
    assert (root / "schema" / "t.sql").is_file()
    assert not (root / "other.sql").exists()
