"""Task 357: a request that finds the write lock held is served by the holder, never dropped.

A refused writer leaves ``write.pending`` and tries the lock once more; the holder looks for it
after every unlock and re-runs an incremental while it is set. The window tests drive two writers
through each ordering with a stand-in ``_build``; AC1 is a real rebase with the hooks installed.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.index_lock import build_in_progress, is_pending, pending_path_for
from code_atlas.indexer import full_build
from code_atlas.store import LAST_COMMIT_KEY, GraphStore
from code_atlas.tools import build_or_update_index
from code_atlas.tools.build_or_update_index import create
from tests.test_incremental import FAKE, committed, config_for, fake_env, git

REPO = Path(__file__).resolve().parent.parent
HOOKS = REPO / "contrib" / "git"


class Builds:
    """A stand-in ``_build``: records each call's ``full``, and can hold the first one open."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls: list[bool] = []
        self.entered = threading.Event()
        self.release = threading.Event()
        monkeypatch.setattr(build_or_update_index, "_build", self)

    def __call__(self, config: object, *, full: bool, **_: object) -> dict[str, object]:
        self.calls.append(full)
        if len(self.calls) == 1:
            self.entered.set()
            assert self.release.wait(timeout=10), "the holder's build was never released"
        return {"mode": "full" if full else "incremental", "call": len(self.calls)}


def _holder(config: object, *, full: bool = False) -> tuple[threading.Thread, dict[str, object]]:
    answer: dict[str, object] = {}

    def run() -> None:
        answer.update(create(config)(full=full))  # type: ignore[arg-type]

    thread = threading.Thread(target=run)
    thread.start()
    return thread, answer


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    committed(tmp_path, {"src/Widget.aa": "class Widget {}\n"})
    return tmp_path


