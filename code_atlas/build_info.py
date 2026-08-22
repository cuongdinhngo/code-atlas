"""Server identity — package version plus a build id derived from the installed artifact (125).

The id prefers the git commit when a checkout is available; otherwise it is a content hash of the
``code_atlas`` package tree so a shipped wheel or runtime container still names its build (R4.2 —
no timestamps, identical artifact → identical id). A modified checkout is not the commit it sits
on, so its id carries ``+dirty``: a retro must never quote a commit that did not answer.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
from functools import lru_cache
from pathlib import Path

from code_atlas import gitutil

BUILD_ID_CHARS = 7
DIRTY_SUFFIX = "+dirty"
UNKNOWN_VERSION = "unknown"
_PACKAGE_ROOT = Path(__file__).resolve().parent


def _package_version() -> str:
    """The declared version, or ``unknown`` — naming the build must never raise (cf. gitutil)."""
    try:
        return importlib.metadata.version("code-atlas")
    except importlib.metadata.PackageNotFoundError:
        return UNKNOWN_VERSION


def _git_root() -> Path | None:
    for parent in (_PACKAGE_ROOT, *_PACKAGE_ROOT.parents):
        if (parent / ".git").is_dir():
            return parent
    return None


def _git_build_id() -> str | None:
    root = _git_root()
    if root is None:
        return None
    commit = gitutil.head_commit(root)
    if not commit:
        return None
    build = commit[:BUILD_ID_CHARS]
    # `working_tree_dirty` is None when git cannot answer — an unknown tree is not a dirty one.
    return f"{build}{DIRTY_SUFFIX}" if gitutil.working_tree_dirty(root) else build


def _content_build_id() -> str:
    digest = hashlib.sha256()
    for path in sorted(_PACKAGE_ROOT.rglob("*.py")):
        rel = path.relative_to(_PACKAGE_ROOT).as_posix().encode()
        digest.update(rel)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:BUILD_ID_CHARS]


@lru_cache(maxsize=1)
def server_identity() -> dict[str, str]:
    """``version`` from package metadata; ``build`` from git or package content."""
    build = _git_build_id() or _content_build_id()
    return {"version": _package_version(), "build": build}


__all__ = ["BUILD_ID_CHARS", "DIRTY_SUFFIX", "UNKNOWN_VERSION", "server_identity"]
