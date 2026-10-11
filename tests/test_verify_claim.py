"""Task 383 — a signed claim re-run from a shell: ``holds``, ``changed`` or ``unverifiable``.

The claims are signed through the shell route itself, then verified by ``code-atlas query
--verify-claim`` against the same index — or against one a fixture change has moved, which is the
case a pasted claim exists to catch.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from code_atlas import query
from code_atlas.config import Config, load_config
from code_atlas.store import LAST_COMMIT_KEY, GraphStore
from code_atlas.tools import (
    claim,
    find_callers,
    find_references,
    get_index_status,
    impact,
    impact_modules,
)
from tests.test_claim_signing import CALLER, OWNER, SOURCE, SUBJECT, indexed_repo
from tests.test_incremental import committed, git
from tests.test_nav_tools import edge, node

# One signing call per tool that publishes ``sign`` (100); test_claim_signing pins that set.
SIGNED_CALLS: dict[str, dict[str, object]] = {
    impact.NAME: {"qnames": [SUBJECT]},
    impact_modules.NAME: {"paths": [SOURCE]},
    find_callers.NAME: {"qname": SUBJECT},
    find_references.NAME: {"qname": SUBJECT},
    get_index_status.NAME: {"detail_level": "minimal"},
}

SECOND = "src/b.php"
SECOND_CALLER = "\\App\\Job::run"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Config]:
    root = tmp_path / "repo"
    call = edge("CALLS", CALLER, "save", SOURCE, target_qname=SUBJECT)
    db_path = indexed_repo(root, edges=[call])
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setenv("CA_DB_PATH", str(db_path))
    return root, load_config(root)


def shell(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, list[Any]]:
    code = query.main(list(argv))
    out, _ = capsys.readouterr()
    return code, [json.loads(line) for line in out.splitlines() if line.strip()]


def signed(capsys: pytest.CaptureFixture[str], tool: str, args: dict[str, object]) -> str:
    code, [payload] = shell(capsys, tool, "--args", json.dumps({**args, "sign": True}))
    assert code == query.OK
    return str(payload[claim.CLAIM_KEY])


def verify(capsys: pytest.CaptureFixture[str], line: str) -> tuple[int, dict[str, Any]]:
    code, [verdict] = shell(capsys, "--verify-claim", line)
    return code, verdict


def add_caller(root: Path, config: Config) -> None:
    """A second committed file whose method calls the subject, indexed at the new HEAD."""
    committed(root, {SECOND: "<?php class Job {}\n"}, "add a caller")
    digest = hashlib.sha256((root / SECOND).read_bytes()).hexdigest()
    with GraphStore(config.db_path) as store:
        store.upsert_file(SECOND, digest, "php")
        store.replace_file_rows(
            SECOND,
            [node("Method", "run", SECOND_CALLER, SECOND)],
            [edge("CALLS", SECOND_CALLER, "save", SECOND, target_qname=SUBJECT)],
        )
        store.set_meta(LAST_COMMIT_KEY, git(root, "rev-parse", "HEAD"))


def drop_subject(config: Config) -> None:
    """The subject's method is gone from the index; its class and caller remain."""
    with GraphStore(config.db_path) as store:
        store.replace_file_rows(
            SOURCE,
            [
                node("Class", "UserRepo", OWNER, SOURCE),
                node("Method", "store", CALLER, SOURCE),
            ],
            [],
        )


@pytest.mark.parametrize("tool", sorted(SIGNED_CALLS))
def test_a_claim_reverified_at_its_own_revision_holds(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str], tool: str
) -> None:
    """AC1 (proving test): each of the five signing tools, signed at rev A and re-run at rev A."""
    line = signed(capsys, tool, SIGNED_CALLS[tool])
    code, verdict = verify(capsys, line)

    assert verdict["status"] == query.HOLDS, verdict
    assert code == query.OK
    assert verdict["then"] == verdict["now"]
    assert verdict["then"]["answer"]  # positive control: an asserted key was compared
    assert verdict["rev_then"] == verdict["rev_now"]
    assert "changed" not in verdict


