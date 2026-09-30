"""Task 177: a long build publishes progress, and the claim dies with the process."""

from __future__ import annotations

import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

from code_atlas import cli
from code_atlas.config import load_config
from code_atlas.index_lock import (
    LOCK_NAME,
    build_in_progress,
    lock_path_for,
    publish_build_progress,
    read_build_progress,
)
from code_atlas.indexer import BUILD_PHASES, full_build
from code_atlas.store import GraphStore
from code_atlas.tools.build_or_update_index import create

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"


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


def test_progress_names_the_phase_not_only_a_file_counter(tmp_path: Path) -> None:
    """AC2: a counter alone hits 100% and then sits in the late writes, which reads as a wedge."""
    for index in range(4):
        write(tmp_path, f"src/a{index}.aa", f"class Thing{index} {{}}\n")
    config = config_for(tmp_path)
    seen: list[tuple[str, int, int]] = []
    with GraphStore(config.db_path) as store:
        full_build(config, store, progress=lambda *row: seen.append(row))

    phases = [phase for phase, _done, _total in seen]
    assert set(phases) <= set(BUILD_PHASES), f"phase outside the build's vocabulary: {set(phases)}"
    # The parse counter reaches its total, and work is still reported after it does.
    assert ("parse", 4, 4) in seen
    after_parse = phases[phases.index("parse") + phases.count("parse") :]
    assert "enrichment" in after_parse and "resolve" in after_parse, phases
    assert phases.index("resolve") > phases.index("parse")


def test_a_build_with_no_reader_reports_nothing(tmp_path: Path) -> None:
    """AC5/061: the default is no sink, so a short build runs the pre-177 code path."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
    assert report.files == 1
    assert not lock_path_for(config.db_path).is_file()


def test_the_build_tool_publishes_progress_and_its_payload_is_unchanged(tmp_path: Path) -> None:
    """AC1/AC5: progress rides the lock file; the tool's payload gains nothing (061)."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    config = config_for(tmp_path)
    payload = create(config)(full=True)

    assert payload["mode"] == "full"
    assert not [key for key in payload if "progress" in key or key == "job_id"]
    # The build has finished, so the lock is free and the line is no longer a live claim...
    assert read_build_progress(config.db_path) is None
    # ...but it was written during the build, and it named a phase.
    assert "phase=" in lock_path_for(config.db_path).read_text(encoding="utf-8")


def test_a_killed_writer_leaves_no_claim_that_a_build_is_running(tmp_path: Path) -> None:
    """AC3: liveness is the live flock, so SIGKILL cannot leave a durable false claim."""
    db = tmp_path / ".code-atlas" / "graph.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys, time\n"
            "from pathlib import Path\n"
            "from code_atlas.index_lock import try_index_write_lock, publish_build_progress\n"
            "db = Path(sys.argv[1])\n"
            "with try_index_write_lock(db) as held:\n"
            "    assert held\n"
            "    publish_build_progress(db, 'phase=resolve done=9 total=9 pid=1')\n"
            "    print('holding', flush=True)\n"
            "    time.sleep(60)\n",
            str(db),
        ],
        stdout=subprocess.PIPE,
        cwd=REPO,
    )
    assert holder.stdout is not None
    assert holder.stdout.readline().strip() == b"holding"

    assert build_in_progress(db) is True
    assert read_build_progress(db) == "phase=resolve done=9 total=9 pid=1"

    holder.send_signal(signal.SIGKILL)
    holder.wait(timeout=10)

    assert build_in_progress(db) is False
    assert read_build_progress(db) is None
    # The line is still on disk: it is the *lock*, not a cleanup step, that retracts the claim.
    assert "phase=resolve" in (db.parent / LOCK_NAME).read_text(encoding="utf-8")


def test_progress_is_readable_from_a_shell_without_a_second_mcp_client(tmp_path: Path) -> None:
    """AC4: the caller that started the build is blocked inside it — read from elsewhere."""
    db = tmp_path / ".code-atlas" / "graph.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), **fake_env()}
    env["CA_DB_PATH"] = str(db)

    def run_status() -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, "-m", "code_atlas.cli", "--status"],
            env=env,
            cwd=tmp_path,
            capture_output=True,
            check=False,
        )

    from code_atlas.index_lock import try_index_write_lock

    with try_index_write_lock(db) as held:
        assert held
        publish_build_progress(db, "phase=parse done=7 total=19000 pid=1")
        running = run_status()
    idle = run_status()

    assert running.returncode == cli.OK
    assert b"phase=parse done=7 total=19000" in running.stderr
    assert idle.returncode == cli.NOTHING_TO_DO
    assert b"no build is running" in idle.stderr


def test_the_busy_refusal_is_unchanged(tmp_path: Path) -> None:
    """AC6/R4.3: one mutex; the loser still gets 072's payload, progress or not."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    config = config_for(tmp_path)
    create(config)(full=True)

    from code_atlas.index_lock import try_index_write_lock

    with try_index_write_lock(config.db_path) as held:
        assert held
        busy = create(config)(full=True)

    assert busy["mode"] == "busy"
    assert busy["reason"] == "another_build_running"
    assert busy["performed"] is False
    assert "staleness" in busy and "last_commit" in busy


def test_the_progress_write_is_bounded(tmp_path: Path) -> None:
    """Cost constraint: one fixed-width line, rewritten in place — the file never grows."""
    db = tmp_path / ".code-atlas" / "graph.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    lock_path_for(db).write_text("", encoding="utf-8")

    started = time.perf_counter()
    for index in range(500):
        publish_build_progress(db, f"phase=parse done={index} total=500 pid=1")
    elapsed = time.perf_counter() - started

    assert lock_path_for(db).stat().st_size == 200
    assert elapsed / 500 < 0.01, f"{elapsed / 500:.6f}s per publish"
