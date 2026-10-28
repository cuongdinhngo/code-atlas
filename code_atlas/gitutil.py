"""Read-only git helpers for the build (§8.1 / §8.3).

Every helper returns ``None`` rather than raising when git cannot answer — a directory that is not a
repo, or a repo with no commit yet, is a normal state the build degrades through (the walk fallback,
an absent ``last_commit``), not a configuration error.

Every git process code-atlas starts is spawned by ``_run``, hardened against the indexed repo's own
configuration, and a revision read from data must be a full object id before it reaches git (419).
"""

import functools
import os
import re
import subprocess
import sys
from pathlib import Path

# Metadata ops (rev-parse/ls-files/diff --name-only) are sub-second even on huge repos; 30s covers a
# cold FS. The tree-kill + bounded drain below is the real backstop, so the ceiling stays tight.
GIT_TIMEOUT = 30.0

# (commit, ref) from one HEAD read; either is None when git cannot name it (077).
GitHead = tuple[str | None, str | None]

# Headless native Windows wedges git three ways; each guard below is a no-op off Windows (task 271).
# stdin=DEVNULL stops the inherited-console-handle block; CREATE_NO_WINDOW stops a new console;
# tree-kill on timeout frees the capture pipe a grandchild still holds while the reader blocks.
_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# The indexed repo is untrusted (SECURITY.md): none of its config may run a program for us (419).
HARDENED_CONFIG = (
    "core.fsmonitor=false",
    "core.hooksPath=/dev/null",
    "core.sshCommand=",
    "diff.external=",
)
HARDENED_ENV = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
# A full SHA-1 or SHA-256 object id; ``HEAD`` is the one symbolic revision code-atlas writes itself.
_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_HEAD = "HEAD"
# ``--end-of-options`` arrived in git 2.24; an older git fails every revision call, loudly.
END_OF_OPTIONS_SINCE = (2, 24)


def ls_files(root: Path) -> tuple[str, ...] | None:
    """Every tracked path, repo-relative and POSIX-separated, or None outside a git repo.

    ``-z`` bypasses git's own quoting of unusual names, so a path holding a space or a non-ASCII
    byte arrives verbatim instead of wrapped in escaped quotes.
    """
    found = _run(root, "ls-files", "-z")
    if found is None:
        return None
    return tuple(sorted(path for path in found.split("\0") if path))


def tracked(root: Path, paths: tuple[str, ...]) -> tuple[str, ...] | None:
    """Which tracked paths lie at or under ``paths`` (repo-relative, read literally), or None."""
    pathspecs = tuple(f":(literal){path}" for path in paths)
    found = _run(root, "ls-files", "-z", "--", *pathspecs)
    if found is None:
        return None
    return tuple(sorted(path for path in found.split("\0") if path))


def ls_untracked(root: Path) -> tuple[str, ...] | None:
    """Untracked paths git does not ignore, repo-relative and POSIX-separated, or None.

    ``--exclude-standard`` drops gitignored names; ``-z`` matches ``ls_files``. Sorted here
    so the untracked census is a property of this core (R4.2), not of git's listing order.
    """
    found = _run(root, "ls-files", "-o", "-z", "--exclude-standard")
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


def head_commit_and_ref(root: Path) -> GitHead:
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


def changed_paths(root: Path, since: str, *, renames: bool = True) -> tuple[str, ...] | None:
    """Paths that differ from ``since`` on disk, or None when git cannot answer (§8.3).

    One ``git diff <since>`` — ``since`` against the working tree, staged and unstaged — so an
    uncommitted edit is visible to ``full=false`` the same way a full build would see it, and HEAD
    is never read: a commit landing mid-build cannot slip between two reads (360). Renames
    contribute the new path; the old path drops out of ``collect`` and must be folded into
    affected qnames by the indexer before reconcile. ``renames=False`` lists both ends (389).
    """
    flags = () if renames else ("--no-renames",)
    found = _run(root, "diff", "--name-only", "-z", *flags, revision=since)
    if found is None:
        return None
    return tuple(sorted({path for path in found.split("\0") if path}))


def dirty_paths(root: Path) -> tuple[str, ...] | None:
    """Tracked paths that differ from HEAD (staged or not), or None when git cannot answer.

    Untracked paths (including ``.code-atlas/graph.db``) never appear: ``collect`` only indexes
    tracked files in a git repo, so they cannot stale the index. The caller decides which of
    these paths the *index* covers — a dirty README is not a stale graph (047).
    """
    found = _run(root, "diff", "--name-only", "-z", revision=_HEAD)
    if found is None:
        return None
    return tuple(sorted(path for path in found.split("\0") if path))


