"""Task 381 AC2 / AC4 — the session-start line a person must act on reaches the person.

SessionStart stdout reaches only the agent, so the anchor's skew line fired and nobody read it.
The hook now answers JSON: `systemMessage` for the developer, `additionalContext` with every line
for the agent. 427 removed the "pinned install" line: it told a user to unpin.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from code_atlas.hooks import state
from tests.test_session_state_hook import project  # noqa: F401 — the indexed, current fixture


def _run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], event: str, *args: str
) -> str:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"hook_event_name": event})))
    assert state.main(list(args)) == 0
    return capsys.readouterr().out


def test_the_skew_line_reaches_the_screen_and_the_agent(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC2: hooks a release behind the tool — on screen, and the agent keeps its copy."""
    sent = json.loads(_run(monkeypatch, capsys, "SessionStart", "--expect-version", "0.0.1"))
    skew = sent["systemMessage"]
    assert skew.startswith(state.PREFIX + "hooks expect code-atlas 0.0.1")
    assert sent["hookSpecificOutput"] == {
        "hookEventName": "SessionStart",
        "additionalContext": skew,
    }


def test_precompact_keeps_plain_text(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Claude Code discards a PreCompact hook's `systemMessage`, so it stays the plain line."""
    out = _run(monkeypatch, capsys, "PreCompact", "--expect-version", "0.0.1")
    assert out.startswith(state.PREFIX + "hooks expect code-atlas 0.0.1")


def test_a_current_install_stays_silent(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _run(monkeypatch, capsys, "SessionStart") == ""
