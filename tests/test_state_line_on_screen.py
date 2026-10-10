"""Task 381 AC2 / AC4 — the session-start line a person must act on reaches the person.

SessionStart stdout reaches only the agent, so the anchor's skew line fired and nobody read it.
The hook now answers JSON: `systemMessage` for the developer, `additionalContext` with every line
for the agent. A uv tool install pinned to one commit, which `uv tool upgrade` never moves, is
named too.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from code_atlas.hooks import state
from tests.test_session_state_hook import project  # noqa: F401 — the indexed, current fixture

URL = "https://github.com/cuongdinhngo/code-atlas.git"
UNPINNED = f"`uv tool install --force git+{URL}`"


def _receipt(prefix: Path, git: str, name: str = "code-atlas") -> Path:
    prefix.mkdir(parents=True, exist_ok=True)
    (prefix / state.RECEIPT).write_text(
        f'[tool]\nrequirements = [{{ name = "{name}", git = "{git}" }}]\n', encoding="utf-8"
    )
    return prefix


def _run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], event: str, *args: str
) -> str:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"hook_event_name": event})))
    assert state.main(list(args)) == 0
    return capsys.readouterr().out


@pytest.mark.parametrize("pin", ["rev=54242f1", "tag=v0.3.0"])
def test_a_pinned_install_is_named_with_the_unpinned_command(tmp_path: Path, pin: str) -> None:
    """AC4: the receipt's pin and the reinstall that frees it, from the receipt's own URL."""
    line = state.pinned_line(_receipt(tmp_path, f"{URL}?{pin}"))
    assert line is not None
    assert f"`{pin}`" in line and UNPINNED in line


@pytest.mark.parametrize(
    "receipt",
    [None, URL, f"{URL}?branch=main"],
    ids=["no receipt (pipx, a checkout)", "unpinned", "a branch moves on upgrade"],
)
def test_an_unpinned_install_is_silent(tmp_path: Path, receipt: str | None) -> None:
    """AC4: silent for an unpinned install, and for one uv did not make."""
    prefix = tmp_path if receipt is None else _receipt(tmp_path, receipt)
    assert state.pinned_line(prefix) is None


def test_another_tools_pin_is_not_ours(tmp_path: Path) -> None:
    assert state.pinned_line(_receipt(tmp_path, f"{URL}?rev=abc", name="other-tool")) is None


def test_the_skew_line_reaches_the_screen_and_the_agent(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC2: hooks a release behind the tool — on screen, and the agent keeps its copy."""
    monkeypatch.setattr(sys, "prefix", str(project / "no-receipt"))
    sent = json.loads(_run(monkeypatch, capsys, "SessionStart", "--expect-version", "0.0.1"))
    skew = sent["systemMessage"]
    assert skew.startswith(state.PREFIX + "hooks expect code-atlas 0.0.1")
    assert sent["hookSpecificOutput"] == {
        "hookEventName": "SessionStart",
        "additionalContext": skew,
    }


def test_a_pinned_install_reaches_the_screen(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "prefix", str(_receipt(project / "tool", f"{URL}?rev=54242f1")))
    sent = json.loads(_run(monkeypatch, capsys, "SessionStart"))
    assert "`rev=54242f1`" in sent["systemMessage"]


def test_precompact_keeps_plain_text(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Claude Code discards a PreCompact hook's `systemMessage`, so it stays the plain line."""
    monkeypatch.setattr(sys, "prefix", str(project / "no-receipt"))
    out = _run(monkeypatch, capsys, "PreCompact", "--expect-version", "0.0.1")
    assert out.startswith(state.PREFIX + "hooks expect code-atlas 0.0.1")


def test_a_current_unpinned_install_stays_silent(
    project: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "prefix", str(_receipt(project / "tool", URL)))
    assert _run(monkeypatch, capsys, "SessionStart") == ""
