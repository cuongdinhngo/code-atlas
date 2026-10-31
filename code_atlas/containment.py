"""Every path code-atlas reads from, or writes into, the indexed repo resolves inside it (342).

The indexed repo is untrusted content and git stores symlinks, so a committed link can aim a read
(an indexed body, a quoted README) or a write (the onboarding tree) anywhere on the host. This is
the one containment rule; each read or write site asks it rather than carrying its own check.

Every file the index keeps is opened here (420): the file itself never through a link, its
directory a real one inside the given root, created private to the user. ``generate_onboarding``'s
cache is written the same way (430); its page tree is guarded by ``require_writable``.
Reads that cross the trust line go through :func:`open_inside` (430).
"""

import contextlib
import errno
import os
import secrets
from pathlib import Path
from typing import BinaryIO

PRIVATE_DIR = 0o700
PRIVATE_FILE = 0o600
# Windows has neither flag; there a link is refused by a check before the open instead.
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_PLATFORM_FLAGS = getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_BINARY", 0)


class UnsafeWrite(OSError):
    """A write that would follow a link or leave its root. An ``OSError``, so best-effort stays."""


class UnsafeRead(OSError):
    """A read that follows a link, leaves its root, or opens a file other than the one checked."""


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


def make_private_dir(path: Path) -> None:
    """Create ``path`` and its parents, the leaf ``0700``; an existing directory is left as is."""
    path.mkdir(mode=PRIVATE_DIR, parents=True, exist_ok=True)


def safe_open(path: Path, flags: int, *, root: Path | None = None) -> int:
    """A descriptor for ``path``, created ``0600``, that follows no link and stays inside ``root``.

    ``root`` defaults to the file's own directory, which must then not be a link itself.
    """
    parent = path.parent
    linked = parent.is_symlink() or parent.is_junction()
    if linked or not resolves_inside(parent if root is None else root, parent):
        raise UnsafeWrite(errno.ELOOP, "refusing to write through a link", str(path))
    if not _NOFOLLOW and path.is_symlink():
        raise UnsafeWrite(errno.ELOOP, "refusing to write through a link", str(path))
    return os.open(path, flags | _NOFOLLOW | _PLATFORM_FLAGS, PRIVATE_FILE)


def safe_write(path: Path, data: str | bytes, *, root: Path | None = None) -> None:
    """Replace ``path`` with ``data``: a fresh private file beside it, then one ``os.replace``.

    The replace swaps a planted link for the file rather than writing through it.
    """
    payload = data.encode("utf-8") if isinstance(data, str) else data
    staged = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    descriptor = safe_open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL, root=root)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
        os.replace(staged, path)
    except BaseException:
        with contextlib.suppress(OSError):
            staged.unlink()
        raise


def safe_append(path: Path, text: str, *, root: Path | None = None) -> None:
    """Append ``text`` to ``path``, created private; a linked file is refused, never followed."""
    descriptor = safe_open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, root=root)
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        handle.write(text)


def open_inside(root: Path, path: Path) -> BinaryIO:
    """``path`` opened for reading only if it resolves inside ``root`` and is what was checked.

    The resolved path is opened without following a final link, and the open descriptor must be the
    very file the resolved path names: a swap between the check and the open is refused (430).
    """
    if not resolves_inside(root, path):
        raise UnsafeRead(errno.ELOOP, "refusing to read outside the indexed repo", str(path))
    resolved = path.resolve()
    descriptor = os.open(resolved, os.O_RDONLY | _NOFOLLOW | _PLATFORM_FLAGS)
    try:
        opened, named = os.fstat(descriptor), os.stat(resolved)
        if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
            raise UnsafeRead(errno.ELOOP, "the file changed while it was opened", str(path))
    except BaseException:
        os.close(descriptor)
        raise
    return os.fdopen(descriptor, "rb")


def read_bytes(root: Path, path: Path) -> bytes:
    """The bytes of ``path`` read through :func:`open_inside`; ``UnsafeRead`` when it is refused."""
    with open_inside(root, path) as handle:
        return handle.read()
