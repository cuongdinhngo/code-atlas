"""Task 284 — stale-process impact verdict + content-hash build kind."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from code_atlas import build_info


def _force_diverged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, surface_now: str, surface_loaded: str
) -> None:
    build_info.reset_identity_cache()
    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", "0ldc0de")
    monkeypatch.setattr(build_info, "_LOADED_TOOL_SURFACE_ID", surface_loaded)
    monkeypatch.setattr(build_info, "_tool_surface_id", lambda: surface_now)
    monkeypatch.setattr(build_info, "_git_root", lambda: tmp_path)
    monkeypatch.setattr(build_info.gitutil, "head_commit", lambda root: "abcdef1234567890")


def test_diverged_unchanged_tool_surface_reports_impact_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1: package bytes moved but tool-contract surface did not → impact says so."""
    _force_diverged(monkeypatch, tmp_path, surface_now="same001", surface_loaded="same001")
    prov = build_info.server_provenance()
    build_info.reset_identity_cache()

    assert prov["server_stale_process"] is True
    assert prov["server_stale_impact"] == build_info.STALE_IMPACT_UNCHANGED
    assert prov["server_build_kind"] == build_info.BUILD_KIND_CONTENT_HASH
    assert prov["server_build"] == "0ldc0de"
    # Checkout HEAD — documented as worktree tip, not the answering process.
    assert prov["server_repo_head"] == "abcdef1"


def test_diverged_changed_tool_surface_reports_impact_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2: tool-contract surface moved with the disk → opposite, distinguishable verdict."""
    _force_diverged(monkeypatch, tmp_path, surface_now="new0001", surface_loaded="old0001")
    prov = build_info.server_provenance()
    build_info.reset_identity_cache()

    assert prov["server_stale_impact"] == build_info.STALE_IMPACT_CHANGED
    assert prov["server_stale_impact"] != build_info.STALE_IMPACT_UNCHANGED
    assert prov["server_build_kind"] == build_info.BUILD_KIND_CONTENT_HASH


def test_matching_process_payload_keys_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC4 / 061: matching process stays byte-identical — no impact / kind fields."""
    build_info.reset_identity_cache()
    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", build_info._content_build_id())
    monkeypatch.setattr(build_info, "_git_root", lambda: tmp_path)
    monkeypatch.setattr(build_info.gitutil, "head_commit", lambda root: "abcdef1234567890")
    monkeypatch.setattr(build_info.gitutil, "working_tree_dirty", lambda root: False)

    prov = build_info.server_provenance()
    build_info.reset_identity_cache()

    assert set(prov) == {"server_version", "server_build", "server_stale_process"}
    assert "server_stale_impact" not in prov
    assert "server_build_kind" not in prov


def test_published_fields_carry_no_mtime_or_timestamp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5 / R4.2: impact and kind derive from stored hashes, never probe mtimes."""
    _force_diverged(monkeypatch, tmp_path, surface_now="same001", surface_loaded="same001")
    # Poison the probe state with distinctive mtime stamps — must not leak into the payload.
    build_info._probe_state["code_atlas.fake"] = (1_700_000_000_000_000_000, 42)
    with patch.object(build_info, "_loaded_modules_changed", return_value=True):
        prov = build_info.server_provenance()
    build_info.reset_identity_cache()

    blob = repr(prov)
    assert "1700000000000000000" not in blob
    assert "mtime" not in blob.lower()
    assert prov["server_stale_impact"] == build_info.STALE_IMPACT_UNCHANGED


def test_tool_surface_id_changes_when_a_tool_file_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Impact rides stored evidence: the tool-surface hash moves when a tool module moves."""
    pkg = tmp_path / "code_atlas"
    tools = pkg / "tools"
    tools.mkdir(parents=True)
    (pkg / "contract.py").write_text("CONTRACT = 1\n", encoding="utf-8")
    (pkg / "build_info.py").write_text("BUILD = 1\n", encoding="utf-8")
    tool = tools / "find_references.py"
    tool.write_text("def answer(): return 'via_members'\n", encoding="utf-8")

    monkeypatch.setattr(build_info, "_PACKAGE_ROOT", pkg)
    first = build_info._tool_surface_id()
    tool.write_text("def answer(): return 'relationship_not_modelled'\n", encoding="utf-8")
    second = build_info._tool_surface_id()
    assert first != second
