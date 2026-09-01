"""Task 202: a build killed mid-write must not leave an index that reports `current`.

Field run, 2026-08-31: `timeout 300 code-atlas-refresh` was killed mid-reconcile after it had
committed its delete batches. 1,367 files, 13,278 nodes and 96,627 edges were gone, and
`get_index_status` answered `staleness: "current"` with an empty `next_tool_suggestions` — and no
incremental could repair it, because `last_commit` still named HEAD so the next git diff was empty.

The fixture is the deliverable (AC4). This class of defect is only ever found by killing a process,
so nothing here sets `build_complete` by hand: a real subprocess is started and SIGKILLed mid-parse.
"""

from __future__ import annotations

import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import load_config
from code_atlas.gitutil import head_commit
from code_atlas.index_lock import read_build_progress
from code_atlas.indexer import INCOMPLETE_INDEX, build_incomplete
from code_atlas.store import (
    BUILD_COMPLETE_KEY,
    CONTRACT_VERSION_KEY,
    LAST_COMMIT_KEY,
    GraphStore,
)
from code_atlas.tools.build_or_update_index import NAME as BUILD_NAME
from code_atlas.tools.build_or_update_index import create as build_tool
from code_atlas.tools.find_callers import create as find_callers_tool
from code_atlas.tools.get_index_status import INDEX_COMPLETE
from code_atlas.tools.get_index_status import NAME as STATUS_NAME
from code_atlas.tools.get_index_status import create as status_tool
from code_atlas.tools.staleness import CURRENT, INCOMPLETE

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
# Enough files that the parse phase outlives the poll below; the real window is minutes.
FILES = 1500
KILL_TIMEOUT = 60.0


def env_for(root: Path) -> dict[str, str]:
    return {
        "CA_WORKERS": "1",
        "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
        "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
    }


def config_for(root: Path):
    return load_config(root, env_for(root))


def big_repo(root: Path) -> None:
    src = root / "src"
    src.mkdir(parents=True, exist_ok=True)
    for n in range(FILES):
        (src / f"m{n}.aa").write_text(f"class Thing{n} {{}}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"],
        cwd=root, check=True, capture_output=True,
    )


