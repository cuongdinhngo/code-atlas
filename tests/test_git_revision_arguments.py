"""Task 419 — a revision read from the index never reaches git as an option."""

from __future__ import annotations

import ast
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from code_atlas import gitutil
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.overlay import active_overlay
from code_atlas.store import LAST_COMMIT_KEY, GraphStore
from code_atlas.tools import build_or_update_index, get_index_status
from code_atlas.tools.freshness import dirty_indexed_paths

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
VICTIM_BYTES = b"must survive\n"
SHA1 = "a" * 40


def _env() -> dict[str, str]:
    return {"CA_WORKERS": "1", "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"])}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repo(tmp_path: Path) -> tuple[Path, Path, Config]:
    """A built repo, a linked worktree of it, and a victim file outside both."""
    root, worktree = tmp_path / "repo", tmp_path / "wt"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.aa").write_text("class Thing {}\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    config = load_config(root, _env())
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    _git(root, "worktree", "add", "-q", "-b", "feature", str(worktree))
    (worktree / "src" / "a.aa").write_text("class Other {}\n", encoding="utf-8")
    (tmp_path / "victim.txt").write_bytes(VICTIM_BYTES)
    return worktree, tmp_path / "victim.txt", config


def _poison(config: Config, victim: Path) -> None:
    with GraphStore(config.db_path) as store:
        store.set_meta(LAST_COMMIT_KEY, f"--output={victim}")


def _hook(module: str, root: Path) -> None:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root), **_env()}
    subprocess.run(
        [sys.executable, "-m", module],
        input=b'{"hook_event_name": "SessionStart"}',
        env=env,
        cwd=root,
        capture_output=True,
    )


def _freshness(config: Config) -> None:
    with GraphStore(config.db_path) as store:
        dirty_indexed_paths(store, config)


def _overlay(config: Config, worktree: Path) -> None:
    with GraphStore(config.db_path) as store:
        active_overlay(config, store, worktree)


@pytest.mark.parametrize(
    "step",
    ["freshness", "overlay", "get_index_status", "state_hook", "refresh_hook", "build"],
)
def test_a_poisoned_last_commit_leaves_the_victim_untouched(tmp_path: Path, step: str) -> None:
    worktree, victim, config = _repo(tmp_path)
    _poison(config, victim)
    steps: dict[str, Callable[[], object]] = {
        "freshness": lambda: _freshness(config),
        "overlay": lambda: _overlay(config, worktree),
        "get_index_status": lambda: get_index_status.create(config, ())(),
        "state_hook": lambda: _hook("code_atlas.hooks.state", config.root),
        "refresh_hook": lambda: _hook("code_atlas.hooks.refresh", config.root),
        "build": lambda: build_or_update_index.create(config)(full=False),
    }
    steps[step]()
    assert victim.read_bytes() == VICTIM_BYTES


def test_a_non_object_id_is_refused_and_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    worktree, _, _ = _repo(tmp_path)
    assert gitutil.changed_paths(worktree, "HEAD~1") is None
    assert "not a full object id" in capsys.readouterr().err
    head = gitutil.head_commit(worktree)
    assert head is not None and gitutil.changed_paths(worktree, head) == ("src/a.aa",)


def test_every_call_carries_the_hardening(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: list[tuple[list[str], dict[str, str]]] = []

    class Spy:
        returncode = 0

        def __init__(self, argv: list[str], **kwargs: object) -> None:
            env = kwargs["env"]
            assert isinstance(env, dict)
            seen.append((argv, env))

        def communicate(self, timeout: float) -> tuple[str, str]:
            return "", ""

    monkeypatch.setattr(gitutil.subprocess, "Popen", Spy)
    gitutil.changed_paths(tmp_path, SHA1)
    gitutil.ls_files(tmp_path)
    for argv, env in seen:
        assert env["GIT_CONFIG_NOSYSTEM"] == "1" and env["GIT_TERMINAL_PROMPT"] == "0"
        for setting in gitutil.HARDENED_CONFIG:
            assert f"-c {setting}" in " ".join(argv)
    diff = seen[0][0]
    assert "--no-ext-diff" in diff and "--no-textconv" in diff
    assert diff[diff.index("--end-of-options") + 1 :] == [SHA1, "--"]


def test_an_old_git_fails_loud(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = tmp_path / "bin" / "git"
    fake.parent.mkdir()
    fake.write_text(
        '#!/bin/sh\ncase "$*" in *--version*) echo "git version 2.20.1";; *) exit 128;; esac\n'
    )
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake.parent}{os.pathsep}{os.environ['PATH']}")
    gitutil.git_version.cache_clear()
    try:
        assert gitutil.changed_paths(tmp_path, SHA1) is None
    finally:
        gitutil.git_version.cache_clear()
    assert "2.24" in capsys.readouterr().err


# adapter.py launches CA_<LANG>_CMD, never git; gitutil.py is the one home of git (AC5).
SPAWNERS = {"gitutil.py", "adapter.py"}
_OS_SPAWNS = ("system", "popen", "exec", "spawn", "posix_spawn", "fork")


def _spawn_sites(tree: ast.AST) -> list[int]:
    """Lines that import ``subprocess`` (any form) or call an ``os`` process spawner."""
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            alias.name.split(".")[0] == "subprocess" for alias in node.names
        ):
            lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "subprocess":
            lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            if any(alias.name.startswith(_OS_SPAWNS) for alias in node.names):
                lines.append(node.lineno)
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
            and node.attr.startswith(_OS_SPAWNS)
        ):
            lines.append(node.lineno)
    return lines


def test_only_gitutil_runs_git() -> None:
    core = REPO / "code_atlas"
    found = {
        str(path.relative_to(REPO)): lines
        for path in sorted(core.rglob("*.py"))
        if path.name not in SPAWNERS
        and (lines := _spawn_sites(ast.parse(path.read_text(encoding="utf-8"))))
    }
    assert found == {}, json.dumps(found)
    adapter = (core / "adapter.py").read_text(encoding="utf-8")
    assert '"git"' not in adapter and "'git'" not in adapter
