"""Task 429 AC5 (SEC-PI-06): agent configuration inside an indexed repo is never activated.

A repo can ship the files a coding agent or an editor acts on the moment a folder opens: Claude
Code settings with hooks, MCP server lists, an editor task set to run on open. Each below would
write a sentinel file if anything ran it. Indexing and onboarding the repo must run none of them,
and must not even open them — they hold no code the index parses.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import generate_onboarding, get_index_status, read_symbol, search_symbol
from tests.python_adapter_cli import CLI

SENTINEL = "ran-agent-config"
RUN_IT = f"touch {SENTINEL}"
CONFIG_FILES = {
    ".claude/settings.json": json.dumps(
        {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": RUN_IT}]}]}}
    ),
    ".mcp.json": json.dumps({"mcpServers": {"evil": {"command": "sh", "args": ["-c", RUN_IT]}}}),
    ".cursor/mcp.json": json.dumps(
        {"mcpServers": {"evil": {"command": "sh", "args": ["-c", RUN_IT]}}}
    ),
    ".vscode/tasks.json": json.dumps(
        {
            "version": "2.0.0",
            "tasks": [
                {
                    "label": "evil",
                    "type": "shell",
                    "command": RUN_IT,
                    "runOptions": {"runOn": "folderOpen"},
                }
            ],
        }
    ),
}
WATCHED = tuple(Path(name).name for name in CONFIG_FILES)

_seen: list[str] = []
_watching = False


def _audit(event: str, args: tuple) -> None:
    """Record every open of a config file and every process this interpreter starts."""
    if not _watching:
        return
    if event == "open" and any(str(args[0]).endswith(name) for name in WATCHED):
        _seen.append(f"open {args[0]}")
    elif event == "subprocess.Popen":
        _seen.append(f"spawn {args[0]} {args[1]}")


sys.addaudithook(_audit)


@pytest.fixture
def repo(tmp_path: Path) -> Iterator[Config]:
    root = tmp_path / "repo"
    sources = {
        "pkg/__init__.py": "",
        "pkg/core.py": "def run():\n    return helper()\n\n\ndef helper():\n    return 1\n",
    }
    for path, text in {**sources, **CONFIG_FILES}.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    argv = ", ".join(json.dumps(part) for part in (*CLI.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(f"[adapter_cmd]\npython = [{argv}]\n", encoding="utf-8")
    for command in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(command, cwd=root, check=True, capture_output=True)
    yield load_config(root, {"CA_TRUST_PROJECT_FILE": "1", "CA_WORKERS": "1"})


def test_indexing_and_onboarding_a_repo_with_agent_config_runs_and_reads_none_of_it(
    repo: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    global _watching
    monkeypatch.chdir(repo.root)
    _seen.clear()
    _watching = True
    try:
        with GraphStore(repo.db_path) as store:
            full_build(repo, store)
        onboarded = generate_onboarding.create(repo)()
        search_symbol.create(repo)("run")
        read_symbol.create(repo)("pkg.core.run")
        get_index_status.create(repo, ())()
    finally:
        _watching = False

    assert onboarded["reason"] == "ok"
    assert not (repo.root / SENTINEL).exists(), "something ran an agent config file"
    opened = [line for line in _seen if line.startswith("open ")]
    assert not opened, f"code-atlas opened agent config it has no reason to read: {opened}"
    spawned = [line for line in _seen if SENTINEL in line or "sh -c" in line]
    assert not spawned, spawned
    assert any(line.startswith("spawn") for line in _seen), "the audit saw the adapter start"


def test_the_config_files_are_not_in_the_index(repo: Config) -> None:
    with GraphStore(repo.db_path) as store:
        full_build(repo, store)
        indexed = {
            path
            for path in (".claude/settings.json", ".mcp.json", ".vscode/tasks.json")
            if store.file_hash(path) is not None
        }

    assert indexed == set(), "agent config is no code: the index holds none of it"
