"""Task 348 — an installed code-atlas can tell it is outdated.

A release is the package version plus the contract and schema it ships, named by the changelog's top
heading. A version bump that forgets the changelog, or a contract bump that forgets the version,
goes red here. The state hook then reports a plugin/package skew from that same version, offline.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from code_atlas import build_info, contract
from code_atlas.hooks import state
from code_atlas.store import SCHEMA_VERSION

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import gen_skill  # noqa: E402

HEADING = re.compile(r"^## (\S+) — (\d{4}-\d{2}-\d{2}) · contract (\d+) · schema (\d+)$", re.M)
REBUILD_FLAG = "**Full rebuild required.**"


def _version() -> str:
    return str(tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"])


def release_drift(changelog: str, version: str, contract_version: int, schema: str) -> list[str]:
    """Every way the top changelog entry disagrees with the code it claims to describe."""
    entries = HEADING.findall(changelog)
    if not entries:
        return ["CHANGELOG.md has no release heading"]
    top, *older = entries
    drift = []
    if top[0] != version:
        drift.append(f"top entry is {top[0]}, pyproject says {version} — add a release entry")
    if (int(top[2]), top[3]) != (contract_version, schema):
        drift.append(
            f"release {top[0]} names contract {top[2]} · schema {top[3]}, the code is "
            f"contract {contract_version} · schema {schema} — bump the version and add an entry"
        )
    if older and (top[2], top[3]) != (older[0][2], older[0][3]):
        body = changelog.split("\n## ", 2)[1]
        if REBUILD_FLAG not in body:
            drift.append(f"release {top[0]} moves contract/schema but does not flag a rebuild")
    return drift


def test_the_top_release_is_the_code_that_ships() -> None:
    """348 AC1: version, contract and schema agree with the changelog's newest release."""
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert release_drift(changelog, _version(), contract.CONTRACT_VERSION, SCHEMA_VERSION) == []


@pytest.mark.parametrize(
    ("contract_version", "schema", "version"),
    [
        (contract.CONTRACT_VERSION + 1, SCHEMA_VERSION, None),  # contract bumped, version not
        (contract.CONTRACT_VERSION, str(int(SCHEMA_VERSION) + 1), None),  # schema bumped
        (contract.CONTRACT_VERSION, SCHEMA_VERSION, "9.9.9"),  # version bumped, no entry
    ],
)
def test_a_drifted_release_goes_red(
    contract_version: int, schema: str, version: str | None
) -> None:
    """R6.5: the same check fails on each drift it exists to catch."""
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert release_drift(changelog, version or _version(), contract_version, schema)


def test_an_era_move_without_the_rebuild_flag_goes_red() -> None:
    older = "## 0.1.0 — 2026-01-01 · contract 12 · schema 6\n\n- x\n"
    newer = "## 0.2.0 — 2026-02-01 · contract 13 · schema 6\n\n- y\n"
    assert release_drift(f"# C\n\n{newer}\n{older}", "0.2.0", 13, "6")
    flagged = newer.replace("- y", f"- {REBUILD_FLAG} x")
    assert release_drift(f"# C\n\n{flagged}\n{older}", "0.2.0", 13, "6") == []


def test_every_generated_hook_table_expects_this_release() -> None:
    """348 AC2 wiring: both hook tables carry the package version and contract (344, 374)."""
    for path in (gen_skill.CLAUDE_CODE_SNIPPET_PATH, gen_skill.PLUGIN_HOOKS_PATH):
        hooks = json.loads(path.read_text(encoding="utf-8"))["hooks"]
        commands = [h["command"] for e in hooks["SessionStart"] for h in e["hooks"]]
        expect = (
            f"code-atlas-state {state.EXPECT_CONTRACT_FLAG} {contract.CONTRACT_VERSION}"
            f" {state.EXPECT_FLAG} {_version()}"
        )
        assert any(c.endswith(expect) for c in commands), (path.name, commands)


@pytest.mark.parametrize(
    ("installed", "expected", "fix"),
    [
        ("0.1.0", "0.2.0", state.TOOL_UPGRADE),  # the tool install lags the plugin
        ("0.3.0", "0.2.0", state.HOOKS_UPGRADE),  # the plugin lags the tool install
    ],
)
def test_a_skew_names_both_releases_and_the_side_to_move(
    monkeypatch: pytest.MonkeyPatch, installed: str, expected: str, fix: str
) -> None:
    monkeypatch.setattr(build_info, "package_version", lambda: installed)
    line = state.skew_line(expected)
    assert line == (
        f"{state.PREFIX}hooks expect code-atlas {expected} but {installed} is installed — run {fix}"
    )


@pytest.mark.parametrize("installed", ["0.2.0", build_info.UNKNOWN_VERSION])
def test_no_skew_line_when_they_match_or_the_version_is_unknown(
    monkeypatch: pytest.MonkeyPatch, installed: str
) -> None:
    monkeypatch.setattr(build_info, "package_version", lambda: installed)
    assert state.skew_line("0.2.0") is None
    assert state.skew_line(None) is None


def _plugin_state_command(version: str) -> str:
    hooks = json.loads(gen_skill.PLUGIN_HOOKS_PATH.read_text(encoding="utf-8"))["hooks"]
    (command,) = [
        h["command"]
        for e in hooks["SessionStart"]
        for h in e["hooks"]
        if state.EXPECT_FLAG in h["command"]
    ]
    return command.replace(f"{state.EXPECT_FLAG} {_version()}", f"{state.EXPECT_FLAG} {version}")


def _run_plugin_hook(project: Path, version: str) -> subprocess.CompletedProcess[str]:
    """The plugin's own SessionStart command, the installed console script, a real payload."""
    bin_dir = str(Path(sys.executable).parent)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    env["CLAUDE_PROJECT_DIR"] = str(project)
    return subprocess.run(
        ["bash", "-c", _plugin_state_command(version)],
        input=json.dumps({"hook_event_name": "SessionStart", "source": "startup"}),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_the_plugin_hook_names_a_skew_against_the_installed_package(tmp_path: Path) -> None:
    """348 AC2: a plugin one release behind the installed package prints the skew line."""
    installed = build_info.package_version()
    project = tmp_path / "project"
    (project / ".code-atlas").mkdir(parents=True)
    (project / ".code-atlas" / "graph.db").write_bytes(b"not a real index")
    done = _run_plugin_hook(project, "0.0.1")
    assert done.returncode == 0
    assert f"hooks expect code-atlas 0.0.1 but {installed} is installed" in done.stdout
    same = _run_plugin_hook(project, installed)
    assert "hooks expect" not in same.stdout


def test_the_plugin_hook_is_silent_with_no_index(tmp_path: Path) -> None:
    """348 AC2: the 344 gate still holds, skew or not."""
    project = tmp_path / "project"
    project.mkdir()
    done = _run_plugin_hook(project, "0.0.1")
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")