def kill_an_incremental_mid_write(root: Path) -> None:
    """Reproduce the field state: kill a real INCREMENTAL, then leave HEAD where it was.

    A killed *full* build leaves no `last_commit`, so `_run` already degrades to full and the index
    is not the unrepairable one this ticket is about. The field case is a killed **incremental** on
    an index whose `last_commit` still equals HEAD — so the next git diff is empty and no
    incremental can ever repair it. The tree is dirtied to give that incremental work to do, and
    restored afterwards so `staleness` reads exactly as the field payload did: `current`.

    Never sets `build_complete` by hand — AC4 is explicit that a hand-set flag does not prove this.
    """
    for path in sorted((root / "src").glob("*.aa")):
        path.write_text(path.read_text(encoding="utf-8") + "class More {}\n", encoding="utf-8")
    script = (
        "from code_atlas.config import load_config;"
        "from code_atlas.tools.build_or_update_index import create;"
        "import os, pathlib;"
        "create(load_config(pathlib.Path(os.environ['CA_ROOT'])))(full=False)"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", script],
        env={**os.environ, **env_for(root), "CA_ROOT": str(root)},
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    db = config_for(root).db_path
    deadline = time.monotonic() + KILL_TIMEOUT
    try:
        while time.monotonic() < deadline:
            line = read_build_progress(db)
            if line and "phase=parse" in line and "done=" in line:
                child.send_signal(signal.SIGKILL)
                child.wait(timeout=30)
                subprocess.run(
                    ["git", "checkout", "--", "."], cwd=root, check=True, capture_output=True
                )
                return
            if child.poll() is not None:
                raise AssertionError(
                    "the build finished before it could be killed — the fixture is too small to "
                    "exercise the window, so any pass below would be vacuous (R6.5)"
                )
            time.sleep(0.02)
    finally:
        if child.poll() is None:
            child.send_signal(signal.SIGKILL)
            child.wait(timeout=30)
        # HEAD never moved in the field case; restoring the tree makes `staleness` read `current`,
        # which is the answer this ticket exists to stop.
        subprocess.run(["git", "checkout", "--", "."], cwd=root, check=True, capture_output=True)
    raise AssertionError(f"no build progress reached `phase=parse` within {KILL_TIMEOUT}s")


@pytest.fixture
def killed_index(tmp_path: Path) -> Path:
    big_repo(tmp_path)
    build_tool(config_for(tmp_path))(full=True)
    kill_an_incremental_mid_write(tmp_path)
    with GraphStore(config_for(tmp_path).db_path) as store:
        assert store.get_meta(BUILD_COMPLETE_KEY) == "0", "the kill left no incomplete mark"
        assert build_incomplete(store) is True
        # The field state exactly: the index still names HEAD, so no incremental can repair it.
        assert store.get_meta(LAST_COMMIT_KEY) == head_commit(tmp_path)
    return tmp_path


def test_a_killed_build_does_not_report_current(killed_index: Path) -> None:
    """AC1 — the proving test. Red before the fix: `current`, with nothing suggested."""
    status = status_tool(config_for(killed_index), (STATUS_NAME, BUILD_NAME))()

    assert status["staleness"] == INCOMPLETE
    assert status["staleness"] != CURRENT
    assert status["next_tool_suggestions"], "a gutted index suggested nothing to do"
    assert status[INDEX_COMPLETE] is False


def test_the_next_build_escalates_and_says_so(killed_index: Path) -> None:
    """AC2 — an incremental over a mid-write graph is not equivalent to a full one."""
    payload = build_tool(config_for(killed_index))(full=False)

    assert payload["mode"] == "full"
    escalation = payload[INCOMPLETE_INDEX]
    assert isinstance(escalation, dict) and escalation["escalated_to"] == "full"
    wrote = payload["wrote"]
    assert isinstance(wrote, dict) and wrote["files"] == FILES, "the repair actually rebuilt"


def test_the_repair_leaves_an_index_that_reports_current(killed_index: Path) -> None:
    """AC2's other half: the escalation is only worth having if it ends the damaged state."""
    build_tool(config_for(killed_index))(full=False)

    status = status_tool(config_for(killed_index), (STATUS_NAME, BUILD_NAME))()

    assert status["staleness"] == CURRENT
    assert INDEX_COMPLETE not in status
    assert status["next_tool_suggestions"] == []


def test_a_completed_build_reports_exactly_as_before(tmp_path: Path) -> None:
    """AC3/061 — the healthy path gains no field and changes no wording."""
    big_repo(tmp_path)
    build_tool(config_for(tmp_path))(full=True)

    status = status_tool(config_for(tmp_path), (STATUS_NAME, BUILD_NAME))()
    payload = build_tool(config_for(tmp_path))(full=False)

    assert status["staleness"] == CURRENT
    assert INDEX_COMPLETE not in status
    assert status["next_tool_suggestions"] == []
    assert payload["mode"] == "incremental"
    assert INCOMPLETE_INDEX not in payload


def test_index_complete_and_staleness_cannot_disagree(killed_index: Path) -> None:
    """AC6/R6.7 — both fields are read off one predicate, on one payload."""
    status = status_tool(config_for(killed_index), (STATUS_NAME, BUILD_NAME))()

    assert (status[INDEX_COMPLETE] is False) == (status["staleness"] == INCOMPLETE)


def test_the_refresh_hook_reports_and_does_not_rebuild(killed_index: Path) -> None:
    """The ratified want: 053 says this hook never builds, and a killed repair would loop."""
    completed = subprocess.run(
        [sys.executable, "-m", "code_atlas.hooks.refresh", "--verbose"],
        env={**os.environ, **env_for(killed_index), "CLAUDE_PROJECT_DIR": str(killed_index)},
        cwd=killed_index, capture_output=True, text=True,
    )

    assert completed.returncode == 0, "a hook must never fail the git command (053)"
    assert INCOMPLETE_INDEX in completed.stderr
    assert "code-atlas-build --full" in completed.stderr
    with GraphStore(config_for(killed_index).db_path) as store:
        assert build_incomplete(store) is True, "the hook repaired the index instead of reporting"


def test_a_nav_tool_over_a_gutted_graph_says_so_too(killed_index: Path) -> None:
    """R6.9 — assert at the consumers. A `find_callers` zero here is the confident-wrong-zero.

    The status tool is not the only reader: `compute_staleness` has six consumers, and four of them
    sign a nav payload with it. Fixing only `get_index_status` would leave every one of them
    reporting `current` over an index missing 6% of its files, which is what the ticket's opening
    names as 065/054's defect class arriving through a door neither of them watches.
    """
    answer = find_callers_tool(config_for(killed_index))(qname="\\Nope", sign=True)

    claim_line = answer.get("claim")
    assert claim_line is not None, "the signed payload carries no claim to inspect"
    assert INCOMPLETE in str(claim_line), f"a nav tool still reads healthy: {claim_line}"


def test_both_escalation_causes_are_reported_when_both_hold(killed_index: Path) -> None:
    """AC5 — disjoint keys mean neither cause has to win a precedence the caller cannot see.

    Raised by the ticket-blind challenger: with an incomplete index *and* a lagging vocabulary era,
    whichever check ran first would be the only one reported. Both are true, so both are said.
    """
    with GraphStore(config_for(killed_index).db_path) as store:
        store.set_meta(CONTRACT_VERSION_KEY, str(contract.CONTRACT_VERSION - 1))

    payload = build_tool(config_for(killed_index))(full=False, allow_full_rebuild=True)

    assert payload["mode"] == "full"
    assert INCOMPLETE_INDEX in payload
    assert "contract_change" in payload
