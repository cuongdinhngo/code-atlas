"""Task 305: versioned Change Assurance evidence bundle around a 303 check result."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from code_atlas import check
from code_atlas import evidence_bundle as eb
from code_atlas.config import load_config
from code_atlas.evidence_bundle import (
    EVIDENCE_BUNDLE_VERSION,
    load_bundle,
    render_json,
    render_markdown,
    validate_bundle,
    wrap_check_result,
    write_bundle,
)


def _sample_result(**overrides: object) -> dict[str, object]:
    base = {
        "base": "abc",
        "head": "def",
        "head_ref": "main",
        "mode": "report_only",
        "reason": "report_only",
        "confirmed_count": 1,
        "candidate_count": 0,
        "caveats": ["impact:truncated", "dirty_unindexed:README.md — disclosed"],
        "changed_indexed": ["a.aa"],
        "changed_paths": ["a.aa", "README.md"],
        "dirty_unindexed": ["README.md"],
        "impact": {"staleness": "current", "claim": "subject=a.aa answer=0", "total_count": 0},
        "architecture_rules": {"total_count": 1},
        "architecture_diff": {"reason": "no_architectural_change"},
    }
    base.update(overrides)
    return base


def test_round_trip_byte_identical(tmp_path: Path) -> None:
    """AC — a real 303 check result round-trips write/read/validate."""
    from tests.test_check_cli import _prepare

    config = _prepare(tmp_path)
    _code, result = check.run_check(tmp_path, base_override="main", skip_build=True)
    bundle = wrap_check_result(result, config)
    path = tmp_path / "out" / "bundle.json"
    write_bundle(bundle, json_path=path)
    loaded = load_bundle(path)
    assert render_json(loaded) == render_json(bundle)
    assert validate_bundle(loaded, expected_index_root=config.index_root)["ok"] is True
    assert "config_build" in bundle and bundle["config_build"]
    assert "confidence" in bundle and "truncation" in bundle
    assert isinstance(bundle["claims"], list)


def test_markdown_attests_every_caveat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A caveat present in JSON must reach Markdown, or validation refuses to attest."""
    config = load_config(tmp_path, {})
    bundle = wrap_check_result(_sample_result(), config)
    md = render_markdown(bundle)
    assert bundle["caveats"]
    for caveat in bundle["caveats"]:
        assert caveat in md
    original = eb.render_markdown

    def drop_caveats(b: Mapping[str, object]) -> str:
        text = original(b)
        for caveat in b.get("caveats") or []:  # type: ignore[union-attr]
            text = text.replace(str(caveat), "")
        return text

    monkeypatch.setattr(eb, "render_markdown", drop_caveats)
    verdict = validate_bundle(bundle, expected_index_root=config.index_root)
    assert verdict["ok"] is False
    assert verdict["reason"] == "caveat_not_attested"


def test_newer_version_refused_directionally(tmp_path: Path) -> None:
    config = load_config(tmp_path, {})
    bundle = wrap_check_result(_sample_result(), config)
    bundle["bundle_version"] = EVIDENCE_BUNDLE_VERSION + 1
    verdict = validate_bundle(bundle, expected_index_root=config.index_root)
    assert verdict["ok"] is False
    assert verdict["reason"] == "unsupported_bundle_version"
    assert verdict["direction"] == "newer"


def test_malformed_never_reads_as_empty_ok(tmp_path: Path) -> None:
    verdict = validate_bundle({"bundle_version": 1}, expected_index_root="x")
    assert verdict["ok"] is False
    assert verdict["reason"] == "malformed_bundle"


def test_deterministic_two_runs(tmp_path: Path) -> None:
    config = load_config(tmp_path, {})
    a = wrap_check_result(_sample_result(), config)
    b = wrap_check_result(_sample_result(), config)
    assert render_json(a) == render_json(b)


def test_default_writes_nothing(tmp_path: Path) -> None:
    """Stdout path does not create tracked files under the repo root."""
    before = {p for p in tmp_path.rglob("*") if p.is_file()}
    config = load_config(tmp_path, {})
    wrap_check_result(_sample_result(), config)  # no write
    after = {p for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before


def test_cross_repository_rejected(tmp_path: Path) -> None:
    config = load_config(tmp_path, {})
    bundle = wrap_check_result(_sample_result(), config)
    verdict = validate_bundle(bundle, expected_index_root="/other/root")
    assert verdict["ok"] is False
    assert verdict["reason"] == "cross_repository_bundle"


def test_json_and_markdown_share_counts(tmp_path: Path) -> None:
    config = load_config(tmp_path, {})
    bundle = wrap_check_result(_sample_result(), config)
    md = render_markdown(bundle)
    assert f"`{bundle['confirmed_count']}`" in md
    assert f"`{bundle['base']}`" in md
    assert f"`{bundle['head']}`" in md


def test_cli_bundle_flags_write_only_requested_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--bundle-json`` / ``--bundle-md`` write exactly the explicit paths, and nothing else."""
    from tests.test_check_cli import _prepare

    config = _prepare(tmp_path)
    out = tmp_path / "artifacts"
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    code = check.main(
        [
            "--base", "main", "--skip-build",
            "--bundle-json", str(out / "b.json"),
            "--bundle-md", str(out / "b.md"),
        ]
    )
    assert code == check.OK
    written = sorted(p.name for p in out.iterdir())
    assert written == ["b.json", "b.md"]
    loaded = load_bundle(out / "b.json")
    assert validate_bundle(loaded, expected_index_root=config.index_root)["ok"] is True
    assert "# Change Assurance evidence bundle" in (out / "b.md").read_text(encoding="utf-8")
