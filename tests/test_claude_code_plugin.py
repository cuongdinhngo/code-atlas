"""Task 344 — the Claude Code plugin ships the snippet's hooks, gated, plus the server and skill.

A user-scope plugin fires in every project, so each hook must be silent where there is no index,
and the plugin's hooks may not drift from the snippet a hand install copies (AC2, AC3).
"""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import gen_skill  # noqa: E402

REFRESH = "code-atlas-refresh"


def _load(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _commands(hooks: dict[str, Any]) -> list[str]:
    return [h["command"] for entries in hooks.values() for e in entries for h in e["hooks"]]


def _ungated(plugin: dict[str, Any]) -> dict[str, Any]:
    """The plugin's hook table with the gate stripped and its plugin-only refresh entry removed."""
    table = copy.deepcopy(plugin["hooks"])
    for event, entries in table.items():
        for entry in entries:
            for hook in entry["hooks"]:
                hook["command"] = hook["command"].removeprefix(gen_skill.PLUGIN_GATE)
        table[event] = [e for e in entries if e["hooks"][0]["command"] != REFRESH]
    return {"hooks": table}


def test_the_plugin_hook_list_matches_the_snippet() -> None:
    """AC3: the plugin and the hand-install snippet carry the same hooks, event for event."""
    snippet = _load(gen_skill.CLAUDE_CODE_SNIPPET_PATH)
    assert _ungated(_load(gen_skill.PLUGIN_HOOKS_PATH)) == snippet


def test_a_drifted_hook_list_is_caught() -> None:
    """R6.5: the comparison above must go red when one side loses an entry."""
    plugin = _load(gen_skill.PLUGIN_HOOKS_PATH)
    plugin["hooks"]["PostToolUse"].pop()
    assert _ungated(plugin) != _load(gen_skill.CLAUDE_CODE_SNIPPET_PATH)


def test_the_plugin_adds_only_the_background_refresh() -> None:
    """Scope 2: the one plugin-only hook is a SessionStart refresh that never blocks the start."""
    plugin = _load(gen_skill.PLUGIN_HOOKS_PATH)["hooks"]
    extra = [
        h for e in plugin["SessionStart"] for h in e["hooks"] if h["command"].endswith(REFRESH)
    ]
    assert len(extra) == 1 and extra[0]["async"] is True
    assert sum(c.endswith(REFRESH) for c in _commands(plugin)) == 1


def _gated_commands() -> list[str]:
    return sorted(set(_commands(_load(gen_skill.PLUGIN_HOOKS_PATH)["hooks"])))


def test_every_plugin_hook_is_gated_and_names_a_declared_script() -> None:
    """R6: all four commands pass the index gate first; each calls a script the package ships."""
    scripts = set(tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["scripts"])
    called = {c.removeprefix(gen_skill.PLUGIN_GATE) for c in _gated_commands()}
    assert all(c.startswith(gen_skill.PLUGIN_GATE) for c in _gated_commands())
    assert called <= scripts and len(called) == 4, called


def _fake_scripts(tmp_path: Path) -> dict[str, str]:
    """Every console script, stubbed to announce itself — so a spawn is visible, never assumed."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for command in _gated_commands():
        name = command.removeprefix(gen_skill.PLUGIN_GATE)
        stub = bin_dir / name
        stub.write_text(f"#!/bin/sh\necho SPAWNED {name}\n", encoding="utf-8")
        stub.chmod(0o755)
    return {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}


@pytest.mark.parametrize("command", _gated_commands())
def test_each_hook_is_silent_in_a_repo_with_no_index(tmp_path: Path, command: str) -> None:
    """AC2: no output, exit 0, and no Python process spawned where `.code-atlas/` is absent."""
    project = tmp_path / "project"
    project.mkdir()
    env = {**_fake_scripts(tmp_path), "CLAUDE_PROJECT_DIR": str(project)}
    done = subprocess.run(["bash", "-c", command], env=env, capture_output=True, text=True)
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


@pytest.mark.parametrize("command", _gated_commands())
def test_each_hook_runs_its_script_in_an_indexed_repo(tmp_path: Path, command: str) -> None:
    """The gate's other side: with `.code-atlas/` present the script really runs."""
    project = tmp_path / "project"
    (project / ".code-atlas").mkdir(parents=True)
    env = {**_fake_scripts(tmp_path), "CLAUDE_PROJECT_DIR": str(project)}
    done = subprocess.run(["bash", "-c", command], env=env, capture_output=True, text=True)
    assert done.stdout.startswith("SPAWNED code-atlas-")


def test_the_manifest_and_marketplace_carry_the_package_version() -> None:
    """R6.7: the plugin's version is the package's, read — never a second copy to bump."""
    version = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"]
    assert _load(gen_skill.PLUGIN_MANIFEST_PATH)["version"] == version
    (entry,) = _load(gen_skill.MARKETPLACE_PATH)["plugins"]
    assert entry["version"] == version
    assert (REPO / entry["source"]).resolve() == gen_skill.PLUGIN_DIR


def test_the_server_is_launched_by_its_console_script_name() -> None:
    """W1: no interpreter path anywhere in the plugin — the console script is on PATH."""
    server = _load(gen_skill.PLUGIN_MCP_PATH)["mcpServers"]["code-atlas"]
    assert server == {"command": "code-atlas"}


@pytest.mark.parametrize(
    "path", [gen_skill.CLAUDE_CODE_SNIPPET_PATH, gen_skill.PLUGIN_HOOKS_PATH], ids=lambda p: p.name
)
def test_every_if_filter_is_a_single_rule(path: Path) -> None:
    """Claude Code 2.1.284 never matched a `|`-joined `if` (344): poke and signal never fired."""
    hooks = _load(path)["hooks"]
    every = [h for entries in hooks.values() for e in entries for h in e["hooks"]]
    filters = [h["if"] for h in every if "if" in h]
    assert filters and all(re.fullmatch(r"(Edit|Write|Read)\(\*\.\w+\)", f) for f in filters)
