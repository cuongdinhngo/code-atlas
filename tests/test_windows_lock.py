"""Task 237: the index lock works on native Windows, and its POSIX behaviour is unchanged.

The lock is the only POSIX-only import the core had (`fcntl`). These tests pin the platform-selected
arm: on Windows the byte-range lock via `LockFileEx`, on POSIX the unchanged `flock`. The Windows
cases are the ticket's AC2-AC4 arm; CI runs the POSIX arm and the cross-platform cases.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import time
from pathlib import Path

import pytest

from code_atlas import index_lock
from code_atlas.index_lock import build_in_progress

ENTRY_MODULES = (
    "code_atlas.cli",
    "code_atlas.main",
    "code_atlas.tools.build_or_update_index",
    "code_atlas.tools.get_index_status",
)
LOCK_SOURCE = Path(index_lock.__file__)


def test_entry_modules_import_without_fcntl() -> None:
    """AC1 — the proving test. `fcntl` is imported only under the non-win32 arm, not at module top.

    Red before the fix: `index_lock.py` did `import fcntl` at module scope, so on a host without
    `fcntl` (Windows) every entry point raised `ModuleNotFoundError`. Green after: the import is
    guarded by the `sys.platform` switch. Proven from the platform the test runs on — on win32 the
    modules import with `fcntl` genuinely absent; on POSIX the guard is asserted structurally so the
    win32 host would import.
    """
    if sys.platform == "win32":
        import importlib

        assert "fcntl" not in sys.modules, "fcntl does not exist on Windows"
        for name in ENTRY_MODULES:
            assert importlib.import_module(name) is not None
        return

    tree = ast.parse(LOCK_SOURCE.read_text(encoding="utf-8"))
    top_level_fcntl = [
        node
        for node in tree.body  # module scope only — a guarded import lives inside an If, not here
        if isinstance(node, ast.Import) and any(alias.name == "fcntl" for alias in node.names)
    ]
    assert not top_level_fcntl, (
        "index_lock imports fcntl at module scope — every entry point would raise "
        "ModuleNotFoundError on Windows. It must be guarded by the sys.platform switch."
    )


def test_lock_primitives_are_platform_selected() -> None:
    """The five-function API is backed by three platform primitives, on either platform."""
    for name in ("_lock_exclusive_nb", "_lock_shared_nb", "_unlock"):
        assert callable(getattr(index_lock, name)), name


def test_lock_and_probe_roundtrip(tmp_path: Path) -> None:
    """The public API composes on the running platform: acquire, probe, publish, read, release."""
    db = tmp_path / ".code-atlas" / "graph.db"
    with index_lock.try_index_write_lock(db) as got:
        assert got is True
        assert build_in_progress(db) is True
        index_lock.publish_build_progress(db, "phase=parse done=3")
        assert index_lock.read_build_progress(db) == "phase=parse done=3"
    assert build_in_progress(db) is False
    assert index_lock.read_build_progress(db) is None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows byte-range lock arm (AC2-AC4)")
class TestWindowsLockArm:
    """The ticket's AC2-AC4 on the Windows arm — recorded once on a Windows host (E2)."""

    def test_two_writers_serialise(self, tmp_path: Path) -> None:
        """AC2 — the second concurrent writer gets False, exactly as flock gives on POSIX."""
        db = tmp_path / ".code-atlas" / "graph.db"
        with index_lock.try_index_write_lock(db) as first:
            assert first is True
            with index_lock.try_index_write_lock(db) as second:
                assert second is False

    def test_progress_is_readable_while_the_exclusive_lock_is_held(self, tmp_path: Path) -> None:
        """AC3 — publish/read touch bytes [0,200); the lock is a byte past them, so both work."""
        db = tmp_path / ".code-atlas" / "graph.db"
        with index_lock.try_index_write_lock(db) as got:
            assert got is True
            index_lock.publish_build_progress(db, "phase=parse done=held")
            assert index_lock.read_build_progress(db) == "phase=parse done=held"

    def test_lock_offset_is_disjoint_from_the_progress_region(self) -> None:
        """AC3's guard: the test fails if the lock ever covers byte 0, breaking publish/read."""
        assert index_lock._LOCK_OFFSET >= index_lock._PROGRESS_WIDTH


def _hold_script() -> str:
    return (
        "import sys, time\n"
        "from pathlib import Path\n"
        "from code_atlas.index_lock import try_index_write_lock, publish_build_progress\n"
        "db = Path(sys.argv[1])\n"
        "with try_index_write_lock(db) as got:\n"
        "    if not got:\n"
        "        sys.exit(3)\n"
        "    publish_build_progress(db, 'phase=parse done=held')\n"
        "    sys.stdout.write('ACQUIRED\\n'); sys.stdout.flush()\n"
        "    time.sleep(120)\n"
    )


def test_a_killed_holder_releases_the_lock(tmp_path: Path) -> None:
    """AC4 — kill the holder without cleanup; build_in_progress reads False. Both platforms.

    The OS releases the lock on process death (SIGKILL / TerminateProcess), so no carrier of a
    `building: true` claim outlives the process that made it (C1 / 072). The child must be seen to
    acquire before the kill, or a False afterwards would be vacuous (R6.5).
    """
    db = tmp_path / ".code-atlas" / "graph.db"
    child = subprocess.Popen(
        [sys.executable, "-c", _hold_script(), str(db)],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout is not None
        ready = child.stdout.readline()
        if ready.strip() != "ACQUIRED":
            code = child.poll()
            raise AssertionError(
                f"the child never acquired the lock (exit={code}) — any False below would be "
                "vacuous (R6.5)"
            )
        assert build_in_progress(db) is True, "the holder is alive but the lock reads free"
        child.kill()  # SIGKILL on POSIX, TerminateProcess on Windows — no cleanup runs
        child.wait(timeout=30)
        deadline = time.monotonic() + 10
        while build_in_progress(db) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert build_in_progress(db) is False, "a killed build still holds the lock"
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=30)
