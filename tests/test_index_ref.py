"""Task 077: status names the revision (branch/ref), not only the commit SHA."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from code_atlas import gitutil
from code_atlas.config import load_config
from code_atlas.tools import get_index_status
from tests.test_incremental import committed, fake_env, git
from tests.test_mcp_server import BUILD, build_server, call, committed_repo, served_config
from tests.test_staleness_scope import SOURCE, build_index, status


def test_branch_switch_names_distinct_refs(tmp_path: Path) -> None:
    """Proving test: after a checkout without rebuild, last_ref and head_ref differ."""
    committed(tmp_path, {SOURCE: "<?php class A {}\n", "README.md": "docs\n"})
    built_on = git(tmp_path, "rev-parse", "--abbrev-ref", "HEAD")
    db_path = build_index(tmp_path)

    git(tmp_path, "checkout", "-qb", "feature-077")
    found = status(tmp_path, db_path)

    assert found["last_ref"] == built_on
    assert found["head_ref"] == "feature-077"
    assert found["last_ref"] != found["head_ref"]


def test_status_after_rebuild_names_the_new_ref(tmp_path: Path) -> None:
    """AC2: after switch + rebuild, both refs name the new branch (not a bare silent current)."""
    committed_repo(tmp_path, "src/a.aa")
    config = served_config(tmp_path)
    server = build_server(config)
    call(server, BUILD, {})
    git(tmp_path, "checkout", "-qb", "other-077")
    call(server, BUILD, {})
    found = call(server, "get_index_status", {"detail_level": "minimal"})

    assert found["last_ref"] == found["head_ref"] == "other-077"
    assert found["staleness"] == "current"


def test_detached_head_is_a_value_not_an_omission(tmp_path: Path) -> None:
    committed(tmp_path, {SOURCE: "<?php class A {}\n"})
    db_path = build_index(tmp_path)
    git(tmp_path, "checkout", "--detach", "HEAD")

    found = status(tmp_path, db_path)

    assert found["head_ref"] == "HEAD"
    assert found["last_ref"] is not None


def test_non_git_directory_degrades_without_raising(tmp_path: Path) -> None:
    root = tmp_path / "not-a-repo"
    root.mkdir()
    db_path = root / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    config = load_config(root, {"CA_DB_PATH": str(db_path)})
    served = (get_index_status.NAME, get_index_status.BUILD_TOOL)

    found = get_index_status.create(config, served)(detail_level="minimal")

    assert found["last_ref"] is None
    assert found["head_ref"] is None
    assert found["staleness"] == "unknown"


def test_git_failure_returns_none_not_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    committed(tmp_path, {SOURCE: "<?php class A {}\n"})
    monkeypatch.setattr(gitutil, "_run", lambda *a, **k: None)

    assert gitutil.head_ref(tmp_path) is None


def test_worktree_mismatch_revealed_by_index_root(tmp_path: Path) -> None:
    """AC4: when server root ≠ caller cwd, index_root is the revealing field (071/077)."""
    repo = tmp_path / "indexed-tree"
    repo.mkdir()
    committed_repo(repo, "src/a.aa")
    elsewhere = tmp_path / "agent-cwd"
    elsewhere.mkdir()
    config = load_config(repo, fake_env())

    previous = Path.cwd()
    try:
        os.chdir(elsewhere)
        server = build_server(config)
        call(server, BUILD, {})
        found = call(server, "get_index_status", {"detail_level": "minimal"})
    finally:
        os.chdir(previous)

    assert found["index_root"] == str(config.root.resolve())
    assert found["index_root"] != str(elsewhere.resolve())
    assert found["last_ref"] == found["head_ref"]
    assert found["head_ref"] is not None
