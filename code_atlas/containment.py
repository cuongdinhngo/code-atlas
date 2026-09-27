"""Every path code-atlas reads from, or writes into, the indexed repo resolves inside it (342).

The indexed repo is untrusted content and git stores symlinks, so a committed link can aim a read
(an indexed body, a quoted README) or a write (the onboarding tree) anywhere on the host. This is
the one containment rule; each read or write site asks it rather than carrying its own check.
"""

from pathlib import Path


def resolves_inside(root: Path, path: Path) -> bool:
    """Whether ``path``, symlinks followed, is ``root`` or under it. A loop or error is outside."""
    try:
        target = path.resolve()
        base = root.resolve()
    except (OSError, RuntimeError):  # RuntimeError: a symlink loop, before Python 3.13
        return False
    if target.is_symlink():  # 3.13 returns a loop unresolved instead of raising (R4.2)
        return False
    return target == base or target.is_relative_to(base)


def require_writable(root: Path, path: Path) -> Path:
    """``path`` if a write there stays in the repo; a symlinked target is refused even in-root.

    Writing through an in-root link would overwrite whatever file it names — source included.
    """
    if path.is_symlink() or not resolves_inside(root, path):
        raise ValueError(
            f"refusing to write {path.relative_to(root).as_posix()}: it is a symlink or "
            f"resolves outside the indexed repo"
        )
    return path
