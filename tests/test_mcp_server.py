"""Task 010: the MCP server and its first two tools, driven by a real MCP client (§12).

Every criterion here fails at the runtime or integration layer or not at all — a tool that is
registered but unreachable, a payload counted from the wrong table, a store opened on the wrong
thread. So the server is exercised through ``fastmcp.Client``: in-memory where the question is about
one repo's answers, and over a **real stdio subprocess** where the question is "does it start".

The subprocess proof keeps the thread rule honest: FastMCP runs a tool on a worker thread, so a
connection opened anywhere but inside the call raises ``sqlite3.ProgrammingError`` on first use.
"""

import asyncio
import json
import os
import shlex
import subprocess
import sys
import threading
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, get_args

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from fastmcp.exceptions import ToolError

from code_atlas import tools
from code_atlas.config import Config, ConfigError, load_config
from code_atlas.indexer import full_build
from code_atlas.main import TOOL_NAMES, build_server
from code_atlas.store import GraphStore
from code_atlas.tools.architecture_overview import NAME as OVERVIEW
from code_atlas.tools.build_or_update_index import NAME as BUILD
from code_atlas.tools.explain_path import NAME as EXPLAIN
from code_atlas.tools.file_outline import NAME as OUTLINE
from code_atlas.tools.find_callers import NAME as CALLERS
from code_atlas.tools.find_implementations import NAME as IMPLS
from code_atlas.tools.find_orphans import NAME as ORPHANS
from code_atlas.tools.find_references import NAME as REFS
from code_atlas.tools.find_view_data import NAME as VIEW_DATA
from code_atlas.tools.get_index_status import NAME as STATUS
from code_atlas.tools.guided_tour import NAME as TOUR
from code_atlas.tools.impact import NAME as IMPACT
from code_atlas.tools.include_graph import NAME as INCLUDE
from code_atlas.tools.reachable_from import NAME as REACHABLE
from code_atlas.tools.read_symbol import NAME as READ
from code_atlas.tools.search_symbol import NAME as SEARCH

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
MAIN = REPO / "code_atlas" / "main.py"

# The ~100-token budget of §12's "call first" tool, pinned to characters at ~4 chars per token.
MINIMAL_BUDGET = 400

# Long enough for a cold interpreter start on a loaded CI runner, short enough to fail a hang fast.
STDIO_TIMEOUT = 90.0


# --- fixtures and helpers ------------------------------------------------------------------------


def fake_env(workers: int = 2) -> dict[str, str]:
    """The environment that wires a repo to the protocol fixture, with the fan-out **pinned**."""
    return {
        "CA_WORKERS": str(workers),
        "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
    }


def served_config(root: Path, **extra: str) -> Config:
    return load_config(root, {**fake_env(), **extra})


def tree(root: Path, *paths: str) -> tuple[str, ...]:
    for index, path in enumerate(paths):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"content {index} of {path}\n", encoding="utf-8")
    return tuple(sorted(paths))


def git(root: Path, *arguments: str) -> str:
    """Run one git command with an identity, so a commit works on a bare CI checkout."""
    done = subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=test", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def committed_repo(root: Path, *paths: str) -> tuple[str, ...]:
    """A git repo with one commit — the state a staleness verdict can actually be made about."""
    created = tree(root, *paths)
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "first")
    return created


@pytest.fixture
def repo(tmp_path: Path) -> Iterator[Path]:
    """A small committed repo: two files the fixture adapter claims, one it does not."""
    committed_repo(tmp_path, "src/a.aa", "src/b.bb", "docs/notes.md")
    yield tmp_path


def call(server: Any, name: str, arguments: Mapping[str, object] | None = None) -> Any:
    """One in-memory client call. Sync on purpose: no async plugin is needed to drive a client."""

    async def once() -> Any:
        async with Client(server) as client:
            return (await client.call_tool(name, dict(arguments or {}))).data

    return asyncio.run(once())


