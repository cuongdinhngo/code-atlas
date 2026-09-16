"""Server identity — package version plus a build id derived from the installed artifact (125).

The id names the code the **process loaded**, not the checkout it sits in (164). A content hash of
the ``code_atlas`` tree is frozen at import (``_LOADED_BUILD_ID`` ≈ what was loaded); when the disk
still matches it we report the git commit as identity (byte-identical to a plain checkout), and when
the disk has moved under a running server we report the loaded id plus ``stale_process`` and the
checkout HEAD as context (``server_repo_head`` — the worktree tip, never the running process). So a
retro can never quote a commit that did not answer (R4.2 — no timestamps, identical artifact →
identical id). The orthogonal ``+dirty`` axis still marks a worktree that differs from its commit.

When the process is stale, the payload also says whether the drift is answer-affecting (284):
``server_stale_impact`` compares the frozen tool-contract surface to disk, and ``server_build_kind``
marks a content-hash ``server_build`` as not-a-commit so a reader does not ``git log`` it.
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
# Action a reader (including an autonomous agent) can take — never interactive `/mcp` (267).
SERVER_STALE_ACTION = "restart_mcp_server_process"
SERVER_STALE_DIFFERS = ("code_atlas_package_bytes_on_disk",)
# Impact verdicts — only on the stale path; matching payloads stay byte-identical (061 / 284).
STALE_IMPACT_UNCHANGED = "tool_contract_unchanged"
STALE_IMPACT_CHANGED = "tool_contract_changed"
BUILD_KIND_CONTENT_HASH = "content_hash"
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


def _hash_paths(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        rel = path.relative_to(_PACKAGE_ROOT).as_posix().encode()
        digest.update(rel)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:BUILD_ID_CHARS]


def _content_build_id() -> str:
    return _hash_paths(sorted(_PACKAGE_ROOT.rglob("*.py")))


def _tool_surface_paths() -> list[Path]:
    """Contract vocabulary + build provenance + every tool module (284)."""
    paths: list[Path] = [_PACKAGE_ROOT / "contract.py", _PACKAGE_ROOT / "build_info.py"]
    tools = _PACKAGE_ROOT / "tools"
    if tools.is_dir():
        paths.extend(sorted(tools.rglob("*.py")))
    return [p for p in paths if p.is_file()]


def _tool_surface_id() -> str:
    """Content hash of the tool-contract surface — stored evidence for ``server_stale_impact``."""
    return _hash_paths(_tool_surface_paths())


def _capture_loaded_build_id() -> str:
    # Frozen at import ≈ the code the process loaded; a vanished file mid-walk must not
    # break naming the build, so degrade to UNKNOWN_VERSION rather than raise (cf. gitutil).
    try:
        return _content_build_id()
    except OSError:
        return UNKNOWN_VERSION


def _capture_loaded_tool_surface_id() -> str:
    try:
        return _tool_surface_id()
    except OSError:
        return UNKNOWN_VERSION


_LOADED_BUILD_ID = _capture_loaded_build_id()
_LOADED_TOOL_SURFACE_ID = _capture_loaded_tool_surface_id()

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
    # Impact only when diverged — same gate as the content re-hash (170 / 284 cost constraint).
    surface_now = _tool_surface_id()
    impact = (
        STALE_IMPACT_UNCHANGED
        if surface_now == _LOADED_TOOL_SURFACE_ID
        else STALE_IMPACT_CHANGED
    )
    return {
        "version": version,
        "build": _LOADED_BUILD_ID,
        "stale_process": True,
        # Checkout HEAD (worktree tip), not the running process — documented at emit site too (284).
        "repo_head": commit[:BUILD_ID_CHARS] if commit else _LOADED_BUILD_ID,
        "stale_impact": impact,
        "build_kind": BUILD_KIND_CONTENT_HASH,
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
    """The ``server_*`` payload fields — one spelling for every tool (125 / 162 / 164 / 284).

    Cheap after warm-up: the identity is memoised per on-disk fingerprint, so a payload pays one
    stat per loaded module and touches git only when the disk actually moved (170). A process that
    matches its disk carries ``server_stale_process: false`` — the verdict, so silence cannot be
    mistaken for a clean answer; a stale one flips it and adds ``server_repo_head`` (the
    **checkout's** HEAD, not the process), ``server_stale_impact``, and ``server_build_kind``.
    """
    ident = server_identity()
    prov: dict[str, object] = {
        "server_version": ident["version"],
        "server_build": ident["build"],
        "server_stale_process": bool(ident.get("stale_process")),
    }
    if ident.get("stale_process"):
        # Checkout HEAD — worktree tip under the process, never "which code answered".
        prov["server_repo_head"] = ident["repo_head"]
        # Name a restart action + what differs — a warning without either is noise (267).
        prov["server_stale_action"] = SERVER_STALE_ACTION
        prov["server_stale_differs"] = list(SERVER_STALE_DIFFERS)
        prov["server_stale_impact"] = ident["stale_impact"]
        # Content-hash build: not a git object — do not `git log` it (284).
        prov["server_build_kind"] = ident["build_kind"]
    return prov


def maybe_server_provenance(detail_level: str) -> dict[str, object]:
    """Identity on ``standard``/``verbose``; ``minimal`` leaves it to status (223)."""
    if detail_level == "minimal":
        return {}
    return server_provenance()


__all__ = [
    "BUILD_ID_CHARS",
    "BUILD_KIND_CONTENT_HASH",
    "DIRTY_SUFFIX",
    "SERVER_STALE_ACTION",
    "SERVER_STALE_DIFFERS",
    "STALE_IMPACT_CHANGED",
    "STALE_IMPACT_UNCHANGED",
    "UNKNOWN_VERSION",
    "maybe_server_provenance",
    "reset_identity_cache",
    "server_identity",
    "server_provenance",
]
