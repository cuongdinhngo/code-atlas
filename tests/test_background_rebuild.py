"""Task 455: a repo that opted in rebuilds in the background, not waiting on `rebuild required`."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from code_atlas import contract, setup_hooks
from code_atlas.hooks import state
from code_atlas.setup_hooks import record_path
from code_atlas.store import CONTRACT_VERSION_KEY, GraphStore
from tests.test_incremental import config_for
from tests.test_session_state_hook import project  # noqa: F401 — an indexed, current fixture


def _older_contract(root: Path) -> None:
    with GraphStore(config_for(root).db_path) as store:
        store.set_meta(CONTRACT_VERSION_KEY, str(contract.CONTRACT_VERSION - 1))


def _consent(root: Path) -> None:
    record = json.loads(record_path(root).read_text(encoding="utf-8"))
    record_path(root).write_text(json.dumps({**record, "rebuild": "auto"}), encoding="utf-8")


def _stand_in(root: Path, monkeypatch: pytest.MonkeyPatch, *, sleep: float = 0.0) -> Path:
    """A `code-atlas-build` that records its argv, after an optional wait."""
    marker = root / "built.txt"
    script = root / "fake-build"
    script.write_text(f'#!/bin/sh\nsleep {sleep}\necho "$@" >> {marker}\n', encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setattr(setup_hooks, "script_path", lambda name: str(script))
    return marker


def _wait_for(path: Path, seconds: float = 10) -> str:
    deadline = time.monotonic() + seconds
    while not path.is_file() and time.monotonic() < deadline:
        time.sleep(0.1)
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def test_ac1_an_older_contract_with_consent_starts_one_detached_full_build(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _older_contract(project)
    _consent(project)
    marker = _stand_in(project, monkeypatch)
    line = state.state_line(project, refresh=True)
    assert line is not None and line.startswith(state.PREFIX + "rebuild required")
    assert line.endswith(state.BACKGROUND_REBUILD)
    assert _wait_for(marker).split() == ["--full"]


def test_ac1_after_a_pull_the_rebuild_still_starts_not_a_refresh(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Challenger: upgrade, then pull — `behind` and an older contract; a refresh would refuse."""
    from tests.test_session_state_hook import _behind

    _older_contract(project)
    _behind(project)
    _consent(project)
    marker = _stand_in(project, monkeypatch)
    monkeypatch.setattr(state, "start_refresh", lambda root: pytest.fail("refreshed instead"))
    line = state.state_line(project, refresh=True)
    assert line is not None and line.endswith(state.BACKGROUND_REBUILD)
    assert _wait_for(marker).split() == ["--full"]


def test_ac2_no_consent_leaves_the_line_byte_identical(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _older_contract(project)
    marker = _stand_in(project, monkeypatch)
    assert state.state_line(project, refresh=True) == state.state_line(project)
    time.sleep(0.3)
    assert not marker.exists()


def test_ac3_two_session_starts_start_one_build(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _older_contract(project)
    _consent(project)
    marker = _stand_in(project, monkeypatch)
    first = state.state_line(project, refresh=True)
    second = state.state_line(project, refresh=True)
    assert first is not None and first.endswith(state.BACKGROUND_REBUILD)
    assert second is not None and "the last automatic rebuild started at" in second
    time.sleep(0.5)
    assert _wait_for(marker).split() == ["--full"]


def test_a_start_late_in_a_second_still_holds_the_window(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CI flake on #186: a stamp rounded up read as "future" and started a second build."""
    _older_contract(project)
    _consent(project)
    _stand_in(project, monkeypatch)
    monkeypatch.setattr(state.time, "time", lambda: 1_000_000.9)
    assert state.start_rebuild(project) == state.BACKGROUND_REBUILD
    held = state.start_rebuild(project)
    assert held is not None and "the last automatic rebuild started at" in held


def _held(root: Path, stamp: float, contract_version: int) -> None:
    (root / ".code-atlas" / state.REBUILD_MARKER).write_text(
        f"{stamp:.0f} {contract_version}\n", encoding="utf-8"
    )


@pytest.mark.parametrize(
    "stamp_offset, contract_offset",
    [(-state.REBUILD_BACKOFF - 60, 0), (3600, 0), (-60, -1)],
    ids=["window-expired", "future-stamp", "another-contract"],
)
def test_a_marker_that_no_longer_holds_starts_a_build(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    stamp_offset: float,
    contract_offset: int,
) -> None:
    """Review of 455: only a past stamp under this contract holds the six-hour window."""
    _older_contract(project)
    _consent(project)
    marker = _stand_in(project, monkeypatch)
    _held(project, time.time() + stamp_offset, contract.CONTRACT_VERSION + contract_offset)
    line = state.state_line(project, refresh=True)
    assert line is not None and line.endswith(state.BACKGROUND_REBUILD)
    assert _wait_for(marker).split() == ["--full"]


def test_a_failed_start_leaves_no_marker(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _older_contract(project)
    _consent(project)
    _stand_in(project, monkeypatch)

    def refuse(root: Path, argv: list[str]) -> bool:
        raise OSError("cannot start")

    monkeypatch.setattr(state, "_detach", refuse)
    assert state.start_rebuild(project) is None  # the plain line stays; the next session retries
    assert not (project / ".code-atlas" / state.REBUILD_MARKER).exists()


def test_ac4_killing_the_hook_does_not_kill_the_build(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _older_contract(project)
    _consent(project)
    marker = _stand_in(project, monkeypatch, sleep=1.5)
    script = setup_hooks.script_path("code-atlas-build")
    hook = (
        "import sys; from pathlib import Path; from code_atlas import setup_hooks; "
        f"setup_hooks.script_path = lambda name: {script!r}; "
        "from code_atlas.hooks import state; "
        "print(state.state_line(Path(sys.argv[1]), refresh=True), flush=True); "
        "import time; time.sleep(30)"
    )
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    proc = subprocess.Popen(
        [sys.executable, "-c", hook, str(project)], stdout=subprocess.PIPE, text=True, env=env
    )
    assert proc.stdout is not None and state.BACKGROUND_REBUILD in proc.stdout.readline()
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait()
    assert _wait_for(marker).split() == ["--full"]


def test_setup_records_the_consent_and_a_rerun_keeps_it(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(project)
    setup_hooks.main(["--auto-rebuild"])
    assert setup_hooks.rebuild_consent(project) == "auto"
    setup_hooks.main([])
    assert setup_hooks.rebuild_consent(project) == "auto"
    setup_hooks.main(["--no-auto-rebuild"])
    assert setup_hooks.rebuild_consent(project) == "ask"
