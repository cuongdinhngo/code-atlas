"""Task 306: bounded agent change brief from explicit graph seeds."""

from __future__ import annotations

from pathlib import Path

import pytest

from code_atlas.change_brief import (
    DEFAULT_BRIEF_TOKEN_CEILING,
    build_brief_sections,
    render_brief,
)
from code_atlas.tokens import estimate_tokens
from tests.test_check_cli import _prepare


def test_fixture_brief_from_underlying_tools(tmp_path: Path) -> None:
    config = _prepare(tmp_path)
    sections = build_brief_sections(
        config, paths=["domain/Model.aa"], base="main", head="HEAD"
    )
    text = render_brief(sections)
    assert "# Agent change brief" in text
    assert "## Caveats" in text
    assert "domain/Model.aa" in text
    # Source note from impact_modules must surface as a caveat.
    assert any("note=" in str(c) for c in sections["caveats"])
    rules = sections["architecture_rules"]
    assert isinstance(rules, dict)
    if int(rules.get("total_count") or 0) > 0:
        assert "domain-must-not-reach-http" in text


def test_committed_token_ceiling_constant() -> None:
    """AC — committed reporter pins the configured ceiling (fixture + sample use same const)."""
    assert DEFAULT_BRIEF_TOKEN_CEILING == 800
    assert estimate_tokens("x" * (DEFAULT_BRIEF_TOKEN_CEILING * 4)) == DEFAULT_BRIEF_TOKEN_CEILING


def test_token_reporter_fixture_and_pinned_sample(tmp_path: Path) -> None:
    from code_atlas.change_brief import report_token_ceiling

    config = _prepare(tmp_path)
    sections = build_brief_sections(
        config, paths=["domain/Model.aa"], token_ceiling=DEFAULT_BRIEF_TOKEN_CEILING
    )
    fixture_report = report_token_ceiling(sections=sections, sample="fixture")
    pinned_report = report_token_ceiling(sample="pinned")
    assert fixture_report["ceiling"] == DEFAULT_BRIEF_TOKEN_CEILING
    assert pinned_report["ceiling"] == DEFAULT_BRIEF_TOKEN_CEILING
    assert fixture_report["within_ceiling"] is True
    assert pinned_report["within_ceiling"] is True
    assert fixture_report["truncated"] is False
    assert pinned_report["truncated"] is False
    assert pinned_report["sample"] == "pinned"


def test_resolved_survives_cap_over_heuristic() -> None:
    from code_atlas.change_brief import _rank_impact_rows

    rows = [
        {"qname": "H", "confidence_tier": "HEURISTIC", "file": "h.aa"},
        {"qname": "R", "confidence_tier": "RESOLVED", "file": "r.aa"},
    ]
    ranked = _rank_impact_rows(rows)
    assert ranked[0]["confidence_tier"] == "RESOLVED"
    # Forced tiny ceiling still keeps RESOLVED suggestion first.
    sections = {
        "base": "b",
        "head": "h",
        "paths": ["r.aa"],
        "qnames": [],
        "impact": {"claim": "c", "results": rows},
        "impact_modules": {"results": []},
        "architecture_rules": {"results": [], "candidates": []},
        "ranked_impact": ranked,
        "modules": [],
        "confirmed_rules": [],
        "candidate_rules": [],
        "caveats": [],
        "token_ceiling": 120,
    }
    text = render_brief(sections)
    assert "r.aa" in text
    # The cap keeps the RESOLVED file; the HEURISTIC one cannot displace or precede it.
    sug = text.split("## Suggested first files")[1].split("## Caveats")[0]
    assert "r.aa" in sug
    assert "h.aa" not in sug


def test_missing_seeds_render_caveat(tmp_path: Path) -> None:
    config = _prepare(tmp_path)
    sections = build_brief_sections(
        config, paths=["no/such/file.aa"], base="main", head="HEAD"
    )
    text = render_brief(sections)
    assert "## Caveats" in text
    caveats = sections["caveats"]
    assert isinstance(caveats, list)
    assert any("seed" in str(c) or "reason" in str(c) for c in caveats)
    assert "_No walkable seeds — see caveats._" in text


def test_token_ceiling_reporter(tmp_path: Path) -> None:
    config = _prepare(tmp_path)
    sections = build_brief_sections(
        config, paths=["domain/Model.aa"], token_ceiling=DEFAULT_BRIEF_TOKEN_CEILING
    )
    text = render_brief(sections)
    tokens = estimate_tokens(text.split("<!--")[0])
    assert tokens <= DEFAULT_BRIEF_TOKEN_CEILING or "truncated:true" in text
    assert f"ceiling:{DEFAULT_BRIEF_TOKEN_CEILING}" in text


def test_byte_identical(tmp_path: Path) -> None:
    config = _prepare(tmp_path)
    a = render_brief(build_brief_sections(config, paths=["domain/Model.aa"], base="b", head="h"))
    b = render_brief(build_brief_sections(config, paths=["domain/Model.aa"], base="b", head="h"))
    assert a == b


def test_dropping_source_caveat_fails_consumer(tmp_path: Path) -> None:
    config = _prepare(tmp_path)
    sections = build_brief_sections(config, paths=["domain/Model.aa"])
    text = render_brief(sections)
    # Consumer-level: every caveat in the section list must appear in Markdown.
    for caveat in sections["caveats"]:
        assert str(caveat) in text
    # A renderer that drops the caveat section must be detectable by the same consumer check.
    broken = text.split("## Caveats")[0] + "## Caveats\n\n_None._\n"
    assert any(str(caveat) not in broken for caveat in sections["caveats"])


def test_cli_brief_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``--brief`` renders the brief on stdout; ``--brief-out`` writes the same bytes to PATH."""
    from code_atlas import check

    _prepare(tmp_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "artifacts" / "brief.md"
    code = check.main(["--base", "main", "--skip-build", "--brief", "--brief-out", str(out)])
    assert code == check.OK
    written = out.read_text(encoding="utf-8")
    assert written.startswith("# Agent change brief")
    assert "## Caveats" in written


def test_cli_brief_write_failure_is_operational(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unwritable artifact path exits operational instead of raising through main."""
    from code_atlas import check

    _prepare(tmp_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory\n", encoding="utf-8")
    code = check.main(
        ["--base", "main", "--skip-build", "--brief-out", str(blocker / "brief.md")]
    )
    assert code == check.OPERATIONAL
