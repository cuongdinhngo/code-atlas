"""Non-blocking exclusive lock beside ``graph.db`` (R4.3 / task 053).

Shared by ``code-atlas-refresh`` and ``build_or_update_index`` so a hook and the
MCP server never both write. The loser skips cleanly (hook exit 0 / tool
``mode: busy``).
"""

from __future__ import annotations

import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

LOCK_NAME = "write.lock"


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
