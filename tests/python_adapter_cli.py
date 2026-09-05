"""Python binding for the shared adapter spawn (``tests/adapter_cli.py``).

Mirrors ``sql_adapter_cli.py``: zero runtime deps, so the availability gate is only that a Python
interpreter can launch ``adapters/python/index.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from tests.adapter_cli import AdapterCli

ROOT = Path(__file__).resolve().parent.parent
ADAPTER = ROOT / "adapters" / "python"
ENTRY = ADAPTER / "index.py"
FIXTURES = ROOT / "tests" / "fixtures" / "python"

needs_python = pytest.mark.skipif(
    not ENTRY.is_file(),
    reason=f"needs the Python adapter entry at {ENTRY}",
)

CLI = AdapterCli(
    name="python",
    adapter_dir=ADAPTER,
    entry_argv=(sys.executable, str(ENTRY)),
    fixtures_dir=FIXTURES,
    availability=needs_python,
    root=ROOT,
)


def parse_file(repo_relative: str | Path) -> dict[str, Any]:
    """Run ``adapters/python/index.py --file <repo-relative>`` from the repo root."""
    return CLI.parse_file(repo_relative)