def test_the_line_carries_the_call_that_rebuilds_it(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    """Scope 1: the truncated ``subject`` is display; ``call`` is the full question."""
    paths = [SOURCE, "src/x.php", "src/y.php", "src/z.php"]
    line = signed(capsys, impact.NAME, {"paths": paths, "depth": 3})
    [found] = claim.find_claims(line)

    assert found.schema == claim.CLAIM_SCHEMA
    assert found.fields["subject"].endswith(",+1")
    assert json.loads(found.fields[claim.CALL_KEY]) == {"paths": paths, "depth": 3}


def test_an_added_caller_makes_the_find_callers_claim_change_on_answer(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    """AC2: one more caller moves ``answer``; the verdict names it and both revisions."""
    root, config = repo
    line = signed(capsys, find_callers.NAME, {"qname": SUBJECT})
    add_caller(root, config)
    code, verdict = verify(capsys, line)

    assert verdict["status"] == query.CHANGED
    assert code == query.NOT_HELD
    assert "answer" in verdict["changed"]
    assert (verdict["then"]["answer"], verdict["now"]["answer"]) == ("1", "2")
    assert verdict["rev_now"] != verdict["rev_then"]


@pytest.mark.parametrize("tool", [find_callers.NAME, impact.NAME])
def test_a_subject_that_no_longer_resolves_changes_with_the_tools_reason(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str], tool: str
) -> None:
    """AC3: ``changed`` with the tool's ``reason`` — never ``holds``, never a crash. ``impact``
    signs nothing for a lost subject, so its verdict is built from the payload's reason."""
    _, config = repo
    line = signed(capsys, tool, SIGNED_CALLS[tool])
    drop_subject(config)
    code, verdict = verify(capsys, line)

    assert verdict["status"] == query.CHANGED
    assert code == query.NOT_HELD
    assert "reason" in verdict["changed"]
    assert verdict["now"]["reason"] == "no_such_symbol"


def test_verify_claims_finds_exactly_the_claims_in_a_markdown_page(
    repo: tuple[Path, Config], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC4: three claims — fenced, inline code, bare — amid prose that names the format."""
    lines = [signed(capsys, tool, SIGNED_CALLS[tool]) for tool in (
        find_callers.NAME, impact.NAME, get_index_status.NAME)]
    page = tmp_path / "notes.md"
    page.write_text(
        "# Save path\n\nClaims use the code-atlas/2 format; a line names its tool.\n\n"
        f"```\n{lines[0]}\n```\n\n"
        f"The radius is `{lines[1]}` as of the release.\n\n"
        f"{lines[2]}\n\nSee also code-atlas/1, the older format.\n",
        encoding="utf-8",
    )
    code, verdicts = shell(capsys, "--verify-claims", str(page))

    assert [verdict["tool"] for verdict in verdicts] == [
        find_callers.NAME, impact.NAME, get_index_status.NAME]
    assert [verdict["source"] for verdict in verdicts] == [
        f"{page}:6", f"{page}:9", f"{page}:11"]
    assert {verdict["status"] for verdict in verdicts} == {query.HOLDS}
    assert code == query.OK


def test_an_older_format_claim_is_unverifiable_and_names_its_version(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    """Design assumption: a ``code-atlas/1`` line carries no call, so it is never a ``holds``."""
    current = signed(capsys, find_callers.NAME, {"qname": SUBJECT})
    older = "code-atlas/1 " + current.split(" ", 1)[1].rsplit(" call=", 1)[0]
    code, verdict = verify(capsys, older)

    assert verify(capsys, current)[1]["status"] == query.HOLDS  # positive control
    assert verdict["status"] == query.UNVERIFIABLE
    assert (verdict["reason"], verdict["format"]) == ("claim_format", "code-atlas/1")
    assert code == query.NOT_HELD


def test_a_claim_with_no_readable_call_is_unverifiable(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    current = signed(capsys, find_callers.NAME, {"qname": SUBJECT})
    _, verdict = verify(capsys, current.rsplit(" call=", 1)[0])

    assert (verdict["status"], verdict["reason"]) == (query.UNVERIFIABLE, "call_unreadable")


def test_a_line_that_asserts_nothing_is_never_a_holds(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    """Challenger finding 3: a hand-trimmed line compares nothing, so it cannot hold."""
    current = signed(capsys, find_callers.NAME, {"qname": SUBJECT})
    call = current[current.index(" call="):]
    _, verdict = verify(capsys, f"code-atlas/2 tool={find_callers.NAME}{call}")

    assert (verdict["status"], verdict["reason"]) == (query.UNVERIFIABLE, "nothing_asserted")


def test_a_value_with_a_backtick_round_trips() -> None:
    """Challenger finding 1: a bare value stopped at a backtick, so one is quoted now."""
    payload = claim.sign(
        {"results": [], "total_count": 0},
        tool=find_callers.NAME,
        question=find_callers.QUESTION,
        subject_parts=["`users`"],
        staleness={},
        call={"qname": "`users`"},
    )
    [found] = claim.find_claims(str(payload[claim.CLAIM_KEY]))

    assert found.fields["subject"] == "`users`"
    assert json.loads(found.fields[claim.CALL_KEY]) == {"qname": "`users`"}


def test_a_re_run_never_replays_a_counter_reset(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    args = {"reset_fit_counts": True, "detail_level": "minimal"}
    line = signed(capsys, get_index_status.NAME, args)
    [found] = claim.find_claims(line)

    assert json.loads(found.fields[claim.CALL_KEY]) == {"detail_level": "minimal"}


def test_a_hand_edited_call_that_would_write_is_refused(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    """A scanned page is untrusted input: a forged ``reset_fit_counts`` is never replayed."""
    line = signed(capsys, get_index_status.NAME, {"detail_level": "minimal"})
    forged = line.replace('call="{', 'call="{""reset_fit_counts"":true,')
    _, verdict = verify(capsys, forged)

    assert verify(capsys, line)[1]["status"] == query.HOLDS  # positive control
    assert (verdict["status"], verdict["reason"]) == (query.UNVERIFIABLE, "call_rejected")


def test_a_verdict_names_the_index_state_it_was_answered_on(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    """A ``holds`` on a behind index is about the indexed tree; ``index_now`` says so."""
    root, _ = repo
    line = signed(capsys, impact.NAME, SIGNED_CALLS[impact.NAME])
    current = verify(capsys, line)[1]
    committed(root, {"src/c.php": "<?php class C {}\n"}, "move HEAD past the index")
    behind = verify(capsys, line)[1]

    assert current["index_now"] == "current"  # positive control
    assert (behind["status"], behind["index_now"]) == (query.HOLDS, "behind")


def test_verify_takes_exactly_one_mode(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as raised:
        query.main(["find_callers", "--verify-claim", "x"])
    assert raised.value.code == query.USAGE
    code, _ = shell(capsys, "--verify-claim", "no claim in this text")
    assert code == query.USAGE
