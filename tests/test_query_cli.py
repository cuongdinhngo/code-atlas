"""Task 382 — ``code-atlas query``: the read tools from a shell, payload-equal to the MCP route.

A deterministic consumer (a script anchoring records to code, a CI check) needs answers and no
model. The proof compares parsed JSON from the shell with the MCP client's payload for the same
arguments on the same index — equality, not "similar".
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from code_atlas import query
from code_atlas.config import Config, load_config
from code_atlas.index_lock import try_index_write_lock
from code_atlas.main import TOOL_NAMES, build_server
from code_atlas.store import GraphStore
from code_atlas.tools import build_or_update_index, generate_onboarding
from tests.test_claim_signing import CALLER, OWNER, SOURCE, SUBJECT, indexed_repo
from tests.test_nav_tools import edge

REPO = Path(__file__).resolve().parent.parent
READ_TOOLS = tuple(name for name in TOOL_NAMES if name not in query.REFUSED_TOOLS)

# One argument set per read tool, aimed at rows the fixture holds so most answers are non-empty.
ARGS: dict[str, dict[str, object]] = {
    "get_index_status": {},
    "search_symbol": {"query": "save"},
    "file_outline": {"path": SOURCE},
    "read_symbol": {"qname": SUBJECT},
    "find_callers": {"qname": SUBJECT},
    "find_references": {"qname": SUBJECT},
    "find_implementations": {"qname": OWNER},
    "find_view_data": {"qname": CALLER},
    "include_graph": {"path": SOURCE},
    "impact": {"qnames": [SUBJECT]},
    "impact_modules": {"paths": [SOURCE]},
    "subtree_dependencies": {"subtree": "src"},
    "reachable_from": {},
    "find_orphans": {},
    "explain_path": {"from_qname": CALLER, "to_qname": SUBJECT},
    "architecture_overview": {},
    "guided_tour": {},
    "check_architecture_rules": {},
    "check_column_defaults": {"table": "users"},
    "diff_architecture": {"before": "HEAD", "after": "HEAD"},
    "class_diagram": {"qname": OWNER},
    "trace_capability": {"qname": CALLER},
}


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Config]:
    root = tmp_path / "repo"
    call = edge("CALLS", CALLER, "save", SOURCE, target_qname=SUBJECT)
    db_path = indexed_repo(root, edges=[call])
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setenv("CA_DB_PATH", str(db_path))
    # The shell reads os.environ; the MCP side must see the same knobs or the payloads differ.
    return root, load_config(root)


def mcp_payloads(config: Config, requests: list[tuple[str, dict[str, object]]]) -> list[Any]:
    """What an MCP client that declares this checkout as its root receives, call by call."""

    async def once() -> list[Any]:
        server = build_server(config)
        async with Client(server, roots=[config.root.as_uri()]) as client:
            return [
                (await client.call_tool(tool, args)).structured_content for tool, args in requests
            ]

    return asyncio.run(once())


def shell(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, list[Any], str]:
    code = query.main(list(argv))
    out, err = capsys.readouterr()
    return code, [json.loads(line) for line in out.splitlines() if line.strip()], err


def _has_rows(payload: dict[str, Any]) -> bool:
    return payload.get("reason", "ok") == "ok" and bool(
        payload.get("results") or payload.get("symbols") or payload.get("source")
    )


def fit_rows(config: Config) -> list[dict[str, object]]:
    with GraphStore(config.db_path) as store:
        return store.list_fit_counts() + store.list_cost_counts()


def write_batch(path: Path, requests: list[tuple[str, dict[str, object]]]) -> Path:
    lines = (json.dumps({"tool": tool, "args": args}) for tool, args in requests)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_every_read_tool_has_an_argument_set() -> None:
    # A tool added to TOOL_NAMES without a row here would silently drop out of AC1.
    assert set(ARGS) == set(READ_TOOLS)
    assert len(READ_TOOLS) == len(TOOL_NAMES) - 2


def test_shell_payload_equals_the_mcp_payload_for_every_read_tool(
    repo: tuple[Path, Config], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC1: per tool, the parsed shell line equals the MCP client's payload."""
    _, config = repo
    requests = [(tool, ARGS[tool]) for tool in READ_TOOLS]
    code, answers, err = shell(capsys, "--batch", str(write_batch(tmp_path / "b.jsonl", requests)))
    assert code == query.OK, err
    expected = mcp_payloads(config, requests)
    assert len(answers) == len(requests)
    for (tool, _), got, want in zip(requests, answers, expected, strict=True):
        assert got == want, tool
    # Not empty-equals-empty: the nav tools aimed at fixture rows answer ok with rows.
    answered = {tool for (tool, _), got in zip(requests, answers, strict=True) if _has_rows(got)}
    assert {"search_symbol", "file_outline", "read_symbol", "find_callers"} <= answered, answered
    print(f"tools answering ok with rows: {len(answered)}/{len(requests)} {sorted(answered)}")
    # Not vacuous: the fixture's caller edge is in the answer both routes gave.
    callers = answers[READ_TOOLS.index("find_callers")]
    assert [row["qname"] for row in callers["results"]] == [CALLER]


