"""340 — a commit's author and committer identity is checked the way 325 checks the tree.

Each planted marker is assembled at runtime, so this file never holds the string it detects
(325 finding 5). The repos are throwaway `git init`s under `tmp_path`.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from scripts.identity_markers import commit_identity_offences, main

CLEAN = ("Maintainer", "someone@" + "gmail.com")
MERGE_BOT = ("GitHub", "noreply@" + "github.com")
LOGON = "BIGCORP" + "\\" + "j.doe"
CORP_EMAIL = "j.doe@" + "acme" + ".com" + ".au"


def _commit(repo: Path, author: tuple[str, str], committer: tuple[str, str]) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": author[0],
        "GIT_AUTHOR_EMAIL": author[1],
        "GIT_COMMITTER_NAME": committer[0],
        "GIT_COMMITTER_EMAIL": committer[1],
    }
    subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "-m", "x"], cwd=repo, env=env, check=True
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    _commit(tmp_path, CLEAN, CLEAN)
    return tmp_path


def test_a_logon_shaped_author_name_is_named_by_commit(repo: Path) -> None:
    """AC1 — red before 340: nothing read `%an`."""
    sha = _commit(repo, (LOGON, CLEAN[1]), CLEAN)
    count, offences = commit_identity_offences("HEAD~1..HEAD", repo)
    assert count == 1
    assert offences == [f"{sha[:12]} author name: a Windows domain logon"]
    assert all(LOGON not in line for line in offences), "the offence must not echo the value"


def test_a_corporate_committer_email_is_named_by_commit(repo: Path) -> None:
    """AC2 — trips the corporate-domain and the allowlist arms, and nothing else."""
    sha = _commit(repo, CLEAN, (CLEAN[0], CORP_EMAIL))
    _, offences = commit_identity_offences("HEAD~1..HEAD", repo)
    assert sorted(offences) == [
        f"{sha[:12]} committer email: corporate domain",
        f"{sha[:12]} committer email: email outside the allowed domains",
    ]


def test_clean_commits_and_the_merge_bot_pass(repo: Path) -> None:
    """AC3 — the maintainer's public identity and GitHub's merge identity are not offences."""
    _commit(repo, CLEAN, MERGE_BOT)
    _commit(repo, ("Bot", "1+bot@users.noreply" + ".github.com"), CLEAN)
    count, offences = commit_identity_offences("HEAD~2..HEAD", repo)
    assert (count, offences) == (2, [])


def test_an_empty_range_fails_rather_than_passing() -> None:
    """AC4 — R6.5: zero commits read is not a clean result."""
    assert main(["HEAD..HEAD"]) == 2


def test_an_unreadable_range_fails_rather_than_passing() -> None:
    assert main(["no-such-ref-340..HEAD"]) == 2


def test_the_cli_exits_one_on_an_offence_and_zero_when_clean(repo: Path) -> None:
    """The exit code CI and gate.sh act on, not only the list."""
    _commit(repo, CLEAN, MERGE_BOT)
    assert main(["HEAD~1..HEAD"], repo) == 0
    _commit(repo, (LOGON, CLEAN[1]), CLEAN)
    assert main(["HEAD~1..HEAD"], repo) == 1
