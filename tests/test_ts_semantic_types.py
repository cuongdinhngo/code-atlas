"""Task 153: a local type table gives the TS adapter the `semantic_types` capability — a member
call whose receiver the table types resolves to `<Class>::method` at RESOLVED, not a bare HEURISTIC
name. Drives the real indexer + resolver, and checks the handshake advertises the capability. Node.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from tests.ts_adapter_cli import ENTRY, FIXTURES, NODE, needs_node

RESOLVE = FIXTURES / "resolve"


@needs_node
def test_adapter_announces_semantic_types() -> None:
    # AC2: the capability is advertised in the handshake now the table backs it. Empty stdin closes
    # the server after it emits the announce line.
    proc = subprocess.run(
        [str(NODE), str(ENTRY), "--server"],
        input="",
        capture_output=True,
        text=True,
        timeout=30,
    )
    meta = json.loads(proc.stdout.splitlines()[0])
    assert meta["capabilities"].get("semantic_types") is True


@needs_node
def test_local_type_table_promotes_member_call_to_resolved(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    for name in ("models.ts", "typed.ts"):
        shutil.copy(RESOLVE / name, src / name)
    (tmp_path / ".code-atlas.toml").write_text(
        f"[adapter_cmd]\ntypescript = ['{NODE}', '{ENTRY}', '--server']\n", encoding="utf-8"
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
        # `u.greet()` where `const u = new User()` -> User::greet, RESOLVED (not a bare name).
        calls = store.edges_by_source("src/typed.ts::build", kinds=("CALLS",), limit=10)
        assert len(calls) == 1
        assert calls[0]["target_raw"] == "src/models.ts::User::greet"
        assert calls[0]["target_qname"] == "src/models.ts::User::greet"
        assert calls[0]["confidence_tier"] == "RESOLVED"