def listed(server: Any) -> list[str]:
    async def once() -> list[str]:
        async with Client(server) as client:
            return sorted(tool.name for tool in await client.list_tools())

    return asyncio.run(once())


def raises_through_the_client(server: Any, name: str, arguments: Mapping[str, object]) -> str:
    """The client-visible error text, which is what a caller of a bad argument actually sees."""
    with pytest.raises(ToolError) as error:
        call(server, name, arguments)
    return str(error.value)


def table_counts(db_path: Path) -> dict[str, int]:
    """Counted straight from the tables, so accuracy is judged against rows and not against the
    same read the tool used."""
    with GraphStore(db_path) as store:
        return {
            table: int(store._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("files", "nodes", "edges")
        }


def snapshot(db_path: Path) -> dict[str, list[tuple[object, ...]]]:
    """Row content, ids and wall-clock excluded — task 004's ratified determinism carve-out."""
    with GraphStore(db_path) as store:
        conn = store._conn
        return {
            "files": conn.execute(
                "SELECT path, hash, language, parsed_ok FROM files ORDER BY path"
            ).fetchall(),
            "nodes": conn.execute(
                "SELECT qualified_name, kind, file_path, line_start FROM nodes "
                "ORDER BY qualified_name, file_path"
            ).fetchall(),
        }


# --- the guard on the guards ---------------------------------------------------------------------


def test_the_proof_has_something_to_run() -> None:
    # A server module still holding its stub would make every assertion below vacuous.
    assert FAKE.is_file()
    assert len(MAIN.read_text(encoding="utf-8").splitlines()) > 20
    assert TOOL_NAMES == (
        STATUS,
        BUILD,
        SEARCH,
        OUTLINE,
        READ,
        CALLERS,
        REFS,
        IMPLS,
        VIEW_DATA,
        INCLUDE,
        IMPACT,
        REACHABLE,
        ORPHANS,
        EXPLAIN,
        OVERVIEW,
        TOUR,
    )


# --- AC1 · the proving test: a real client, a real subprocess, a real build ----------------------


def test_a_real_client_over_stdio_lists_the_tools_then_builds_and_reports_the_index(
    repo: Path,
) -> None:
    """AC1 + AC3 end to end: the server starts as its own process and does the work over stdio."""

    async def session() -> tuple[list[str], Any, Any]:
        transport = StdioTransport(
            command=sys.executable,
            args=["-m", "code_atlas.main"],
            cwd=str(repo),
            env={**os.environ, **fake_env(), "PYTHONPATH": str(REPO)},
        )
        async with Client(transport) as client:
            names = sorted(tool.name for tool in await client.list_tools())
            built = (await client.call_tool(BUILD, {})).data
            status = (await client.call_tool(STATUS, {})).data
            return names, built, status

    names, built, status = asyncio.run(asyncio.wait_for(session(), STDIO_TIMEOUT))

    assert names == sorted(TOOL_NAMES)
    assert built["wrote"]["files"] == 2 and built["wrote"]["parsed"] == 2, built
    assert built["wrote"]["nodes"] == 2 and built["seconds"] >= 0
    for field in ("files", "parsed", "failed", "nodes", "edges", "stubs"):
        assert status[field] == built["graph"][field], f"{field}: status disagrees with graph"
        assert built["wrote"][field] == built["graph"][field], f"{field}: full wrote ≠ graph"


def test_the_server_module_runs_as_a_script_too(repo: Path) -> None:
    """`python -m code_atlas.main` is what an `.mcp.json` names, so it must work uninstalled."""
    done = subprocess.run(
        [sys.executable, "-m", "code_atlas.main"],
        cwd=repo,
        env={**os.environ, **fake_env(), "PYTHONPATH": str(REPO)},
        input="",
        capture_output=True,
        text=True,
        timeout=STDIO_TIMEOUT,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    # stdout carries the protocol and nothing else: an empty stdin yields no reply, not chatter.
    assert done.stdout == "", done.stdout[:500]


# --- AC2 · accurate stats ------------------------------------------------------------------------


def test_the_reported_stats_are_the_databases_own_row_counts(repo: Path) -> None:
    config = served_config(repo)
    call(build_server(config), BUILD, {})

    status = call(build_server(config), STATUS, {})

    counted = table_counts(config.db_path)
    assert status["files"] == counted["files"] == 2
    assert status["nodes"] == counted["nodes"] == 2
    assert status["edges"] == counted["edges"] == 0
    assert status["parsed"] == 2 and status["failed"] == 0
    assert status["indexed"] is True


def test_a_failed_parse_is_counted_as_failed_not_parsed(tmp_path: Path) -> None:
    """`parsed` must come from `parsed_ok`, not from the file total (R5.1)."""
    committed_repo(tmp_path, "soft-error/bad.aa", "src/good.aa")
    config = served_config(tmp_path)
    call(build_server(config), BUILD, {})

    status = call(build_server(config), STATUS, {})

    assert (status["files"], status["parsed"], status["failed"]) == (2, 1, 1)


# --- AC3 · the build tool really builds ----------------------------------------------------------


def test_the_build_tool_produces_the_same_index_a_direct_build_does(repo: Path) -> None:
    config = served_config(repo)
    call(build_server(config), BUILD, {})
    through_the_tool = snapshot(config.db_path)

    direct_path = repo / ".code-atlas" / "direct.db"
    with GraphStore(direct_path) as store:
        direct = load_config(repo, {**fake_env(), "CA_DB_PATH": str(direct_path)})
        report = full_build(direct, store)

    assert report.files == 2, "a vacuous build would make the comparison below meaningless"
    assert through_the_tool == snapshot(direct_path)


@pytest.mark.parametrize("full", [False, True], ids=["full-false", "full-true"])
def test_the_requested_mode_is_echoed_and_the_mode_that_ran_is_named(
    repo: Path, full: bool
) -> None:
    """On a fresh index there is no last_commit yet, so both requests run a full build."""
    result = call(build_server(served_config(repo)), BUILD, {"full": full})

    assert result["mode"] == "full"
    assert result["requested_full"] is full


def test_full_false_after_a_commit_runs_incremental(repo: Path) -> None:
    config = served_config(repo)
    call(build_server(config), BUILD, {"full": True})
    tree(repo, "src/a.aa")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "edit")

    result = call(build_server(config), BUILD, {"full": False})

    assert result["mode"] == "incremental"
    assert result["requested_full"] is False


# --- R2 · the CA_TOOLS allow-list (per-item, N=2) ------------------------------------------------


def test_every_tool_is_served_when_the_allow_list_is_unset(repo: Path) -> None:
    assert listed(build_server(served_config(repo))) == sorted(TOOL_NAMES)


@pytest.mark.parametrize("only", TOOL_NAMES)
def test_each_tool_can_be_served_alone(repo: Path, only: str) -> None:
    # Per-item, not an aggregate: a filter that always kept the first tool would pass a count.
    assert listed(build_server(served_config(repo, CA_TOOLS=only))) == [only]


def test_an_unknown_tool_name_in_the_allow_list_fails_loud(repo: Path) -> None:
    """R5.3: a typo that silently served nothing would look exactly like a working server."""
    with pytest.raises(ConfigError) as error:
        build_server(served_config(repo, CA_TOOLS="get_index_status,serch_symbol"))
    assert "serch_symbol" in str(error.value)


# --- R3 · last_commit, staleness, suggestions ----------------------------------------------------


def test_a_fresh_build_is_current_and_a_later_commit_leaves_it_behind(repo: Path) -> None:
    config = served_config(repo)
    call(build_server(config), BUILD, {})

    assert call(build_server(config), STATUS, {})["staleness"] == "current"
    assert call(build_server(config), STATUS, {})["last_commit"] == git(repo, "rev-parse", "HEAD")

    tree(repo, "src/d.aa")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "second")

    assert call(build_server(config), STATUS, {})["staleness"] == "behind"


