"""Task 160 — a zero answer names the index's language coverage; include_graph inbound is not bare.

AC1: a genuine-absence answer (no_matches / no_such_symbol) on an index with a shipped-but-unwired
adapter carries ``unconfigured_adapters`` — distinct from the same miss on a fully-wired index.
AC2: ``include_graph(..., imported_by)`` never ships a bare ``results: []`` with no reason. The note
names what the index does not cover, never the subject's own language (160 out of scope).

**160's AC3 was REVERSED by task 192** — see ``test_a_partial_answer_now_carries_the_note``. It read
"a confident non-empty answer is byte-identical", and field retro 8-A measured what that exempted:
one hit returned with ``reason: ok`` for a symbol with 281 real sites in an unindexed language.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas import adapter
from code_atlas.config import load_config
from code_atlas.tools import coverage, find_references, include_graph, search_symbol
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_SUBSTRING_MATCH,
)
from tests.test_nav_tools import (  # noqa: F401 — store is a fixture
    db_config,
    node,
    seed_file,
    store,
)

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


def test_a_partial_answer_now_carries_the_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """192 AC1 — and this test REPLACES 160's AC3, deliberately.

    160 asserted the opposite: results present ⇒ no note, even with a coverage gap. Field retro
    8-A measured the cost of that exemption — ``search_symbol("DialogueService")`` answered one
    hit with ``reason: ok`` while **281 `.js` files** referenced it, in a language the index does
    not hold. The gap belongs to the INDEX, not to how many rows came back.
    """
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = load_config(tmp_path, {"CA_PHP_CMD": "php run"})
    payload = {"indexed": True, "results": [{"qname": "\\X"}], "reason": "ok", "total_count": 1}
    coverage.attach_coverage_note(payload, config)
    assert payload["unconfigured_adapters"] == _TS_GAP


def test_a_partial_answer_on_a_covered_index_gets_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """192 AC2 — the no-false-alarm half, and the reason 192 is safe to apply to every answer.

    Omit-when-empty (061) does the work: an index with no coverage gap is byte-identical whether
    the answer carries results or not. Without this, widening the note would put a field on every
    payload of every fully-configured server.
    """
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = load_config(tmp_path, {"CA_PHP_CMD": "php run", "CA_TYPESCRIPT_CMD": "node run"})
    payload = {"indexed": True, "results": [{"qname": "\\X"}], "reason": "ok", "total_count": 1}
    coverage.attach_coverage_note(payload, config)
    assert payload == {
        "indexed": True,
        "results": [{"qname": "\\X"}],
        "reason": "ok",
        "total_count": 1,
    }


def test_a_not_indexed_or_stale_answer_with_results_still_gets_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """192 AC3 — the gates 160 built that must survive the widening, now with results present."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = load_config(tmp_path, {"CA_PHP_CMD": "php run"})
    rows = [{"qname": "\\X"}]
    not_indexed = {"indexed": False, "results": rows, "reason": "ok", "total_count": 1}
    stale = {"indexed": True, "results": rows, "reason": REASON_INDEX_STALE, "total_count": 1}
    coverage.attach_coverage_note(not_indexed, config)
    coverage.attach_coverage_note(stale, config)
    assert "unconfigured_adapters" not in not_indexed
    assert "unconfigured_adapters" in stale  # stale-with-results is a partial answer too


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
    result = search_symbol.create(config)("iziToast", detail_level="standard")
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


def test_substring_near_miss_is_labelled_and_carries_the_gap(
    tmp_path: Path, store, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    """167 AC1/AC2: asking for a symbol that exists only as a substring of another is a near-miss.

    The `storeCRM` → `restoreCRM` shape with generic names (R2): the query matches `resetPaginate`
    as a substring but is neither an exact nor a prefix match, so the answer is `substring_match`,
    not `ok`, and 160's coverage note rides it despite the row being present.
    """
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = replace(
        load_config(tmp_path, {"CA_PHP_CMD": "php run"}), db_path=tmp_path / "graph.db"
    )
    seed_file(
        store,
        "a.php",
        [node("Method", "resetPaginate", "\\Ns\\Model::resetPaginate", "a.php")],
        [],
        root=tmp_path,
    )
    result = search_symbol.create(config)("paginate", detail_level="standard")
    assert result["total_count"] == 1
    assert result["reason"] == REASON_SUBSTRING_MATCH
    assert result["results"][0]["qname"] == "\\Ns\\Model::resetPaginate"
    assert result["unconfigured_adapters"] == _TS_GAP


def test_exact_and_prefix_matches_stay_ok_and_now_carry_the_gap(
    tmp_path: Path, store, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    """167 AC3's `reason` half is unchanged; 160's no-note half is REVERSED by 192.

    An exact match is still `ok` — that is 167's labelling and 192 does not touch it. What changes
    is that a confident answer on an index missing a whole language now says so: 8-A's one hit
    against 281 real sites was `ok` too, and being right about the rows it had is exactly why the
    answer was believed.
    """
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = replace(
        load_config(tmp_path, {"CA_PHP_CMD": "php run"}), db_path=tmp_path / "graph.db"
    )
    seed_file(
        store,
        "a.php",
        [
            node("Method", "paginate", "\\Ns\\Model::paginate", "a.php"),
            node("Method", "paginateQuery", "\\Ns\\Model::paginateQuery", "a.php"),
        ],
        [],
        root=tmp_path,
    )
    exact = search_symbol.create(config)("paginate", detail_level="standard")
    assert exact["reason"] == "ok"
    assert exact["unconfigured_adapters"] == _TS_GAP
    prefix = search_symbol.create(config)("paginateQ", detail_level="standard")
    assert prefix["reason"] == "ok"
    assert prefix["unconfigured_adapters"] == _TS_GAP


def test_sweep_substring_near_miss_names_the_gap_on_the_envelope(
    tmp_path: Path, store, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    """167 AC4: the sweep path carries the same discriminator + envelope note (160 AC1e lesson)."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = replace(
        load_config(tmp_path, {"CA_PHP_CMD": "php run"}), db_path=tmp_path / "graph.db"
    )
    seed_file(
        store,
        "a.php",
        [node("Method", "resetPaginate", "\\Ns\\Model::resetPaginate", "a.php")],
        [],
        root=tmp_path,
    )
    result = search_symbol.create(config)(queries=["paginate"])
    assert result["subjects"][0]["reason"] == REASON_SUBSTRING_MATCH
    assert result["subjects"][0]["total_count"] == 1
    assert result["unconfigured_adapters"] == _TS_GAP


def test_coverage_note_rides_a_substring_match_with_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """167 AC2: the note attaches on a substring_match answer even though it carries results."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = load_config(tmp_path, {"CA_PHP_CMD": "php run"})
    payload = {
        "indexed": True,
        "results": [{"qname": "\\Ns\\Model::resetPaginate"}],
        "reason": REASON_SUBSTRING_MATCH,
        "total_count": 1,
    }
    coverage.attach_coverage_note(payload, config)
    assert payload["unconfigured_adapters"] == _TS_GAP


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


def test_minimal_omits_the_coverage_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """223: demote unconfigured_adapters off minimal — ask standard/verbose for the note."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = load_config(tmp_path, {"CA_PHP_CMD": "php run"})
    payload = {"indexed": True, "results": [{"qname": "\\X"}], "reason": "ok", "total_count": 1}
    coverage.attach_coverage_note(payload, config, detail_level="minimal")
    assert "unconfigured_adapters" not in payload
    coverage.attach_coverage_note(payload, config, detail_level="standard")
    assert payload["unconfigured_adapters"] == _TS_GAP
