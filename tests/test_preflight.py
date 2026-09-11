"""Task 237: the startup preflight names each silent-failure trap and its fix; clean host is silent.

Each footgun (237 / R5.3) surfaces today as a mystery OSError or a silent full rebuild. The
preflight turns each into one loud line with the action to take. Detection only — changes nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from code_atlas import preflight
from code_atlas.preflight import check_environment


def test_a_clean_host_is_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    """The whole point of R5.3's loud/quiet split: nothing to warn about prints nothing."""
    monkeypatch.setattr(preflight, "_long_paths_disabled", lambda: [])
    monkeypatch.setattr(preflight, "_git_config", lambda root, key: "false")
    warnings = check_environment(Path("/home/dev/repo"), {"typescript": (sys.executable, "x.js")})
    assert warnings == []


def test_autocrlf_true_is_reported_with_its_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    """core.autocrlf=true → every file reparses; the warning names the setting and the remedy."""
    monkeypatch.setattr(preflight, "_git_config", lambda root, key: "true")
    warnings = preflight._autocrlf_true(Path("/repo"))
    assert len(warnings) == 1
    assert "core.autocrlf" in warnings[0]
    assert "core.autocrlf=false" in warnings[0] or "rebuild" in warnings[0]


def test_autocrlf_false_or_absent_is_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(preflight, "_git_config", lambda root, key: "false")
    assert preflight._autocrlf_true(Path("/repo")) == []
    monkeypatch.setattr(preflight, "_git_config", lambda root, key: None)
    assert preflight._autocrlf_true(Path("/repo")) == []


def test_a_repo_under_wsl_mount_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """A repo under /mnt/* on WSL crosses the 9p boundary — the documented ~100x trap (220)."""
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    warnings = preflight._repo_under_wsl_mount(Path("/mnt/d/<org>/the anchor repo"))
    assert len(warnings) == 1
    assert "/mnt/" in warnings[0]
    assert "Linux-native" in warnings[0]


def test_a_repo_off_the_mount_is_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    assert preflight._repo_under_wsl_mount(Path("/home/dev/repo")) == []
    assert preflight._repo_under_wsl_mount(Path("D:/PROJECTS/code-atlas")) == []


def test_a_plain_linux_mount_is_not_called_wsl(monkeypatch: pytest.MonkeyPatch) -> None:
    """/mnt on a plain-Linux host is an ordinary mount, so the 9p claim would be false.

    Made to fail: drop the `_running_under_wsl` guard and this host is told it crosses 9p.
    """
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.setattr(preflight, "_running_under_wsl", lambda: False)
    assert preflight._repo_under_wsl_mount(Path("/mnt/data/repo")) == []


def test_a_missing_adapter_runtime_is_reported() -> None:
    """R5.3 proper: a configured adapter whose command is absent would index nothing for it."""
    cmds = {"php": ("no_such_executable_zzz", "adapter.php")}
    warnings = preflight._missing_adapter_runtime(cmds)
    assert len(warnings) == 1
    assert "php" in warnings[0]
    assert "PATH" in warnings[0]


def test_a_present_adapter_runtime_is_silent() -> None:
    assert preflight._missing_adapter_runtime({"python": (sys.executable, "parse.py")}) == []


def test_long_paths_check_is_windows_only() -> None:
    """Off-Windows the check is inert (empty); on Windows any warning it emits names the key."""
    warnings = preflight._long_paths_disabled()
    assert sys.platform == "win32" or warnings == []
    assert all("LongPathsEnabled" in warning for warning in warnings)