def test_a_tree_git_cannot_name_a_commit_for_is_unknown_not_current(tmp_path: Path) -> None:
    """§8.1 step 4 leaves `last_commit` unset rather than fabricating one; staleness must follow."""
    tree(tmp_path, "src/a.aa")
    config = served_config(tmp_path)
    call(build_server(config), BUILD, {})

    status = call(build_server(config), STATUS, {})

    assert status["last_commit"] is None
    assert status["staleness"] == "unknown"


def test_status_on_an_unbuilt_repo_answers_without_creating_a_database(repo: Path) -> None:
    config = served_config(repo)

    status = call(build_server(config), STATUS, {})

    assert status["indexed"] is False and status["files"] == 0
    assert status["staleness"] == "unknown"
    assert not config.db_path.exists(), "a read tool created an index as a side effect"


def test_the_suggestions_only_name_tools_this_server_serves(repo: Path) -> None:
    unbuilt = call(build_server(served_config(repo)), STATUS, {})
    assert unbuilt["next_tool_suggestions"] == [BUILD]

    # With the build tool withheld, suggesting it would send the client at a tool it cannot call.
    alone = build_server(served_config(repo, CA_TOOLS=STATUS))
    assert call(alone, STATUS, {})["next_tool_suggestions"] == []


def test_a_current_index_is_not_told_to_rebuild(repo: Path) -> None:
    config = served_config(repo)
    call(build_server(config), BUILD, {})

    assert call(build_server(config), STATUS, {})["next_tool_suggestions"] == []


