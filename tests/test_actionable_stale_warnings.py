"""Task 267 — loud serve-behind for changed subjects; actionable stale-process."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import build_info
from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from code_atlas.tools.claim import REV_CHARS
from code_atlas.tools.freshness import label_serve_behind
from code_atlas.tools.nav_result import (
    REASON_INDEX_BEHIND,
    REASON_INDEX_BEHIND_SUBJECT_CHANGED,
    REASON_INDEX_STALE,
    REASON_OK,
)
from code_atlas.tools.staleness import BEHIND

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
def test_serve_behind_labels_changed_subject(
    tmp_path: Path, store: GraphStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1 — opt-in + unrepaired dirty subject → rows + subject-changed reason + revision."""
    _plant(tmp_path)
    config = load_config(tmp_path, _env())
    assert full_build(config, store).failed == 0
    indexed_rev = store.get_meta("last_commit")
    assert isinstance(indexed_rev, str) and indexed_rev
    _commit_edit(
        tmp_path,
        "src/stable.php",
        "<?php\nnamespace App;\nclass Stable { public function hit() { return 1; } "
        "public function run() { $this->hit(); } }\n",
    )
    monkeypatch.setattr(
        "code_atlas.tools.freshness.reparse_file", lambda *_a, **_k: False
    )
    payload = find_callers.create(config)(
        "\\App\\Stable::hit", detail_level="minimal", serve_behind=True
    )
    assert payload["reason"] == REASON_INDEX_BEHIND_SUBJECT_CHANGED, payload
    assert payload["last_commit"] == indexed_rev
    assert payload["results"], payload
    short = indexed_rev[:REV_CHARS]
    assert all(row.get("index_revision") == short for row in payload["results"])


@needs_php
def test_serve_behind_off_still_refuses_changed_subject(
    tmp_path: Path, store: GraphStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1 off arm — default refuse-when-stale is unchanged for a dirty subject."""
    _plant(tmp_path)
    config = load_config(tmp_path, _env())
    assert full_build(config, store).failed == 0
    _commit_edit(
        tmp_path,
        "src/stable.php",
        "<?php\nnamespace App;\nclass Stable { public function hit() { return 2; } "
        "public function run() { $this->hit(); } }\n",
    )
    monkeypatch.setattr(
        "code_atlas.tools.freshness.reparse_file", lambda *_a, **_k: False
    )
    payload = find_callers.create(config)(
        "\\App\\Stable::hit", detail_level="minimal", serve_behind=False
    )
    assert payload["reason"] == REASON_INDEX_STALE, payload
    assert payload["results"] == []


def test_behind_labelled_row_always_carries_revision() -> None:
    """AC2 — no behind-index label without a revision stamp."""
    ok = {"reason": REASON_OK, "results": [{"qname": "A::b"}]}
    labelled = label_serve_behind(
        ok,
        serve_behind=True,
        subject_path="src/a.php",
        revision={"staleness": BEHIND, "last_commit": "abcdef1234567890"},
        dirty_paths=["src/other.php"],
    )
    assert labelled["reason"] == REASON_INDEX_BEHIND
    assert labelled["last_commit"] == "abcdef1234567890"
    assert labelled["results"][0]["index_revision"] == "abcdef1"

    changed = {"reason": REASON_OK, "results": [{"qname": "A::b"}]}
    labelled2 = label_serve_behind(
        changed,
        serve_behind=True,
        subject_path="src/a.php",
        revision={"staleness": BEHIND, "last_commit": "abcdef1234567890"},
        dirty_paths=["src/a.php"],
        subject_unrepaired=True,
    )
    assert labelled2["reason"] == REASON_INDEX_BEHIND_SUBJECT_CHANGED
    assert labelled2["results"][0]["index_revision"] == "abcdef1"

    silent = label_serve_behind(
        {"reason": REASON_OK, "results": [{"qname": "A::b"}], "total_count": 1},
        serve_behind=True,
        subject_path="src/a.php",
        revision={"staleness": BEHIND, "last_commit": ""},
        dirty_paths=["src/a.php"],
        subject_unrepaired=True,
    )
    assert silent["reason"] == REASON_INDEX_STALE
    assert silent["results"] == []
    assert silent["total_count"] == 0

    no_rev = label_serve_behind(
        {"reason": REASON_OK, "results": [{"qname": "A::b"}], "total_count": 1},
        serve_behind=True,
        subject_path="src/a.php",
        revision=None,
        dirty_paths=["src/a.php"],
        subject_unrepaired=True,
    )
    assert no_rev["reason"] == REASON_INDEX_STALE
    assert no_rev["results"] == []


def test_server_stale_process_names_restart_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3 — stale_process true always names a restart action + what differs; never only /mcp."""
    build_info.reset_identity_cache()
    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", "0ldc0de")
    monkeypatch.setattr(build_info, "_git_root", lambda: tmp_path)
    monkeypatch.setattr(build_info.gitutil, "head_commit", lambda root: "abcdef1234567890")

    prov = build_info.server_provenance()
    build_info.reset_identity_cache()

    assert prov["server_stale_process"] is True
    assert prov["server_stale_action"] == build_info.SERVER_STALE_ACTION
    assert prov["server_stale_differs"] == list(build_info.SERVER_STALE_DIFFERS)
    assert "/mcp" not in str(prov["server_stale_action"]).lower()
    assert "mcp" in str(prov["server_stale_action"]).lower()
