"""Shared one-shot ``--file`` invocation for the PHP adapter.

R3.4's conformance harness and the PHP fixture tests must agree on cwd, a repo-relative
path, and one line of stdout — keep that contract here so adapter #2 does not invent a fourth copy.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ADAPTER = ROOT / "adapters" / "php"
ENTRY = ADAPTER / "index.php"
AUTOLOAD = ADAPTER / "vendor" / "autoload.php"
FIXTURES = ROOT / "tests" / "fixtures" / "php"
PHP = shutil.which("php")

needs_php = pytest.mark.skipif(
    PHP is None or not AUTOLOAD.is_file(),
    reason=f"needs the PHP CLI and `composer install` in {ADAPTER}",
)


def parse_file(repo_relative: str | Path) -> dict[str, object]:
    """Run ``adapters/php/index.php --file <repo-relative>`` from the repo root."""
    relative = str(repo_relative)
    completed = subprocess.run(
        [str(PHP), str(ENTRY), "--file", relative],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.count("\n") == 1, "--file emits one line and nothing else"
    return json.loads(completed.stdout)
