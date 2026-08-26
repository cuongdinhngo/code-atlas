"""Task 160 — a zero answer names the index's language coverage; include_graph inbound is not bare.

AC1: a genuine-absence answer (no_matches / no_such_symbol) on an index with a shipped-but-unwired
adapter carries ``unconfigured_adapters`` — distinct from the same miss on a fully-wired index.
AC2: ``include_graph(..., imported_by)`` never ships a bare ``results: []`` with no reason. AC3: a
confident non-empty answer is byte-identical. The note names what the index does not cover, never
the subject's own language (160 out of scope).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas import adapter
from code_atlas.config import load_config
from code_atlas.tools import coverage, find_references, include_graph, search_symbol
from code_atlas.tools.nav_result import REASON_INDEX_STALE, REASON_NO_MATCHES
from tests.test_nav_tools import db_config, seed_file, store  # noqa: F401 — store is a fixture

_TS_GAP = [{"language": "typescript", "enable": "CA_TYPESCRIPT_CMD"}]


def _plant_adapters(tmp_path: Path, *names: str) -> Path:
    root = tmp_path / "adapters"
    root.mkdir()
    for name in names:
        (root / name / "src").mkdir(parents=True)
    return root


# --- coverage helper gating (AC1 / AC3, no index needed) ---------------------------------------


def test_note_rides_an_indexed_genuine_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = load_config(tmp_path, {"CA_PHP_CMD": "php run"})
    payload = {"indexed": True, "results": [], "reason": REASON_NO_MATCHES, "total_count": 0}
    coverage.attach_coverage_note(payload, config)
    assert payload["unconfigured_adapters"] == _TS_GAP


def test_a_fully_wired_index_adds_no_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC1: the same miss on an index with no coverage gap is a bare typo miss — no note."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = load_config(tmp_path, {"CA_PHP_CMD": "php run", "CA_TYPESCRIPT_CMD": "node run"})
    payload = {"indexed": True, "results": [], "reason": REASON_NO_MATCHES, "total_count": 0}
    coverage.attach_coverage_note(payload, config)
    assert "unconfigured_adapters" not in payload


def test_a_confident_non_empty_answer_is_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3: results present ⇒ no note, even with a coverage gap."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = load_config(tmp_path, {"CA_PHP_CMD": "php run"})
    payload = {"indexed": True, "results": [{"qname": "\\X"}], "reason": "ok", "total_count": 1}
    coverage.attach_coverage_note(payload, config)
    assert "unconfigured_adapters" not in payload


def test_not_indexed_and_stale_answers_get_no_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = load_config(tmp_path, {"CA_PHP_CMD": "php run"})
    not_indexed = {"indexed": False, "results": [], "reason": REASON_NO_MATCHES}
    stale = {"indexed": True, "results": [], "reason": REASON_INDEX_STALE, "total_count": 0}
    coverage.attach_coverage_note(not_indexed, config)
    coverage.attach_coverage_note(stale, config)
    assert "unconfigured_adapters" not in not_indexed
    assert "unconfigured_adapters" not in stale


# --- through the tools (store-based, no PHP) ----------------------------------------------------


def test_find_references_miss_names_the_coverage_gap(
    tmp_path: Path, store, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    """AC1: a no_such_symbol miss carries the gap so it is not read as absence."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = replace(
        load_config(tmp_path, {"CA_PHP_CMD": "php run"}), db_path=tmp_path / "graph.db"
    )
    result = find_references.create(config)("\\App\\Nope")
    assert result["total_count"] == 0
    assert result["unconfigured_adapters"] == _TS_GAP


def test_search_symbol_miss_names_the_coverage_gap(
    tmp_path: Path, store, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    """AC1: search_symbol's empty answer carries the gap (the 8-A / iziToast shape)."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = replace(
        load_config(tmp_path, {"CA_PHP_CMD": "php run"}), db_path=tmp_path / "graph.db"
    )
    result = search_symbol.create(config)("iziToast", detail_level="minimal")
    assert result["total_count"] == 0
    assert result["unconfigured_adapters"] == _TS_GAP


def test_search_symbol_sweep_names_the_coverage_gap(
    tmp_path: Path, store, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    """AC1e: the batch/sweep entry (queries=[...]) carries the gap on the envelope too."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = replace(
        load_config(tmp_path, {"CA_PHP_CMD": "php run"}), db_path=tmp_path / "graph.db"
    )
    result = search_symbol.create(config)(queries=["iziToast"])
    assert result["subjects"][0]["total_count"] == 0
    assert result["unconfigured_adapters"] == _TS_GAP


def test_include_graph_imported_by_is_never_a_bare_zero(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """AC2: an empty imported_by answer carries a reason, not a bare []. A file with no unlinked
    mentions is a genuine zero → no_matches (065 keeps that distinct from not-modelled).
    """
    seed_file(store, "a.php", [], [], root=tmp_path)
    config = db_config(tmp_path)
    result = include_graph.create(config)("a.php", direction="imported_by")
    assert result["results"] == []
    assert result["reason"] == REASON_NO_MATCHES
