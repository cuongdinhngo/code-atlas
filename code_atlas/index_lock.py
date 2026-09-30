"""Non-blocking exclusive lock beside ``graph.db`` (R4.3 / task 053).

Shared by ``code-atlas-refresh`` and ``build_or_update_index`` so a hook and the
MCP server never both write. The loser skips cleanly (hook exit 0 / tool
``mode: busy``).

The same file carries the running build's progress line (task 177). It is the only
carrier whose claim cannot outlive the claimant: the lock is released by the OS on
process death, so a reader that finds the lock free reports *no build* however
recently the line was written. A ``building: true`` flag in the DB or a status file
survives ``kill -9`` and becomes a permanent lie — 072's own bug class.

The lock primitive is platform-selected once at import (task 237). POSIX uses
``fcntl.flock`` (advisory, per open file description). Windows uses ``LockFileEx``
on a byte disjoint from the progress region, so the mandatory per-handle lock never
covers the bytes ``publish``/``read`` touch — see the ``win32`` branch below.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

LOCK_NAME = "write.lock"

# One line, rewritten in place: the file never grows, and a reader never scans.
_PROGRESS_WIDTH = 200


# --- platform lock primitives (task 237) -----------------------------------
#
# Three primitives behind the five public functions. Each acquires non-blocking
# and raises ``BlockingIOError`` when the lock is held — so the public functions'
# ``except BlockingIOError`` / ``except OSError`` bodies are unchanged on both
# platforms. ``BlockingIOError`` is an ``OSError``, so the shared probe's broad
# ``except OSError`` catches it too.

if sys.platform == "win32":
    import ctypes
    import msvcrt
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _LOCKFILE_FAIL_IMMEDIATELY = 0x1
    _LOCKFILE_EXCLUSIVE_LOCK = 0x2
    # Lock one byte past the 200-byte progress region. Locking past EOF is legal on
    # Windows, so nothing pads the file; bytes [0, 200) stay lockless for publish/read.
    _LOCK_OFFSET = 1 << 20

    class _Overlapped(ctypes.Structure):
        _fields_ = [
            ("Internal", ctypes.c_void_p),
            ("InternalHigh", ctypes.c_void_p),
            ("Offset", wintypes.DWORD),
            ("OffsetHigh", wintypes.DWORD),
            ("hEvent", wintypes.HANDLE),
        ]

    def _overlapped() -> _Overlapped:
        overlapped = _Overlapped()
        overlapped.Offset = _LOCK_OFFSET & 0xFFFFFFFF
        overlapped.OffsetHigh = (_LOCK_OFFSET >> 32) & 0xFFFFFFFF
        return overlapped

    def _win_lock(fileno: int, *, exclusive: bool) -> None:
        handle = msvcrt.get_osfhandle(fileno)
        flags = _LOCKFILE_FAIL_IMMEDIATELY | (_LOCKFILE_EXCLUSIVE_LOCK if exclusive else 0)
        if not _kernel32.LockFileEx(handle, flags, 0, 1, 0, ctypes.byref(_overlapped())):
            # Held by another handle: report it as flock's non-blocking failure does.
            raise BlockingIOError(ctypes.get_last_error(), "index write lock is held")

    def _lock_exclusive_nb(fileno: int) -> None:
        _win_lock(fileno, exclusive=True)

    def _lock_shared_nb(fileno: int) -> None:
        _win_lock(fileno, exclusive=False)

    def _unlock(fileno: int) -> None:
        handle = msvcrt.get_osfhandle(fileno)
        _kernel32.UnlockFileEx(handle, 0, 1, 0, ctypes.byref(_overlapped()))

else:
    import fcntl

    def _lock_exclusive_nb(fileno: int) -> None:
        fcntl.flock(fileno, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _lock_shared_nb(fileno: int) -> None:
        fcntl.flock(fileno, fcntl.LOCK_SH | fcntl.LOCK_NB)

    def _unlock(fileno: int) -> None:
        fcntl.flock(fileno, fcntl.LOCK_UN)


@contextmanager
def try_index_write_lock(db_path: Path) -> Iterator[bool]:
    """Yield ``True`` while holding the lock; ``False`` if another writer holds it."""
    lock_path = db_path.parent / LOCK_NAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        try:
            _lock_exclusive_nb(lock_file.fileno())
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            _unlock(lock_file.fileno())


def lock_path_for(db_path: Path) -> Path:
    """Where the write lock lives for this index — the one definition site (R6.7)."""
    return db_path.parent / LOCK_NAME


def build_in_progress(db_path: Path) -> bool:
    """Is a writer holding the lock right now? Read-only, non-blocking, creates nothing.

    A shared probe rather than an exclusive one: it cannot make a real writer wait, and it
    fails exactly when a writer holds the exclusive lock. A missing file is *no build*, never
    unknown (077).
    """
    path = lock_path_for(db_path)
    try:
        handle = path.open("r", encoding="utf-8")
    except OSError:
        return False
    try:
        _lock_shared_nb(handle.fileno())
    except OSError:
        return True
    else:
        _unlock(handle.fileno())
        return False
    finally:
        handle.close()


def publish_build_progress(db_path: Path, line: str) -> None:
    """Write the holder's progress line into the lock file. Best-effort: never raises.

    Called only by the process holding the lock, on a second descriptor. The lock covers a
    byte past the progress region (or, on POSIX, is per open file description), so this neither
    takes nor disturbs the lock it writes inside.
    """
    try:
        with lock_path_for(db_path).open("r+", encoding="utf-8") as handle:
            # Fixed width, rewritten from offset 0: no truncate, so a concurrent reader never
            # sees a half-length line, and the file never grows over a long build.
            handle.seek(0)
            handle.write(line[:_PROGRESS_WIDTH].ljust(_PROGRESS_WIDTH))
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        return


def read_build_progress(db_path: Path) -> str | None:
    """The live build's progress line, or ``None`` when no writer holds the lock.

    The liveness test comes first: a line left behind by a killed build is never reported, which
    is what makes the claim self-invalidating rather than durable.
    """
    if not build_in_progress(db_path):
        return None
    try:
        raw = lock_path_for(db_path).read_text(encoding="utf-8")
    except OSError:
        return None
    line = raw.strip()
    return line or None


def build_phase(db_path: Path) -> str | None:
    """The live build's phase name (``parse``, ``publish`` …), or ``None`` when none is readable."""
    line = read_build_progress(db_path)
    if line is None:
        return None
    for token in line.split():
        if token.startswith("phase="):
            return token[len("phase=") :] or None
    return None
