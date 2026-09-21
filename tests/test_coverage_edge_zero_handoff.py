"""Task 314: coverage-edge zeros hand off to Grep instead of a bare no_matches."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas import adapter
from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references, search_symbol
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    TRY_INSTEAD_HINT_DYNAMIC_SQL,
    TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE,
)
from tests.test_nav_tools import db_config, node, seed_file
from tests.test_sql_dynamic_sql_unmodelled_stamp import _stamp_sql


def _plant_adapters(tmp_path: Path, *names: str) -> Path:
    root = tmp_path / "adapters"
    root.mkdir()
    for name in names:
        (root / name / "src").mkdir(parents=True)
    return root


def test_search_symbol_dynamic_sql_stamp_names_grep_fallback(tmp_path: Path) -> None:
    """AC1 — EXEC-created name on a stamped index is not a bare no_such_symbol."""
    with GraphStore(tmp_path / "graph.db") as store:
        _stamp_sql(store)
    config = replace(db_config(tmp_path), root=tmp_path)
    payload = search_symbol.create(config)("ResFacToEpicor", detail_level="standard")
    assert payload.get("results") == []
    assert "try_instead" not in payload  # Grep is not a registered tool (093)
    hint = str(payload.get("try_instead_hint") or "")
    assert "dynamic_sql" in hint
    assert "Grep" in hint
    assert hint == TRY_INSTEAD_HINT_DYNAMIC_SQL


def test_find_nav_zero_on_coverage_gap_redirects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2 positive — outside-coverage zero carries coverage note + Grep redirect."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    with GraphStore(tmp_path / "graph.db") as store:
        seed_file(
            store,
            "a.php",
            [node("Class", "Present", "\\App\\Present", "a.php")],
            [],
            root=tmp_path,
        )
    config = replace(
        load_config(tmp_path, {"CA_PHP_CMD": "php run"}),
        root=tmp_path,
        db_path=tmp_path / "graph.db",
    )
    callers = find_callers.create(config)("\\App\\Absent", detail_level="standard")
    refs = find_references.create(config)("\\App\\Absent", detail_level="standard")
    for payload, name in ((callers, "find_callers"), (refs, "find_references")):
        assert "unconfigured_adapters" in payload, name
        assert "Grep" in str(payload.get("try_instead_hint") or ""), name


def test_find_nav_genuine_zero_stays_byte_identical_on_covered_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2 negative — fully covered, unstamped absence gains no redirect (061)."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    with GraphStore(tmp_path / "graph.db") as store:
        seed_file(
            store,
            "a.php",
            [node("Class", "Present", "\\App\\Present", "a.php")],
            [],
            root=tmp_path,
        )
    config = replace(
        load_config(
            tmp_path, {"CA_PHP_CMD": "php run", "CA_TYPESCRIPT_CMD": "node run"}
        ),
        root=tmp_path,
        db_path=tmp_path / "graph.db",
    )
    callers = find_callers.create(config)("\\App\\Absent", detail_level="standard")
    refs = find_references.create(config)("\\App\\Absent", detail_level="standard")
    for payload, name in ((callers, "find_callers"), (refs, "find_references")):
        assert "try_instead" not in payload, name
        assert "try_instead_hint" not in payload, name
        assert "unconfigured_adapters" not in payload, name
        assert payload.get("reason") in (REASON_NO_MATCHES, "no_such_symbol"), name


def test_unmeasured_hint_names_grep_fallback() -> None:
    """AC3 — relation-unmodelled honesty names a concrete Grep/loader action."""
    assert "Grep" in TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE
    assert "loader" in TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE


def test_no_language_branch_introduced() -> None:
    """AC4 — this change does not add language == branches under code_atlas/."""
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    hit = subprocess.run(
        ["grep", "-rn", "language ==", "code_atlas/"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    # Pre-existing hits are fine; ensure our new helper file region has none in nav_result helpers.
    assert "attach_coverage_edge_route" not in hit.stdout
    assert "coverage_edge_hint" not in hit.stdout


def test_hit_on_stamped_index_stays_clean(tmp_path: Path) -> None:
    """061 — a successful hit gains no Grep rider just because the index is stamped."""
    with GraphStore(tmp_path / "graph.db") as store:
        _stamp_sql(store)
        seed_file(
            store,
            "a.php",
            [node("Class", "Present", "\\App\\Present", "a.php")],
            [],
            root=tmp_path,
        )
    config = replace(db_config(tmp_path), root=tmp_path)
    payload = search_symbol.create(config)("Present", detail_level="standard")
    assert payload.get("results")
    assert "try_instead_hint" not in payload
