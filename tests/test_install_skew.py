"""Task 374 — every half of an install that lags is named at session start, offline.

348 compared the plugin with the tool install. The adapter checkout ``CA_<LANG>_CMD`` points into is
a third half, and nothing checked it before a build: the anchor's core spoke contract 13, its
checkout 14, and the first sign was a refused build. The hook now launches each configured adapter
and reads its handshake, falls back to the contract a refused build recorded, and names every half
older than the newest one with its fix, in the order they must run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from code_atlas import adapter_skew, build_info, contract, indexer
from code_atlas.adapter import AdapterContractError, AdapterError, SubprocessAdapter
from code_atlas.config import load_config
from code_atlas.hooks import state
from code_atlas.tokens import estimate_tokens

FIXTURE = Path(__file__).parent / "fixtures" / "adapter" / "fake_adapter.py"
CORE = contract.CONTRACT_VERSION
HOOK_TIMEOUT = 10  # the generated SessionStart entry's `timeout`


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / ".code-atlas").mkdir(parents=True)
    (project / ".code-atlas" / "graph.db").write_bytes(b"not a real index")
    return project


def _run_hook(
    project: Path, mode: str | None, **extra: str
) -> tuple[subprocess.CompletedProcess[str], float]:
    """The installed console script, a real payload, the fake adapter as its CA_*_CMD (R6.10)."""
    installed = build_info.package_version()
    env = {k: v for k, v in os.environ.items() if not k.startswith("CA_")}
    env["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{env['PATH']}"
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env.update(extra)
    if mode is not None:
        env["CA_FAKE_CMD"] = f"{sys.executable} {FIXTURE} {mode}"
    command = [
        "code-atlas-state",
        state.EXPECT_CONTRACT_FLAG,
        str(CORE),
        state.EXPECT_FLAG,
        installed,
    ]
    started = time.monotonic()
    done = subprocess.run(
        command,
        input=json.dumps({"hook_event_name": "SessionStart", "source": "startup"}),
        env=env,
        cwd=project,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return done, time.monotonic() - started


def _skew_lines(done: subprocess.CompletedProcess[str]) -> list[str]:
    return [line for line in done.stdout.splitlines() if "contract" in line or "(v" in line]


def test_a_checkout_behind_the_core_is_named_with_its_fix(tmp_path: Path) -> None:
    """AC1: one line — the adapter, both contracts, the checkout's fix — within the hook timeout."""
    done, seconds = _run_hook(_project(tmp_path), "stale-version")
    assert done.returncode == 0
    assert seconds < HOOK_TIMEOUT
    assert _skew_lines(done) == [
        f"{state.PREFIX}adapter 'fake' speaks contract v1 but this core speaks v{CORE} — run "
        f"{state.CHECKOUT_UPGRADE}"
    ]


def test_a_core_behind_the_checkout_is_named_with_the_tool_upgrade(tmp_path: Path) -> None:
    """AC1, the anchor's case: the checkout leads, so the tool (and the plugin it shipped) move."""
    done, seconds = _run_hook(_project(tmp_path), "bad-version")
    assert done.returncode == 0
    assert seconds < HOOK_TIMEOUT
    (line,) = _skew_lines(done)
    for part in ("'fake'", "(v99)", f"(v{CORE})", state.TOOL_STEP):
        assert part in line, line


@pytest.mark.parametrize("mode", ["ok", None], ids=["contracts-match", "no-adapter"])
def test_the_hook_is_silent_about_adapters_when_the_contracts_match(
    tmp_path: Path, mode: str | None
) -> None:
    """AC1: an adapter on this core's contract, or none configured, adds nothing."""
    done, _ = _run_hook(_project(tmp_path), mode)
    assert done.returncode == 0
    assert "contract" not in done.stdout


def test_the_hook_launches_nothing_and_says_nothing_with_no_index(tmp_path: Path) -> None:
    """AC1: 344's gate — no index, no launch, no line."""
    project = tmp_path / "project"
    project.mkdir()
    log = tmp_path / "boot.log"
    done, _ = _run_hook(project, "bad-version", CA_FAKE_BOOTLOG=str(log))
    assert (done.returncode, done.stdout) == (0, "")
    assert not log.exists()


def test_a_silent_adapter_cannot_hold_the_hook_past_its_timeout(tmp_path: Path) -> None:
    """AC1: an adapter that never announces itself is unknown, and the hook still exits in time."""
    done, seconds = _run_hook(_project(tmp_path), "silent-boot")
    assert done.returncode == 0
    assert seconds < HOOK_TIMEOUT
    assert "contract" not in done.stdout


def test_a_refused_build_speaks_for_an_adapter_the_launch_cannot_answer_for(
    tmp_path: Path,
) -> None:
    """W1: a recorded refusal speaks when the handshake times out; a build that runs clears it."""
    project = _project(tmp_path)
    db = project / ".code-atlas" / "graph.db"
    adapter_skew.record_refusal(db, AdapterContractError("fake", 99))
    done, _ = _run_hook(project, "silent-boot")
    (line,) = _skew_lines(done)
    assert "'fake' (v99)" in line, line
    adapter_skew.clear_refusals(db)
    done, _ = _run_hook(project, "silent-boot")
    assert "contract" not in done.stdout


def _line(
    *,
    installed: str,
    plugin: str,
    plugin_contract: int,
    adapters: dict[str, int | None],
    windows: bool,
) -> str:
    line = state.install_line(
        installed=installed,
        expected=plugin,
        expected_contract=plugin_contract,
        adapters=adapters,
        windows=windows,
    )
    assert line is not None
    return line


