"""The index directory is trusted only if code-atlas wrote it (420).

A repository can commit ``.code-atlas/`` (or the directory of a repo-relative ``db_path``): a
database whose schema it chose, a lock file linked out of the repo. So the index is refused when
git tracks any of it, or when it, its database or a database sibling is a link or leads outside
the repo. ``load_config`` asks this for every entry point; ``get_index_status`` asks again, since a
server outlives a ``git pull``. An index outside the repo is the operator's ``CA_DB_PATH``. Where
git cannot answer (no repo, no git, an ownership refusal) the index is not known to be tracked.
"""

from __future__ import annotations

import os
import shlex
from pathlib import Path

from code_atlas import gitutil
from code_atlas.config import ConfigError
from code_atlas.containment import resolves_inside

# git's answer per (root, paths), kept while ``.git/index`` is unchanged.
_TRACKED: dict[tuple[Path, tuple[str, ...]], tuple[tuple[int, int], tuple[str, ...] | None]] = {}
# The database's own files: SQLite's WAL siblings and the full rebuild's shadow (356).
_SIBLINGS = ("-wal", "-shm", ".shadow", ".shadow-wal", ".shadow-shm")


class IndexTrustError(ConfigError):
    """The index directory or database was not written by code-atlas; the message is the fix."""


def _database_files(db_path: Path) -> tuple[Path, ...]:
    return (db_path, *(db_path.with_name(db_path.name + suffix) for suffix in _SIBLINGS))


def refusal(root: Path, db_path: Path) -> str | None:
    """Why the index at ``db_path`` cannot be trusted, as one line naming the fix; else ``None``."""
    if not db_path.is_relative_to(root):
        return None
    index = db_path.parent
    owned = (*((index,) if index != root else ()), *_database_files(db_path))
    shown = (index if index != root else db_path).relative_to(root).as_posix()
    linked = any(path.is_symlink() for path in owned)
    if linked or not resolves_inside(root, index):
        return (
            f"the index path {shown} is a symlink or resolves outside the repo — remove the link, "
            "or set CA_DB_PATH to a directory you control"
        )
    present = [path.relative_to(root).as_posix() for path in owned if os.path.lexists(path)]
    found = _tracked(root, tuple(present)) if present else None
    if not found:
        return None
    target = shlex.quote(shown)
    return (
        f"the index {shown} is tracked by git ({len(found)} path(s)), so the repo wrote it, not "
        f"code-atlas — untrack it (git rm -r --cached {target}) and add it to .gitignore"
    )


def _tracked(root: Path, paths: tuple[str, ...]) -> tuple[str, ...] | None:
    try:
        stat = (root / ".git" / "index").stat()
    except OSError:  # a linked worktree or no repo: ask every time
        return gitutil.tracked(root, paths)
    stamp = (stat.st_mtime_ns, stat.st_size)
    kept = _TRACKED.get((root, paths))
    if kept is not None and kept[0] == stamp:
        return kept[1]
    found = gitutil.tracked(root, paths)
    _TRACKED[(root, paths)] = (stamp, found)
    return found


def check_index(root: Path, db_path: Path) -> None:
    """Raise :class:`IndexTrustError` with the fix when :func:`refusal` names one."""
    reason = refusal(root, db_path)
    if reason is not None:
        raise IndexTrustError(reason)
