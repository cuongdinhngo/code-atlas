"""Task 268 — six-tool preset, worktree DB refuse, nominations, minimal large walks."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.main import FIELD18_TOOLS, TOOL_NAMES, allowed_tools
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, get_index_status, reachable_from
from code_atlas.tools.nav_result import REASON_INDEX_ROOT_MISMATCH
from code_atlas.tools.nominate_roots import CANDIDATE_ENTRY_GLOBS, entry_point_nominations
from code_atlas.tools.schema_guard import guard
from code_atlas.worktree_guard import worktree_db_refusal

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / ".code-atlas" / "graph.db") as opened:
        yield opened


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_field18_preset_is_six_and_default_is_still_full() -> None:
    """AC1 — documented preset size; default surface stays 24."""
    assert len(FIELD18_TOOLS) == 6
    assert set(FIELD18_TOOLS) <= set(TOOL_NAMES)
    assert len(TOOL_NAMES) == 24
    assert allowed_tools(None) == TOOL_NAMES
    assert allowed_tools(FIELD18_TOOLS) == FIELD18_TOOLS


def test_nominate_entry_globs_count_and_never_auto_apply() -> None:
    """AC3 — candidates list files_matched; zeros stay; patterns are the fixed set."""
    paths = ["public/index.php", "src/main.py", "vendor/pkg/x.php", "readme.md"]
    rows = entry_point_nominations(paths)
    assert [row["glob"] for row in rows] == list(CANDIDATE_ENTRY_GLOBS)
    by_glob = {str(row["glob"]): int(row["files_matched"]) for row in rows}
    assert by_glob["public/**"] == 1
    assert by_glob["**/main.*"] == 1
    assert by_glob["bin/**"] == 0


def test_unbuilt_status_nominates_without_applying(tmp_path: Path) -> None:
    (tmp_path / "public").mkdir()
    (tmp_path / "public" / "index.php").write_text("<?php\n", encoding="utf-8")
    config = load_config(tmp_path, {})
    assert config.entry_points is None
    status = get_index_status.create(config, TOOL_NAMES)(detail_level="minimal")
    assert "entry_point_candidates" in status
    assert "stub_root_candidates" in status
    assert config.entry_points is None
    assert config.stub_roots is None


def test_reachable_from_defaults_to_minimal(tmp_path: Path) -> None:
    """AC4 — large-walk default is minimal (standard still requestable)."""
    import inspect

    config = load_config(tmp_path, {})
    sig = inspect.signature(reachable_from.create(config))
    assert sig.parameters["detail_level"].default == "minimal"


def test_reachable_from_default_payload_smaller_than_standard(tmp_path: Path) -> None:
    """AC4 — measurable size drop on a pinned sample when default is minimal."""
    import json

    from tests.test_reachability import config_for, plant_graph

    with GraphStore(tmp_path / "graph.db") as store:
        plant_graph(store)
    config = config_for(tmp_path)
    tool = reachable_from.create(config)
    default_payload = tool()
    standard_payload = tool(detail_level="standard")
    assert default_payload["status"] == "ok"
    assert standard_payload["status"] == "ok"
    assert "edge_health" not in default_payload
    assert "edge_health" in standard_payload
    default_bytes = len(json.dumps(default_payload, sort_keys=True, default=str))
    standard_bytes = len(json.dumps(standard_payload, sort_keys=True, default=str))
    assert default_bytes < standard_bytes, (default_bytes, standard_bytes)


@needs_php
def test_worktree_outside_db_refuses_ok(tmp_path: Path) -> None:
    """AC2 — linked worktree + CA_DB_PATH outside → index_root_mismatch, never reason=ok."""
    main = tmp_path / "main"
    wt = tmp_path / "wt"
    main.mkdir()
    (main / "src").mkdir()
    (main / "src" / "a.php").write_text(
        "<?php\nnamespace App;\nclass A { public function hit() {} }\n",
        encoding="utf-8",
    )
    _git(main, "init", "-q")
    _git(main, "add", "-A")
    _git(main, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    env = {
        "CA_WORKERS": "2",
        "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
    }
    config_main = load_config(main, env)
    with GraphStore(config_main.db_path) as main_store:
        assert full_build(config_main, main_store).failed == 0
    _git(main, "worktree", "add", str(wt), "HEAD")
    assert (wt / ".git").is_file()
    outside = {
        **env,
        "CA_DB_PATH": str(config_main.db_path.resolve()),
    }
    config_wt = load_config(wt, outside)
    refusal = worktree_db_refusal(config_wt)
    assert refusal is not None
    assert refusal["reason"] == REASON_INDEX_ROOT_MISMATCH
    tool = guard(find_callers.create(config_wt), config_wt)
    payload = tool("\\App\\A::hit", detail_level="minimal")
    assert payload["reason"] == REASON_INDEX_ROOT_MISMATCH
    assert payload.get("reason") != "ok"


def test_worktree_local_db_is_under_worktree(tmp_path: Path) -> None:
    main = tmp_path / "main"
    wt = tmp_path / "wt"
    main.mkdir()
    _git(main, "init", "-q")
    (main / "README").write_text("x\n", encoding="utf-8")
    _git(main, "add", "-A")
    _git(main, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    _git(main, "worktree", "add", str(wt), "HEAD")
    config = load_config(wt, {})
    assert worktree_db_refusal(config) is None
    assert str(wt.resolve()) in str(config.db_path.resolve())


def test_one_line_install_console_script_importable() -> None:
    """AC5 — package exposes the console script named by the one-line install docs."""
    import importlib.metadata

    eps = importlib.metadata.entry_points()
    scripts = eps.select(group="console_scripts") if hasattr(eps, "select") else eps.get(
        "console_scripts", []
    )
    names = {ep.name for ep in scripts}
    assert "code-atlas" in names
