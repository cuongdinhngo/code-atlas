"""PHP binding for the shared adapter spawn (``tests/adapter_cli.py``).

R3.4's conformance harness and the PHP fixture tests must agree on cwd, a repo-relative path, and
one line of stdout. That contract lives once, in ``AdapterCli``; this module only names PHP's launch
data and re-exports it, so no test invents a second spawn.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from tests.adapter_cli import AdapterCli

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

CLI = AdapterCli(
    name="php",
    adapter_dir=ADAPTER,
    entry_argv=(str(PHP), str(ENTRY)),
    fixtures_dir=FIXTURES,
    availability=needs_php,
    root=ROOT,
)


def parse_file(repo_relative: str | Path) -> dict[str, Any]:
    """Run ``adapters/php/index.php --file <repo-relative>`` from the repo root."""
    return CLI.parse_file(repo_relative)
