"""Task 366 — an answer about another commit than the caller's checkout says so.

The server is rooted at the main checkout; the agent works in a linked worktree at another commit.
Only the client knows that, through MCP ``roots``, so these drive a real in-process client that
reports them, against a real index and a real ``git worktree``.
"""

from __future__ import annotations

import ast
import asyncio
import shlex
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.main import build_server
from code_atlas.ref_check import (
    REASON_AT_INDEX_FIELD,
    REF_CHECK_FIELD,
    REF_CHECK_NO_ROOTS,
    _path,
)
from code_atlas.store import GraphStore
from code_atlas.tools import build_or_update_index
from code_atlas.tools.nav_result import REASON_OK, REASON_REF_MISMATCH

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP = shutil.which("php")
pytestmark = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

SUBJECT = "\\App\\Account::close"
# Each navigation tool with the arguments that make it answer about SUBJECT's file.
NAV_CALLS: dict[str, dict[str, object]] = {
    "search_symbol": {"query": "close"},
    "read_symbol": {"qname": SUBJECT},
    "file_outline": {"path": "src/Account.php"},
    "find_callers": {"qname": SUBJECT},
    "find_references": {"qname": SUBJECT},
    "impact": {"qnames": [SUBJECT]},
}


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def _write(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Config, Path, Path, str]:
    """Main indexed at A; worktree ``side`` committed to B; worktree ``same`` still at A."""
    main = tmp_path / "main"
    _write(
        main,
        "src/Account.php",
        "<?php\nnamespace App;\nclass Account { public function close() {} }\n",
    )
    _write(
        main,
        "src/Teller.php",
        "<?php\nnamespace App;\nclass Teller { public function run() {"
        " $a = new Account(); $a->close(); } }\n",
    )
    _write(main, ".gitignore", ".code-atlas/\n")
    _git(main, "init", "-q")
    _git(main, "add", "-A")
    _git(main, "commit", "-qm", "init")
    built = _git(main, "rev-parse", "HEAD")
    config = load_config(
        main, {"CA_WORKERS": "2", "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"])}
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    side, same = tmp_path / "side", tmp_path / "same"
    _git(main, "worktree", "add", "-q", "-b", "side", str(side))
    _git(main, "worktree", "add", "-q", "-b", "same", str(same))
    _write(side, "src/Extra.php", "<?php\nnamespace App;\nclass Extra {}\n")
    _git(side, "add", "-A")
    _git(side, "commit", "-qm", "side work")
    return config, side, same, built


def _calls(config: Config, roots: list[Path] | None, names: dict[str, dict[str, object]]) -> Any:
    """Every call in one client session, reporting ``roots`` (None: no roots capability)."""
    server = build_server(config)
    uris = None if roots is None else [path.as_uri() for path in roots]

    async def session() -> dict[str, Any]:
        async with Client(server, roots=uris) as client:
            return {
                name: (await client.call_tool(name, arguments)).structured_content
                for name, arguments in names.items()
            }

    return asyncio.run(session())


def test_every_navigation_tool_names_the_mismatch_with_both_revisions(
    repo: tuple[Config, Path, Path, str],
) -> None:
    """AC1 — index at A, caller's worktree at B: not ``ok``, both commits named, rows kept."""
    config, side, _, built = repo
    side_head = _git(side, "rev-parse", "HEAD")
    answers = _calls(config, [side], NAV_CALLS)
    for name, answer in answers.items():
        assert answer["reason"] == REASON_REF_MISMATCH, name
        assert answer["index_commit"] == built, name
        assert answer["caller_commit"] == side_head, name
        assert answer["caller_root"] == str(side.resolve()), name
    assert answers["find_callers"][REASON_AT_INDEX_FIELD] == REASON_OK
    assert answers["find_callers"]["total_count"] == 1


def test_status_names_the_mismatch_and_the_route(repo: tuple[Config, Path, Path, str]) -> None:
    """Scope 2 — the summary names both commits and the fix; no reason key is invented."""
    config, side, _, built = repo
    status = _calls(config, [side], {"get_index_status": {}})["get_index_status"]
    summary = str(status["summary"])
    assert REASON_REF_MISMATCH in summary
    assert built[:7] in summary
    assert "per-worktree index" in summary
    assert "reason" not in status
    assert status["caller_root"] == str(side.resolve())