def test_a_request_during_the_build_is_served_after_the_unlock(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5, ordering 1: the request lands between the holder's last look and its unlock."""
    config = config_for(repo)
    builds = Builds(monkeypatch)
    thread, holder = _holder(config)
    assert builds.entered.wait(timeout=10)

    late = create(config)()
    builds.release.set()
    thread.join(timeout=10)

    assert late["mode"] == "busy"
    assert builds.calls == [False, False]  # the holder ran once more, for the late request
    assert holder["call"] == 1  # the holder answers its own call
    assert not is_pending(config.db_path)


def test_a_request_landing_after_the_holder_looked_runs_itself(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5, ordering 2: the holder unlocks and finds no request before this one's marker lands.

    The late writer's first try failed while the holder held the lock; it is paused before it
    writes the marker until the holder has returned. Its own retry then takes the lock.
    """
    config = config_for(repo)
    builds = Builds(monkeypatch)
    thread, _ = _holder(config)
    assert builds.entered.wait(timeout=10)
    real_mark = build_or_update_index.mark_pending

    def mark_after_the_holder_left(db_path: Path) -> None:
        builds.release.set()
        thread.join(timeout=10)
        assert not thread.is_alive()
        real_mark(db_path)

    monkeypatch.setattr(build_or_update_index, "mark_pending", mark_after_the_holder_left)

    late = create(config)()

    assert late["mode"] == "incremental"
    assert builds.calls == [False, False]
    assert not is_pending(config.db_path)


def test_two_requests_during_one_build_cost_one_extra_incremental(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2: the marker is a flag, so two waiting requests are one re-run."""
    config = config_for(repo)
    builds = Builds(monkeypatch)
    thread, _ = _holder(config)
    assert builds.entered.wait(timeout=10)

    assert create(config)()["mode"] == "busy"
    assert create(config)()["mode"] == "busy"
    builds.release.set()
    thread.join(timeout=10)

    assert builds.calls == [False, False]


def test_a_request_during_a_full_rebuild_is_one_incremental_after_it(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scope 3: the full rebuild is not repeated; the re-run is an incremental."""
    config = config_for(repo)
    builds = Builds(monkeypatch)
    thread, _ = _holder(config, full=True)
    assert builds.entered.wait(timeout=10)

    create(config)()
    builds.release.set()
    thread.join(timeout=10)

    assert builds.calls == [True, False]


def test_a_marker_left_by_a_dead_holder_is_consumed_by_the_next_writer(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3: no owner, nothing to reclaim — the next writer clears it and runs once."""
    config = config_for(repo)
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path_for(config.db_path).touch()
    builds = Builds(monkeypatch)
    builds.release.set()

    create(config)()

    assert builds.calls == [False]
    assert not is_pending(config.db_path)


def test_a_holder_killed_with_a_marker_pending_strands_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3 with a real kill: SIGKILL drops the lock, the marker stays, the next writer clears it."""
    config = config_for(repo)
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    holder = subprocess.Popen(
        [sys.executable, "-c", _HOLD.format(db=str(config.db_path))],
        env={**os.environ, "PYTHONPATH": str(REPO)},
        stdout=subprocess.PIPE,
        text=True,
    )
    assert holder.stdout is not None and holder.stdout.readline().strip() == "held"
    assert build_in_progress(config.db_path) and is_pending(config.db_path)
    holder.kill()
    holder.wait(timeout=10)
    builds = Builds(monkeypatch)
    builds.release.set()

    create(config)()

    assert not build_in_progress(config.db_path)
    assert builds.calls == [False]
    assert not is_pending(config.db_path)


_HOLD = """
import time
from pathlib import Path
from code_atlas.index_lock import mark_pending, try_index_write_lock
db = Path({db!r})
with try_index_write_lock(db) as held:
    assert held
    mark_pending(db)
    print("held", flush=True)
    time.sleep(60)
"""


def test_a_marker_that_cannot_be_removed_costs_one_build_not_a_loop(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A read-only or foreign marker must not turn the post-unlock look into an endless re-run."""
    config = config_for(repo)
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path_for(config.db_path).touch()
    monkeypatch.setattr(build_or_update_index, "clear_pending", lambda db_path: False)
    builds = Builds(monkeypatch)
    builds.release.set()

    create(config)()

    assert builds.calls == [False]


def _hook_env(root: Path, bin_dir: Path) -> dict[str, str]:
    """Hooks run the tree under test, with one slow-starting adapter so a refresh holds the lock.

    The adapter sleeps before its handshake, so the first pick's refresh is still running when
    the second pick and `post-rewrite` ask; an inherited `CA_<LANG>_CMD` would widen scope (356).
    """
    slow = shlex.join(["sh", "-c", f"sleep 2; exec {shlex.quote(sys.executable)} {FAKE} ok"])
    inherited = {key: value for key, value in os.environ.items() if not key.startswith("CA_")}
    return {
        **inherited,
        **fake_env(),
        "CA_FAKE_CMD": slow,
        "CLAUDE_PROJECT_DIR": str(root),
        "PYTHONPATH": str(REPO),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
    }


def _install_hooks(root: Path) -> Path:
    for name in ("post-commit", "post-rewrite", "post-merge", "post-checkout"):
        target = root / ".git" / "hooks" / name
        shutil.copy(HOOKS / name, target)
        target.chmod(0o755)
    bin_dir = root.parent / f"{root.name}-bin"
    bin_dir.mkdir()
    shim = bin_dir / "code-atlas-refresh"
    shim.write_text(
        f'#!/bin/sh\nexec {shlex.quote(sys.executable)} -m code_atlas.hooks.refresh "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return bin_dir


def _settled(db_path: Path, head: str, *, until: Callable[[], bool], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not build_in_progress(db_path) and not is_pending(db_path) and until():
            break
        time.sleep(0.2)
    time.sleep(1.0)  # a straggling refresh would start inside this window
    while build_in_progress(db_path) and time.monotonic() < deadline:
        time.sleep(0.2)


def _counts(db_path: Path) -> tuple[int, int, int]:
    with GraphStore(db_path) as store:
        conn = store._conn
        return tuple(  # type: ignore[return-value]
            conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("files", "nodes", "edges")
        )


def test_a_real_rebase_of_two_picks_leaves_the_index_at_head(tmp_path: Path) -> None:
    """AC1 (proving test): every pick's refresh but the first finds the lock held; the last
    request still lands, so the index equals a fresh full build at HEAD."""
    root = tmp_path / "repo"
    root.mkdir()
    committed(root, {"src/Base.aa": "class Base {}\n"}, message="base")
    base = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    git(root, "checkout", "-qb", "topic")
    committed(root, {"src/One.aa": "class One {}\n"}, message="one")
    committed(root, {"src/Two.aa": "class Two { One o; }\n"}, message="two")
    git(root, "checkout", "-q", "-")
    committed(root, {"src/Main.aa": "class Main {}\n"}, message="main")
    git(root, "checkout", "-q", "topic")
    config = load_config(root, fake_env())
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    env = _hook_env(root, _install_hooks(root))

    # `-x sleep` spaces the picks, so the first pick's refresh reads its own HEAD.
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "rebase",
            "-q",
            "-x",
            "sleep 0.7",
            base,
        ],
        cwd=root,
        env=env,
        check=True,
        capture_output=True,
    )
    head = git(root, "rev-parse", "HEAD")

    def stamped_at_head() -> bool:
        with GraphStore(config.db_path) as store:
            return store.get_meta(LAST_COMMIT_KEY) == head

    _settled(config.db_path, head, until=stamped_at_head, timeout=60)

    assert stamped_at_head()
    fresh = load_config(root, {**fake_env(), "CA_DB_PATH": str(tmp_path / "fresh.db")})
    with GraphStore(fresh.db_path) as store:
        full_build(fresh, store)
    assert _counts(config.db_path) == _counts(fresh.db_path)
