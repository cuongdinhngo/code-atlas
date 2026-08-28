"""Task 176: ``code-atlas-build`` — a full build from a shell, with no MCP client."""

from __future__ import annotations

import fcntl
import importlib.metadata as md
import os
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

from code_atlas import cli
from code_atlas.config import load_config
from code_atlas.index_lock import LOCK_NAME
from code_atlas.store import GraphStore
from code_atlas.tools.build_or_update_index import create

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"


def fake_env() -> dict[str, str]:
    return {
        "CA_WORKERS": "1",
        "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
    }


def write(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def run_build(
    root: Path,
    *,
    extra_args: list[str] | None = None,
    with_adapter: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
    if with_adapter:
        env.update(fake_env())
    else:
        # Strip EVERY adapter command, not just the fake one: the gate exports `CA_PHP_CMD`, and
        # inheriting it would configure a real adapter and turn this refusal into a success.
        for name in [k for k in env if k.startswith("CA_") and k.endswith("_CMD")]:
            del env[name]
    cmd = [sys.executable, "-m", "code_atlas.cli", *(extra_args or [])]
    return subprocess.run(cmd, env=env, cwd=root, capture_output=True, check=False)


def git_repo(root: Path) -> None:
    """An incremental build needs a git diff; without one the tool correctly falls back to full."""
    for args in (["init", "-q", "."], ["add", "-A"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=root,
        check=True,
        capture_output=True,
    )


def counts_of(root: Path) -> dict[str, int]:
    config = load_config(root, {**fake_env(), "CA_DB_PATH": str(root / ".code-atlas" / "graph.db")})
    with GraphStore(config.db_path) as store:
        return dict(store.counts())


def test_full_build_from_shell_with_no_index_matches_mcp_route(tmp_path: Path) -> None:
    """AC1/AC4: a shell full build on a repo with no index writes the MCP route's rows."""
    shell_root, mcp_root = tmp_path / "shell", tmp_path / "mcp"
    for root in (shell_root, mcp_root):
        write(root, "src/a.aa", "class Thing {}\n")
        write(root, "src/b.aa", "class Other {}\n")

    assert not (shell_root / ".code-atlas" / "graph.db").is_file()
    completed = run_build(shell_root, extra_args=["--full"])
    assert completed.returncode == cli.OK, completed.stderr
    assert (shell_root / ".code-atlas" / "graph.db").is_file()

    config = load_config(
        mcp_root, {**fake_env(), "CA_DB_PATH": str(mcp_root / ".code-atlas" / "graph.db")}
    )
    create(config)(full=True)

    assert counts_of(shell_root) == counts_of(mcp_root)
    assert counts_of(shell_root)["nodes"] == 2


def test_nothing_to_do_is_its_own_exit_code(tmp_path: Path) -> None:
    """AC3: a build with nothing to write is distinguishable from one that wrote."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    git_repo(tmp_path)
    assert run_build(tmp_path, extra_args=["--full"]).returncode == cli.OK

    completed = run_build(tmp_path)
    assert completed.returncode == cli.NOTHING_TO_DO
    assert b"incremental: 0 file(s)" in completed.stderr


def test_busy_peer_is_its_own_exit_code(tmp_path: Path) -> None:
    """AC3/R4.3: a peer holding the one write lock is a named skip, not a failure."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    assert run_build(tmp_path, extra_args=["--full"]).returncode == cli.OK
    before = counts_of(tmp_path)

    lock_path = tmp_path / ".code-atlas" / LOCK_NAME
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            completed = run_build(tmp_path, extra_args=["--full"])
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    assert completed.returncode == cli.BUSY_PEER
    assert b"another build is running" in completed.stderr
    assert counts_of(tmp_path) == before


def test_failure_is_its_own_exit_code(tmp_path: Path) -> None:
    """AC3: an unusable adapter fails the process, so a CI job cannot read it as success."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    completed = run_build(tmp_path, extra_args=["--full"], with_adapter=False)
    assert completed.returncode == cli.FAILED
    assert b"refused: no_usable_adapter" in completed.stderr
    assert counts_of(tmp_path)["nodes"] == 0


def test_refresh_hook_still_never_builds_without_an_index(tmp_path: Path) -> None:
    """AC2: 053's safety property is untouched — the full path is opt-in per invocation."""
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), **fake_env()}
    for args in ([], ["--full"]):
        completed = subprocess.run(
            [sys.executable, "-m", "code_atlas.hooks.refresh", *args],
            env=env,
            cwd=tmp_path,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0
        assert not (tmp_path / ".code-atlas" / "graph.db").is_file()


def test_build_cli_is_a_declared_entry_point() -> None:
    """AC5: gate.sh derives its check from [project.scripts], so the script must be declared."""
    declared = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["scripts"]
    assert declared["code-atlas-build"] == "code_atlas.cli:main"
    installed = {
        e.name: e
        for e in md.entry_points(group="console_scripts")
        if e.dist and e.dist.name == "code-atlas"
    }
    assert installed["code-atlas-build"].load() is cli.main
