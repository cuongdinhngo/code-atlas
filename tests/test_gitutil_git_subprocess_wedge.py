"""Task 271: git subprocesses must never wedge ``_run`` past its timeout.

Field repro, 2026-09-14 on the headless native-Windows MCP server: an MCP-spawned
``git diff --name-only -z HEAD`` against a real repo sat alive > 3 min while the identical command
in a console returned in 0s, so ``get_index_status`` never returned. Root cause: ``subprocess.run``
on Windows, on ``TimeoutExpired``, does an UNBOUNDED ``communicate()`` after ``kill()`` — a git
grandchild holding the capture pipe blocks the reader forever; and with no explicit stdin git blocks
on an inherited console handle. The fix (Popen + stdin=DEVNULL + CREATE_NO_WINDOW + a tree kill +
a bounded second drain) was applied to the working copy before but never committed, so every pull
reverted it and the server wedged again.

Two guards:
  * ``test_timeout_kills_the_tree_and_bounds_the_drain`` — portable, runs in POSIX CI. Locks each
    leg of the fix individually so a PARTIAL revert also reddens CI.
  * ``test_native_windows_git_wedge_is_bounded`` — win32-only, the real wedge with a real
    pipe-holding grandchild. The bug is native-Windows-only (POSIX ``run`` uses ``wait()``, not a
    second ``communicate()``), so this one cannot run in the Linux CI and is skipped there.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from code_atlas import gitutil

FAKE_GIT = Path(__file__).resolve().parent / "fixtures" / "gitutil" / "fake_git.py"


def test_timeout_kills_the_tree_and_bounds_the_drain(monkeypatch, tmp_path):
    """On a timeout ``_run`` must kill the process TREE and drain with a BOUND, then return None.

    Portable: it fakes a git whose first ``communicate`` never yields EOF (a grandchild holding the
    pipe) and asserts what ``_run`` does next. Old code (``subprocess.run``, no tree kill, no
    bounded drain) fails; the four asserts are separate so a partial revert still reddens CI.
    """
    seen: dict[str, object] = {"popen_kwargs": None, "drains": []}

    class _WedgedPopen:
        def __init__(self, *_args, **kwargs):
            seen["popen_kwargs"] = kwargs
            self.returncode = None
            self.pid = 424242

        def communicate(self, timeout=None):
            seen["drains"].append(timeout)  # type: ignore[attr-defined]
            if len(seen["drains"]) == 1:  # type: ignore[arg-type]
                raise subprocess.TimeoutExpired(cmd="git", timeout=timeout)
            return ("", "")

        def poll(self):
            return None

        def kill(self):
            self.returncode = -9

    class _FakeCompleted:
        returncode = 0
        stdout = "OLD-CODE-RETURNED-A-VALUE-WITH-NO-WEDGE-HANDLING"

    killed: list[object] = []
    # getattr so old code (no _kill_tree) fails on the behavioural asserts below, not here.
    real_kill_tree = getattr(gitutil, "_kill_tree", lambda _proc: None)

    def _spy_kill_tree(proc):
        killed.append(proc)
        real_kill_tree(proc)  # exercise the real helper (proc.kill / taskkill) too

    monkeypatch.setattr(gitutil.subprocess, "Popen", _WedgedPopen)
    monkeypatch.setattr(gitutil, "_kill_tree", _spy_kill_tree, raising=False)
    # win32's _kill_tree shells out to taskkill; keep the unit test hermetic. On old code this is
    # the main git call and returns non-None, so the `result is None` assert fails cleanly (red).
    monkeypatch.setattr(gitutil.subprocess, "run", lambda *a, **k: _FakeCompleted())
    monkeypatch.setattr(gitutil, "GIT_TIMEOUT", 0.01)

    result = gitutil._run(tmp_path, "diff", "--name-only", "-z", "HEAD")

    assert result is None, "a wedged git is None, never a partial answer"
    kwargs = seen["popen_kwargs"]
    assert kwargs is not None, "the fix must spawn git via Popen, not subprocess.run"
    assert kwargs["stdin"] is subprocess.DEVNULL, "stdin=DEVNULL stops the inherited-console block"
    assert kwargs["creationflags"] == gitutil._CREATE_NO_WINDOW, "CREATE_NO_WINDOW must be wired"
    assert killed, "the timeout path must kill the process tree"
    drains = seen["drains"]
    assert len(drains) >= 2, "a drain must run after the tree kill"  # type: ignore[arg-type]
    assert drains[1] is not None and drains[1] <= 5, "the second drain must be BOUNDED, never open"  # type: ignore[index]


def test_kill_tree_falls_back_and_never_raises_when_taskkill_fails(monkeypatch):
    """A stuck or absent taskkill must not reintroduce the wedge: _kill_tree bounds it, and on
    failure falls back to proc.kill() rather than letting the error escape (module contract)."""
    killed = {"n": 0}

    class _Proc:
        pid = 999999

        def poll(self):
            return None

        def kill(self):
            killed["n"] += 1

    def _boom(*_a, **_k):
        raise OSError("taskkill unavailable")

    monkeypatch.setattr(gitutil.sys, "platform", "win32")  # force the taskkill branch on any host
    monkeypatch.setattr(gitutil.subprocess, "run", _boom)

    gitutil._kill_tree(_Proc())  # must not raise

    assert killed["n"] == 1, "a failed taskkill must fall back to proc.kill()"


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="the wedge is native-Windows-only: POSIX subprocess.run uses wait(), not communicate()",
)
def test_native_windows_git_wedge_is_bounded(monkeypatch, tmp_path):
    """The real wedge: a fake git spawns a grandchild that holds the capture pipe and keeps the tree
    alive. Only a TREE kill + bounded drain frees the reader. Old code hangs past the timeout (the
    watchdog thread never finishes); the fix returns None within a few seconds."""
    sentinel = tmp_path / "grandchild-up.txt"
    real_popen = subprocess.Popen

    def _fake_popen(cmd, **kwargs):
        # Swap ONLY the git binary; every real _run kwarg (DEVNULL/PIPE/creationflags/text) and the
        # real taskkill are preserved, so this exercises the actual mechanism.
        if cmd and cmd[0] == "git":
            cmd = [sys.executable, str(FAKE_GIT), str(sentinel)]
        return real_popen(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(gitutil, "GIT_TIMEOUT", 2.0)

    box: dict[str, object] = {}

    def _go():
        box["result"] = gitutil._run(tmp_path, "diff", "--name-only", "-z", "HEAD")

    worker = threading.Thread(target=_go, daemon=True)
    started = time.monotonic()
    worker.start()
    worker.join(15)
    elapsed = time.monotonic() - started

    if worker.is_alive():
        pytest.fail("_run wedged past its timeout — the native-Windows git fix is missing")
    assert sentinel.exists(), "fixture never reached the pipe-holding grandchild (vacuous run)"
    assert box["result"] is None, "a wedged-then-killed git is None"
    assert elapsed < 10, f"returned but too slow ({elapsed:.1f}s) — wedge not cleanly bounded"
