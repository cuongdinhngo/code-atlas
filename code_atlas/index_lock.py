"""Non-blocking exclusive lock beside ``graph.db`` (R4.3 / task 053).

Shared by ``code-atlas-refresh`` and ``build_or_update_index`` so a hook and the
MCP server never both write. The loser skips cleanly (hook exit 0 / tool
``mode: busy``).

The same file carries the running build's progress line (task 177). It is the only
carrier whose claim cannot outlive the claimant: ``flock`` is released by the OS on
process death, so a reader that finds the lock free reports *no build* however
recently the line was written. A ``building: true`` flag in the DB or a status file
survives ``kill -9`` and becomes a permanent lie — 072's own bug class.
"""

from __future__ import annotations

import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

LOCK_NAME = "write.lock"

# One line, rewritten in place: the file never grows, and a reader never scans.
_PROGRESS_WIDTH = 200


@contextmanager
def try_index_write_lock(db_path: Path) -> Iterator[bool]:
    """Yield ``True`` while holding the lock; ``False`` if another writer holds it."""
    lock_path = db_path.parent / LOCK_NAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def lock_path_for(db_path: Path) -> Path:
    """Where the write lock lives for this index — the one definition site (R6.7)."""
    return db_path.parent / LOCK_NAME


def build_in_progress(db_path: Path) -> bool:
    """Is a writer holding the lock right now? Read-only, non-blocking, creates nothing.

    ``LOCK_SH`` rather than ``LOCK_EX``: a shared probe cannot make a real writer wait, and it
    fails exactly when a writer holds the exclusive lock. A missing file is *no build*, never
    unknown (077).
    """
    path = lock_path_for(db_path)
    try:
        handle = path.open("r", encoding="utf-8")
    except OSError:
        return False
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
    except OSError:
        return True
    else:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return False
    finally:
        handle.close()


def publish_build_progress(db_path: Path, line: str) -> None:
    """Write the holder's progress line into the lock file. Best-effort: never raises.

    Called only by the process holding the lock, on a second descriptor — ``flock`` is per open
    file description, so this neither takes nor disturbs the lock it writes inside.
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
