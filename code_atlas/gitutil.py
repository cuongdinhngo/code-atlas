"""Read-only git helpers for the build (§8.1). Diff-driven incremental support lands in task 016.

Every helper returns ``None`` rather than raising when git cannot answer — a directory that is not a
repo, or a repo with no commit yet, is a normal state the build degrades through (the walk fallback,
an absent ``last_commit``), not a configuration error.
"""

import subprocess
from pathlib import Path

# Long enough for a huge index on a cold cache, short enough that a wedged git is not forever.
GIT_TIMEOUT = 120.0


def ls_files(root: Path) -> tuple[str, ...] | None:
    """Every tracked path, repo-relative and POSIX-separated, or None outside a git repo.

    ``-z`` bypasses git's own quoting of unusual names, so a path holding a space or a non-ASCII
    byte arrives verbatim instead of wrapped in escaped quotes.
    """
    found = _run(root, "ls-files", "-z")
    if found is None:
        return None
    return tuple(sorted(path for path in found.split("\0") if path))


def head_commit(root: Path) -> str | None:
    """The commit the working tree is at, or None when there is no repo or no commit yet."""
    found = _run(root, "rev-parse", "HEAD")
    return None if found is None else (found.strip() or None)


def _run(root: Path, *arguments: str) -> str | None:
    """One read-only git command. Anything git cannot answer is None, never a partial answer."""
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return None if completed.returncode != 0 else completed.stdout
