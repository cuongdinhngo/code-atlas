"""SQL binding for the shared adapter spawn (``tests/adapter_cli.py``).

Mirrors ``ts_adapter_cli.py``: it names the SQL adapter's launch data and re-exports ``AdapterCli``,
so no test invents a second spawn (task 147 AC4 — this module never names the one-shot flag itself).
Unlike the TS adapter there is no ``node_modules`` gate: the scanner has zero runtime dependencies.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from tests.adapter_cli import AdapterCli

ROOT = Path(__file__).resolve().parent.parent
ADAPTER = ROOT / "adapters" / "sql"
ENTRY = ADAPTER / "index.js"
FIXTURES = ROOT / "tests" / "fixtures" / "sql"
NODE = shutil.which("node")

needs_node = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {ENTRY}")

CLI = AdapterCli(
    name="sql",
    adapter_dir=ADAPTER,
    entry_argv=(str(NODE), str(ENTRY)),
    fixtures_dir=FIXTURES,
    availability=needs_node,
    root=ROOT,
)


def parse_file(repo_relative: str | Path) -> dict[str, Any]:
    """Run ``adapters/sql/index.js --file <repo-relative>`` from the repo root."""
    return CLI.parse_file(repo_relative)
