"""Task 274 — behind status names served families + serve_behind; not only rebuild."""

from __future__ import annotations

import json
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
from code_atlas.tools.get_index_status import (
    BEHIND_REFUSES_FIELD,
    BEHIND_SERVES_FIELD,
    BUILD_TOOL,
    CALLERS_TOOL,
    CHANGED_INDEXED_BETWEEN,
    CHANGED_INDEXED_BETWEEN_FIELD,
    CHANGED_INDEXED_FILES_FIELD,
    READ_TOOL,
    REFERENCES_TOOL,
    SEARCH_TOOL,
    SERVE_BEHIND_OPT_IN,
    SERVE_BEHIND_OPT_IN_FIELD,
)
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    TRY_INSTEAD_HINT_SERVE_BEHIND,
)
from code_atlas.tools.nav_result import (
    SERVE_BEHIND_OPT_IN_FIELD as NAV_OPT_IN_FIELD,
)
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
def test_behind_suggestions_are_not_only_build(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC — next_tool_suggestions on behind is not only the build tool."""
    _plant(tmp_path)
    config = load_config(tmp_path, _env())
    assert full_build(config, store).failed == 0
    status_fn = get_index_status.create(
        config, ["get_index_status", BUILD_TOOL, SEARCH_TOOL, READ_TOOL]
    )
    current = status_fn(detail_level="minimal")
    assert current["staleness"] == CURRENT
    assert "next_tool_suggestions" not in current
    assert BEHIND_SERVES_FIELD not in current
    assert SERVE_BEHIND_OPT_IN_FIELD not in current

    _commit_edit(
        tmp_path,
        "src/drift.php",
        "<?php\nnamespace App;\nclass Drift { public function run() { return 1; } }\n",
    )
    behind = status_fn(detail_level="minimal")
    assert behind["staleness"] == BEHIND
    suggestions = behind["next_tool_suggestions"]
    assert BUILD_TOOL in suggestions
    assert SEARCH_TOOL in suggestions
    assert READ_TOOL in suggestions
    assert suggestions != [BUILD_TOOL]
    assert behind[BEHIND_SERVES_FIELD] == [SEARCH_TOOL, READ_TOOL]
    assert behind[BEHIND_REFUSES_FIELD] == [CALLERS_TOOL, REFERENCES_TOOL]
    assert behind[SERVE_BEHIND_OPT_IN_FIELD] == SERVE_BEHIND_OPT_IN
    assert behind[CHANGED_INDEXED_BETWEEN_FIELD] == list(CHANGED_INDEXED_BETWEEN)
    assert CHANGED_INDEXED_FILES_FIELD not in behind  # minimal: no extra git (274)

    standard = status_fn(detail_level="standard")
    assert standard[CHANGED_INDEXED_FILES_FIELD] >= 1
    assert standard[SERVE_BEHIND_OPT_IN_FIELD] == SERVE_BEHIND_OPT_IN
    assert standard[CHANGED_INDEXED_BETWEEN_FIELD] == list(CHANGED_INDEXED_BETWEEN)


@needs_php
def test_current_index_status_byte_identical(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC — a current-index status stays free of behind-only fields."""
    _plant(tmp_path)
    config = load_config(tmp_path, _env())
    assert full_build(config, store).failed == 0
    status_fn = get_index_status.create(
        config, ["get_index_status", BUILD_TOOL, SEARCH_TOOL, READ_TOOL]
    )
    for level in ("minimal", "standard"):
        payload = status_fn(detail_level=level)
        assert payload["staleness"] == CURRENT
        assert BEHIND_SERVES_FIELD not in payload
        assert BEHIND_REFUSES_FIELD not in payload
        assert SERVE_BEHIND_OPT_IN_FIELD not in payload
        assert CHANGED_INDEXED_FILES_FIELD not in payload
        assert CHANGED_INDEXED_BETWEEN_FIELD not in payload
        # Round-trip: no behind keys appear after a deepcopy serialize check.
        assert json.loads(json.dumps(payload)) == payload


@needs_php
def test_index_stale_refusal_names_serve_behind(
    tmp_path: Path, store: GraphStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC — index_stale on a drifted subject names serve_behind in its route."""
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
    assert payload[NAV_OPT_IN_FIELD] == SERVE_BEHIND_OPT_IN
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_SERVE_BEHIND
    assert "try_instead" not in payload


def test_unbuilt_status_does_not_gain_behind_fields(tmp_path: Path) -> None:
    """No behind disclosure and no git spawn on the unbuilt path (077 / 274)."""
    config = load_config(tmp_path, {"CA_WORKERS": "1"})
    status_fn = get_index_status.create(config, ["get_index_status", BUILD_TOOL])
    unbuilt = status_fn(detail_level="minimal")
    assert unbuilt["indexed"] is False
    assert unbuilt["next_tool_suggestions"] == [BUILD_TOOL]
    assert BEHIND_SERVES_FIELD not in unbuilt
    assert SERVE_BEHIND_OPT_IN_FIELD not in unbuilt
    assert CHANGED_INDEXED_FILES_FIELD not in unbuilt