def test_a_behind_index_suggests_a_build(repo: Path) -> None:
    config = served_config(repo)
    call(build_server(config), BUILD, {})
    # Mutate an indexed file so staleness is behind without a new commit (047 / 061).
    path = next(p for p in (repo / "src").rglob("*") if p.is_file())
    path.write_text(path.read_text(encoding="utf-8") + "// dirty\n", encoding="utf-8")
    assert call(build_server(config), STATUS, {})["next_tool_suggestions"] == [BUILD]


# --- R5 · detail_level on every tool -------------------------------------------------------------


def declared_levels() -> dict[str, list[str]]:
    """Each tool's allowed levels, read off its own module's ``DetailLevel`` alias (R6.7).

    The alias IS the enum FastMCP publishes, so hand-listing which tool also accepts ``verbose`` is
    exactly the list that drifts silently when tool N+1 arrives.
    """
    levels: dict[str, list[str]] = {}
    for module in vars(tools).values():
        name = getattr(module, "NAME", None)
        alias = getattr(module, "DetailLevel", None)
        if isinstance(name, str) and alias is not None:
            levels[name] = sorted(get_args(alias))
    return levels


CALLS: tuple[tuple[str, dict[str, object]], ...] = (
    (STATUS, {}),
    (BUILD, {}),
    (SEARCH, {"query": "Missing"}),
    (OUTLINE, {"path": "missing.php"}),
    (READ, {"qname": "\\Missing"}),
    (CALLERS, {"qname": "\\Missing"}),
    (REFS, {"qname": "\\Missing"}),
    (IMPLS, {"qname": "\\Missing"}),
    (INCLUDE, {"path": "missing.php"}),
    (IMPACT, {"qnames": ["\\Missing"]}),
    (REACHABLE, {}),
    (ORPHANS, {}),
    (EXPLAIN, {"from_qname": "\\A", "to_qname": "\\B"}),
    (OVERVIEW, {}),
)


