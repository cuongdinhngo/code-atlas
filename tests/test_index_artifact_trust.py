"""Task 420 — the index directory is trusted only if code-atlas wrote it."""

from __future__ import annotations

import ast
import contextlib
import json
import os
import shlex
import sqlite3
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from code_atlas.config import Config, ConfigError, load_config
from code_atlas.indexer import full_build
from code_atlas.store import (
    LAST_COMMIT_KEY,
    SYMBOL_SHAPES_BY_LANGUAGE_KEY,
    GraphStore,
    bump_fit_count,
    read_meta_readonly,
)
from code_atlas.tools import build_or_update_index, get_index_status

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
VICTIM_BYTES = b"must survive\n"
FIX = "git rm -r --cached"
SHAPES = {"fake": {"extensions": [".aa"], "shapes": [{"kind": "call", "pattern": r"\w+\("}]}}
GREP = {"tool_name": "Grep", "tool_input": {"pattern": "Thing("}, "session_id": "s1"}

posix_only = pytest.mark.skipif(os.name == "nt", reason="symlinks and modes are POSIX here")


def _env() -> dict[str, str]:
    return {"CA_WORKERS": "1", "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"])}


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def _repo(tmp_path: Path) -> Config:
    """A committed source tree with a current index, and a victim file outside the repo."""
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.aa").write_text("class Thing {}\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    config = load_config(root, _env())
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        store.set_meta(SYMBOL_SHAPES_BY_LANGUAGE_KEY, json.dumps(SHAPES, sort_keys=True))
        store.set_meta(LAST_COMMIT_KEY, _git(root, "rev-parse", "HEAD"))
    (tmp_path / "victim.txt").write_bytes(VICTIM_BYTES)
    return config


