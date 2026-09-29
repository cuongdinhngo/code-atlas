"""The one-shot ``--file`` adapter spawn, shared by every adapter (R3.4, AC4 of task 147).

This module owns the **single** ``subprocess.run`` that drives an adapter in one-shot ``--file``
mode. Per-language bindings (``tests/php_adapter_cli.py``) instantiate ``AdapterCli`` and re-export
its members; they never spawn a second copy — the "fourth copy" the split was written to prevent.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


def run_adapter_file(
    entry_argv: Sequence[str],
    repo_relative: str | Path,
    *,
    cwd: Path,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    """Run ``<entry_argv> --file <repo-relative>`` from ``cwd``. The only ``--file`` spawn."""
    return subprocess.run(
        [*entry_argv, "--file", str(repo_relative)],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )


@dataclass(frozen=True)
class AdapterCli:
    """One adapter's launch contract: cwd, entry argv, fixtures dir, availability marker."""

    name: str  # adapter directory name — the registry key, never a language literal
    adapter_dir: Path
    entry_argv: tuple[str, ...]
    fixtures_dir: Path
    availability: pytest.MarkDecorator
    root: Path

    def handshake(self) -> dict[str, Any]:
        """The `--server` meta line an adapter opens with, stdin closed at once (345)."""
        completed = subprocess.run(
            [*self.entry_argv, "--server"],
            cwd=self.root,
            input="",
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        assert completed.returncode == 0, completed.stderr
        return dict(json.loads(completed.stdout.splitlines()[0]))

    def parse_file(self, repo_relative: str | Path) -> dict[str, Any]:
        """Positive path: assert clean rc + one line of stdout, return the parsed result."""
        completed = run_adapter_file(self.entry_argv, repo_relative, cwd=self.root)
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout.count("\n") == 1, "one-shot mode emits one line and nothing else"
        return json.loads(completed.stdout)
