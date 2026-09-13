"""259: CA_MAX_RESULTS is no longer both the page cap and the resolver fan-out."""

from __future__ import annotations

from pathlib import Path

from code_atlas.config import (
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_PAGE_LIMIT,
    PROJECT_FILE,
    clamp_limit,
    config_identity,
    load_config,
)


def test_ca_max_results_alone_yields_fanout_10_and_page_50(tmp_path: Path) -> None:
    """AC3 proving test: disk pin of 10 must not shrink pages to 10."""
    config = load_config(tmp_path, {"CA_MAX_RESULTS": "10"})
    assert config.max_candidates == 10
    assert config.page_limit == 50
    cap, clamped = clamp_limit(100, config.page_limit)
    assert cap == 50 and clamped is True


def test_defaults_and_independence(tmp_path: Path) -> None:
    """AC2: defaults stay 50; fan-out env does not move page; page env does not move fan-out."""
    plain = load_config(tmp_path, {})
    assert plain.page_limit == DEFAULT_PAGE_LIMIT == 50
    assert plain.max_candidates == DEFAULT_MAX_CANDIDATES == 50

    fan = load_config(tmp_path, {"CA_MAX_CANDIDATES": "7"})
    assert fan.max_candidates == 7
    assert fan.page_limit == 50

    page = load_config(tmp_path, {"CA_PAGE_LIMIT": "12"})
    assert page.page_limit == 12
    assert page.max_candidates == 50


def test_project_file_max_results_alias_is_fanout_only(tmp_path: Path) -> None:
    (tmp_path / PROJECT_FILE).write_text("max_results = 10\n", encoding="utf-8")
    config = load_config(tmp_path, {})
    assert config.max_candidates == 10
    assert config.page_limit == 50


def test_indexer_uses_max_candidates_not_max_results() -> None:
    """AC1: indexer.py must not thread config.max_results into resolve_edges."""
    source = Path("code_atlas/indexer.py").read_text(encoding="utf-8")
    assert "config.max_results" not in source
    assert source.count("max_candidates=config.max_candidates") == 2


def test_indexer_does_not_read_page_limit() -> None:
    """AC2: page cap cannot change edge counts because the indexer never reads it."""
    source = Path("code_atlas/indexer.py").read_text(encoding="utf-8")
    assert "page_limit" not in source
    assert "config.max_candidates" in source


def test_page_limit_change_does_not_force_rebuild_identity(tmp_path: Path) -> None:
    """Changing the page cap must not move config identity (no rebuild)."""
    base = config_identity(tmp_path, {})
    assert config_identity(tmp_path, {"CA_PAGE_LIMIT": "3"}) == base
    assert config_identity(tmp_path, {"CA_MAX_CANDIDATES": "3"}) != base
    assert config_identity(tmp_path, {"CA_MAX_RESULTS": "3"}) != base


def test_runbook_states_which_key_needs_rebuild() -> None:
    """AC4: runbook names rebuild vs not."""
    text = Path("docs/runbooks/onboarding-a-repo.md").read_text(encoding="utf-8")
    assert "CA_MAX_CANDIDATES" in text or "max_candidates" in text
    assert "CA_PAGE_LIMIT" in text or "page_limit" in text
    assert "rebuild" in text.lower()
