"""Task 261 — per-language edge-health verdict at ``standard``; ``pairs`` stay verbose-only.

The README listed four adapters as peers while HEURISTIC CALLS runs 1–4 % on PHP and 82 % on
Python. The stamp that would say so already existed; only ``verbose`` carried it. Spec-driven
fixtures reuse 183's ``fake``/``second`` adapters (R2/R6.2).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from code_atlas import adapter
from code_atlas.store import EDGE_HEALTH_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import get_index_status
from code_atlas.tools.get_index_status import EDGE_HEALTH_BY_LANGUAGE_FIELD
from tests.test_edge_health_per_language import (
    ONE_ADAPTER,
    TWO_ADAPTERS,
    build,
    seed_two_languages,
    write,
)

FIELD = EDGE_HEALTH_BY_LANGUAGE_FIELD
REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"

# Report outputs the README must quote (R6.7) — produced by scripts/edge_health_report.py.
REPORT_SOURCES = {
    "1–4 %": REPO / "docs/benchmarks/137_type-table.md",
    # edge_health_report --only ky / --only flask
    "54.1%": REPO / "docs/benchmarks/153_227_heuristic-share-ts-python.md",
    "82.2%": REPO / "docs/benchmarks/153_227_heuristic-share-ts-python.md",
}


@pytest.fixture(autouse=True)
def only_these_adapters_ship(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "shipped"
    for name in ("fake", "second"):
        (root / name / "src").mkdir(parents=True)
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", root)


def test_standard_carries_per_language_verdict_without_pairs(tmp_path: Path) -> None:
    """AC1: ``standard`` has ``unlinked``/``by_tier`` per language; ``pairs`` stay verbose-only."""
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    tool = get_index_status.create(config, (get_index_status.NAME,))

    standard = tool(detail_level="standard")
    assert FIELD in standard
    block = standard[FIELD]
    assert "cross_language" not in block  # type: ignore[operator]
    assert "pairs" not in json.dumps(block)
    by_language = dict(block["by_language"])  # type: ignore[index]
    assert sorted(by_language) == ["fake", "second"]
    for bucket in by_language.values():
        assert set(bucket) == {"unlinked", "by_tier"}  # type: ignore[arg-type]
        assert "linked" not in bucket  # type: ignore[operator]

    assert FIELD not in tool(detail_level="minimal")

    verbose = tool(detail_level="verbose")
    full = verbose[FIELD]
    assert "cross_language" in full  # type: ignore[operator]
    assert "pairs" in full["cross_language"]  # type: ignore[index]
    # Verbose replaces the verdict with the full stamp (linked returns).
    fake = dict(full["by_language"])["fake"]  # type: ignore[index]
    assert "linked" in fake


def test_standard_verdict_is_one_meta_read_never_a_live_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1: no query-time scan — live fold must not run on the answer path."""
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)

    def boom(self: GraphStore) -> dict[str, object]:
        raise AssertionError("live edge_health_by_language must not run at answer time")

    monkeypatch.setattr(GraphStore, "edge_health_by_language", boom)
    payload = get_index_status.create(config, (get_index_status.NAME,))(
        detail_level="standard"
    )
    assert FIELD in payload


def test_single_language_and_missing_stamp_stay_silent(tmp_path: Path) -> None:
    """061 / R5.6: one bucket or no stamp → omit the field."""
    write(tmp_path, "lib/core.aa")
    write(tmp_path, "dep/a.aa")
    one = get_index_status.create(build(tmp_path, ONE_ADAPTER), (get_index_status.NAME,))(
        detail_level="standard"
    )
    assert FIELD not in one

    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    with GraphStore(config.db_path) as store:
        store.delete_meta(EDGE_HEALTH_BY_LANGUAGE_KEY)
    assert FIELD not in get_index_status.create(config, (get_index_status.NAME,))(
        detail_level="standard"
    )


def test_readme_adapter_heuristic_figures_quote_the_report() -> None:
    """AC2/AC3: README HEURISTIC CALLS figures match the report outputs they quote."""
    text = README.read_text(encoding="utf-8")
    assert "edge_health_report.py" in text
    assert "depth standard" in text.lower()
    for figure, source in REPORT_SOURCES.items():
        assert figure in text, f"README must state {figure}"
        assert figure in source.read_text(encoding="utf-8"), (
            f"{figure} must still appear in {source.relative_to(REPO)} "
            "(the report output the README quotes)"
        )
    # T-SQL is not a CALLS-HEURISTIC peer — 233_sql says so.
    assert "T-SQL" in text
    assert "HEURISTIC" in text and "CALLS" in text
    # No deepening ticket proposed by this change.
    assert "deepen Python" not in text
    assert "deepen TypeScript" not in text
    assert "deepen TS" not in text
