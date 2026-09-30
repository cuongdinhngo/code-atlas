"""Task 355: a commit refreshes the index, and a refused refresh reaches the state line.

1. ``contrib/git/post-commit`` and ``post-rewrite`` are run by real git in a temp repo, against a
   stand-in ``code-atlas-refresh`` on PATH that only logs each call — so the count is the hooks',
   not the build's.
2. An index whose covered language has no adapter now says so in its one-sentence summary, and
   ``code-atlas-state`` prints it at an unmoved HEAD instead of staying silent on ``current``.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.indexer import COVERAGE_LOSS_HINT, full_build
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status

REPO = Path(__file__).resolve().parent.parent
HOOKS = REPO / "contrib" / "git"
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
SETTLE = 1.0


def git(root: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root, check=True, capture_output=True, env=env,
    )


def hooked_repo(root: Path) -> tuple[dict[str, str], Path]:
    """A repo with both hooks installed and a logging stand-in for `code-atlas-refresh`."""
    git(root, "init", "-q", ".")
    for name in ("post-commit", "post-rewrite"):
        target = root / ".git" / "hooks" / name
        shutil.copy(HOOKS / name, target)
        target.chmod(0o755)
    bin_dir = root.parent / f"{root.name}-bin"
    bin_dir.mkdir()
    log = root.parent / f"{root.name}-refresh.log"
    stub = bin_dir / "code-atlas-refresh"
    stub.write_text(f"#!/bin/sh\necho refresh >> {shlex.quote(str(log))}\n", encoding="utf-8")
    stub.chmod(0o755)
    return {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}, log


def refreshes(log: Path, expected: int) -> int:
    """How many background refreshes ran, once the count has reached ``expected`` and settled."""
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if log.is_file() and len(log.read_text(encoding="utf-8").splitlines()) >= expected:
            break
        time.sleep(0.05)
    time.sleep(SETTLE)  # a second, unwanted refresh would land inside this window
    return len(log.read_text(encoding="utf-8").splitlines()) if log.is_file() else 0


def test_a_commit_and_an_amend_each_trigger_one_refresh(tmp_path: Path) -> None:
    """AC1 (proving test): one background refresh per commit and per amend — an amend also fires
    post-rewrite, which must not add a second."""
    root = tmp_path / "repo"
    root.mkdir()
    env, log = hooked_repo(root)
    (root / "a.txt").write_text("one\n", encoding="utf-8")
    git(root, "add", "-A", env=env)

    git(root, "commit", "-qm", "one", env=env)
    assert refreshes(log, 1) == 1

    (root / "a.txt").write_text("two\n", encoding="utf-8")
    git(root, "commit", "-qam", "one, amended", "--amend", env=env)
    assert refreshes(log, 2) == 2


def test_a_rebase_refreshes_after_its_last_pick(tmp_path: Path) -> None:
    """post-rewrite's own case: once more after the rebase, on top of post-commit's per-pick calls."""
    root = tmp_path / "repo"
    root.mkdir()
    env, log = hooked_repo(root)
    (root / "base.txt").write_text("base\n", encoding="utf-8")
    git(root, "add", "-A", env=env)
    git(root, "commit", "-qm", "base", env=env)
    git(root, "checkout", "-qb", "side", env=env)
    (root / "side.txt").write_text("side\n", encoding="utf-8")
    git(root, "add", "-A", env=env)
    git(root, "commit", "-qm", "side", env=env)
    git(root, "checkout", "-q", "-", env=env)
    (root / "main.txt").write_text("main\n", encoding="utf-8")
    git(root, "add", "-A", env=env)
    git(root, "commit", "-qm", "main", env=env)
    before = refreshes(log, 3)

    git(root, "checkout", "-q", "side", env=env)
    git(root, "rebase", "-q", "-", env=env)

    # One post-commit for the single pick, one post-rewrite for the rebase.
    assert refreshes(log, before + 2) == before + 2


def coverage_loss_index(root: Path) -> dict[str, str]:
    """A committed repo indexed with the fake adapter, then read with no adapter configured."""
    (root / "src").mkdir()
    (root / "src" / "a.aa").write_text("class Thing {}\n", encoding="utf-8")
    git(root, "init", "-q", ".")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "one")
    db = root / ".code-atlas" / "graph.db"
    built = load_config(
        root,
        {"CA_WORKERS": "1", "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
         "CA_DB_PATH": str(db)},
    )
    with GraphStore(built.db_path) as store:
        full_build(built, store)
    inherited = {k: v for k, v in os.environ.items() if not k.startswith("CA_")}
    return {**inherited, "CA_DB_PATH": str(db), "CLAUDE_PROJECT_DIR": str(root)}


def test_a_pending_coverage_loss_is_in_the_summary_with_its_route(tmp_path: Path) -> None:
    """AC2: the summary names the refusal and the fix, so the one line a session reads carries it."""
    env = coverage_loss_index(tmp_path)
    status = get_index_status.create(load_config(tmp_path, env), ())()

    assert status["staleness"] == "current"
    assert get_index_status.COVERAGE_LOSS_PENDING in status
    summary = str(status["summary"])
    assert "fake" in summary and COVERAGE_LOSS_HINT in summary, summary


def test_the_state_hook_speaks_for_a_coverage_loss_at_an_unmoved_head(tmp_path: Path) -> None:
    """AC2: `code-atlas-state` on SessionStart prints the loss although the index is `current`."""
    env = coverage_loss_index(tmp_path)
    completed = subprocess.run(
        [sys.executable, "-m", "code_atlas.hooks.state"],
        input=json.dumps({"hook_event_name": "SessionStart", "source": "startup"}),
        env=env, cwd=tmp_path, capture_output=True, text=True, check=True,
    )

    assert "fake" in completed.stdout and COVERAGE_LOSS_HINT in completed.stdout, completed


def test_no_pending_loss_leaves_the_summary_byte_identical() -> None:
    """AC4 (061): the clause rides only on the state that has it."""
    payload: dict[str, object] = {
        "files": 3, "nodes": 7, "last_commit": "a" * 40, "indexed": True,
        "staleness": "current", "edge_health": {"unlinked": 0},
    }
    assert get_index_status._compose_summary(payload) == "current @ aaaaaaa · 3 files · 7 symbols · healthy"
