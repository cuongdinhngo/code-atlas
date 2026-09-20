"""Task 311: `semantic_types` means one thing — a file-at-a-time local type table backs
member-call receivers — and every adapter that has that mechanism declares it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from code_atlas import contract
from code_atlas.adapter import SubprocessAdapter
from tests.php_adapter_cli import needs_php
from tests.python_adapter_cli import ENTRY as PY_ENTRY
from tests.python_adapter_cli import needs_python
from tests.ts_adapter_cli import ENTRY as TS_ENTRY
from tests.ts_adapter_cli import NODE, needs_node

REPO = Path(__file__).resolve().parent.parent
PHP = shutil.which("php")
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"


def test_contract_states_semantic_types_means_local_type_table() -> None:
    """AC1: the meaning lives next to KNOWN_CAPABILITIES, not only in a task file."""
    src = (REPO / "code_atlas" / "contract.py").read_text(encoding="utf-8")
    anchor = src.index("KNOWN_CAPABILITIES")
    preface = src[max(0, anchor - 400) : anchor]
    assert "local type table" in preface
    assert "member-call" in preface or "member call" in preface
    assert "semantic_types" in contract.KNOWN_CAPABILITIES


@needs_php
def test_php_declares_semantic_types_for_its_local_type_table() -> None:
    """AC2: PHP ships the 137 table and must declare the flag (311 option a)."""
    with SubprocessAdapter("php", [str(PHP), str(PHP_ENTRY), "--server"], REPO) as adapter:
        assert adapter.capabilities.get("semantic_types") is True


@needs_node
def test_typescript_still_declares_semantic_types() -> None:
    proc = subprocess.run(
        [str(NODE), str(TS_ENTRY), "--server"],
        input="",
        capture_output=True,
        text=True,
        timeout=30,
    )
    meta = json.loads(proc.stdout.splitlines()[0])
    assert meta["capabilities"].get("semantic_types") is True


@needs_python
def test_python_still_declares_semantic_types() -> None:
    proc = subprocess.run(
        [sys.executable, str(PY_ENTRY), "--server"],
        input="",
        capture_output=True,
        text=True,
        timeout=30,
    )
    meta = json.loads(proc.stdout.splitlines()[0])
    assert meta["capabilities"].get("semantic_types") is True


def test_sql_does_not_declare_semantic_types() -> None:
    """SQL has no local type table; declaring the flag would be the 231 defect inverted."""
    src = (REPO / "adapters" / "sql" / "index.js").read_text(encoding="utf-8")
    # The capabilities object must not list the flag (comment above may mention it).
    cap_block = src.split("capabilities:")[1].split("},", 1)[0]
    assert "semantic_types" not in cap_block
