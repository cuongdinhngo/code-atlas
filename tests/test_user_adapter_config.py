"""Task 452: a git hook refreshes with the adapters the user recorded, and a skip says why.

The adapter commands live in a user-level file (``code-atlas/config.toml`` under
``XDG_CONFIG_HOME``), never in the repo (R9.1), so a hook run without the shell's ``CA_*`` still
finds them; the environment still wins.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

import pytest

from code_atlas.config import ConfigError, config_identity, load_config, user_config_path
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
FAKE_ARGV = [sys.executable, str(FAKE), "ok"]
SKIP_LINE = re.compile(
    r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ code-atlas refresh skipped \(post-commit\): "
    r"coverage_loss — lost: ",
    re.MULTILINE,
)


def write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def user_file(config_home: Path, argv: list[str]) -> Path:
    path = config_home / "code-atlas" / "config.toml"
    words = ", ".join(f"'{word}'" for word in argv)
    write(path, f"[adapter_cmd]\nfake = [{words}]\n")
    return path


def built_index(root: Path) -> Path:
    write(root / "src" / "a.aa", "class Thing {}\n")
    config = load_config(root, {"CA_WORKERS": "1", "CA_FAKE_CMD": shlex.join(FAKE_ARGV)})
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    return config.db_path


def stripped_env(home: Path) -> dict[str, str]:
    """What `env -i` leaves a hook: a home and a PATH holding the console scripts (W1)."""
    return {"HOME": str(home), "PATH": f"{Path(sys.executable).parent}{os.pathsep}/usr/bin:/bin"}


def test_ac1_a_hook_in_a_stripped_environment_refreshes_from_the_user_file(tmp_path: Path) -> None:
    root, home = tmp_path / "repo", tmp_path / "home"
    db = built_index(root)
    user_file(home / ".config", FAKE_ARGV)
    with GraphStore(db) as store:
        before = store.file_hash("src/a.aa")
    write(root / "src" / "a.aa", "// changed\nclass Thing {}\n")

    hook = REPO / "contrib" / "git" / "post-commit"
    subprocess.run(["sh", str(hook)], cwd=root, env=stripped_env(home), check=True)

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        with GraphStore(db) as store:
            if store.file_hash("src/a.aa") != before:
                return
        time.sleep(0.5)
    pytest.fail("the hook never refreshed the index from the user file")


def test_ac2_a_skipped_refresh_names_the_time_the_trigger_and_the_adapter(tmp_path: Path) -> None:
    root, home = tmp_path / "repo", tmp_path / "home"
    built_index(root)
    completed = subprocess.run(
        [sys.executable, "-m", "code_atlas.hooks.refresh", "--trigger", "post-commit"],
        cwd=root,
        env=stripped_env(home),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert SKIP_LINE.search(completed.stderr), completed.stderr


def test_ac2_an_adapter_that_cannot_start_is_named_on_the_line(tmp_path: Path) -> None:
    root, home = tmp_path / "repo", tmp_path / "home"
    built_index(root)
    user_file(home / ".config", [str(tmp_path / "no-such-adapter")])
    completed = subprocess.run(
        [sys.executable, "-m", "code_atlas.hooks.refresh", "--trigger", "post-merge"],
        cwd=root,
        env=stripped_env(home),
        capture_output=True,
        text=True,
        check=False,
    )
    pattern = r"^\S+Z code-atlas refresh skipped \(post-merge\): (.*)$"
    line = re.search(pattern, completed.stderr, re.M)
    assert line, completed.stderr
    assert line.group(1).startswith("no_usable_adapter — ") and "fake" in line.group(1)


def test_ac2_a_named_language_is_spelled_out() -> None:
    from code_atlas.hooks.refresh import _why

    assert _why({"lost_languages": ["php", "sql"]}) == "lost: php, sql"
    assert _why({"reason": "no_usable_adapter", "detail": "adapter 'php' failed"}) == (
        "adapter 'php' failed"
    )


def test_ac3_the_environment_wins_over_the_user_file(tmp_path: Path) -> None:
    user_file(tmp_path / "xdg", ["from-file"])
    env = {"XDG_CONFIG_HOME": str(tmp_path / "xdg"), "CA_FAKE_CMD": "from-env --server"}
    assert load_config(tmp_path / "repo", env).adapter_cmd("fake") == ("from-env", "--server")
    del env["CA_FAKE_CMD"]
    assert load_config(tmp_path / "repo", env).adapter_cmd("fake") == ("from-file",)


def test_the_user_file_needs_no_trust_flag_but_the_repo_file_still_does(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    user_file(tmp_path / "xdg", ["from-file"])
    env = {"XDG_CONFIG_HOME": str(tmp_path / "xdg")}
    assert load_config(root, env).adapter_cmd("fake") == ("from-file",)
    write(root / ".code-atlas.toml", "[adapter_cmd]\nfake = ['from-repo']\n")
    with pytest.raises(ConfigError, match="not trusted"):
        load_config(root, env)


def test_a_user_file_key_other_than_adapter_cmd_is_a_loud_error(tmp_path: Path) -> None:
    write(tmp_path / "xdg" / "code-atlas" / "config.toml", "workers = 3\n")
    with pytest.raises(ConfigError, match="adapter_cmd"):
        load_config(tmp_path / "repo", {"XDG_CONFIG_HOME": str(tmp_path / "xdg")})


def test_the_id_moves_with_the_user_file_and_not_without_one(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    env = {"XDG_CONFIG_HOME": str(tmp_path / "xdg")}
    without = config_identity(root, env)
    assert without == config_identity(root, {}), "no user file must keep the old id (R4.2)"
    user_file(tmp_path / "xdg", ["from-file"])
    assert config_identity(root, env, user_file=user_config_path(env)) != without


def test_the_path_comes_only_from_the_mapping_it_is_given(tmp_path: Path) -> None:
    assert user_config_path({}) is None
    home = {"HOME": str(tmp_path)}
    assert user_config_path(home) == tmp_path / ".config" / "code-atlas" / "config.toml"
    xdg = {**home, "XDG_CONFIG_HOME": str(tmp_path / "x")}
    assert user_config_path(xdg) == tmp_path / "x" / "code-atlas" / "config.toml"
