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
import os
import sys
from pathlib import Path

from code_atlas import gitutil

BUILD_ID_CHARS = 7
DIRTY_SUFFIX = "+dirty"
UNKNOWN_VERSION = "unknown"
_PACKAGE_ROOT = Path(__file__).resolve().parent
_PACKAGE_NAME = __name__.split(".")[0]


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

# `(mtime_ns, size)` per already-loaded module. The probe's state, never part of any id, so R4.2
# holds: an identical artifact yields an identical build id on a host whose mtimes differ.
_probe_state: dict[str, tuple[int, int]] = {}
_identity: dict[str, object] | None = None


def _loaded_modules_changed() -> bool:
    """Has a module this process ALREADY loaded changed on disk since the last look (task 170)?

    164's check sat behind an unconditional ``lru_cache``, so it ran once and a swap after the
    first payload was structurally unreportable. Re-hashing per payload is the wrong fix — 164
    measured that walk at 6.35 ms. This stats only ``sys.modules``: the cheap set, and the *right*
    one, since ``server_build`` names the code the process loaded.
    """
    changed = False
    for name, module in list(sys.modules.items()):
        if not name.startswith(_PACKAGE_NAME):
            continue
        source = getattr(module, "__file__", None)
        if not source:
            continue
        try:
            info = os.stat(source)
        except OSError:
            continue  # A vanished file must not break naming the build (cf. gitutil).
        stamp = (info.st_mtime_ns, info.st_size)
        previous = _probe_state.get(name)
        # A newly-imported module is not a divergence; only a module we have seen before moving is.
        if previous is not None and previous != stamp:
            changed = True
        _probe_state[name] = stamp
    return changed


def _compute_identity() -> dict[str, object]:
    """The identity for the disk as it is right now — the expensive half, run only when it moved."""
    version = _package_version()
    root = _git_root()
    diverged = _content_build_id() != _LOADED_BUILD_ID
    if not diverged:
        build = _LOADED_BUILD_ID if root is None else (_git_build_id() or _LOADED_BUILD_ID)
        # `stale_process: False` is a VERDICT, not a value: omitting it made "checked, and still
        # matching" byte-identical to "never checked" — round 11 §12.c could not tell them apart.
        return {"version": version, "build": build, "stale_process": False}
    commit = gitutil.head_commit(root) if root is not None else None
    return {
        "version": version,
        "build": _LOADED_BUILD_ID,
        "stale_process": True,
        "repo_head": commit[:BUILD_ID_CHARS] if commit else _LOADED_BUILD_ID,
    }


def server_identity() -> dict[str, object]:
    """``version`` from metadata; ``build`` names the loaded code, not the checkout (164).

    No checkout → the loaded content id (wheel / container). Checkout whose disk still matches the
    loaded code → the git commit (byte-identical to 162). Disk moved under the process → the loaded
    id, plus ``repo_head``. ``stale_process`` is present either way, so a reader can tell
    *checked-and-matching* from *not checked at all* (task 170).

    Re-evaluated whenever a loaded module moved on disk, so a swap after the first payload is
    reportable — the cache 164 shipped made that structurally impossible.
    """
    global _identity
    if _identity is None or _loaded_modules_changed():
        _identity = _compute_identity()
    return _identity


def reset_identity_cache() -> None:
    """Drop the memo and the probe state. For tests; in a live process the probe decides."""
    global _identity
    _identity = None
    _probe_state.clear()


def server_provenance() -> dict[str, object]:
    """The ``server_*`` payload fields — one spelling for every tool (125 / 162 / 164).

    Cheap after warm-up: the identity is memoised per on-disk fingerprint, so a payload pays one
    stat per loaded module and touches git only when the disk actually moved (170). A process that
    matches its disk carries ``server_stale_process: false`` — the verdict, so silence cannot be
    mistaken for a clean answer; a stale one flips it and adds ``server_repo_head``.
    """
    ident = server_identity()
    prov: dict[str, object] = {
        "server_version": ident["version"],
        "server_build": ident["build"],
        "server_stale_process": bool(ident.get("stale_process")),
    }
    if ident.get("stale_process"):
        prov["server_repo_head"] = ident["repo_head"]
    return prov


__all__ = [
    "BUILD_ID_CHARS",
    "DIRTY_SUFFIX",
    "UNKNOWN_VERSION",
    "reset_identity_cache",
    "server_identity",
    "server_provenance",
]
