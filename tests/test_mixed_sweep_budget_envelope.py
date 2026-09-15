"""Task 275 — mixed sweep envelope + kind-excluded vs absence."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import search_symbol
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_KIND_EXCLUDED,
    REASON_OK,
    RETRY_AS_FIELD,
    RETRY_AS_QUERY,
    TRY_INSTEAD_HINT_SINGLE_SUBJECT_REPAIR,
)
from tests.test_nav_tools import node, seed_file

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


def _env() -> dict[str, str]:
    return {
        "CA_WORKERS": "2",
        "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
    }


def _plant_php(root: Path) -> None:
    src = root / "src"
    src.mkdir()
    for name, body in (
        (
            "a.php",
            "<?php\nnamespace App;\nclass Alpha { public function run() {} }\n",
        ),
        (
            "b.php",
            "<?php\nnamespace App;\nclass Beta { public function run() {} }\n",
        ),
        (
            "c.php",
            "<?php\nnamespace App;\nclass Gamma { public function run() {} }\n",
        ),
        (
            "d.php",
            "<?php\nnamespace App;\nclass Drift { public function run() {} }\n",
        ),
    ):
        (src / name).write_text(body, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")


@needs_php
def test_mixed_sweep_envelope_names_stale_subject(
    tmp_path: Path, store: GraphStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1/AC2 — mixed ok+index_stale names the refused subject + single-subject route."""
    _plant_php(tmp_path)
    config = load_config(tmp_path, _env())
    assert full_build(config, store).failed == 0
    (tmp_path / "src" / "d.php").write_text(
        "<?php\nnamespace App;\nclass Drift { public function run() { return 1; } }\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "code_atlas.tools.freshness.reparse_file", lambda *_a, **_k: False
    )
    tool = search_symbol.create(config)
    payload = tool(
        queries=["\\App\\Alpha", "\\App\\Beta", "\\App\\Gamma", "\\App\\Drift"],
        detail_level="minimal",
    )
    by_q = {s["query"]: s for s in payload["subjects"]}
    assert by_q["\\App\\Alpha"]["reason"] == REASON_OK
    assert by_q["\\App\\Beta"]["reason"] == REASON_OK
    assert by_q["\\App\\Gamma"]["reason"] == REASON_OK
    assert by_q["\\App\\Drift"]["reason"] == REASON_INDEX_STALE
    assert payload["repair_budget_shared"] is True
    assert payload["index_stale_subjects"] == ["\\App\\Drift"]
    assert payload["repair_budget_order"] == "queries"
    refused = by_q["\\App\\Drift"]
    assert refused[RETRY_AS_FIELD] == RETRY_AS_QUERY
    assert refused["try_instead_hint"] == TRY_INSTEAD_HINT_SINGLE_SUBJECT_REPAIR
    assert "try_instead" not in refused
    for q in ("\\App\\Alpha", "\\App\\Beta", "\\App\\Gamma"):
        assert RETRY_AS_FIELD not in by_q[q]
        assert "try_instead_hint" not in by_q[q]


@needs_php
def test_fully_ok_sweep_byte_identical(tmp_path: Path, store: GraphStore) -> None:
    """AC4 — every-ok sweep gains no envelope fields."""
    _plant_php(tmp_path)
    config = load_config(tmp_path, _env())
    assert full_build(config, store).failed == 0
    tool = search_symbol.create(config)
    payload = tool(
        queries=["\\App\\Alpha", "\\App\\Beta", "\\App\\Gamma"],
        detail_level="minimal",
    )
    assert all(s["reason"] == REASON_OK for s in payload["subjects"])
    assert "repair_budget_shared" not in payload
    assert "index_stale_subjects" not in payload
    assert "repair_budget_order" not in payload
    assert json.loads(json.dumps(payload)) == payload


def test_kind_filter_exclusion_is_not_absence(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC3 — kind=Table excluding a View exact hit reports kind_excluded."""
    seed_file(
        store,
        "schema.sql",
        [node("View", "Schedule_Detail", "dbo.Schedule_Detail", "schema.sql")],
        [],
        root=tmp_path,
    )
    config = replace(load_config(tmp_path, {}), db_path=tmp_path / ".code-atlas" / "graph.db")
    payload = search_symbol.create(config)(
        query="Schedule_Detail", kind="Table", detail_level="minimal"
    )
    assert payload["reason"] == REASON_KIND_EXCLUDED
    assert payload["results"] == []
    assert payload["kind_excluded"] == ["View"]
    assert payload["total_count"] == 0
