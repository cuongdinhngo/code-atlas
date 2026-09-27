"""Task 227: a local type table gives the Python adapter the `semantic_types` capability.

A member call whose receiver the table types resolves to ``<Class>::method`` at RESOLVED, not a
bare HEURISTIC name. Flow-forgetful: an unknown reassignment re-opens the name (AC3). Drives the
real indexer + resolver, and checks the handshake advertises the capability.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from tests.python_adapter_cli import ENTRY, FIXTURES, needs_python

RESOLVE = FIXTURES / "resolve"
MOD = "src.typed_receiver"


@needs_python
def test_adapter_announces_semantic_types() -> None:
    proc = subprocess.run(
        [sys.executable, str(ENTRY), "--server"],
        input="",
        capture_output=True,
        text=True,
        timeout=30,
    )
    meta = json.loads(proc.stdout.splitlines()[0])
    assert meta["capabilities"].get("semantic_types") is True


@needs_python
def test_local_type_table_promotes_annotated_receiver(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(RESOLVE / "typed_receiver.py", src / "typed_receiver.py")
    (tmp_path / ".code-atlas.toml").write_text(
        f"[adapter_cmd]\npython = [{sys.executable!r}, {str(ENTRY)!r}, '--server']\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)

    db_path = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(
        tmp_path, {"CA_TRUST_PROJECT_FILE": "1", "CA_WORKERS": "1", "CA_DB_PATH": str(db_path)}
    )
    with GraphStore(db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
        calls = store.edges_by_source(f"{MOD}.build_annotated", kinds=("CALLS",), limit=10)
        assert len(calls) == 1
        assert calls[0]["target_raw"] == f"{MOD}.Service::run"
        assert calls[0]["target_qname"] == f"{MOD}.Service::run"
        assert calls[0]["confidence_tier"] == "RESOLVED"


@needs_python
def test_local_type_table_promotes_constructed_receiver(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(RESOLVE / "typed_receiver.py", src / "typed_receiver.py")
    (tmp_path / ".code-atlas.toml").write_text(
        f"[adapter_cmd]\npython = [{sys.executable!r}, {str(ENTRY)!r}, '--server']\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)

    db_path = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(
        tmp_path, {"CA_TRUST_PROJECT_FILE": "1", "CA_WORKERS": "1", "CA_DB_PATH": str(db_path)}
    )
    with GraphStore(db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
        calls = store.edges_by_source(f"{MOD}.build_constructed", kinds=("CALLS",), limit=10)
        member = [e for e in calls if str(e["target_raw"]).endswith("::run")]
        assert len(member) == 1
        assert member[0]["target_raw"] == f"{MOD}.Service::run"
        assert member[0]["confidence_tier"] == "RESOLVED"


@needs_python
def test_reassignment_from_unknown_reopens_receiver(tmp_path: Path) -> None:
    """AC3 — a stale RESOLVED is worse than an honest HEURISTIC (R5.2)."""
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(RESOLVE / "typed_receiver.py", src / "typed_receiver.py")
    (tmp_path / ".code-atlas.toml").write_text(
        f"[adapter_cmd]\npython = [{sys.executable!r}, {str(ENTRY)!r}, '--server']\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)

    db_path = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(
        tmp_path, {"CA_TRUST_PROJECT_FILE": "1", "CA_WORKERS": "1", "CA_DB_PATH": str(db_path)}
    )
    with GraphStore(db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
        calls = store.edges_by_source(f"{MOD}.build_forgotten", kinds=("CALLS",), limit=20)
        member_calls = [
            e for e in calls
            if e["target_raw"] == "run" or str(e["target_raw"]).endswith("::run")
        ]
        assert any(
            e["confidence_tier"] == "HEURISTIC" and e["target_raw"] == "run"
            for e in member_calls
        )
        assert not any(
            e["confidence_tier"] == "RESOLVED" and str(e["target_raw"]).endswith("Service::run")
            for e in member_calls
        )
