"""Task 462 — `code-atlas --help` prints usage instead of starting the MCP server.

It used to start the stdio server and wait, so an agent asking whether `verify_refs` runs in CI read
nothing and concluded it was MCP-only. The usage names `query`, its CI flags and what no argument
does.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from code_atlas import query
from code_atlas.main import usage

ROOT = Path(__file__).resolve().parent.parent


HELP = [["--help"], ["-h"], ["help"], ["--expect-version", "0.0.0", "--help"]]


@pytest.mark.parametrize("argv", HELP)
def test_help_prints_usage_and_exits_at_once(argv: list[str], tmp_path: Path) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CA_")}
    env["PYTHONPATH"] = str(ROOT)
    done = subprocess.run(
        [sys.executable, "-m", "code_atlas.main", *argv],
        cwd=tmp_path, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
        # Importing fastmcp alone takes ~2 s on a cold runner; the usage text, not the clock,
        # proves the server never started.
        timeout=60,
    )
    assert done.returncode == 0, done.stderr
    for needle in ("query", "--verify-refs", "--fail-on", "--refs-diff", "MCP server"):
        assert needle in done.stdout, needle
    assert not (tmp_path / ".code-atlas").exists()  # no config read, no index touched


def test_every_flag_the_usage_names_is_a_real_query_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        query.main(["--help"])
    real = set(re.findall(r"--[a-z][a-z-]+", capsys.readouterr().out))
    named = set(re.findall(r"--[a-z][a-z-]+", usage())) - {"--help", "--expect-version"}
    assert named <= real, named - real
