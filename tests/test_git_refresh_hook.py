"""Task 053: git opt-in incremental refresh hook."""

from __future__ import annotations

import fcntl
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.hooks import refresh as refresh_mod
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore

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


def run_refresh(
    root: Path,
    *,
    extra_args: list[str] | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root), **fake_env()}
    if extra_env:
        env.update(extra_env)
    cmd = [sys.executable, "-m", "code_atlas.hooks.refresh", *(extra_args or [])]
    return subprocess.run(cmd, env=env, cwd=root, capture_output=True, check=False)


def test_refresh_is_noop_without_index(tmp_path: Path) -> None:
    completed = run_refresh(tmp_path)
    assert completed.returncode == 0
    assert not (tmp_path / ".code-atlas" / "graph.db").is_file()


def test_refresh_runs_incremental_with_index(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    db = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(tmp_path, {**fake_env(), "CA_DB_PATH": str(db)})
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        before = store.file_hash("src/a.aa")
    write(tmp_path, "src/a.aa", "// refreshed\nclass Thing {}\n")
    completed = run_refresh(tmp_path, extra_args=["--verbose"])
    assert completed.returncode == 0
    assert b"refreshed" in completed.stderr
    with GraphStore(config.db_path) as store:
        assert store.file_hash("src/a.aa") != before


def test_second_refresh_skips_while_lock_held(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    db = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(tmp_path, {**fake_env(), "CA_DB_PATH": str(db)})
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        before = dict(store.counts())
    lock_path = db.parent / "refresh.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            completed = run_refresh(tmp_path, extra_args=["--verbose"])
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    assert completed.returncode == 0
    assert b"another refresh is running" in completed.stderr
    with GraphStore(config.db_path) as store:
        assert dict(store.counts()) == before


def test_refresh_install_error_still_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from code_atlas.config import ConfigError

    def bad_load(*_a: object, **_k: object) -> object:
        raise ConfigError("no adapters")

    import code_atlas.config as config_mod

    monkeypatch.setattr(config_mod, "load_config", bad_load)
    assert refresh_mod.refresh(tmp_path) == 0
    err = capsys.readouterr().err
    assert "code-atlas refresh skipped:" in err


def test_is_branch_checkout_only_when_flag_is_one() -> None:
    assert refresh_mod.is_branch_checkout("1") is True
    assert refresh_mod.is_branch_checkout("0") is False
    assert refresh_mod.is_branch_checkout(None) is False


def test_post_checkout_snippet_guards_third_arg() -> None:
    text = (REPO / "contrib" / "git" / "post-checkout").read_text(encoding="utf-8")
    assert '[ "$3" = "1" ]' in text
    assert "exit 0" in text


def test_contrib_readme_says_manual_install() -> None:
    text = (REPO / "contrib" / "git" / "README.md").read_text(encoding="utf-8")
    assert "not installed automatically" in text.lower()
    assert "code-atlas-refresh" in text
