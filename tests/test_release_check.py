"""Task 401 — an install a tagged release behind is told by the plugin; the core stays offline.

The newest release is the highest `vX.Y.Z` tag on the remote (381). An async hook caches it at most
once a day; a sync hook reads only that cache and speaks when it is newer than the plugin's release.
Both exit 0 with nothing on stdout on any failure.
"""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

import release_check
from code_atlas.hooks import state

START = json.dumps({"hook_event_name": "SessionStart"})


@pytest.fixture(autouse=True)
def cache_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(home))
    monkeypatch.delenv(release_check.OPT_OUT, raising=False)
    return home


def _remote(tmp_path: Path, tags: list[str]) -> str:
    repo = tmp_path / "remote"
    repo.mkdir()
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "r"], check=True)
    for tag in tags:
        subprocess.run([*git, "tag", "-a", tag, "-m", tag], check=True)
    return str(repo)


def _cache(latest: str, checked_at: float) -> None:
    path = release_check.cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"checked_at": checked_at, "latest": latest}), encoding="utf-8")


def _main(args: list[str], stdin: str, monkeypatch: pytest.MonkeyPatch) -> str:
    out = io.StringIO()
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    monkeypatch.setattr("sys.stdout", out)
    assert release_check.main(args) == 0
    return out.getvalue()


def test_the_newest_tag_is_numeric_and_ignores_non_releases() -> None:
    listing = "\n".join(
        f"abc\trefs/tags/{t}" for t in ("v0.2.0", "v0.10.0", "v0.9.1", "v1.0.0-rc1", "latest")
    )
    assert release_check.newest_tag(listing) == "0.10.0"
    assert release_check.newest_tag("abc\trefs/tags/nightly\n") is None


def test_fetch_caches_the_remote_s_newest_release(tmp_path: Path) -> None:
    remote = _remote(tmp_path, ["v0.2.0", "v0.10.0", "v0.9.1"])
    assert release_check.fetch(remote, now=1_000_000) == "0.10.0"
    cached = json.loads(release_check.cache_path().read_text(encoding="utf-8"))
    assert cached == {"checked_at": 1_000_000, "latest": "0.10.0", "remote": remote}


def test_fetch_stays_off_the_network_inside_a_day(tmp_path: Path) -> None:
    """A fresh cache means no listing — a remote that cannot exist proves `git` was not run."""
    _cache("0.5.0", checked_at=1_000_000)
    missing = str(tmp_path / "no-such-remote")
    assert release_check.fetch(missing, now=1_000_000 + release_check.CHECK_INTERVAL_S - 1) is None
    with pytest.raises(subprocess.CalledProcessError):
        release_check.fetch(missing, now=1_000_000 + release_check.CHECK_INTERVAL_S)


@pytest.mark.parametrize(
    ("latest", "expected", "speaks"),
    [("0.6.0", "0.5.0", True), ("0.5.0", "0.5.0", False), ("0.4.0", "0.5.0", False)],
)
def test_the_line_speaks_only_for_a_newer_release(latest: str, expected: str, speaks: bool) -> None:
    _cache(latest, checked_at=0)
    line = release_check.release_line(expected)
    assert (line is not None) == speaks
    if line:
        assert line.startswith(state.PREFIX) and latest in line and state.UPGRADING_POINTER in line


def test_the_session_start_hook_puts_the_line_on_screen(monkeypatch: pytest.MonkeyPatch) -> None:
    """R6.9: assert what the host reads — `systemMessage` for the person, context for the agent."""
    _cache("0.6.0", checked_at=0)
    sent = json.loads(_main([state.EXPECT_FLAG, "0.5.0"], START, monkeypatch))
    line = release_check.release_line("0.5.0")
    assert sent == {
        "systemMessage": line,
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": line},
    }
    assert sent["systemMessage"].isascii()


@pytest.mark.parametrize(
    ("args", "stdin", "env"),
    [
        ([state.EXPECT_FLAG, "0.5.0"], json.dumps({"hook_event_name": "PreCompact"}), None),
        ([state.EXPECT_FLAG, "0.5.0"], "not json", None),
        ([state.EXPECT_FLAG, "0.5.0"], START, "0"),
        ([release_check.FETCH_FLAG, "/no/such/remote"], "", None),
    ],
    ids=["other-event", "broken-stdin", "opted-out", "offline-fetch"],
)
def test_every_other_path_is_silent(
    args: list[str], stdin: str, env: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _cache("0.6.0", checked_at=0)
    if env is not None:
        monkeypatch.setenv(release_check.OPT_OUT, env)
    assert _main(args, stdin, monkeypatch) == ""


def test_an_unreadable_cache_is_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    path = release_check.cache_path()
    path.parent.mkdir(parents=True)
    path.write_text("{", encoding="utf-8")
    assert _main([state.EXPECT_FLAG, "0.5.0"], START, monkeypatch) == ""
