"""Task 077: status names the revision (branch/ref), not only the commit SHA."""

from __future__ import annotations

from pathlib import Path

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import LAST_COMMIT_KEY, LAST_REF_KEY, GraphStore
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


def test_rebuild_without_git_clears_stale_last_ref(tmp_path: Path) -> None:
    """A rebuild that cannot name a ref must not inherit the prior branch stamp."""
    committed(tmp_path, {SOURCE: "<?php class A {}\n"})
    db_path = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(tmp_path, {**fake_env(), "CA_DB_PATH": str(db_path)})
    with GraphStore(db_path) as store:
        full_build(config, store)
        assert store.get_meta(LAST_REF_KEY) is not None

    git_dir = tmp_path / ".git"
    git_dir.rename(tmp_path / ".git.bak")
    try:
        with GraphStore(db_path) as store:
            full_build(config, store)
            assert not store.has_meta(LAST_REF_KEY)
            assert not store.has_meta(LAST_COMMIT_KEY)
    finally:
        (tmp_path / ".git.bak").rename(git_dir)

    found = status(tmp_path, db_path)
    assert found["last_ref"] is None
    assert found["last_commit"] is None


def test_pre_077_index_omits_last_ref_rather_than_claiming_non_git(tmp_path: Path) -> None:
    """Absent last_ref key + present last_commit ⇒ omit the field (not null=non-git)."""
    committed(tmp_path, {SOURCE: "<?php class A {}\n"})
    db_path = build_index(tmp_path)
    with GraphStore(db_path) as store:
        store.delete_meta(LAST_REF_KEY)
        assert store.get_meta(LAST_COMMIT_KEY) is not None
        assert not store.has_meta(LAST_REF_KEY)

    found = status(tmp_path, db_path)

    assert "last_ref" not in found
    assert found["head_ref"] is not None
    assert found["last_commit"] is not None
