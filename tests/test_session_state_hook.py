"""322 — the index state line, restated at the session boundaries where `initialize`'s copy decayed.

Two field retros filed "a progress signal on a multi-minute build" as missing; `get_index_status`
already names it. The line rode `initialize` once, so by the time the build was the open question
it was far behind — and after a compaction, gone. The silence tests matter as much as the fire
tests: a line that always prints is the chrome the next retro asks us to remove.
"""

from __future__ import annotations

import io
import json
import sqlite3
import tomllib
from pathlib import Path

import pytest

from code_atlas.hooks import state
from code_atlas.index_lock import publish_build_progress, try_index_write_lock
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tokens import estimate_tokens
from code_atlas.tools import get_index_status
from tests.test_incremental import committed, config_for, fake_env

REPO = Path(__file__).resolve().parent.parent
SOURCE = {"src/a.aa": "# symbol: alpha\n"}


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An indexed, current project the hook resolves from its own environment, as a host runs it."""
    for key, value in fake_env().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("CA_DB_PATH", str(tmp_path / ".code-atlas" / "graph.db"))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    committed(tmp_path, SOURCE)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    return tmp_path


def _behind(root: Path) -> None:
    committed(root, {"src/b.aa": "# symbol: beta\n"}, message="moves HEAD past the index")


def _summary(root: Path) -> str:
    return str(get_index_status.create(config_for(root), ())()["summary"])


def _run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], stdin: str
) -> tuple[int, str]:
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    code = state.main([])
    return code, capsys.readouterr().out


def _event(name: str) -> str:
    return json.dumps({"hook_event_name": name, "source": "compact"})


def test_an_older_era_index_speaks_at_an_unmoved_head(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """347 AC2: `current` by revision, an older contract by era — SessionStart must say so."""
    from code_atlas import contract
    from code_atlas.store import CONTRACT_VERSION_KEY

    with GraphStore(config_for(project).db_path) as store:
        store.set_meta(CONTRACT_VERSION_KEY, str(contract.CONTRACT_VERSION - 1))
    code, out = _run(monkeypatch, capsys, _event("SessionStart"))
    assert code == 0
    # A pending rebuild is for the developer too (381): on screen, and the agent keeps its copy.
    sent = json.loads(out)
    line = state.PREFIX + _summary(project)
    assert line.startswith(state.PREFIX + "rebuild required")
    assert sent["systemMessage"] == line
    assert sent["hookSpecificOutput"]["additionalContext"] == line


def test_a_running_build_is_named_with_its_live_phase_and_route(project: Path) -> None:
    """AC1 — the lock is held: the line carries the phase and `code-atlas-build --status`."""
    db = config_for(project).db_path
    with try_index_write_lock(db) as held:
        assert held
        publish_build_progress(db, "phase=parse done=7 total=19000 pid=1")
        line = state.state_line(project)
    assert line is not None
    assert "phase=parse done=7 total=19000" in line
    assert "code-atlas-build --status" in line


def test_without_a_build_the_line_never_mentions_one(project: Path) -> None:
    """AC1 — behind with no build: the summary alone, no build words."""
    _behind(project)
    line = state.state_line(project)
    assert line is not None and "behind" in line
    assert "build is running" not in line and "--status" not in line


def test_a_current_index_with_no_build_is_silent(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC2 red arm — current and idle prints nothing; the same hook fires once HEAD moves."""
    assert state.state_line(project) is None
    assert _run(monkeypatch, capsys, _event("SessionStart")) == (0, "")
    _behind(project)
    code, out = _run(monkeypatch, capsys, _event("SessionStart"))
    assert code == 0 and out.startswith(state.PREFIX), "the silence must not be vacuous"


def test_the_line_lifts_get_index_status_summary_byte_for_byte(project: Path) -> None:
    """AC3 — one composition site, asserted: prefix + the tool's own summary, nothing rebuilt."""
    _behind(project)
    assert state.state_line(project) == state.PREFIX + _summary(project)
    db = config_for(project).db_path
    with try_index_write_lock(db) as held:
        assert held
        line = state.state_line(project)
        summary = _summary(project)
    assert line is not None and line.startswith(state.PREFIX + summary + " · ")


