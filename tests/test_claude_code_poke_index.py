"""Task 036: Claude Code Edit/Write index-poke script."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.hooks import poke as poke_mod
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol

REPO = Path(__file__).resolve().parent.parent
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
    extra_args: list[str] | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root), **fake_env()}
    if extra_env:
        env.update(extra_env)
    cmd = [sys.executable, "-m", "code_atlas.hooks.poke", *(extra_args or [])]
    if path_arg is not None:
        cmd.append(path_arg)
        stdin = None
    else:
        stdin = json.dumps(payload or {}).encode("utf-8")
    return subprocess.run(
        cmd, input=stdin, env=env, cwd=root, capture_output=True, check=False
    )


def test_poke_is_noop_without_index(tmp_path: Path) -> None:
    payload = {
        "tool_name": "Edit",
        "tool_input": {"file_path": str(tmp_path / "src" / "a.aa")},
    }
    completed = run_poke(tmp_path, payload)
    assert completed.returncode == 0
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
    completed = run_poke(tmp_path, payload, extra_args=["--verbose"])
    assert completed.returncode == 0
    assert b"poked src/a.aa" in completed.stderr
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
    completed = run_poke(tmp_path, path_arg=str(tmp_path / "src" / "a.aa"))
    assert completed.returncode == 0
    with GraphStore(config.db_path) as store:
        assert store.file_hash("src/a.aa") != old_hash


def test_repo_relative_rejects_parent_escape(tmp_path: Path) -> None:
    assert poke_mod._repo_relative(tmp_path, "../outside.php") is None
    assert poke_mod._repo_relative(tmp_path, "src/a.aa") == "src/a.aa"


def test_poke_exits_zero_on_bad_config_env(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    db = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(tmp_path, {**fake_env(), "CA_DB_PATH": str(db)})
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    completed = run_poke(
        tmp_path,
        path_arg=str(tmp_path / "src" / "a.aa"),
        extra_env={"CA_HOST_ROOT": "/tmp/host"},
    )
    assert completed.returncode == 0
    assert b"code-atlas poke skipped: ConfigError" in completed.stderr


def test_poke_skips_unchanged_file(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    db = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(tmp_path, {**fake_env(), "CA_DB_PATH": str(db)})
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        old_hash = store.file_hash("src/a.aa")
    path_log = tmp_path / "paths.log"
    completed = run_poke(
        tmp_path,
        path_arg=str(tmp_path / "src" / "a.aa"),
        extra_args=["--verbose"],
        extra_env={"CA_FAKE_PATHLOG": str(path_log)},
    )
    assert completed.returncode == 0
    assert b"skipped: current" in completed.stderr
    assert not path_log.is_file() or path_log.read_text(encoding="utf-8") == ""
    with GraphStore(config.db_path) as store:
        assert store.file_hash("src/a.aa") == old_hash


def test_poke_unowned_suffix_is_quiet_noop(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    write(tmp_path, "README.md", "# hi\n")
    db = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(tmp_path, {**fake_env(), "CA_DB_PATH": str(db)})
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    path_log = tmp_path / "paths.log"
    completed = run_poke(
        tmp_path,
        path_arg=str(tmp_path / "README.md"),
        extra_args=["--verbose"],
        extra_env={"CA_FAKE_PATHLOG": str(path_log)},
    )
    assert completed.returncode == 0
    assert b"skipped: no adapter owns" in completed.stderr
    # Announce may still boot once inside reparse_file; PATHLOG records parse() only.
    assert not path_log.is_file() or "README.md" not in path_log.read_text(encoding="utf-8")


def test_poke_indexes_brand_new_file(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    db = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(tmp_path, {**fake_env(), "CA_DB_PATH": str(db)})
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        assert store.file_hash("src/b.aa") is None
    write(tmp_path, "src/b.aa", "class Other {}\n")
    completed = run_poke(
        tmp_path,
        path_arg=str(tmp_path / "src" / "b.aa"),
        extra_args=["--verbose"],
    )
    assert completed.returncode == 0
    assert b"poked src/b.aa" in completed.stderr
    with GraphStore(config.db_path) as store:
        assert store.file_hash("src/b.aa") is not None


def test_poke_failure_prints_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("install broken")

    monkeypatch.setattr("code_atlas.config.load_config", boom)
    assert poke_mod.poke(tmp_path, "src/a.aa") == 0
    err = capsys.readouterr().err
    assert "code-atlas poke skipped: RuntimeError: install broken" in err
