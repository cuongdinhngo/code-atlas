"""Task 178: status must not read `current` while a build is still linking, or after one died."""

from __future__ import annotations

import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.index_lock import LOCK_NAME, try_index_write_lock
from code_atlas.indexer import full_build
from code_atlas.store import BUILD_COMPLETE_KEY, GraphStore
from code_atlas.tools.build_or_update_index import create as build_tool
from code_atlas.tools.get_index_status import BUILD_IN_PROGRESS, INDEX_COMPLETE
from code_atlas.tools.get_index_status import create as status_tool

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
SERVABLE = ("build_or_update_index", "search_symbol")


def fake_env() -> dict[str, str]:
    return {
        "CA_WORKERS": "1",
        "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
    }


def write(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def config_for(root: Path):
    return load_config(root, {**fake_env(), "CA_DB_PATH": str(root / ".code-atlas" / "graph.db")})


def status_of(root: Path, **kwargs: object) -> dict[str, object]:
    return status_tool(config_for(root), SERVABLE)(**kwargs)  # type: ignore[arg-type]


def test_status_names_a_build_in_flight(tmp_path: Path) -> None:
    """AC1: the reader who never called the build gets the signal 072 only gave the caller."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    config = config_for(tmp_path)
    build_tool(config)(full=True)

    quiet = status_of(tmp_path)
    assert BUILD_IN_PROGRESS not in quiet

    with try_index_write_lock(config.db_path) as held:
        assert held
        busy = status_of(tmp_path)
    assert busy[BUILD_IN_PROGRESS] is True


def test_the_probe_creates_nothing_and_never_blocks(tmp_path: Path) -> None:
    """AC2: read-only, non-blocking; and with no `.code-atlas/` at all it still answers (077)."""
    started = time.perf_counter()
    unbuilt = status_of(tmp_path)
    elapsed = time.perf_counter() - started

    assert unbuilt["indexed"] is False
    assert BUILD_IN_PROGRESS not in unbuilt, "a missing lock file is *no build*, not unknown"
    assert not (tmp_path / ".code-atlas").exists(), "a status probe must not create the index root"
    assert elapsed < 1.0, f"the probe blocked for {elapsed:.3f}s"


def test_the_probe_costs_one_lock_test_per_call(tmp_path: Path) -> None:
    """AC5: the added cost is per call, never per row — measured, not asserted."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    build_tool(config_for(tmp_path))(full=True)

    started = time.perf_counter()
    for _ in range(200):
        status_of(tmp_path)
    per_call = (time.perf_counter() - started) / 200
    assert per_call < 0.05, f"{per_call * 1000:.3f} ms per status call"


def test_an_unfinished_link_phase_does_not_present_as_a_finished_index(tmp_path: Path) -> None:
    """AC3: the durable case — a build killed between the parse and the late writes.

    Reproduced by interrupting exactly there: the graph holds parsed rows, the link phase never
    ran, and nothing stamped completion. Before 178 this index reported `staleness: "current"`
    with `built_at` set, permanently.
    """
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    config = config_for(tmp_path)

    import code_atlas.indexer as indexer_mod

    class Interrupted(RuntimeError):
        pass

    original = indexer_mod._count_late_writes

    def die_before_linking(*args: object, **kwargs: object) -> None:
        raise Interrupted("killed between the parse and the late writes")

    indexer_mod._count_late_writes = die_before_linking  # type: ignore[assignment]
    try:
        with GraphStore(config.db_path) as store, pytest.raises(Interrupted):
            full_build(config, store)
    finally:
        indexer_mod._count_late_writes = original  # type: ignore[assignment]

    # Since 356 the build died in its shadow: the live index was never written, so nothing
    # claims a graph it never published. The in-place stamp is killed_build_is_honest's (202).
    with GraphStore(config.db_path) as store:
        assert store.get_meta(BUILD_COMPLETE_KEY) is None

    status = status_of(tmp_path)
    assert INDEX_COMPLETE not in status
    assert status["built_at"] is None
    assert status["staleness"] != "current"


def test_a_completed_build_says_nothing_extra(tmp_path: Path) -> None:
    """AC5/061: a quiet server with a finished index is byte-identical to before 178."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    build_tool(config_for(tmp_path))(full=True)

    status = status_of(tmp_path)
    assert INDEX_COMPLETE not in status
    assert BUILD_IN_PROGRESS not in status
    assert status["built_at"] is not None


def test_staleness_still_answers_revision_identity_only(tmp_path: Path) -> None:
    """AC4: `staleness` is not overloaded — during a build it still describes the revision."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    config = config_for(tmp_path)
    build_tool(config)(full=True)
    quiet = status_of(tmp_path)

    with try_index_write_lock(config.db_path) as held:
        assert held
        during = status_of(tmp_path)

    assert during["staleness"] == quiet["staleness"]
    assert during["last_commit"] == quiet["last_commit"]
    assert during[BUILD_IN_PROGRESS] is True


def test_the_busy_refusal_payload_is_unchanged(tmp_path: Path) -> None:
    """AC4: 072's payload keeps its shape — the new axes live on status, not on the refusal."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    config = config_for(tmp_path)
    build_tool(config)(full=True)

    with try_index_write_lock(config.db_path) as held:
        assert held
        busy = build_tool(config)(full=True)

    assert busy["mode"] == "busy"
    assert busy["reason"] == "another_build_running"
    assert BUILD_IN_PROGRESS not in busy and INDEX_COMPLETE not in busy


def test_a_killed_build_stops_claiming_to_be_running(tmp_path: Path) -> None:
    """AC1 + 177's rule: the in-flight axis is the live lock, so it cannot outlive the writer."""
    db = tmp_path / ".code-atlas" / "graph.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys, time\n"
            "from pathlib import Path\n"
            "from code_atlas.index_lock import try_index_write_lock\n"
            "with try_index_write_lock(Path(sys.argv[1])) as held:\n"
            "    assert held\n"
            "    print('holding', flush=True)\n"
            "    time.sleep(60)\n",
            str(db),
        ],
        stdout=subprocess.PIPE,
        cwd=REPO,
    )
    assert holder.stdout is not None
    assert holder.stdout.readline().strip() == b"holding"
    assert status_of(tmp_path)[BUILD_IN_PROGRESS] is True

    holder.send_signal(signal.SIGKILL)
    holder.wait(timeout=10)

    assert BUILD_IN_PROGRESS not in status_of(tmp_path)
    # The lock file outlives the writer; the claim does not.
    assert (db.parent / LOCK_NAME).is_file()