@pytest.mark.parametrize("event", ["SessionStart", "PreCompact", "PostCompact"])
def test_each_named_occasion_fires(
    event: str, project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scope 4 — the three occasions the ticket names, and only those (next test)."""
    _behind(project)
    code, out = _run(monkeypatch, capsys, _event(event))
    assert code == 0 and out.strip() == state.PREFIX + _summary(project)


@pytest.mark.parametrize("event", ["UserPromptSubmit", "PostToolUse", "SubagentStart", None])
def test_any_other_occasion_is_silent(
    event: str | None,
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Scope 4 / R1.2 — per-turn re-injection needs its own evidence first."""
    _behind(project)
    assert _run(monkeypatch, capsys, json.dumps({"hook_event_name": event})) == (0, "")


def test_broken_stdin_absent_index_and_unreadable_db_exit_zero_silent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC4 — every failure is exit 0 with nothing on stdout."""
    db = tmp_path / ".code-atlas" / "graph.db"
    monkeypatch.setenv("CA_DB_PATH", str(db))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    assert _run(monkeypatch, capsys, "{not json") == (0, "")
    assert _run(monkeypatch, capsys, "[]") == (0, "")
    assert _run(monkeypatch, capsys, _event("SessionStart")) == (0, "")  # absent index
    assert not db.exists(), "an absent index must not be created by asking about it"
    db.parent.mkdir(parents=True)
    db.write_bytes(b"")
    assert _run(monkeypatch, capsys, _event("SessionStart")) == (0, "")
    assert db.stat().st_size == 0, "an empty file must not be initialised by the hook"
    db.write_bytes(b"this is not a sqlite database" * 64)
    assert _run(monkeypatch, capsys, _event("SessionStart")) == (0, "")


def test_a_held_database_lock_exits_zero_silent(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC4 — a writer holding SQLite exclusively: the read fails, the hook stays silent."""
    _behind(project)
    holder = sqlite3.connect(config_for(project).db_path)
    holder.execute("PRAGMA locking_mode=EXCLUSIVE")
    holder.execute("BEGIN EXCLUSIVE")
    try:
        assert _run(monkeypatch, capsys, _event("SessionStart")) == (0, "")
    finally:
        holder.rollback()
        holder.close()


def test_the_line_stays_under_its_budget_even_with_a_long_phase(project: Path) -> None:
    """AC5 — measured by `tokens.estimate_tokens`; an over-long phase is dropped, the route kept."""
    _behind(project)
    db = config_for(project).db_path
    with try_index_write_lock(db) as held:
        assert held
        publish_build_progress(db, "phase=parse " + "x" * 2000)
        long_phase = state.state_line(project)
        publish_build_progress(db, "phase=resolve done=9 total=9 pid=1")
        short_phase = state.state_line(project)
    for line in (long_phase, short_phase):
        assert line is not None and estimate_tokens(line) <= state.TOKEN_BUDGET, line
    assert long_phase is not None and "code-atlas-build --status" in long_phase
    assert short_phase is not None and "phase=resolve" in short_phase


def test_the_command_is_shipped_and_offered_opt_in() -> None:
    """Scope 1 / 8 — a console script, wired only by the generated snippet a host copies."""
    scripts = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    assert scripts["project"]["scripts"]["code-atlas-state"] == "code_atlas.hooks.state:main"
    snippet = json.loads((REPO / "contrib" / "claude-code" / "settings.snippet.json").read_text())
    for event in ("SessionStart", "PreCompact"):
        commands = [
            h["command"].rpartition("; exec ")[2]
            for entry in snippet["hooks"][event]
            for h in entry["hooks"]
        ]
        # 348: the command carries the release it was generated from, for the skew line.
        assert [c.split()[0] for c in commands] == ["code-atlas-state"], event
