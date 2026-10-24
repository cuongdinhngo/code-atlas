"""Task 408 — a call names the caller's worktree when the session's roots name the main checkout."""

from __future__ import annotations

import asyncio
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastmcp import Client

from code_atlas.main import build_server
from code_atlas.ref_check import CALLER_ROOTS
from code_atlas.tools import (
    file_outline,
    find_callers,
    find_implementations,
    find_references,
    read_symbol,
    search_symbol,
)
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_OK,
    REASON_REF_MISMATCH,
    REASON_WORKTREE_OVERLAY,
)
from code_atlas.tools.schema_guard import guard
from tests.test_worktree_overlay import _commit, _git, _in, _main_and_worktree, _write, needs_php

RUN = "\\App\\Service::run"
FRESH = (
    "<?php\nnamespace App;\n"
    "class Fresh { public function brandNew(Service $s) { $s->run(); } }\n"
)
OVERLAID = (read_symbol, file_outline, search_symbol, find_callers, find_references)


@contextmanager
def _roots(*paths: Path) -> Iterator[None]:
    """The session's MCP roots, as `CallerRoots` sets them for one call."""
    token = CALLER_ROOTS.set(tuple(paths))
    try:
        yield
    finally:
        CALLER_ROOTS.reset(token)


def _subagent(tmp_path: Path) -> tuple[Path, Path]:
    """Main built at A; a worktree that moved `run` and added a class only it holds."""
    main, worktree = _main_and_worktree(tmp_path)
    _write(worktree, "src/Fresh.php", FRESH)
    return main, worktree


@needs_php
def test_ac1_caller_root_answers_from_the_worktree_while_the_roots_name_main(
    tmp_path: Path,
) -> None:
    main, worktree = _subagent(tmp_path)
    config = _in(main, None)
    read = guard(read_symbol.create(config), config)
    with _roots(main):
        built = read(RUN, detail_level="minimal")
        moved = read(RUN, detail_level="minimal", caller_root=str(worktree))
        missing = read("\\App\\Fresh::brandNew", detail_level="minimal")
        fresh = read("\\App\\Fresh::brandNew", detail_level="minimal", caller_root=str(worktree))
    assert "overlay" not in built and built["reason"] == REASON_OK
    assert moved["line_start"] == built["line_start"] + 90, (built, moved)
    assert moved["overlay"] == "worktree"
    assert moved["overlay_root"] == str(worktree.resolve())
    assert missing["found"] is False
    assert fresh["found"] is True and fresh["overlay"] == "worktree"


@needs_php
def test_each_of_the_five_tools_honours_caller_root(tmp_path: Path) -> None:
    """R1, N = 5: every overlaid tool takes the argument, and only with it sees the worktree."""
    main, worktree = _subagent(tmp_path)
    config = _in(main, None)
    calls = {
        read_symbol: {"qname": "\\App\\Fresh::brandNew"},
        file_outline: {"path": "src/Fresh.php"},
        search_symbol: {"query": "brandNew"},
        find_callers: {"qname": RUN},
        find_references: {"qname": RUN},
    }
    assert set(calls) == set(OVERLAID)
    with _roots(main):
        for module, args in calls.items():
            tool = guard(module.create(config), config)
            plain = tool(**args, detail_level="minimal")
            named = tool(**args, detail_level="minimal", caller_root=str(worktree))
            assert "overlay" not in plain, (module.NAME, plain)
            assert named.get("overlay") == "worktree", (module.NAME, named)
    rows = guard(find_callers.create(config), config)(
        RUN, detail_level="minimal", caller_root=str(worktree)
    )
    assert rows["reason"] == REASON_WORKTREE_OVERLAY
    assert "\\App\\Fresh::brandNew" in {str(row["qname"]) for row in rows["results"]}


@needs_php
def test_ac2_a_root_outside_this_repository_is_refused_with_its_cause(tmp_path: Path) -> None:
    main, worktree = _subagent(tmp_path)
    plain = tmp_path / "plain"
    plain.mkdir()
    other = tmp_path / "other"
    _write(other, "x.php", "<?php\n")
    _git(other, "init", "-q")
    _commit(other)
    config = _in(main, None)
    refused = {
        "": "absolute",
        "src": "absolute",
        str(tmp_path / "missing"): "not a directory",
        str(worktree / "src" / "Service.php"): "not a directory",
        str(plain): "not inside a git checkout",
        str(other): "another repository",
    }
    for module in OVERLAID:
        tool = guard(module.create(config), config)
        bare = module.create(config)
        for value, cause in refused.items():
            for call in (tool, bare):
                with pytest.raises(ValueError, match=cause):
                    call("src/Fresh.php" if module is file_outline else RUN, caller_root=value)


