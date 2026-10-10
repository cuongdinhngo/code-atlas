"""Task 381 AC1 — a repo that commits code-atlas's hooks leaves a teammate without it untouched.

The teammate has no plugin, no console scripts and no index. Every hook command code-atlas offers —
the plugin's and the hand snippet a project merges into its committed `.claude/settings.json` — runs
in that repo with a `PATH` holding only recording stubs for `git`, `curl`, `wget` and `uv`: it must
print nothing, exit 0 and invoke none of them. A deliberately ungated copy of each must go red.
"""

from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import gen_skill  # noqa: E402

OFFERS = (gen_skill.PLUGIN_HOOKS_PATH, gen_skill.CLAUDE_CODE_SNIPPET_PATH)
RECORDED = ("git", "curl", "wget", "uv")
SHELLS = tuple(shell for shell in ("bash", "sh") if shutil.which(shell))
# "No measurable start-up time": the hook against `true`, each the median of RUNS spawns.
RUNS = 25
MEASURABLE_MS = 5.0

pytestmark = pytest.mark.skipif(os.name == "nt", reason="the Windows Git Bash arm is task 381's E2")


def _commands() -> list[str]:
    found: set[str] = set()
    for path in OFFERS:
        table = json.loads(path.read_text(encoding="utf-8"))["hooks"]
        found |= {h["command"] for entries in table.values() for e in entries for h in e["hooks"]}
    return sorted(found)


COMMANDS = _commands()


@pytest.fixture
def teammate(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    """The anchor's committed shape — project hooks and a `.code-atlas.toml` — and nothing else."""
    repo = tmp_path / "repo"
    (repo / ".claude").mkdir(parents=True)
    snippet = gen_skill.CLAUDE_CODE_SNIPPET_PATH.read_text(encoding="utf-8")
    (repo / ".claude" / "settings.json").write_text(snippet, encoding="utf-8")
    (repo / ".code-atlas.toml").write_text("workers = 2\n", encoding="utf-8")
    stubs, log = tmp_path / "bin", tmp_path / "invoked.log"
    stubs.mkdir()
    for name in RECORDED:
        stub = stubs / name
        stub.write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\n', encoding="utf-8")
        stub.chmod(0o755)
    # Only the stubs: no console scripts, no interpreter, no network client of its own.
    env = {"PATH": str(stubs), "HOME": str(tmp_path), "CLAUDE_PROJECT_DIR": str(repo)}
    return repo, env, log


def _run(shell: str, command: str, repo: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [shutil.which(shell) or shell, "-c", command],
        cwd=repo,
        env=env,
        input='{"hook_event_name": "SessionStart"}',
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_every_offered_command_is_checked() -> None:
    # R6.5: an empty list would pass every assertion below vacuously.
    assert len(COMMANDS) >= 6 and SHELLS
    assert all(command.startswith(gen_skill.PLUGIN_GATE) for command in COMMANDS), COMMANDS


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize("command", COMMANDS)
def test_a_teammate_without_code_atlas_hears_nothing(
    teammate: tuple[Path, dict[str, str], Path], command: str, shell: str
) -> None:
    repo, env, log = teammate
    done = _run(shell, command, repo, env)
    assert (done.returncode, done.stdout, done.stderr) == (0, "", ""), done
    assert not log.exists(), log.read_text(encoding="utf-8")


@pytest.mark.parametrize("command", COMMANDS)
def test_an_ungated_build_goes_red(
    teammate: tuple[Path, dict[str, str], Path], command: str
) -> None:
    """R6.5: with both gates stripped the same harness sees the hook fail."""
    repo, env, _ = teammate
    done = _run(SHELLS[0], gen_skill.ungate(command), repo, env)
    assert done.returncode != 0 or done.stdout or done.stderr


def test_the_gate_adds_no_measurable_start_up(
    teammate: tuple[Path, dict[str, str], Path],
) -> None:
    """Each hook's median spawn against `true`'s; the figures are recorded in the task."""
    repo, env, _ = teammate

    def median_ms(command: str) -> float:
        samples = []
        for _ in range(RUNS):
            started = time.perf_counter()
            _run(SHELLS[0], command, repo, env)
            samples.append((time.perf_counter() - started) * 1000)
        return statistics.median(samples)

    absent = median_ms("true")
    worst = max(median_ms(command) for command in COMMANDS)
    print(f"hook absent {absent:.2f} ms · slowest gated hook {worst:.2f} ms")
    assert worst - absent < MEASURABLE_MS
