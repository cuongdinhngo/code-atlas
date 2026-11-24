"""Task 454: the grep guard — a symbol grep meets a nudge or a refusal before it answers."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.hooks import guard, state
from code_atlas.setup_hooks import decline, record_path
from code_atlas.store import LAST_COMMIT_KEY, SYMBOL_SHAPES_BY_LANGUAGE_KEY, GraphStore
from tests.contract.adapter_registry import REGISTRY

pytestmark = [REGISTRY["python"].cli.availability]
TOOL = "mcp__plugin_code-atlas_code-atlas__search_symbol"


def _git(root: Path, *command: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.email=t@e", "-c", "user.name=t", *command],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """An index current at HEAD carrying the Python adapter's own stamped shapes (345)."""
    meta = REGISTRY["python"].cli.handshake()
    shapes = {meta["name"]: {"extensions": meta["extensions"], "shapes": meta["symbol_shapes"]}}
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "seed")
    with GraphStore(load_config(tmp_path).db_path) as store:
        store.set_meta(SYMBOL_SHAPES_BY_LANGUAGE_KEY, json.dumps(shapes, sort_keys=True))
        store.set_meta(LAST_COMMIT_KEY, _git(tmp_path, "rev-parse", "HEAD"))
    decline(tmp_path)
    return tmp_path


def _mode(root: Path, mode: str) -> None:
    record = json.loads(record_path(root).read_text(encoding="utf-8"))
    record_path(root).write_text(json.dumps({**record, "guard": mode}), encoding="utf-8")


def _transcript(root: Path, *calls: tuple[str, dict[str, object], bool]) -> Path:
    path = root / "transcript.jsonl"
    rows = []
    for number, (tool, tool_input, failed) in enumerate(calls):
        use = {"type": "tool_use", "id": f"t{number}", "name": tool, "input": tool_input}
        rows.append({"message": {"role": "assistant", "content": [use]}})
        result = {
            "type": "tool_result",
            "tool_use_id": f"t{number}",
            "is_error": failed,
            "content": "connection refused" if failed else "ok",
        }
        rows.append({"message": {"role": "user", "content": [result]}})
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def _payload(command: str, transcript: Path, session: str = "s1") -> dict[str, object]:
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "session_id": session,
        "transcript_path": str(transcript),
    }


def _decision(out: str | None) -> str | None:
    if out is None:
        return None
    return json.loads(out)["hookSpecificOutput"].get("permissionDecision", "context")


def test_ac1_refused_then_nudged_then_allowed_once_asked(root: Path) -> None:
    empty = _transcript(root)
    _mode(root, "refuse")
    out = guard.guard(root, _payload('grep -rn "def foo" .', empty))
    assert _decision(out) == "deny" and "foo" in json.dumps(json.loads(str(out)))
    _mode(root, "nudge")
    assert _decision(guard.guard(root, _payload('grep -rn "def foo" .', empty))) == "context"
    _mode(root, "refuse")
    asked = _transcript(root, (TOOL, {"query": "foo"}, False))
    assert guard.guard(root, _payload('grep -rn "def foo" .', asked)) is None


def test_ac1_a_failed_server_lifts_the_refusal_and_a_bad_argument_does_not(root: Path) -> None:
    _mode(root, "refuse")
    down = _transcript(root, (TOOL, {"query": "other"}, True))
    assert guard.guard(root, _payload('grep -rn "def foo" .', down)) is None
    path = root / "bad.jsonl"
    use = {"type": "tool_use", "id": "a", "name": TOOL, "input": {"query": "other"}}
    bad = {
        "type": "tool_result",
        "tool_use_id": "a",
        "is_error": True,
        "content": "invalid argument: query",
    }
    rows = (json.dumps({"message": {"content": [x]}}) for x in (use, bad))
    path.write_text("\n".join(rows), "utf-8")
    assert _decision(guard.guard(root, _payload('grep -rn "def foo" .', path))) == "deny"


def test_ac2_a_literal_text_grep_is_never_touched(root: Path) -> None:
    _mode(root, "refuse")
    empty = _transcript(root)
    for command in ('grep -rn "TODO: remove" .', "grep -rn 'api_key' config/", "git status"):
        assert guard.guard(root, _payload(command, empty)) is None


def test_off_mode_says_nothing(root: Path) -> None:
    _mode(root, "off")
    assert guard.guard(root, _payload('grep -rn "def foo" .', _transcript(root))) is None


def test_ac3_the_guard_decides_in_under_50_ms(root: Path) -> None:
    _mode(root, "refuse")
    empty = _transcript(root)
    guard.guard(root, _payload('grep -rn "def foo" .', empty))  # warm imports
    runs = []
    for _ in range(5):
        start = time.perf_counter()
        guard.guard(root, _payload('grep -rn "def foo" .', empty))
        runs.append(time.perf_counter() - start)
    assert sorted(runs)[2] < 0.050, runs


def test_the_session_reminder_rides_a_settled_index(root: Path) -> None:
    assert state.state_line(root) is None
    assert state.state_line(root, remind=True) == state.REMINDER


def test_a_rebuild_required_error_lifts_the_refusal(root: Path) -> None:
    """Challenger F2: "required" in a server's refusal is an outage, not a bad argument."""
    _mode(root, "refuse")
    path = root / "skew.jsonl"
    use = {"type": "tool_use", "id": "a", "name": TOOL, "input": {"query": "other"}}
    refused = {
        "type": "tool_result",
        "tool_use_id": "a",
        "is_error": True,
        "content": "rebuild required: index contract 20, server 21",
    }
    path.write_text("\n".join(json.dumps({"message": {"content": [x]}}) for x in (use, refused)))
    assert guard.guard(root, _payload('grep -rn "def foo" .', path)) is None


def test_start_refresh_spawns_the_script_detached(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Challenger F5: the real spawn — argv, cwd and the log — with a stand-in script."""
    marker = root / "ran.txt"
    script = root / "fake-refresh"
    script.write_text(f'#!/bin/sh\necho "$@" > {marker}\necho to-log >&2\n', encoding="utf-8")
    script.chmod(0o755)
    from code_atlas import setup_hooks

    monkeypatch.setattr(setup_hooks, "refresh_command", lambda: str(script))
    assert state.start_refresh(root)
    deadline = time.monotonic() + 10
    while not marker.is_file() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert marker.read_text(encoding="utf-8").strip() == "--trigger session-start"
    log = root / ".code-atlas" / "refresh.log"
    while "to-log" not in log.read_text(encoding="utf-8") and time.monotonic() < deadline:
        time.sleep(0.1)
    assert "to-log" in log.read_text(encoding="utf-8")
