"""Task 365 — a read whose subject the running refresh is writing answers at once, labelled.

An in-place incremental holds a SQLite write transaction; read-through repair used to wait out the
5 s busy timeout behind it and refuse ``index_stale``. The repair is already running, so the
guard now sees the DB held, callers/references label the built graph and ``read_symbol`` parses
the file without storing it. A 356 full rebuild writes a shadow, so the live DB still repairs.
"""

from __future__ import annotations

import fcntl
import shlex
import shutil
import sqlite3
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.index_lock import lock_path_for
from code_atlas.indexer import full_build
from code_atlas.store import BUSY_TIMEOUT_MS, GraphStore, shadow_db_path
from code_atlas.tools import (
    find_callers,
    find_implementations,
    find_references,
    get_index_status,
    impact,
    read_symbol,
)
from code_atlas.tools.nav_result import (
    REASON_INDEX_BEHIND_SUBJECT_CHANGED,
    REASON_INDEX_STALE,
    REASON_OK,
)
from code_atlas.tools.schema_guard import BUILD_IN_PROGRESS, guard

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP = shutil.which("php")
pytestmark = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

# The ticket's bar, a fifth of the busy timeout: an answer under it did not wait behind the writer.
NO_BUSY_WAIT_S = 1.0
assert NO_BUSY_WAIT_S < BUSY_TIMEOUT_MS / 1000
CHANGED = "\\App\\Account::close"
UNCHANGED = "\\App\\Ledger::post"
NEW_BODY = "return 'closed';"


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def _write(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


@pytest.fixture
def built(tmp_path: Path) -> tuple[Config, str]:
    """A built index, then a commit changing one file — what the post-commit refresh indexes."""
    _write(
        tmp_path,
        "src/Account.php",
        "<?php\nnamespace App;\nclass Account { public function close() {} }\n",
    )
    _write(
        tmp_path,
        "src/Ledger.php",
        "<?php\nnamespace App;\nclass Ledger { public static function post() {} }\n",
    )
    _write(
        tmp_path,
        "src/Teller.php",
        "<?php\nnamespace App;\nclass Teller { public function run() {"
        " $a = new Account(); $a->close(); Ledger::post(); } }\n",
    )
    _write(tmp_path, ".gitignore", ".code-atlas/\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")
    config = load_config(
        tmp_path,
        {"CA_WORKERS": "2", "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"])},
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    built_rev = _git(tmp_path, "rev-parse", "HEAD")
    _write(
        tmp_path,
        "src/Account.php",
        f"<?php\nnamespace App;\nclass Account {{ public function close() {{ {NEW_BODY} }} }}\n",
    )
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "edit Account")
    return config, built_rev


@contextmanager
def refresh_holding(config: Config, *, sqlite_writer: bool = True) -> Iterator[None]:
    """Hold what a running build holds: ``write.lock``, and for an in-place one the DB itself."""
    lock_path = lock_path_for(config.db_path)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        writer = sqlite3.connect(config.db_path, isolation_level=None) if sqlite_writer else None
        try:
            if writer is not None:
                writer.execute("BEGIN IMMEDIATE")
                writer.execute("INSERT INTO meta (key, value) VALUES ('refresh', 'running')")
            yield
        finally:
            if writer is not None:
                writer.execute("ROLLBACK")
                writer.close()
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _timed(call: Callable[[], dict[str, object]]) -> tuple[dict[str, object], float]:
    started = time.monotonic()
    answer = call()
    return answer, time.monotonic() - started


def _dump(config: Config) -> list[str]:
    conn = sqlite3.connect(config.db_path)
    try:
        return list(conn.iterdump())
    finally:
        conn.close()


def test_callers_and_references_label_a_changed_subject_while_the_db_is_held(
    built: tuple[Config, str],
) -> None:
    """AC1 — labelled with the built revision and the build flag, without the 5 s wait."""
    config, built_rev = built
    callers = guard(find_callers.create(config), config)
    references = guard(find_references.create(config), config)
    with refresh_holding(config):
        by_callers, callers_s = _timed(lambda: callers(CHANGED))
        by_refs, refs_s = _timed(lambda: references(CHANGED))
    for answer, elapsed in ((by_callers, callers_s), (by_refs, refs_s)):
        assert answer["reason"] == REASON_INDEX_BEHIND_SUBJECT_CHANGED, answer
        assert answer["last_commit"] == built_rev
        assert answer[BUILD_IN_PROGRESS] is True
        assert answer["total_count"] == 1
        assert elapsed < NO_BUSY_WAIT_S, elapsed