def working_tree_dirty(root: Path) -> bool | None:
    """True when any tracked file differs from HEAD; None when git cannot answer."""
    found = dirty_paths(root)
    return None if found is None else bool(found)


def is_inside_work_tree(root: Path) -> bool | None:
    """True inside a git work tree, False when git says no, None when git cannot answer."""
    found = _run(root, "rev-parse", "--is-inside-work-tree")
    if found is None:
        return None
    text = found.strip()
    if text == "true":
        return True
    if text == "false":
        return False
    return None


def checkout_identity(root: Path) -> tuple[Path, Path] | None:
    """``(top level, shared git dir)`` of the checkout holding ``root``, or None outside a repo.

    Two linked worktrees of one repository share the git dir and differ in top level (366).
    """
    found = _run(root, "rev-parse", "--show-toplevel", "--git-common-dir")
    if found is None:
        return None
    lines = [line.strip() for line in found.splitlines() if line.strip()]
    if len(lines) != 2:
        return None
    # A relative common dir is relative to the directory git ran in, not to the top level.
    return Path(lines[0]).resolve(), (root / lines[1]).resolve()


def config_value(root: Path, key: str) -> str | None:
    """One config value as git resolves it for ``root``, or None when unset or git cannot answer.

    The system file stays readable: it is the host's, and Git for Windows sets ``core.autocrlf``
    there. Reading a value runs nothing, so only this call skips ``GIT_CONFIG_NOSYSTEM``.
    """
    found = _run(root, "config", "--get", key, system_config=True)
    return None if found is None else found.strip()


@functools.cache
def git_version() -> tuple[int, int] | None:
    """``(major, minor)`` of the git on PATH, or None when it cannot be read. Asked once."""
    found = _run(Path.cwd(), "--version")
    match = re.search(r"(\d+)\.(\d+)", found or "")
    return None if match is None else (int(match.group(1)), int(match.group(2)))


def _report(message: str) -> None:
    print(f"code-atlas git: {message}", file=sys.stderr)


def _kill_tree(proc: "subprocess.Popen[str]") -> None:
    """Kill ``proc``: the whole tree via ``taskkill /T`` on Windows (where a grandchild can hold the
    capture pipe open), just the process elsewhere. Must never itself raise or hang, or a stuck kill
    reintroduces the wedge ``_run`` bounds."""
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                creationflags=_CREATE_NO_WINDOW,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            proc.kill()
    else:
        proc.kill()


def _run(
    root: Path, *arguments: str, revision: str | None = None, system_config: bool = False
) -> str | None:
    """One read-only, hardened git command. Anything git cannot answer is None, never partial.

    ``revision`` goes last, after ``--end-of-options`` and before ``--``, and only as a full
    object id (or ``HEAD``): a value read from the index can never be parsed as an option (419).
    """
    if revision is not None:
        if revision != _HEAD and not _OBJECT_ID.fullmatch(revision):
            _report(f"refused revision {revision!r}: not a full object id; git is not asked")
            return None
        arguments = (*arguments, "--end-of-options", revision, "--")
    if arguments[:1] == ("diff",):
        arguments = ("diff", "--no-ext-diff", "--no-textconv", *arguments[1:])
    skipped = ("GIT_CONFIG_NOSYSTEM",) if system_config else ()
    env = {**os.environ, **{k: v for k, v in HARDENED_ENV.items() if k not in skipped}}
    hardening = [part for setting in HARDENED_CONFIG for part in ("-c", setting)]
    try:
        proc = subprocess.Popen(
            ["git", *hardening, *arguments],
            cwd=root,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="surrogateescape",
            creationflags=_CREATE_NO_WINDOW,
        )
    except OSError:
        return None
    try:
        stdout, _ = proc.communicate(timeout=GIT_TIMEOUT)
    except subprocess.TimeoutExpired:
        # A wedged git (or a grandchild holding the pipe) never yielded EOF. Kill the tree, then
        # drain briefly so communicate() returns rather than blocking on the now-dead pipe.
        _kill_tree(proc)
        try:
            proc.communicate(timeout=5)
        except (subprocess.SubprocessError, OSError, ValueError):
            pass
        return None
    except (OSError, ValueError):
        _kill_tree(proc)
        return None
    if proc.returncode != 0:
        if revision is not None:
            _too_old()
        return None
    return stdout


def _too_old() -> None:
    """A revision call failed: say so when the cause is a git without ``--end-of-options``."""
    version = git_version()
    if version is not None and version < END_OF_OPTIONS_SINCE:
        found = ".".join(map(str, version))
        _report(f"git {found} is older than 2.24 and cannot take --end-of-options; upgrade git")