def test_matching_heads_and_absent_roots_leave_every_answer_as_it_was(
    repo: tuple[Config, Path, Path, str], tmp_path: Path
) -> None:
    """AC2 — the index root itself, a worktree at the built commit, an unrelated root, no roots."""
    config, _, same, _ = repo
    unrelated = tmp_path / "elsewhere"
    unrelated.mkdir()
    baseline = _calls(config, [config.root], NAV_CALLS)
    assert all(answer.get("reason") != REASON_REF_MISMATCH for answer in baseline.values())
    for roots in ([same], [unrelated], None):
        assert _calls(config, roots, NAV_CALLS) == baseline, roots


def test_a_client_without_roots_is_told_the_check_could_not_run(
    repo: tuple[Config, Path, Path, str],
) -> None:
    """Scope 1 — only the status tool says so; a navigation answer stays byte-identical."""
    config, *_ = repo
    answers = _calls(config, None, {"get_index_status": {}, "find_callers": {"qname": SUBJECT}})
    assert answers["get_index_status"][REF_CHECK_FIELD] == REF_CHECK_NO_ROOTS
    assert REF_CHECK_FIELD not in answers["find_callers"]


def test_every_tool_but_the_build_is_served_through_the_guard() -> None:
    """AC1's "every": the check lives in the guard, so every query tool must pass through it."""
    tree = ast.parse((REPO / "code_atlas" / "main.py").read_text(encoding="utf-8"))
    served: dict[str, bool] = {}
    for call in ast.walk(tree):
        if isinstance(call, ast.Call) and getattr(call.func, "id", None) == "serve":
            name_arg, tool_arg = call.args
            assert isinstance(name_arg, ast.Attribute) and isinstance(name_arg.value, ast.Name)
            guarded = isinstance(tool_arg, ast.Call) and getattr(tool_arg.func, "id", "") == "guard"
            served[name_arg.value.id] = guarded
    assert served, "no serve(...) calls found — the sweep went empty"
    assert served.pop(build_or_update_index.__name__.rsplit(".", 1)[-1]) is False
    assert all(served.values()), [name for name, ok in served.items() if not ok]


def test_a_caller_that_moves_into_a_worktree_mid_session_is_seen(
    repo: tuple[Config, Path, Path, str],
) -> None:
    """Challenger F1 — roots are read per call, so a changed root list counts at once."""
    config, side, _, _ = repo
    server = build_server(config)
    # A handler, not a list: the in-process client answers roots/list from it on every request.
    current = [config.root.as_uri()]

    async def session() -> tuple[Any, Any]:
        async with Client(server, roots=lambda _context: list(current)) as client:
            first = (await client.call_tool("find_callers", {"qname": SUBJECT})).structured_content
            current[:] = [side.as_uri()]
            await client.send_roots_list_changed()
            then = (await client.call_tool("find_callers", {"qname": SUBJECT})).structured_content
            return first, then

    first, then = asyncio.run(session())
    assert first["reason"] == REASON_OK
    assert then["reason"] == REASON_REF_MISMATCH


def test_a_foreign_schema_index_still_answers_its_own_refusal(
    repo: tuple[Config, Path, Path, str],
) -> None:
    """Challenger F2 — the built commit is read without a schema check, so nothing raises."""
    config, side, _, _ = repo
    conn = sqlite3.connect(config.db_path)
    conn.execute("UPDATE meta SET value = '0' WHERE key = 'schema_version'")
    conn.commit()
    conn.close()
    answer = _calls(config, [side], {"find_callers": {"qname": SUBJECT}})["find_callers"]
    assert answer["error"] == "schema_version_mismatch"
    assert "reason" not in answer  # an error is its own answer, not one about a commit


def test_a_later_root_is_still_checked_when_an_earlier_one_matches(
    repo: tuple[Config, Path, Path, str],
) -> None:
    """Challenger F7 — a worktree at the built commit does not hide a second one that moved."""
    config, side, same, _ = repo
    answer = _calls(config, [same, side], {"find_callers": {"qname": SUBJECT}})["find_callers"]
    assert answer["reason"] == REASON_REF_MISMATCH


def test_file_uris_become_local_paths() -> None:
    """Challenger F3 — percent-escapes decode; another URI scheme is no root."""
    assert _path("file:///tmp/a%20b") == Path("/tmp/a b")
    assert _path("file://server/share/x") == Path("//server/share/x")
    assert _path("https://example.com/x") is None