def test_read_symbol_returns_the_current_source_without_storing_it(
    built: tuple[Config, str],
) -> None:
    """AC2 — the file's current bytes, parsed this call; the index is not written."""
    config, _ = built
    before = _dump(config)
    tool = guard(read_symbol.create(config), config)
    with refresh_holding(config):
        answer, elapsed = _timed(lambda: tool(CHANGED))
    assert answer["reason"] == REASON_OK, answer
    assert NEW_BODY in str(answer["source"])
    assert answer["parsed_unstored"] is True
    assert answer[BUILD_IN_PROGRESS] is True
    assert elapsed < NO_BUSY_WAIT_S, elapsed
    assert _dump(config) == before


def test_unchanged_subjects_answer_the_same_held_or_free(built: tuple[Config, str]) -> None:
    """AC3 — nothing changes for a subject the refresh is not writing."""
    config, _ = built
    tools = (
        lambda: find_callers.create(config)(UNCHANGED),
        lambda: find_references.create(config)(UNCHANGED),
        lambda: read_symbol.create(config)(UNCHANGED),
    )
    with refresh_holding(config):
        held = [tool() for tool in tools]
    assert held == [tool() for tool in tools]
    assert all(answer["reason"] == REASON_OK for answer in held)


def test_with_nothing_held_a_changed_subject_is_repaired_as_before(
    built: tuple[Config, str],
) -> None:
    """AC3 — lock-free, read-through repair runs and the answer is ``ok`` with no new field."""
    config, _ = built
    answer = read_symbol.create(config)(CHANGED)
    assert answer["reason"] == REASON_OK
    assert NEW_BODY in str(answer["source"])
    assert "parsed_unstored" not in answer
    assert find_callers.create(config)(CHANGED)["reason"] == REASON_OK


def test_a_full_rebuild_holding_only_the_lock_still_repairs(built: tuple[Config, str]) -> None:
    """X5 — a 356 rebuild writes the shadow, so the live DB is free and repair is unchanged."""
    config, _ = built
    shadow_db_path(config.db_path).write_bytes(b"")
    with refresh_holding(config, sqlite_writer=False):
        answer = find_callers.create(config)(CHANGED)
    assert answer["reason"] == REASON_OK
    assert answer["total_count"] == 1


def test_an_in_place_refresh_between_its_transactions_still_counts_as_held(
    built: tuple[Config, str],
) -> None:
    """Challenger F1 — `write.lock` held, no shadow: its next transaction would block a repair."""
    config, built_rev = built
    with refresh_holding(config, sqlite_writer=False):
        answer, elapsed = _timed(lambda: find_callers.create(config)(CHANGED))
    assert answer["reason"] == REASON_INDEX_BEHIND_SUBJECT_CHANGED
    assert answer["last_commit"] == built_rev
    assert elapsed < NO_BUSY_WAIT_S, elapsed


def test_impact_never_refused_and_still_answers_while_held(built: tuple[Config, str]) -> None:
    """X1 — `impact` reports staleness instead of repairing, so it was never in the refusal."""
    config, _ = built
    with refresh_holding(config):
        answer, elapsed = _timed(lambda: impact.create(config)(CHANGED))
    assert answer["reason"] != REASON_INDEX_STALE
    assert answer["staleness"] == "behind"
    assert elapsed < NO_BUSY_WAIT_S, elapsed


def test_other_guard_consumers_refuse_at_once_while_held(built: tuple[Config, str]) -> None:
    """X2 — a tool without a labelled path keeps ``index_stale`` but no longer waits for it."""
    config, _ = built
    with refresh_holding(config):
        answer, elapsed = _timed(lambda: find_implementations.create(config)("\\App\\Account"))
    assert answer["reason"] == REASON_INDEX_STALE
    assert elapsed < NO_BUSY_WAIT_S, elapsed


def test_status_says_the_last_graph_answers_while_the_db_is_held(
    built: tuple[Config, str],
) -> None:
    """Scope 4 — the summary and the behind routes stop telling the caller to wait or opt in."""
    config, _ = built
    status_tool = get_index_status.create(config, (get_index_status.NAME,))
    free = status_tool(detail_level="minimal")
    with refresh_holding(config):
        minimal = status_tool(detail_level="minimal")
        standard = status_tool(detail_level="standard")
    assert free["behind_refuses"] == ["find_callers", "find_references"]
    assert "the last built graph answers" not in str(free["summary"])
    for status in (minimal, standard):
        assert status[BUILD_IN_PROGRESS] is True
        assert "behind_refuses" not in status
        assert "find_callers" in status["behind_serves"]
        assert "the last built graph answers" in str(status["summary"])
