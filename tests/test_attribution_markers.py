"""R7.3 — a commit message carrying any attribution marker is caught, by the one shared script.

Red before the fix: CI and gate.sh grepped `co-authored-by:|generated with|🤖`, so four commits
with a `Claude-Session:` trailer and its session link passed both. Each marker is assembled at
runtime, so this file never holds a string it detects. The repos are throwaway `git init`s.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.attribution_markers import commit_attribution_offences, main, message_offences

SESSION_URL = "https://claude.ai" + "/code/session_" + "0" * 24
# The shape that got through: a normal message whose last line is the session trailer.
LEAKED = "feat(188): an edge is linked\n\nBody.\n\nClaude" + f"-Session: {SESSION_URL}\n"


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (LEAKED, ["attribution trailer", "an assistant session link"]),
        ("fix: x\n\nCo-" + "authored-by: A <a@example.com>\n", ["attribution trailer"]),
        ("fix: x\n\nGenerated-" + "with: a tool\n", ["attribution trailer"]),
        (
            "fix: x\n\n\U0001f916 Generated " + "with a tool\n",
            ["a generated-with line", "the robot emoji"],
        ),
        (f"fix: x\n\nsee {SESSION_URL}\n", ["an assistant session link"]),
    ],
)
def test_every_attribution_shape_is_named(message: str, expected: list[str]) -> None:
    assert message_offences(message) == expected


def test_prose_about_the_rule_is_not_a_trailer() -> None:
    """A message may say what R7.3 bans; only a key at the start of a line is a trailer."""
    message = "docs: R7.3 bans a Co-" + "authored-by: or Claude-" + "Session: trailer\n"
    assert message_offences(message) == []


def _commit(repo: Path, message: str) -> str:
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", message], cwd=repo, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    for key, value in (("user.name", "Maintainer"), ("user.email", "someone@example.com")):
        subprocess.run(["git", "config", key, value], cwd=tmp_path, check=True)
    _commit(tmp_path, "chore: root")
    return tmp_path


def test_the_leaked_shape_is_named_by_commit_without_echoing_the_link(repo: Path) -> None:
    clean = _commit(repo, "fix: clean\n\nA body with several lines.\n")
    leaked = _commit(repo, LEAKED)
    count, offences = commit_attribution_offences("HEAD~2..HEAD", repo)
    assert count == 2
    assert offences == [
        f"{leaked[:12]}: attribution trailer",
        f"{leaked[:12]}: an assistant session link",
    ]
    assert all(clean[:12] not in line for line in offences)
    assert all(SESSION_URL not in line for line in offences), "the offence must not echo the link"


def test_the_cli_exits_one_on_an_offence_and_zero_when_clean(repo: Path) -> None:
    """The exit code CI and gate.sh act on, not only the list."""
    _commit(repo, "fix: clean\n")
    assert main(["HEAD~1..HEAD"], repo) == 0
    _commit(repo, LEAKED)
    assert main(["HEAD~1..HEAD"], repo) == 1


def test_an_empty_or_unreadable_range_fails_rather_than_passing(repo: Path) -> None:
    """R6.5: zero commits read is not a clean result."""
    assert main(["HEAD..HEAD"], repo) == 2
    assert main(["no-such-ref..HEAD"], repo) == 2
