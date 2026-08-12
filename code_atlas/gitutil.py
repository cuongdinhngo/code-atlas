"""Read-only git helpers for the build (§8.1 / §8.3).

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
    commit, _ = head_commit_and_ref(root)
    return commit


def head_ref(root: Path) -> str | None:
    """Branch/ref name at HEAD, ``HEAD`` when detached, or None when git cannot answer (077)."""
    _, ref = head_commit_and_ref(root)
    return ref


def head_commit_and_ref(root: Path) -> tuple[str | None, str | None]:
    """SHA and abbrev-ref from one ``rev-parse`` — one HEAD read, no mid-call drift (077).

    Detached checkouts report the literal ``HEAD`` as the ref (a value, not an omission — 061).
    """
    found = _run(root, "rev-parse", "HEAD", "--abbrev-ref", "HEAD")
    if found is None:
        return None, None
    lines = [line.strip() for line in found.splitlines() if line.strip()]
    if not lines:
        return None, None
    commit = lines[0] or None
    ref = lines[1] if len(lines) > 1 else None
    return commit, ref or None


def changed_paths(root: Path, since: str) -> tuple[str, ...] | None:
    """Paths that differ from ``since`` on disk, or None when git cannot answer (§8.3).

    Unions ``since..HEAD`` with the working tree vs ``HEAD`` (staged and unstaged), so an
    uncommitted edit is visible to ``full=false`` the same way a full build would see it. Renames
    contribute the new path; the old path drops out of ``collect`` and must be folded into
    affected qnames by the indexer before reconcile.
    """
    committed = _run(root, "diff", "--name-only", "-z", f"{since}..HEAD")
    if committed is None:
        return None
    paths = {path for path in committed.split("\0") if path}
    dirty = _run(root, "diff", "--name-only", "-z", "HEAD")
    if dirty is not None:
        paths.update(path for path in dirty.split("\0") if path)
    return tuple(sorted(paths))


def dirty_paths(root: Path) -> tuple[str, ...] | None:
    """Tracked paths that differ from HEAD (staged or not), or None when git cannot answer.

    Untracked paths (including ``.code-atlas/graph.db``) never appear: ``collect`` only indexes
    tracked files in a git repo, so they cannot stale the index. The caller decides which of
    these paths the *index* covers — a dirty README is not a stale graph (047).
    """
    found = _run(root, "diff", "--name-only", "-z", "HEAD")
    if found is None:
        return None
    return tuple(sorted(path for path in found.split("\0") if path))


def working_tree_dirty(root: Path) -> bool | None:
    """True when any tracked file differs from HEAD; None when git cannot answer."""
    found = dirty_paths(root)
    return None if found is None else bool(found)


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