def _hook(
    module: str, root: Path, payload: object = None, *, adapters: bool = True
) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("CA_")}
    env.update({"CLAUDE_PROJECT_DIR": str(root), **(_env() if adapters else {})})
    return subprocess.run(
        [sys.executable, "-m", module],
        input=json.dumps(payload or {}),
        env=env,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _edit(config: Config) -> None:
    (config.root / "src" / "a.aa").write_text("class Other {}\n", encoding="utf-8")


def _build(config: Config) -> None:
    _edit(config)
    with contextlib.suppress(Exception):
        build_or_update_index.create(config)(full=False)


def _refresh(config: Config, *, adapters: bool = True) -> None:
    _edit(config)
    _hook("code_atlas.hooks.refresh", config.root, adapters=adapters)


@posix_only
@pytest.mark.parametrize(
    ("name", "step"),
    [
        ("write.lock", "build"),
        ("write.lock", "refresh_hook"),
        ("nudge.log", "nudge_hook"),
        ("refresh.refused.tmp", "refused_refresh_hook"),
    ],
)
def test_a_linked_index_file_leaves_the_victim_untouched(
    tmp_path: Path, name: str, step: str
) -> None:
    """AC6: a link planted in an untracked index directory is never written through."""
    config = _repo(tmp_path)
    victim = tmp_path / "victim.txt"
    planted = config.db_path.parent / name
    planted.unlink(missing_ok=True)
    planted.symlink_to(victim)
    steps: dict[str, Callable[[], object]] = {
        "build": lambda: _build(config),
        "refresh_hook": lambda: _refresh(config),
        "nudge_hook": lambda: _hook("code_atlas.hooks.nudge", config.root, GREP),
        "refused_refresh_hook": lambda: _refresh(config, adapters=False),
    }
    steps[step]()
    assert victim.read_bytes() == VICTIM_BYTES


def _committed(tmp_path: Path) -> Config:
    config = _repo(tmp_path)
    _git(config.root, "add", "-f", ".code-atlas")
    _git(config.root, "commit", "-qm", "commit the index")
    return config


@pytest.mark.parametrize(
    "step",
    ["build", "server", "state_hook", "refresh_hook", "nudge_hook", "signal_hook", "poke_hook"],
)
def test_a_committed_index_is_refused_with_the_fix(tmp_path: Path, step: str) -> None:
    """AC1: every entry point refuses a tracked index, names the fix, and injects no context."""
    config = _committed(tmp_path)
    root = config.root
    read = {"tool_name": "Read", "tool_input": {"file_path": str(root / "src" / "a.aa")}}
    payloads: dict[str, tuple[str, object]] = {
        "build": ("code_atlas.cli", None),
        "server": ("code_atlas.main", None),
        "state_hook": ("code_atlas.hooks.state", {"hook_event_name": "SessionStart"}),
        "refresh_hook": ("code_atlas.hooks.refresh", None),
        "nudge_hook": ("code_atlas.hooks.nudge", GREP),
        "signal_hook": ("code_atlas.hooks.signal", read),
        "poke_hook": ("code_atlas.hooks.poke", read),
    }
    module, payload = payloads[step]
    done = _hook(module, root, payload)
    assert FIX in done.stderr, done.stderr
    assert done.stdout == ""


def test_a_running_server_refuses_an_index_committed_under_it(tmp_path: Path) -> None:
    """AC1: ``get_index_status`` re-checks, since a server outlives the commit."""
    config = _repo(tmp_path)
    status = get_index_status.create(config, ())
    _git(config.root, "add", "-f", ".code-atlas")
    _git(config.root, "commit", "-qm", "commit the index")
    with pytest.raises(ConfigError, match=FIX):
        status()


@posix_only
@pytest.mark.parametrize(
    "link", ["cache", "cache/graph.db", "cache/graph.db-wal", "shadow", "shadow-wal"]
)
def test_a_linked_db_path_is_refused(tmp_path: Path, link: str) -> None:
    """AC3: the database, its directory, -wal and the shadow must not lead out of the repo."""
    root, outside = tmp_path / "repo", tmp_path / "elsewhere"
    root.mkdir()
    outside.mkdir()
    (root / ".code-atlas.toml").write_text('db_path = "cache/graph.db"\n', encoding="utf-8")
    if link == "cache":
        (root / "cache").symlink_to(outside, target_is_directory=True)
    else:
        (root / "cache").mkdir()
        name = f"cache/graph.db.{link}" if link.startswith("shadow") else link
        (root / name).symlink_to(outside / "x.db")
    with pytest.raises(ConfigError, match="symlink|outside"):
        load_config(root, _env())
    assert not any(outside.iterdir())


@posix_only
def test_a_linked_database_is_never_opened_by_the_store(tmp_path: Path) -> None:
    """AC3: a store opened past ``load_config`` still refuses a database that is a link."""
    victim = tmp_path / "victim.db"
    victim.write_bytes(VICTIM_BYTES)
    (tmp_path / "index").mkdir()
    (tmp_path / "index" / "graph.db").symlink_to(victim)
    with pytest.raises(OSError, match="linked index"):
        GraphStore(tmp_path / "index" / "graph.db")
    assert victim.read_bytes() == VICTIM_BYTES


@pytest.fixture
def sentinel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A file a schema object may write only through a function on code-atlas's own connections."""
    mark = tmp_path / "sentinel"
    mark.write_text("0", encoding="utf-8")
    real = sqlite3.connect

    def connect(*args: object, **kwargs: object) -> sqlite3.Connection:
        conn = real(*args, **kwargs)  # type: ignore[arg-type]
        conn.create_function("touch_sentinel", 0, lambda: mark.write_text("1") and 1)
        return conn

    monkeypatch.setattr(sqlite3, "connect", connect)
    return mark


def test_a_view_in_the_index_runs_no_function(tmp_path: Path, sentinel: Path) -> None:
    """AC4: a read-only meta read of a hostile view never runs what the view calls."""
    db = tmp_path / "graph.db"
    raw = sqlite3.connect(db)
    raw.execute("CREATE VIEW meta AS SELECT 'k' AS key, touch_sentinel() AS value")
    raw.close()
    read_meta_readonly(db, "k")
    assert sentinel.read_text() == "0"


@pytest.mark.parametrize("writer", ["store", "fit_counter"])
def test_a_trigger_in_the_index_runs_no_function(
    tmp_path: Path, sentinel: Path, writer: str
) -> None:
    """AC4: a trigger on ``meta`` never runs its function when code-atlas writes there."""
    config = _repo(tmp_path)
    raw = sqlite3.connect(config.db_path)
    raw.execute(
        "CREATE TRIGGER hostile AFTER INSERT ON meta BEGIN SELECT touch_sentinel(); END"
    )
    raw.close()
    with contextlib.suppress(sqlite3.Error):
        if writer == "store":
            with GraphStore(config.db_path) as store:
                store.set_meta("hostile_probe", "1")
        else:
            bump_fit_count(config.db_path, "probe", "ok", authoritative=True, truncated=False)
    assert sentinel.read_text() == "0"


@posix_only
def test_the_index_is_private(tmp_path: Path) -> None:
    """AC5: the index directory is created 0700 and the files code-atlas writes there 0600."""
    config = _repo(tmp_path)
    _refresh(config, adapters=False)
    index = config.db_path.parent
    assert index.stat().st_mode & 0o777 == 0o700
    written = [index / "graph.db", index / "write.lock", index / "refresh.refused"]
    assert {path.name: path.stat().st_mode & 0o777 for path in written} == {
        path.name: 0o600 for path in written
    }


# Writers outside the AC7 sweep, each with why (the onboarding cache stays out of 420).
EXEMPT = {
    "code_atlas/containment.py": "the one writer",
    "code_atlas/query.py": "the operator's own --out file",
    "code_atlas/tools/generate_onboarding.py": "require_writable refuses links; modes are BACKLOG",
    "code_atlas/adapter.py": "the stderr log path is caller-chosen; no core caller passes one",
}
_WRITE_MODES = set("wax+")
_WRITE_ATTRS = {"write_text", "write_bytes", "touch"}


def _mode(call: ast.Call, position: int) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            return str(keyword.value.value)
    if len(call.args) > position and isinstance(call.args[position], ast.Constant):
        return str(call.args[position].value)
    return None


def _write_sites(tree: ast.AST) -> list[int]:
    """Lines that write a file: a write-mode open, write_text/bytes, touch, os.open/replace."""
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "open":
            mode = _mode(node, 1)
            if mode is not None and _WRITE_MODES & set(mode):
                lines.append(node.lineno)
        elif isinstance(func, ast.Attribute):
            owner = func.value.id if isinstance(func.value, ast.Name) else None
            if func.attr in _WRITE_ATTRS:
                lines.append(node.lineno)
            elif owner == "os" and func.attr in {"open", "replace", "rename"}:
                lines.append(node.lineno)
            elif func.attr == "open" and owner != "os":
                mode = _mode(node, 0)
                if mode is not None and _WRITE_MODES & set(mode):
                    lines.append(node.lineno)
    return lines


def test_only_the_safe_writer_writes_files() -> None:
    """AC7: every file write in the core and the LLM package goes through containment."""
    trees = sorted([*(REPO / "code_atlas").rglob("*.py"), *(REPO / "onboarding_llm").rglob("*.py")])
    found = {
        rel: lines
        for path in trees
        if (rel := path.relative_to(REPO).as_posix()) not in EXEMPT
        and (lines := _write_sites(ast.parse(path.read_text(encoding="utf-8"))))
    }
    assert found == {}, json.dumps(found)
    # The sweep still sees writes: the exempt writer's own are found (R6.5).
    writer = REPO / "code_atlas" / "containment.py"
    assert _write_sites(ast.parse(writer.read_text(encoding="utf-8")))