@pytest.mark.parametrize(("name", "arguments"), CALLS, ids=[name for name, _ in CALLS])
def test_minimal_is_a_strict_reduction_of_standard(
    repo: Path, name: str, arguments: dict[str, object]
) -> None:
    server = build_server(served_config(repo))
    minimal = call(server, name, {**arguments, "detail_level": "minimal"})
    standard = call(server, name, {**arguments, "detail_level": "standard"})

    assert set(minimal) <= set(standard), f"{name}: minimal grew past standard"
    if name in {STATUS, BUILD}:
        assert "db_path" in standard and "db_path" not in minimal
        assert set(minimal) < set(standard)
        if name == STATUS:
            assert "index_root" in minimal and minimal["index_root"] == standard["index_root"]
    else:
        # Nav/search/read no longer carry db_path at standard (task 061).
        assert "db_path" not in standard
        # Every answer names the configured source tree (task 071).
        assert "index_root" in standard and "index_root" in minimal
        assert standard["index_root"] == minimal["index_root"] == str(
            served_config(repo).root.resolve()
        )


@pytest.mark.parametrize(("name", "arguments"), CALLS, ids=[name for name, _ in CALLS])
def test_a_detail_level_outside_the_contract_fails_loud(
    repo: Path, name: str, arguments: dict[str, object]
) -> None:
    server = build_server(served_config(repo))

    message = raises_through_the_client(server, name, {**arguments, "detail_level": "debug"})

    for level in declared_levels()[name]:
        assert level in message, f"{name}: {level} missing from {message!r}"


def test_the_detail_level_choices_are_published_in_the_input_schema(repo: Path) -> None:
    """A client should see the allowed values before calling, not discover them from an error."""

    async def schemas() -> dict[str, Any]:
        async with Client(build_server(served_config(repo))) as client:
            return {tool.name: tool.inputSchema for tool in await client.list_tools()}

    declared = declared_levels()
    assert set(declared) == set(TOOL_NAMES)  # denominator derived, never listed (R6.7)
    for name, schema in asyncio.run(schemas()).items():
        levels = schema["properties"]["detail_level"]
        assert sorted(levels.get("enum", [])) == declared[name], f"{name}: {levels}"


# --- REF1 · the cheap entry point stays cheap ----------------------------------------------------


def test_the_minimal_status_payload_stays_inside_its_budget(repo: Path) -> None:
    """§12 calls this the ~100-token tool; a payload past its budget breaks that promise."""
    config = served_config(repo)
    call(build_server(config), BUILD, {})

    payload = json.dumps(call(build_server(config), STATUS, {"detail_level": "minimal"}))

    assert len(payload) <= MINIMAL_BUDGET, f"{len(payload)} chars: {payload}"


def test_every_part_section_12_names_is_in_the_minimal_payload(repo: Path) -> None:
    # The budget above is only honest if the cheap payload still carries all four parts.
    config = served_config(repo)
    call(build_server(config), BUILD, {})

    minimal = call(build_server(config), STATUS, {"detail_level": "minimal"})

    for part in ("files", "nodes", "edges", "last_commit", "staleness", "next_tool_suggestions"):
        assert part in minimal, part


# --- the thread rule the whole design turns on ---------------------------------------------------


def test_the_tools_run_off_the_thread_that_built_the_server(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spike S2, asserted: FastMCP calls a tool on a worker thread, so no store may outlive a call.

    A connection held by the server would raise ``sqlite3.ProgrammingError`` here instead of
    answering — this is why both tools open the store inside the call.
    """
    config = served_config(repo)
    call(build_server(config), BUILD, {})

    seen: list[int] = []
    original = GraphStore.counts

    def recording(self: GraphStore) -> dict[str, int]:
        seen.append(threading.get_ident())
        return original(self)

    monkeypatch.setattr(GraphStore, "counts", recording)
    call(build_server(config), STATUS, {})

    assert seen and threading.get_ident() not in seen


# --- R3 part 1 · the store read the status tool leans on -----------------------------------------


def test_the_counts_read_agrees_with_a_real_build(repo: Path) -> None:
    config = served_config(repo)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        counts = store.counts()

    assert counts == {
        "files": 2,
        "parsed": 2,
        "failed": 0,
        "nodes": 2,
        "edges": 0,
        "stubs": 0,
    }