def test_single_tool_form_prints_one_payload(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    _, config = repo
    args = {"qname": SUBJECT}
    code, answers, _ = shell(capsys, "find_callers", "--args", json.dumps(args))
    assert code == query.OK
    assert answers == mcp_payloads(config, [("find_callers", args)])


def test_an_empty_answer_exits_zero_with_the_tools_reason(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    """AC3: an honest empty is an answer, with the same reason and try_instead as the tool."""
    _, config = repo
    args = {"qname": "\\App\\Nope::missing"}
    code, answers, _ = shell(capsys, "find_callers", "--args", json.dumps(args))
    assert code == query.OK
    (answer,) = answers
    (want,) = mcp_payloads(config, [("find_callers", args)])
    assert answer["results"] == [] and answer["reason"] != "ok"
    assert answer["reason"] == want["reason"]
    assert answer.get("try_instead") == want.get("try_instead")


def test_a_thousand_line_batch_runs_in_one_process(
    repo: tuple[Path, Config], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC2: one process, one client, one payload per line in order; prints the wall time."""
    cycle = [("search_symbol", {"query": "save"}), ("find_callers", {"qname": SUBJECT})]
    requests = [cycle[i % 2] for i in range(1000)]
    batch = write_batch(tmp_path / "big.jsonl", requests)
    started = time.perf_counter()
    code, answers, err = shell(capsys, "--batch", str(batch))
    elapsed = time.perf_counter() - started
    assert code == query.OK, err
    assert len(answers) == 1000
    assert all("results" in answers[i] for i in range(1000))
    assert answers[0]["results"][0]["qname"] == SUBJECT
    assert [row["qname"] for row in answers[1]["results"]] == [CALLER]
    print(f"1000-line batch: {elapsed:.2f}s")


def test_shell_calls_bump_no_fit_counter(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    """Fit and cost rows count an agent's asks (260, 379); a shell batch is not one."""
    _, config = repo
    shell(capsys, "search_symbol", "--args", '{"query": "save"}')
    assert fit_rows(config) == []
    mcp_payloads(config, [("search_symbol", {"query": "save"})])
    assert fit_rows(config) != []


@pytest.mark.parametrize("tool", sorted(query.REFUSED_TOOLS))
def test_index_writers_are_refused(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str], tool: str
) -> None:
    code, answers, err = shell(capsys, tool)
    assert code == query.USAGE and answers == []
    assert "writes the index" in err


def test_refused_set_names_exactly_the_two_writers() -> None:
    assert query.REFUSED_TOOLS == {build_or_update_index.NAME, generate_onboarding.NAME}


@pytest.mark.parametrize(
    "argv",
    [
        ("no_such_tool",),
        ("search_symbol", "--args", "{not json"),
        ("search_symbol", "--args", "[1]"),
        ("search_symbol", "--args", '{"limit": "many"}'),
    ],
)
def test_usage_errors_exit_two(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str], argv: tuple[str, ...]
) -> None:
    code, answers, _ = shell(capsys, *argv)
    assert code == query.USAGE and answers == []


def test_neither_a_tool_nor_a_batch_is_a_usage_error(repo: tuple[Path, Config]) -> None:
    with pytest.raises(SystemExit) as stopped:
        query.main([])
    assert stopped.value.code == query.USAGE


def test_a_bad_batch_line_is_refused_before_any_line_is_asked(
    repo: tuple[Path, Config], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    batch = tmp_path / "bad.jsonl"
    batch.write_text('{"tool": "search_symbol", "args": {}}\n{"tool": "nope"}\n', encoding="utf-8")
    code, answers, err = shell(capsys, "--batch", str(batch))
    assert code == query.USAGE and answers == []
    assert "line 2" in err


def test_a_batch_that_is_not_utf8_is_a_usage_error(
    repo: tuple[Path, Config], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    batch = tmp_path / "latin1.jsonl"
    batch.write_bytes(b'{"tool": "search_symbol", "args": {"query": "caf\xe9"}}\n')
    code, answers, err = shell(capsys, "--batch", str(batch))
    assert code == query.USAGE and answers == []
    assert "--batch" in err


def test_no_index_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("CA_DB_PATH", raising=False)
    code, answers, err = shell(capsys, "search_symbol")
    assert code == query.FAILED and answers == []
    assert "no index" in err


def test_a_file_that_is_not_a_database_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    db_path = tmp_path / "graph.db"
    db_path.write_text("not sqlite", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CA_DB_PATH", str(db_path))
    code, answers, err = shell(capsys, "search_symbol")
    assert code == query.FAILED and answers == []
    assert "unreadable index" in err


def test_a_batch_reads_stdin_with_a_dash(
    repo: tuple[Path, Config], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    lines = '{"tool": "search_symbol", "args": {"query": "save"}}\n\n{"tool": "file_outline", ' \
        f'"args": {{"path": "{SOURCE}"}}}}\n'
    monkeypatch.setattr(sys, "stdin", io.StringIO(lines))
    code, answers, _ = shell(capsys, "--batch", "-")
    assert code == query.OK
    assert len(answers) == 2  # the blank line is skipped, not answered
    assert answers[0]["results"][0]["qname"] == SUBJECT


def test_a_batch_answers_while_a_writer_holds_the_lock(
    repo: tuple[Path, Config], capsys: pytest.CaptureFixture[str]
) -> None:
    """The git-hook refresh's write lock does not block a shell reader; answers name the build."""
    _, config = repo
    with try_index_write_lock(config.db_path) as acquired:
        assert acquired
        code, answers, _ = shell(capsys, "find_callers", "--args", json.dumps({"qname": SUBJECT}))
    assert code == query.OK
    assert [row["qname"] for row in answers[0]["results"]] == [CALLER]
    assert answers[0].get("build_in_progress") is True


def test_the_installed_entry_point_routes_query(repo: tuple[Path, Config]) -> None:
    """``code-atlas query`` is the server's own script; no subcommand still means serve."""
    root, _ = repo
    done = subprocess.run(
        [sys.executable, "-m", "code_atlas.main", "query", "search_symbol", "--args",
         '{"query": "save"}'],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    assert done.returncode == query.OK, done.stderr
    assert json.loads(done.stdout)["results"][0]["qname"] == SUBJECT
