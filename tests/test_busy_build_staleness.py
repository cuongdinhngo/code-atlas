"""Task 072: a busy refusal names the staleness of the index the loser is about to query.

The field run: two clients raced ``build_or_update_index``; the loser returned ``mode: busy`` in
0.0 s with no staleness, so a "refresh then investigate" agent read it as success and queried a
stale index. The busy payload must now carry ``staleness``/``last_commit``/``head_commit`` (the
``get_index_status`` vocabulary) plus ``performed: false`` — while exactly one build runs (053).
"""

from __future__ import annotations

import fcntl
import threading
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.index_lock import LOCK_NAME
from code_atlas.tools import build_or_update_index
from code_atlas.tools.build_or_update_index import create
from code_atlas.tools.staleness import BEHIND, CURRENT
from tests.test_incremental import committed, fake_env, git
from tests.test_staleness_scope import SOURCE, build_index


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    committed(tmp_path, {SOURCE: "<?php class A {}\n", "README.md": "docs\n"})
    return tmp_path


def config_for(root: Path, db_path: Path) -> Config:
    return load_config(root, {**fake_env(), "CA_DB_PATH": str(db_path)})


def busy_while_locked(config: Config) -> dict[str, object]:
    """Call the build tool while an external writer holds ``write.lock`` → the busy branch."""
    lock_path = config.db_path.parent / LOCK_NAME
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            return create(config)(full=False)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def test_busy_refusal_carries_staleness_of_the_index_it_will_query(repo: Path) -> None:
    """Proving test: a current index refused as busy says so, in the get_index_status vocabulary."""
    db_path = build_index(repo)
    head = git(repo, "rev-parse", "HEAD")

    result = busy_while_locked(config_for(repo, db_path))

    assert result["mode"] == "busy"
    assert result["staleness"] == CURRENT
    assert result["performed"] is False
    assert result["reason"] == "another_build_running"
    assert result["last_commit"] == head
    assert result["head_commit"] == head


def test_busy_refusal_reports_behind_when_head_has_moved(repo: Path) -> None:
    """The two-state distinction (AC1): a behind index is not reported as current."""
    db_path = build_index(repo)
    committed(repo, {"README.md": "docs, committed\n"}, message="second")

    result = busy_while_locked(config_for(repo, db_path))

    assert result["mode"] == "busy"
    assert result["staleness"] == BEHIND
    assert result["last_commit"] != result["head_commit"]


def test_successful_build_payload_carries_no_busy_fields(repo: Path) -> None:
    """AC2: the winning payload is unchanged — no staleness/performed leak onto success."""
    db_path = build_index(repo)

    result = create(config_for(repo, db_path))(full=False)

    assert result["mode"] in {"incremental", "full"}
    assert "performed" not in result
    assert "staleness" not in result
    assert "head_commit" not in result  # staleness fields land only on the rare busy payload (061)


def test_two_concurrent_builds_run_exactly_one_and_the_loser_carries_staleness(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3: two builders race; one builds, one is refused busy carrying staleness — never both.

    The winner is held inside ``_run`` (lock acquired, DB open) while the loser calls, so the
    loser's read-only staleness open happens *while the write lock is held* — the assumption A1
    the design leaned on. A block would hang this test; a raise would fail it.
    """
    db_path = build_index(repo)
    config = config_for(repo, db_path)

    started, release = threading.Event(), threading.Event()
    runs = 0
    real_run = build_or_update_index._run

    def blocking_run(*args: object, **kwargs: object) -> object:
        nonlocal runs
        runs += 1
        started.set()
        release.wait(timeout=5)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(build_or_update_index, "_run", blocking_run)

    winner: dict[str, object] = {}

    def build_winner() -> None:
        winner["result"] = create(config)(full=False)

    thread = threading.Thread(target=build_winner)
    thread.start()
    try:
        assert started.wait(timeout=5), "winner never entered the build"
        loser = create(config)(full=False)
    finally:
        release.set()
        thread.join(timeout=5)

    assert runs == 1  # exactly one build ran
    assert loser["mode"] == "busy"
    assert loser["performed"] is False
    assert loser["staleness"] in {CURRENT, BEHIND}
    assert winner["result"]["mode"] in {"incremental", "full"}
