"""Worktree DB routing — refuse main's index under a linked worktree cwd (268 / 071)."""

from __future__ import annotations

from pathlib import Path

from code_atlas import gitutil
from code_atlas.config import Config
from code_atlas.tools.nav_result import REASON_INDEX_ROOT_MISMATCH


def is_linked_worktree(root: Path) -> bool:
    """True when ``root`` is a git linked worktree (``.git`` is a file, not a directory)."""
    if not (root / ".git").is_file():
        return False
    return bool(gitutil.is_inside_work_tree(root))


def db_resolves_under_root(db_path: Path, root: Path) -> bool:
    """Whether ``db_path`` lives inside ``root`` after resolve (symlink-aware)."""
    try:
        db_path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def worktree_db_refusal(config: Config) -> dict[str, object] | None:
    """Refuse when a linked worktree's ``CA_DB_PATH`` points outside the worktree.

    Default relative ``.code-atlas/graph.db`` under the worktree is fine. An absolute path into
    another checkout (typically main) must never answer ``reason: ok`` (268).
    """
    if not is_linked_worktree(config.root):
        return None
    if db_resolves_under_root(config.db_path, config.root):
        return None
    return {
        "reason": REASON_INDEX_ROOT_MISMATCH,
        "indexed": False,
        "results": [],
        "total_count": 0,
        "truncated": False,
        "index_root": config.index_root,
        "db_path": str(config.db_path.resolve()),
        "message": (
            "index_root≠cwd worktree: CA_DB_PATH resolves outside this worktree — "
            "build under the worktree or point CA_DB_PATH inside it"
        ),
    }


__all__ = [
    "db_resolves_under_root",
    "is_linked_worktree",
    "worktree_db_refusal",
]
