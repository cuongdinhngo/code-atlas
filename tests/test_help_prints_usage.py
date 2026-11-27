"""Task 462 — `code-atlas --help` prints usage instead of starting the MCP server.

It used to start the stdio server and wait, so an agent asking whether `verify_refs` runs in CI read
nothing and concluded it was MCP-only. The usage names `query`, its CI flags and what no argument
does.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_usage_and_exits_at_once(flag: str, tmp_path: Path) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CA_")}
    env["PYTHONPATH"] = str(ROOT)
    done = subprocess.run(
        [sys.executable, "-m", "code_atlas.main", flag],
        cwd=tmp_path, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
        timeout=2,  # the server would wait on stdin past this
    )
    assert done.returncode == 0, done.stderr
    for needle in ("query", "--verify-refs", "--fail-on", "--refs-diff", "MCP server"):
        assert needle in done.stdout, needle
    assert not (tmp_path / ".code-atlas").exists()  # no config read, no index touched
