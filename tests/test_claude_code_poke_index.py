"""Task 036: Claude Code Edit/Write index-poke script."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol

REPO = Path(__file__).resolve().parent.parent
POKE = REPO / "scripts" / "claude_code_poke_index.py"
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"


def fake_env() -> dict[str, str]:
    return {
        "CA_WORKERS": "1",
        "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
    }


def write(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def run_poke(
    root: Path,
    payload: dict[str, object] | None = None,
    *,
    path_arg: str | None = None,
) -> int:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root), **fake_env()}
    cmd = [sys.executable, str(POKE)]
    if path_arg is not None:
        cmd.append(path_arg)
        stdin = None
    else:
        stdin = json.dumps(payload or {}).encode("utf-8")
    completed = subprocess.run(
        cmd, input=stdin, env=env, cwd=root, capture_output=True, check=False
    )
    return completed.returncode


def test_poke_is_noop_without_index(tmp_path: Path) -> None:
    payload = {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(tmp_path / "src" / "a.aa")},
    }
    assert run_poke(tmp_path, payload) == 0
    assert not (tmp_path / ".code-atlas" / "graph.db").is_file()


def test_poke_reparses_edited_file(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    db = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(tmp_path, {**fake_env(), "CA_DB_PATH": str(db)})
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        old_hash = store.file_hash("src/a.aa")
    write(tmp_path, "src/a.aa", "// poked\nclass Thing {}\n")
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "src" / "a.aa")},
    }
    assert run_poke(tmp_path, payload) == 0
    with GraphStore(config.db_path) as store:
        assert store.file_hash("src/a.aa") != old_hash
    result = read_symbol.create(config)("src/a.aa::Thing", detail_level="minimal")
    assert result["stale"] is False
    assert "poked" in str(result["source"])


def test_poke_accepts_cli_path_arg(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    db = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(tmp_path, {**fake_env(), "CA_DB_PATH": str(db)})
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        old_hash = store.file_hash("src/a.aa")
    write(tmp_path, "src/a.aa", "class Thing { /* v2 */ }\n")
    assert run_poke(tmp_path, path_arg=str(tmp_path / "src" / "a.aa")) == 0
    with GraphStore(config.db_path) as store:
        assert store.file_hash("src/a.aa") != old_hash
