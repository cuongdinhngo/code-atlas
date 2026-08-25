"""TypeScript binding for the shared adapter spawn (``tests/adapter_cli.py``).

Mirrors ``php_adapter_cli.py``: it names the TS adapter's launch data and re-exports ``AdapterCli``,
so no test invents a second spawn (task 147 AC4 — this module never names the one-shot flag itself).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from tests.adapter_cli import AdapterCli

ROOT = Path(__file__).resolve().parent.parent
ADAPTER = ROOT / "adapters" / "typescript"
ENTRY = ADAPTER / "index.js"
NODE_MODULES = ADAPTER / "node_modules" / "typescript"
FIXTURES = ROOT / "tests" / "fixtures" / "typescript"
NODE = shutil.which("node")

needs_node = pytest.mark.skipif(
    NODE is None or not NODE_MODULES.is_dir(),
    reason=f"needs the Node CLI and `npm install` in {ADAPTER}",
)

CLI = AdapterCli(
    name="typescript",
    adapter_dir=ADAPTER,
    entry_argv=(str(NODE), str(ENTRY)),
    fixtures_dir=FIXTURES,
    availability=needs_node,
    root=ROOT,
)


def parse_file(repo_relative: str | Path) -> dict[str, Any]:
    """Run ``adapters/typescript/index.js --file <repo-relative>`` from the repo root."""
    return CLI.parse_file(repo_relative)
