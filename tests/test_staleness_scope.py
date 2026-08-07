"""Task 047: staleness reflects the index, not the whole working tree.

The field session that motivated this edited eleven markdown files, was told the index was
``behind``, and paid a 62-second rebuild that reindexed nothing. Every test here is one shape of
"which dirty file should move the signal".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from code_atlas import gitutil
from code_atlas.config import load_config
from code_atlas.store import INDEXED_SUFFIXES_KEY, LAST_COMMIT_KEY, GraphStore
from code_atlas.tools import get_index_status
from code_atlas.tools.get_index_status import BEHIND, CURRENT, UNKNOWN
from tests.test_incremental import committed, git, write
from tests.test_store import nodes_for

SOURCE = "src/a.php"


def build_index(root: Path, *, suffixes: str | None = ".php") -> Path:
    """An index over one PHP file, stamped at HEAD — as a real build would leave it."""
    db_path = root / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with GraphStore(db_path) as store:
        store.upsert_file(SOURCE, "h", "php")
        store.replace_file_rows(SOURCE, nodes_for(SOURCE), [])
        store.set_meta(LAST_COMMIT_KEY, git(root, "rev-parse", "HEAD"))
        if suffixes is not None:
            store.set_meta(INDEXED_SUFFIXES_KEY, suffixes)
    return db_path


def status(root: Path, db_path: Path, detail_level: str = "standard") -> dict[str, object]:
    config = load_config(root, {"CA_DB_PATH": str(db_path)})
    # Both registered: `next_tool_suggestions` only names tools this server actually serves.
    served = (get_index_status.NAME, get_index_status.BUILD_TOOL)
    return get_index_status.create(config, served)(detail_level=detail_level)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    committed(tmp_path, {SOURCE: "<?php class A {}\n", "README.md": "docs\n"})
    return tmp_path


def test_a_dirty_markdown_file_leaves_the_index_current(repo: Path) -> None:
    """The reported defect: docs-only edits cost a rebuild that reindexes nothing."""
    db_path = build_index(repo)
    write(repo, "README.md", "docs, edited\n")

    found = status(repo, db_path)

    assert found["staleness"] == CURRENT
    assert found["dirty_indexed_files"] == 0
    assert get_index_status.BUILD_TOOL not in found["next_tool_suggestions"]  # type: ignore[operator]


def test_a_dirty_source_file_still_reports_behind(repo: Path) -> None:
    """The guard against over-correcting: a false `current` is the dangerous direction."""
    db_path = build_index(repo)
    write(repo, SOURCE, "<?php class A { function b() {} }\n")

    found = status(repo, db_path)

    assert found["staleness"] == BEHIND
    assert found["dirty_indexed_files"] == 1
    assert get_index_status.BUILD_TOOL in found["next_tool_suggestions"]  # type: ignore[operator]


def test_both_dirty_reports_behind_and_counts_only_the_indexed_one(repo: Path) -> None:
    db_path = build_index(repo)
    write(repo, "README.md", "docs, edited\n")
    write(repo, SOURCE, "<?php class A { function b() {} }\n")

    found = status(repo, db_path)

    assert found["staleness"] == BEHIND
    assert found["dirty_indexed_files"] == 1


def test_a_dirty_but_ignored_source_file_leaves_the_index_current(repo: Path) -> None:
    """Tracked, right suffix, excluded by the ignore rules — it is not in the graph (§11)."""
    write(repo, ".codeatlasignore", "legacy/\n")
    committed(repo, {"legacy/old.php": "<?php class Old {}\n"}, message="add ignored tree")
    db_path = build_index(repo)
    write(repo, "legacy/old.php", "<?php class Old { function b() {} }\n")

    found = status(repo, db_path)

    assert found["staleness"] == CURRENT
    assert found["dirty_indexed_files"] == 0


def test_a_moved_head_is_behind_whatever_is_dirty(repo: Path) -> None:
    """Commit drift is a separate axis: scoping the dirty check must not touch it."""
    db_path = build_index(repo)
    committed(repo, {"README.md": "docs, committed\n"}, message="second")

    assert status(repo, db_path)["staleness"] == BEHIND


def test_an_index_built_before_047_falls_back_to_the_whole_tree(repo: Path) -> None:
    """No suffix stamp — over-report rather than promise a freshness that cannot be checked."""
    db_path = build_index(repo, suffixes=None)
    write(repo, "README.md", "docs, edited\n")

    found = status(repo, db_path)

    assert found["staleness"] == BEHIND
    assert found["dirty_indexed_files"] is None


def test_outside_a_git_repo_staleness_stays_unknown(tmp_path: Path) -> None:
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    with GraphStore(db_path) as store:
        store.upsert_file(SOURCE, "h", "php")
        store.replace_file_rows(SOURCE, nodes_for(SOURCE), [])
        store.set_meta(INDEXED_SUFFIXES_KEY, ".php")

    found = status(tmp_path, db_path)

    assert found["staleness"] == UNKNOWN
    assert gitutil.dirty_paths(tmp_path) is None


def test_the_minimal_payload_did_not_grow(repo: Path) -> None:
    db_path = build_index(repo)
    write(repo, SOURCE, "<?php class A { function b() {} }\n")

    minimal = status(repo, db_path, "minimal")

    assert "dirty_indexed_files" not in minimal
    assert minimal["staleness"] == BEHIND


def test_dirty_paths_names_the_files_not_just_a_flag(repo: Path) -> None:
    write(repo, "README.md", "docs, edited\n")
    write(repo, SOURCE, "<?php class A { function b() {} }\n")

    assert gitutil.dirty_paths(repo) == ("README.md", SOURCE)
    assert gitutil.working_tree_dirty(repo) is True
