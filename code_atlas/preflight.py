"""Startup environment preflight — loud, specific warnings for silent-failure traps (237, R5.3).

Each check names a real footgun and the action to take. A clean host produces an empty list, so the
caller prints nothing. Detection only: preflight never changes the environment and never blocks a
build — a warning is advice, not a gate.

The three portability traps (237) each surface today as a mystery ``OSError`` or a silent full
rebuild, which is the failure shape R5.3 exists to forbid:

- ``LongPathsEnabled`` off on Windows — ``vendor/`` trees exceed ``MAX_PATH`` (260).
- ``core.autocrlf=true`` — a DB built under LF and read on a CRLF checkout sees every file changed.
- a repo under ``/mnt/*`` on WSL — crosses the 9p boundary on every read, ~100x slower.

Plus the R5.3 case proper: a configured adapter command whose executable is not on ``PATH`` — the
build would run and silently index nothing for that language.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path


def check_environment(
    root: Path, adapter_cmds: Mapping[str, Sequence[str]] | None = None
) -> list[str]:
    """Every warning that applies here, each naming its action. Empty on a clean host."""
    warnings: list[str] = []
    warnings.extend(_long_paths_disabled())
    warnings.extend(_autocrlf_true(root))
    warnings.extend(_repo_under_wsl_mount(root))
    warnings.extend(_missing_adapter_runtime(adapter_cmds or {}))
    return warnings


def _long_paths_disabled() -> list[str]:
    """Windows only: the OS opt-in for paths past MAX_PATH (260) that vendor trees exceed."""
    if sys.platform != "win32":
        return []
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem"
        ) as key:
            value, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
    except OSError:
        value = 0
    if value == 1:
        return []
    return [
        "LongPathsEnabled is off: paths past 260 chars (deep vendor/ or node_modules trees) will "
        "raise OSError. Enable it: set HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem"
        "\\LongPathsEnabled = 1 (DWORD), then reboot."
    ]


def _autocrlf_true(root: Path) -> list[str]:
    """A DB built under LF (Docker/WSL) and read on a CRLF checkout sees every file changed."""
    value = _git_config(root, "core.autocrlf")
    if value != "true":
        return []
    return [
        "core.autocrlf=true: the stored change-detection digest hashes raw bytes, so a graph.db "
        "built under LF and read on this CRLF checkout reparses every file. Set "
        "core.autocrlf=false for this repo, or rebuild the index on this host."
    ]


def _running_under_wsl() -> bool:
    """WSL only: a plain-Linux host has ordinary mounts under /mnt and no 9p boundary to cross."""
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        release = Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8")
    except OSError:
        return False
    return "microsoft" in release.lower() or "wsl" in release.lower()


def _repo_under_wsl_mount(root: Path) -> list[str]:
    """A repo under /mnt/* on WSL crosses the 9p boundary on every read — ~100x slower (220)."""
    if not str(root).replace("\\", "/").startswith("/mnt/"):
        return []
    if not _running_under_wsl():
        # /mnt on a plain-Linux host is an ordinary mount: warning here would be a false claim.
        return []
    return [
        f"repo is under {root}: on WSL, /mnt/* crosses the 9p boundary on every read and indexes "
        "~100x slower. Move the repo and its .code-atlas/ DB to the Linux-native filesystem (~/…)."
    ]


def _missing_adapter_runtime(adapter_cmds: Mapping[str, Sequence[str]]) -> list[str]:
    """A configured adapter whose executable is not on PATH would index nothing for its language."""
    warnings: list[str] = []
    for lang, command in sorted(adapter_cmds.items()):
        if not command:
            continue
        executable = command[0]
        if shutil.which(executable) is None:
            warnings.append(
                f"adapter {lang!r} command {executable!r} is not on PATH: the build will run and "
                f"index nothing for {lang}. Install it, or unset CA_{lang.upper()}_CMD."
            )
    return warnings


def _git_config(root: Path, key: str) -> str | None:
    """Read one git config value for this repo, or None when git cannot answer."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "config", "--get", key],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()