@pytest.mark.parametrize("windows", [False, True], ids=["posix", "windows"])
def test_every_half_older_than_the_newest_is_named_in_order(windows: bool) -> None:
    """AC2: tool, plugin and checkout on three versions — each lagging half and its command, in
    the Scope 2 order, the Windows disconnect only on Windows, within 90 tokens."""
    line = _line(
        installed="0.3.0",
        plugin="0.2.0",
        plugin_contract=CORE - 1,
        adapters={"php": CORE + 1},
        windows=windows,
    )
    assert estimate_tokens(line) <= state.TOKEN_BUDGET, line
    assert "0.3.0" in line and "0.2.0" in line and f"v{CORE + 1}" in line
    order = [state.TOOL_STEP, state.PLUGIN_STEP, state.RECONNECT_STEP]
    if windows:
        order.insert(0, state.DISCONNECT_STEP)
    positions = [line.index(step) for step in order]
    assert positions == sorted(positions), line
    assert (state.DISCONNECT_STEP in line) is windows
    assert state.CHECKOUT_STEP not in line  # the checkout is the newest half


def test_a_checkout_behind_a_newer_plugin_is_named_with_the_tool() -> None:
    """AC2: the plugin is newest — the tool and the checkout both lag it, in that order."""
    line = _line(
        installed="0.3.0",
        plugin="0.4.0",
        plugin_contract=CORE + 1,
        adapters={"php": CORE},
        windows=False,
    )
    assert estimate_tokens(line) <= state.TOKEN_BUDGET, line
    assert line.index(state.TOOL_STEP) < line.index(state.CHECKOUT_STEP)
    assert state.PLUGIN_STEP not in line


def test_a_line_past_the_budget_collapses_to_a_pointer() -> None:
    """W5: past 90 tokens every lagging half is still named; the commands go to the README."""
    line = _line(
        installed="0.3.0",
        plugin="0.2.0",
        plugin_contract=CORE - 1,
        adapters={f"language{n}": CORE - n for n in range(1, 9)} | {"leader": CORE + 1},
        windows=True,
    )
    assert estimate_tokens(line) <= state.TOKEN_BUDGET, line
    assert state.UPGRADING_POINTER in line
    for half in ("tool 0.3.0", "plugin 0.2.0", "'language8' v6", "'leader'"):
        assert half in line, line


def test_a_checkout_too_long_to_list_is_counted() -> None:
    """W5: when even the pointer form cannot list the adapters, the checkout half is counted."""
    line = _line(
        installed="0.3.0",
        plugin="0.2.0",
        plugin_contract=CORE - 1,
        adapters={f"language{n}": CORE - 1 - n % 3 for n in range(30)} | {"leader": CORE + 1},
        windows=False,
    )
    assert estimate_tokens(line) <= state.TOKEN_BUDGET, line
    for half in ("tool 0.3.0", "plugin 0.2.0", "30 adapters", "'leader'"):
        assert half in line, line


def test_a_tool_and_plugin_skew_alone_keeps_348s_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """348's line is byte-identical when no adapter is involved, off Windows."""
    monkeypatch.setattr(build_info, "package_version", lambda: "0.3.0")
    line = state.install_line(
        installed="0.3.0", expected="0.2.0", expected_contract=None, adapters={}, windows=False
    )
    assert line == state.skew_line("0.2.0")


def test_an_install_whose_halves_agree_says_nothing() -> None:
    assert (
        state.install_line(
            installed="0.3.0",
            expected="0.3.0",
            expected_contract=CORE,
            adapters={"php": CORE, "sql": None},
            windows=True,
        )
        is None
    )


def test_a_refused_handshake_is_recorded_and_a_clean_one_clears_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """W1's second source: every adapter launch (build, refresh, read) records or clears it."""
    for name in [k for k in os.environ if k.startswith("CA_")]:
        monkeypatch.delenv(name)
    project = _project(tmp_path)
    monkeypatch.setenv("CA_FAKE_CMD", f"{sys.executable} {FIXTURE} bad-version")
    config = load_config(project)
    assert indexer.parse_file(config, "src/a.aa") is None
    assert adapter_skew.read_refusals(config.db_path) == {"fake": 99}

    monkeypatch.setenv("CA_FAKE_CMD", f"{sys.executable} {FIXTURE} ok")
    indexer.parse_file(load_config(project), "src/a.aa")
    assert adapter_skew.read_refusals(config.db_path) == {}


def test_a_partial_announce_drops_the_refusals_of_the_adapters_it_proved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An adapter that announced this core's contract before another refused is no longer stale."""
    for name in [k for k in os.environ if k.startswith("CA_")]:
        monkeypatch.delenv(name)
    project = _project(tmp_path)
    config_db = project / ".code-atlas" / "graph.db"
    adapter_skew.record_refusal(config_db, AdapterContractError("alpha", 1))
    monkeypatch.setenv("CA_ALPHA_CMD", f"{sys.executable} {FIXTURE} ok")
    monkeypatch.setenv("CA_ZETA_CMD", f"{sys.executable} {FIXTURE} bad-version")
    assert indexer.parse_file(load_config(project), "src/a.aa") is None
    assert adapter_skew.read_refusals(config_db) == {"zeta": 99}


def test_a_kill_before_the_launch_still_kills_the_child(tmp_path: Path) -> None:
    """The probe's deadline can fire before Popen: the child it then makes must not outlive it."""
    adapter = SubprocessAdapter("fake", (sys.executable, str(FIXTURE), "silent-boot"), tmp_path)
    adapter.kill()
    started = time.monotonic()
    with pytest.raises(AdapterError):
        adapter.start()
    assert time.monotonic() - started < HOOK_TIMEOUT
    adapter.stop()
