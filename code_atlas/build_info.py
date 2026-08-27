"""Server identity — package version plus a build id derived from the installed artifact (125).

The id names the code the **process loaded**, not the checkout it sits in (164). A content hash of
the ``code_atlas`` tree is frozen at import (``_LOADED_BUILD_ID`` ≈ what was loaded); when the disk
still matches it we report the git commit as identity (byte-identical to a plain checkout), and when
the disk has moved under a running server we report the loaded id plus ``stale_process`` and the
repo HEAD as context. So a retro can never quote a commit that did not answer (R4.2 — no timestamps,
identical artifact → identical id). The orthogonal ``+dirty`` axis still marks a worktree that
differs from its commit.
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


def _capture_loaded_build_id() -> str:
    # Frozen at import ≈ the code the process loaded; a vanished file mid-walk must not
    # break naming the build, so degrade to UNKNOWN_VERSION rather than raise (cf. gitutil).
    try:
        return _content_build_id()
    except OSError:
        return UNKNOWN_VERSION


_LOADED_BUILD_ID = _capture_loaded_build_id()


@lru_cache(maxsize=1)
def server_identity() -> dict[str, object]:
    """``version`` from metadata; ``build`` names the loaded code, not the checkout (164).

    No checkout → the loaded content id (wheel / container). Checkout whose disk still matches the
    loaded code → the git commit (byte-identical to 162). Disk moved under the process → the loaded
    id, plus ``stale_process`` and ``repo_head`` so the divergence is legible in-band.
    """
    version = _package_version()
    root = _git_root()
    if root is None:
        return {"version": version, "build": _LOADED_BUILD_ID}
    if _content_build_id() == _LOADED_BUILD_ID:
        return {"version": version, "build": _git_build_id() or _LOADED_BUILD_ID}
    commit = gitutil.head_commit(root)
    return {
        "version": version,
        "build": _LOADED_BUILD_ID,
        "stale_process": True,
        "repo_head": commit[:BUILD_ID_CHARS] if commit else _LOADED_BUILD_ID,
    }


def server_provenance() -> dict[str, object]:
    """The ``server_*`` payload fields — one spelling for every tool (125 / 162 / 164).

    Cheap after warm-up: ``server_identity`` is lru-cached and touches git only once per
    process, so stamping this on the hot path spawns no git (contrast the signing revision). A
    process that matches its disk carries only the two base fields (061); a stale one adds
    ``server_stale_process`` and ``server_repo_head``.
    """
    ident = server_identity()
    prov: dict[str, object] = {
        "server_version": ident["version"],
        "server_build": ident["build"],
    }
    if ident.get("stale_process"):
        prov["server_stale_process"] = True
        prov["server_repo_head"] = ident["repo_head"]
    return prov


__all__ = [
    "BUILD_ID_CHARS",
    "DIRTY_SUFFIX",
    "UNKNOWN_VERSION",
    "server_identity",
    "server_provenance",
]
