"""Task 453: `code-atlas-setup` installs the freshness hooks, and an index without them says so."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

import pytest

from code_atlas import setup_hooks
from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
FAKE_CMD = shlex.join([sys.executable, str(FAKE), "ok"])


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return done.stdout


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A committed, indexed git checkout; HOME is empty, so no real plugin setting is read."""
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.aa").write_text("class Thing {}\n", encoding="utf-8")
    git(root.parent, "init", "-q", str(root))
    git(root, "-c", "user.email=t@example.com", "-c", "user.name=t", "add", "-A")
    git(root, "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "one")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("CA_FAKE_CMD", FAKE_CMD)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    config = load_config(root)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    return root


def snapshot(root: Path) -> dict[str, bytes]:
    hooks, _ = setup_hooks.gitutil.hooks_dir(root) or (root, "")
    paths = [hooks / h for h in setup_hooks.GIT_HOOKS]
    paths += [root / setup_hooks.SETTINGS_FILE, setup_hooks.record_path(root)]
    return {str(p): p.read_bytes() for p in paths if p.is_file()}


def test_ac1_setup_then_a_commit_refreshes_and_a_second_run_changes_no_byte(repo: Path) -> None:
    parts = setup_hooks.run(repo, os.environ)
    assert not [p for p in parts if p.state == "missing"], parts
    first = snapshot(repo)
    assert setup_hooks.run(repo, os.environ) and snapshot(repo) == first

    db = load_config(repo).db_path
    with GraphStore(db) as store:
        before = store.file_hash("src/a.aa")
    (repo / "src" / "a.aa").write_text("// two\nclass Thing {}\n", encoding="utf-8")
    git(repo, "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qam", "two")
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        with GraphStore(db) as store:
            if store.file_hash("src/a.aa") != before:
                return
        time.sleep(0.5)
    pytest.fail("the commit's hook never refreshed the index")


def test_ac2_an_existing_hook_keeps_its_lines_and_gains_the_block(repo: Path) -> None:
    hook = repo / ".git" / "hooks" / "post-merge"
    hook.write_text("#!/bin/sh\necho mine\n", encoding="utf-8")
    setup_hooks.run(repo, os.environ)
    text = hook.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh\n" + setup_hooks.BEGIN) and text.endswith("echo mine\n")
    setup_hooks.run(repo, os.environ)
    assert hook.read_text(encoding="utf-8") == text


def test_the_block_runs_before_a_hook_that_exits(repo: Path) -> None:
    """Challenger F2: a block appended after `exit 0` would never run, yet read as guarded."""
    hook = repo / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    setup_hooks.run(repo, os.environ)
    text = hook.read_text(encoding="utf-8")
    assert text.index(setup_hooks.BEGIN) < text.index("exit 0")


def test_an_empty_settings_object_receives_the_hooks(repo: Path) -> None:
    """Challenger F1: `{}` is a JSON object, not a file to refuse."""
    path = repo / setup_hooks.SETTINGS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n", encoding="utf-8")
    parts = {p.name: p for p in setup_hooks.run(repo, os.environ)}
    assert parts["Claude Code hooks"].state == "wrote"


def test_check_marks_what_is_not_installed_with_a_cross_and_the_fix(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Challenger F4: a part --check would write is ❌ with its fix, never ✅."""
    monkeypatch.chdir(repo)
    assert setup_hooks.main(["--check"]) == setup_hooks.MISSING
    lines = [ln for ln in capsys.readouterr().out.splitlines() if "git hook" in ln]
    assert len(lines) == 4
    assert all(ln.startswith("❌") and ln.endswith("run code-atlas-setup") for ln in lines)


def test_no_hooks_on_an_indexed_repo_is_recorded(repo: Path) -> None:
    """Challenger F3: the choice is recorded on any build, not only a first one."""
    from code_atlas import cli

    cli.first_setup(repo, declined=True)
    assert get_index_status.UNGUARDED not in get_index_status.create(load_config(repo), ())()


def test_ac3_a_local_hooks_path_receives_the_hooks(repo: Path) -> None:
    git(repo, "config", "core.hooksPath", ".husky")
    setup_hooks.run(repo, os.environ)
    assert setup_hooks.BEGIN in (repo / ".husky" / "post-commit").read_text(encoding="utf-8")
    assert not (repo / ".git" / "hooks" / "post-commit").is_file()


def test_ac4_a_removed_hook_fails_check_and_reads_unguarded(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    setup_hooks.run(repo, os.environ)
    status = get_index_status.create(load_config(repo), ())()
    assert get_index_status.UNGUARDED not in status
    (repo / ".git" / "hooks" / "post-commit").unlink()
    monkeypatch.chdir(repo)
    assert setup_hooks.main(["--check"]) == setup_hooks.MISSING
    status = get_index_status.create(load_config(repo), ())()
    gaps = {"gaps": ["post-commit"], "route": "code-atlas-setup"}
    assert status[get_index_status.UNGUARDED] == gaps
    assert str(status["summary"]).endswith("unguarded: run `code-atlas-setup`")


def test_no_setup_on_record_reads_unguarded_and_no_hooks_silences_it(repo: Path) -> None:
    status = get_index_status.create(load_config(repo), ())()
    assert status[get_index_status.UNGUARDED]["gaps"] == ["no setup"]
    setup_hooks.decline(repo)
    assert get_index_status.UNGUARDED not in get_index_status.create(load_config(repo), ())()


def test_a_hook_that_is_not_a_shell_script_is_left_alone(repo: Path) -> None:
    hook = repo / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/usr/bin/env python3\nprint('mine')\n", encoding="utf-8")
    parts = {p.name: p for p in setup_hooks.run(repo, os.environ)}
    assert parts["git hook post-commit"].state == "skipped"
    assert hook.read_text(encoding="utf-8") == "#!/usr/bin/env python3\nprint('mine')\n"


def test_claude_hooks_go_to_the_personal_file_unless_the_plugin_has_them(repo: Path) -> None:
    setup_hooks.run(repo, os.environ)
    settings = json.loads((repo / setup_hooks.SETTINGS_FILE).read_text(encoding="utf-8"))
    assert set(settings["hooks"]) == set(setup_hooks.HOOKS)
    plugin = repo / ".claude" / "settings.json"
    plugin.write_text(json.dumps({"enabledPlugins": {"code-atlas@code-atlas": True}}), "utf-8")
    (repo / setup_hooks.SETTINGS_FILE).unlink()
    parts = {p.name: p for p in setup_hooks.run(repo, os.environ)}
    assert parts["Claude Code hooks"].why == "the code-atlas plugin provides them"
    assert not (repo / setup_hooks.SETTINGS_FILE).is_file()


def test_a_repo_own_hook_entries_survive_setup_and_removal(repo: Path) -> None:
    own = {"type": "command", "command": "bash .claude/hooks/mine.sh"}
    path = repo / setup_hooks.SETTINGS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [own]}]}}), "utf-8")
    setup_hooks.run(repo, os.environ)
    setup_hooks.run(repo, os.environ, remove=True)
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "hooks": {"SessionStart": [{"hooks": [own]}]}
    }
    assert setup_hooks.BEGIN not in (repo / ".git" / "hooks" / "post-commit").read_text("utf-8")


def test_the_shell_adapter_commands_reach_the_user_file_once(repo: Path) -> None:
    parts = {p.name: p for p in setup_hooks.run(repo, os.environ)}
    assert parts["adapter commands"].state == "wrote"
    env = {k: v for k, v in os.environ.items() if k != "CA_FAKE_CMD"}
    assert load_config(repo, env).adapter_cmd("fake") == tuple(shlex.split(FAKE_CMD))
    assert {p.name: p for p in setup_hooks.run(repo, os.environ)}["adapter commands"].state == "ok"


def test_a_global_hooks_path_is_never_written(repo: Path, tmp_path: Path) -> None:
    home = Path(os.environ["HOME"])
    home.mkdir(parents=True, exist_ok=True)
    (home / ".gitconfig").write_text(f"[core]\n\thooksPath = {tmp_path / 'global'}\n", "utf-8")
    parts = {p.name: p for p in setup_hooks.run(repo, os.environ)}
    assert parts["git hooks"].state == "skipped"
    assert not (tmp_path / "global").exists()
