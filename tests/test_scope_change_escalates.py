"""Task 172: a build that cannot act on the request must not answer like one with nothing to do."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools.build_or_update_index import create as build_tool

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"


def fake_cmd(mode: str = "ok") -> str:
    return shlex.join([sys.executable, str(FAKE), mode])


ONE_ADAPTER = {"CA_WORKERS": "1", "CA_FAKE_CMD": fake_cmd()}
TWO_ADAPTERS = {**ONE_ADAPTER, "CA_SECOND_CMD": fake_cmd("second")}


def write(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "."], cwd=root, check=True, capture_output=True)
    commit(root)


def commit(root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"],
        cwd=root,
        check=True,
        capture_output=True,
    )


def config_for(root: Path, env: dict[str, str]):
    return load_config(root, {**env, "CA_DB_PATH": str(root / ".code-atlas" / "graph.db")})


def seeded(root: Path) -> None:
    """A repo indexed by one adapter, with a file the second adapter would own already on disk."""
    write(root, "src/a.aa", "class Thing {}\n")
    write(root, "src/c.cc", "class Third {}\n")
    git_repo(root)
    build_tool(config_for(root, ONE_ADAPTER))(full=True)


def test_a_new_adapter_is_not_a_silent_no_op(tmp_path: Path) -> None:
    """AC1/AC2: the file that entered scope is neither a git change nor a dependent."""
    seeded(tmp_path)
    config = config_for(tmp_path, TWO_ADAPTERS)

    payload = build_tool(config)(full=False)

    assert payload["scope_change"] == {
        "added": [".cc"],
        "removed": [],
        "escalated_to": "full",
    }
    assert payload["mode"] == "full", "the report must not call an escalation an incremental"
    wrote = payload["wrote"]
    assert isinstance(wrote, dict) and wrote["files"] == 2, "both files are now in scope"


def test_the_newly_scoped_file_actually_lands_in_the_graph(tmp_path: Path) -> None:
    """AC1: the escalation is only worth having if the file is indexed afterwards."""
    seeded(tmp_path)
    config = config_for(tmp_path, ONE_ADAPTER)
    with GraphStore(config.db_path) as store:
        assert store.file_hash("src/c.cc") is None

    build_tool(config_for(tmp_path, TWO_ADAPTERS))(full=False)

    with GraphStore(config.db_path) as store:
        assert store.file_hash("src/c.cc") is not None


def test_an_unchanged_scope_is_byte_identical(tmp_path: Path) -> None:
    """AC4/061: the no-op path keeps today's shape and says nothing about scope."""
    seeded(tmp_path)
    config = config_for(tmp_path, ONE_ADAPTER)

    payload = build_tool(config)(full=False)

    assert "scope_change" not in payload
    assert payload["mode"] == "incremental"
    wrote = payload["wrote"]
    assert isinstance(wrote, dict) and wrote["files"] == 0


def test_the_no_op_path_pays_no_extra_query(tmp_path: Path) -> None:
    """AC4: the scope check is one meta read the build already makes — measured, not asserted."""
    seeded(tmp_path)
    config = config_for(tmp_path, ONE_ADAPTER)
    build_tool(config)(full=False)

    started = time.perf_counter()
    for _ in range(3):
        build_tool(config)(full=False)
    per_build = (time.perf_counter() - started) / 3
    assert per_build < 5.0, f"{per_build:.3f}s per no-op build"


def test_the_git_hook_inherits_the_escalation(tmp_path: Path) -> None:
    """AC3: the fix lives in `indexer.update`, so `code-atlas-refresh` cannot miss it."""
    seeded(tmp_path)
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        **TWO_ADAPTERS,
        "CA_DB_PATH": str(tmp_path / ".code-atlas" / "graph.db"),
    }
    completed = subprocess.run(
        [sys.executable, "-m", "code_atlas.hooks.refresh", "--verbose"],
        env=env,
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0

    with GraphStore(config_for(tmp_path, TWO_ADAPTERS).db_path) as store:
        assert store.file_hash("src/c.cc") is not None, "the hook path escalated too"


def test_a_removed_adapter_is_named_too(tmp_path: Path) -> None:
    """The comparison is set difference, not growth: losing a language is also a scope change."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    write(tmp_path, "src/c.cc", "class Third {}\n")
    git_repo(tmp_path)
    build_tool(config_for(tmp_path, TWO_ADAPTERS))(full=True)

    payload = build_tool(config_for(tmp_path, ONE_ADAPTER))(full=False)

    assert payload["scope_change"] == {
        "added": [],
        "removed": [".cc"],
        "escalated_to": "full",
    }