@needs_php
def test_a_worktree_whose_head_does_not_resolve_is_refused(tmp_path: Path) -> None:
    """C1 (challenger D3): no overlay can be built there, so the call must not answer about main."""
    main, worktree = _subagent(tmp_path)
    (main / ".git" / "worktrees" / worktree.name / "HEAD").write_text("ref: refs/heads/gone\n")
    config = _in(main, None)
    with pytest.raises(ValueError, match="HEAD|git checkout"):
        guard(read_symbol.create(config), config)(RUN, caller_root=str(worktree))


@needs_php
def test_the_index_checkout_and_a_worktree_subdirectory_are_accepted(tmp_path: Path) -> None:
    main, worktree = _subagent(tmp_path)
    config = _in(main, None)
    read = guard(read_symbol.create(config), config)
    with _roots(worktree):
        here = read(RUN, detail_level="minimal", caller_root=str(main / "src"))
    with _roots(main):
        built = read(RUN, detail_level="minimal")
        below = read(RUN, detail_level="minimal", caller_root=str(worktree / "src"))
    # Naming the index checkout overrides a worktree root: no overlay, and no 366 label either.
    assert here == built
    assert below["overlay_root"] == str(worktree.resolve())


@needs_php
def test_caller_root_drives_the_ref_label_for_that_call_only(tmp_path: Path) -> None:
    """H1: the 366 label reads the named root, not the session's, and only for that call."""
    main, worktree = _subagent(tmp_path)
    config = _in(main, None)
    # A tool with no overlay shows the label the roots alone would give.
    callers = guard(find_callers.create(config), config)
    with _roots(worktree):
        session = guard(find_implementations.create(config), config)("\\App\\Service")
        named = callers("\\App\\Caller::go", detail_level="minimal", caller_root=str(main))
        after = callers("\\App\\Caller::go", detail_level="minimal")
    assert session["reason"] == REASON_REF_MISMATCH  # the worktree is at another commit
    assert named["reason"] == REASON_NO_MATCHES and "caller_commit" not in named
    assert after.get("overlay") == "worktree"


@needs_php
def test_ac3_without_the_argument_the_roots_and_env_routes_are_unchanged(tmp_path: Path) -> None:
    main, worktree = _subagent(tmp_path)
    via_env = read_symbol.create(_in(main, worktree))(RUN, detail_level="minimal")
    assert via_env["overlay"] == "worktree"  # 389's CA_CALLER_ROOT route
    config = _in(main, None)
    read = guard(read_symbol.create(config), config)
    with _roots(worktree):
        via_roots = read(RUN, detail_level="minimal")
        explicit_none = read(RUN, detail_level="minimal", caller_root=None)
    assert via_roots == explicit_none
    assert via_roots["line_start"] == via_env["line_start"]


@needs_php
def test_ac4_the_five_published_schemas_and_no_other_name_caller_root(tmp_path: Path) -> None:
    main, _worktree = _subagent(tmp_path)

    async def schemas() -> dict[str, dict[str, object]]:
        async with Client(build_server(_in(main, None))) as client:
            return {tool.name: tool.inputSchema for tool in await client.list_tools()}

    published = asyncio.run(schemas())
    takes = {name for name, schema in published.items() if "caller_root" in schema["properties"]}
    assert takes == {module.NAME for module in OVERLAID}


def test_a_refused_root_never_reaches_the_index(tmp_path: Path) -> None:
    """C1 without an adapter: the refusal fires before the database is even looked for."""
    subprocess.run(["git", "init", "-q", str(tmp_path / "repo")], check=True)
    config = _in(tmp_path / "repo", None)
    assert not config.db_path.exists()
    with pytest.raises(ValueError, match="absolute"):
        read_symbol.create(config)(RUN, caller_root="relative/path")
