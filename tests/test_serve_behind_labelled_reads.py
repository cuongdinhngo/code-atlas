"""Task 257 — opt-in labelled reads from a behind index for unchanged subjects."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, get_index_status
from code_atlas.tools.claim import REV_CHARS
from code_atlas.tools.nav_result import REASON_INDEX_BEHIND, REASON_INDEX_STALE, REASON_OK
from code_atlas.tools.staleness import BEHIND, CURRENT

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / ".code-atlas" / "graph.db") as opened:
        yield opened


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _plant(root: Path) -> None:
    src = root / "src"
    src.mkdir()
    (src / "stable.php").write_text(
        "<?php\nnamespace App;\nclass Stable { public function hit() {} "
        "public function run() { $this->hit(); } }\n",
        encoding="utf-8",
    )
    (src / "drift.php").write_text(
        "<?php\nnamespace App;\nclass Drift { public function run() {} }\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("docs\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")


def _env() -> dict[str, str]:
    return {
        "CA_WORKERS": "2",
        "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
    }


def _commit_edit(root: Path, rel: str, body: str) -> None:
    (root / rel).write_text(body, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "edit")


@needs_php
def test_serve_behind_labels_unchanged_subject(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1/AC4 — mode on + behind + unchanged subject → rows with revision, not reason=ok."""
    _plant(tmp_path)
    config = load_config(tmp_path, _env())
    assert full_build(config, store).failed == 0
    indexed_rev = store.get_meta("last_commit")
    assert isinstance(indexed_rev, str) and indexed_rev

    _commit_edit(
        tmp_path,
        "src/drift.php",
        "<?php\nnamespace App;\nclass Drift { public function run() { return 1; } }\n",
    )
    status = get_index_status.create(config, (get_index_status.NAME,))(
        detail_level="minimal"
    )
    assert status["staleness"] == BEHIND

    off = find_callers.create(config)("\\App\\Stable::hit", detail_level="minimal")
    assert off["reason"] == REASON_OK
    assert off["total_count"] >= 1
    assert "last_commit" not in off
    assert all("index_revision" not in row for row in off["results"])

    on = find_callers.create(config)(
        "\\App\\Stable::hit", detail_level="minimal", serve_behind=True, sign=True
    )
    assert on["reason"] == REASON_INDEX_BEHIND
    assert on["total_count"] >= 1
    assert on["last_commit"] == indexed_rev
    short = indexed_rev[:REV_CHARS]
    assert all(row.get("index_revision") == short for row in on["results"])
    claim = str(on.get("claim") or "")
    assert f"rev={short}" in claim
    assert "index=behind" in claim


@needs_php
def test_serve_behind_drifted_subject_still_declines_or_repairs(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2 — drifted subject is not silently labelled as a behind read of stale rows."""
    _plant(tmp_path)
    config = load_config(tmp_path, _env())
    assert full_build(config, store).failed == 0
    _commit_edit(
        tmp_path,
        "src/drift.php",
        "<?php\nnamespace App;\nclass Drift { public function run() { return 2; } }\n",
    )
    # Cap is 1: force unrepaired drift by also dirtying stable so ensure may stale on Drift.
    # Prefer the honest path — if repair succeeds, reason is ok (fresh), never index_behind.
    payload = find_callers.create(config)(
        "\\App\\Drift::run", detail_level="minimal", serve_behind=True
    )
    assert payload["reason"] != REASON_INDEX_BEHIND, payload
    assert payload["reason"] in {
        REASON_OK,
        REASON_INDEX_STALE,
        "no_matches",
        "index_behind_subject_changed",
    }, payload


@needs_php
def test_serve_behind_off_is_byte_identical(tmp_path: Path, store: GraphStore) -> None:
    """AC3 — default off keeps today's payload shape on a behind index."""
    _plant(tmp_path)
    config = load_config(tmp_path, _env())
    assert full_build(config, store).failed == 0
    _commit_edit(
        tmp_path,
        "src/drift.php",
        "<?php\nnamespace App;\nclass Drift { public function run() { return 3; } }\n",
    )
    a = find_callers.create(config)("\\App\\Stable::hit", detail_level="minimal")
    b = find_callers.create(config)(
        "\\App\\Stable::hit", detail_level="minimal", serve_behind=False
    )
    assert a == b
    assert a["reason"] == REASON_OK


@needs_php
def test_unindexed_markdown_dirt_does_not_degrade(tmp_path: Path, store: GraphStore) -> None:
    """AC5 — dirty unindexed files leave staleness current and do not label."""
    _plant(tmp_path)
    config = load_config(tmp_path, _env())
    assert full_build(config, store).failed == 0
    (tmp_path / "README.md").write_text("docs, edited\n", encoding="utf-8")
    status = get_index_status.create(config, (get_index_status.NAME,))(
        detail_level="minimal"
    )
    assert status["staleness"] == CURRENT
    payload = find_callers.create(config)(
        "\\App\\Stable::hit", detail_level="minimal", serve_behind=True
    )
    assert payload["reason"] == REASON_OK
    assert "last_commit" not in payload
