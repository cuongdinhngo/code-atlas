"""Task 246: ensure_miss refuses on the subject, not on the count of drifted files.

READ_THROUGH_CAP verdict (AC4): keep = 1. On the AC1 fixture (4 indexed files, 3 unrelated
committed drifts + current subject) a subject-scoped miss performs 0 reparses when the subject
file is current; raising the cap with dirty-count would reparse the branch on one call.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol, search_symbol
from code_atlas.tools.freshness import FreshnessGuard, nameable_subject_path
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_SUCH_SYMBOL,
    REASON_SUBJECT_FILE_CHECKED,
)
from tests.test_read_through_freshness import config_for, write


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _git_commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", message],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _index_with_subject_and_three_unrelated(tmp_path: Path) -> tuple[object, str]:
    """Index four files; leave subject current; commit drifts on the other three (AC1/AC5)."""
    write(tmp_path, "src/Subject.aa", "class Subject {}\n")
    write(tmp_path, "src/A.aa", "class A {}\n")
    write(tmp_path, "src/B.aa", "class B {}\n")
    write(tmp_path, "src/C.aa", "class C {}\n")
    _git_init(tmp_path)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    write(tmp_path, "src/A.aa", "class A {}\n# drift a\n")
    _git_commit_all(tmp_path, "drift A")
    write(tmp_path, "src/B.aa", "class B {}\n# drift b\n")
    _git_commit_all(tmp_path, "drift B")
    write(tmp_path, "src/C.aa", "class C {}\n# drift c\n")
    _git_commit_all(tmp_path, "drift C")
    return config, "src/Subject.aa::MissingSymbol"


def test_miss_on_current_subject_amid_three_unrelated_drifts_discloses_residue(
    tmp_path: Path,
) -> None:
    """AC1/AC5: path-named miss amid three unrelated drifts is not index_stale."""
    config, subject = _index_with_subject_and_three_unrelated(tmp_path)
    result = read_symbol.create(config)(subject, detail_level="minimal")
    assert result["reason"] == REASON_SUBJECT_FILE_CHECKED, result
    assert result["stale"] is False
    assert result["found"] is False
    assert result["other_indexed_files_drifted"] == 3
    assert result["reason"] != REASON_INDEX_STALE
    assert result["reason"] != REASON_NO_SUCH_SYMBOL


def test_unnameable_subject_amid_multi_drift_still_index_stale(tmp_path: Path) -> None:
    """AC2: bare search (no files-table path) keeps the count-based refuse."""
    config, _ = _index_with_subject_and_three_unrelated(tmp_path)
    result = search_symbol.create(config)("definitelyAbsentZq9", detail_level="minimal")
    assert result["reason"] == REASON_INDEX_STALE, result
    assert result["total_count"] == 0
    assert "other_indexed_files_drifted" not in result


def test_clean_tree_miss_omits_residue_key(tmp_path: Path) -> None:
    """AC3: clean tree stays omit-when-empty (061) — no residue key."""
    write(tmp_path, "src/Subject.aa", "class Subject {}\n")
    _git_init(tmp_path)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    result = read_symbol.create(config)("src/Subject.aa::MissingSymbol", detail_level="minimal")
    assert result["reason"] == REASON_NO_SUCH_SYMBOL
    assert "other_indexed_files_drifted" not in result
    # Byte-stable key set vs a second identical call.
    again = read_symbol.create(config)("src/Subject.aa::MissingSymbol", detail_level="minimal")
    assert json.dumps(result, sort_keys=True) == json.dumps(again, sort_keys=True)


def test_nameable_subject_path_from_files_table(tmp_path: Path) -> None:
    write(tmp_path, "src/Widget.aa", "class Widget {}\n")
    _git_init(tmp_path)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        assert nameable_subject_path(store, "src/Widget.aa::Missing") == "src/Widget.aa"
        assert nameable_subject_path(store, "\\App\\Widget::Missing") is None


def test_ensure_miss_subject_current_among_dirty_is_ok(tmp_path: Path) -> None:
    config, subject = _index_with_subject_and_three_unrelated(tmp_path)
    with GraphStore(config.db_path) as store:
        guard = FreshnessGuard(config, store)
        assert guard.ensure_miss("src/Subject.aa") == "ok"
        assert guard.other_indexed_files_drifted == 3
        assert guard.ensure_miss(None) == "stale"


def test_batch_residue_belongs_to_the_subject_that_earned_it(tmp_path: Path) -> None:
    """Review / 101: one guard serves the sweep, so residue must not cross subjects.

    A confident hit that never ran a subject check must read the same batched as alone (061).
    """
    config, subject = _index_with_subject_and_three_unrelated(tmp_path)
    tool = search_symbol.create(config)
    swept = tool(queries=[subject, "Subject"], detail_level="minimal")["subjects"]
    missed, hit = swept[0], swept[1]
    assert missed["reason"] == REASON_SUBJECT_FILE_CHECKED
    assert missed["other_indexed_files_drifted"] == 3
    assert hit["total_count"] == 1
    assert "other_indexed_files_drifted" not in hit
    alone = tool(queries=["Subject"], detail_level="minimal")["subjects"][0]
    assert json.dumps(hit, sort_keys=True) == json.dumps(alone, sort_keys=True)
