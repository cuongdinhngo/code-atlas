"""Task 448 — an `EXEC` target links case-insensitively to one routine; its misses are counted."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import BuildReport, full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, get_index_status
from tests.sql_adapter_cli import CLI, needs_node

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)
pytestmark = needs_node

PROCS = {
    "db/procs.sql": (
        "CREATE PROCEDURE dbo.Insert_Order AS SELECT 1\nGO\n"
        "CREATE PROCEDURE sales.Close_Order AS SELECT 1\nGO\n"
    ),
    "db/caller.sql": (
        "CREATE PROCEDURE dbo.Nightly AS\nBEGIN\n"
        "    exec insert_order\n"
        "    exec SALES.close_order\n"
        "END\nGO\n"
    ),
}
HOST = {
    "src/Repo.php": (
        "<?php\nclass Repo {\n"
        "    public function save($db) { $db->query('exec insert_order @id = 1'); }\n}\n"
    ),
}
# Two schemas declare one name: a bare call names neither, so it stays unlinked and counted.
TWINS = {
    "db/twins.sql": (
        "CREATE PROCEDURE dbo.Twin_Proc AS SELECT 1\nGO\n"
        "CREATE PROCEDURE sales.TWIN_PROC AS SELECT 1\nGO\n"
        "CREATE PROCEDURE dbo.UsesTwin AS\nBEGIN\n    exec twin_proc\nEND\nGO\n"
    ),
}


def _built(root: Path, files: dict[str, str]) -> tuple[Config, BuildReport]:
    for rel, body in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "init")):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=root,
            check=True,
            capture_output=True,
        )
    env = {"CA_WORKERS": "2"}
    if any(rel.endswith(".sql") for rel in files):
        env["CA_SQL_CMD"] = shlex.join([*CLI.entry_argv, "--server"])
    if any(rel.endswith(".php") for rel in files):
        env["CA_PHP_CMD"] = shlex.join([str(PHP), str(PHP_ENTRY), "--server"])
    config = load_config(root, env)
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
    assert report.failed == 0
    return config, report


def _callers(config: Config, subject: str) -> set[str]:
    payload = find_callers.create(config)(subject, detail_level="minimal")
    rows = payload["results"]
    assert isinstance(rows, list)
    return {str(row["qname"]) for row in rows if "candidate_of" not in row}


def test_ac1_a_lowercase_bare_exec_links_from_tsql(tmp_path: Path) -> None:
    config, _ = _built(tmp_path, PROCS)
    assert "dbo.Nightly" in _callers(config, "dbo.Insert_Order")


@needs_php
def test_ac1_a_lowercase_exec_in_a_php_string_links(tmp_path: Path) -> None:
    config, _ = _built(tmp_path, {**PROCS, **HOST})
    assert {"dbo.Nightly", "\\Repo::save"} <= _callers(config, "dbo.Insert_Order")


def test_scope2_a_schema_qualified_exec_folds_in_its_own_schema(tmp_path: Path) -> None:
    config, _ = _built(tmp_path, PROCS)
    assert "dbo.Nightly" in _callers(config, "sales.Close_Order")


def test_ac2_one_name_in_two_schemas_stays_unlinked_and_counted(tmp_path: Path) -> None:
    config, report = _built(tmp_path, TWINS)
    for qname in ("dbo.Twin_Proc", "sales.TWIN_PROC"):
        assert "dbo.UsesTwin" not in _callers(config, qname)
    assert report.exec_unresolved == 1
    status = get_index_status.create(config, (get_index_status.NAME,))(detail_level="standard")
    assert status["exec_unresolved"] == 1


@needs_php
def test_scope3_a_linked_index_counts_zero_and_status_says_so(tmp_path: Path) -> None:
    config, report = _built(tmp_path, {**PROCS, **HOST})
    assert report.exec_unresolved == 0
    assert get_index_status.create(config, (get_index_status.NAME,))(detail_level="standard")["exec_unresolved"] == 0


@needs_php
def test_scope3_a_host_string_miss_is_counted(tmp_path: Path) -> None:
    missing = {
        "src/Gone.php": "<?php\nfunction f($db) { $db->query('exec no_such_proc @id = 1'); }\n"
    }
    _, report = _built(tmp_path, {**PROCS, **missing})
    assert report.exec_unresolved == 1


@needs_php
def test_out_of_scope_a_php_function_never_folds_onto_a_routine(tmp_path: Path) -> None:
    """Casefold is the SQL routines' rule: a PHP call keeps exact matching (386)."""
    php = {
        "src/use.php": "<?php\nfunction run() { INSERT_ORDER(); }\nfunction insert_order() {}\n"
    }
    config, _ = _built(tmp_path, {**PROCS, **php})
    assert "\\run" not in _callers(config, "dbo.Insert_Order")


@needs_php
def test_no_folding_adapter_leaves_status_unchanged(tmp_path: Path) -> None:
    """A repo with no SQL keeps an unchanged status: no `exec_unresolved` key at all."""
    config, report = _built(tmp_path, HOST)
    assert report.exec_unresolved == 0
    status = get_index_status.create(config, (get_index_status.NAME,))(detail_level="standard")
    assert "exec_unresolved" not in status
