"""Task 159 — get_index_status names adapters that ship in-repo but are not wired.

A shipped-but-unconfigured adapter is invisible from inside the running server (finding 8-G). The
fact is derived from the ``adapters/`` directory (data, not a language branch — R1.1) and reported
with the ``CA_<LANG>_CMD`` key that enables it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from code_atlas import adapter
from code_atlas.config import load_config
from code_atlas.tools import get_index_status
from code_atlas.tools.get_index_status import NAME as STATUS


def _plant_adapters(tmp_path: Path, *names: str) -> Path:
    root = tmp_path / "adapters"
    root.mkdir()
    (root / ".gitkeep").write_text("", encoding="utf-8")  # a file, not an adapter
    for name in names:
        (root / name / "src").mkdir(parents=True)
    return root


def test_shipped_adapters_reads_the_directory_not_a_literal(tmp_path: Path) -> None:
    """AC3: the name comes from the directory — a novel language appears with no code change."""
    root = _plant_adapters(tmp_path, "php", "typescript", "ruby")
    assert adapter.shipped_adapters(root) == ("php", "ruby", "typescript")


def test_shipped_adapters_is_empty_when_the_directory_is_absent(tmp_path: Path) -> None:
    """A wheel that ships no adapters discovers none — the honest answer, not a crash (R4.2)."""
    assert adapter.shipped_adapters(tmp_path / "nope") == ()


def test_unconfigured_lists_the_unwired_adapter_with_its_enable_key(tmp_path: Path) -> None:
    """AC1: php wired, typescript not → typescript is reported with CA_TYPESCRIPT_CMD."""
    root = _plant_adapters(tmp_path, "php", "typescript")
    assert adapter.unconfigured_adapters(["php"], root) == [
        {"language": "typescript", "enable": "CA_TYPESCRIPT_CMD"}
    ]


def test_unconfigured_is_empty_when_every_adapter_is_wired(tmp_path: Path) -> None:
    """AC2 basis: nothing to report when both shipped adapters are configured."""
    root = _plant_adapters(tmp_path, "php", "typescript")
    assert adapter.unconfigured_adapters(["php", "typescript"], root) == []


def test_status_names_an_unconfigured_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1 end-to-end: get_index_status(standard) reports the shipped-but-unwired adapter."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = load_config(tmp_path, {"CA_PHP_CMD": "php run"})
    status = get_index_status.create(config, (STATUS,))(detail_level="standard")
    assert status["unconfigured_adapters"] == [
        {"language": "typescript", "enable": "CA_TYPESCRIPT_CMD"}
    ]


def test_status_omits_the_field_when_all_adapters_are_wired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2 (061): a fully-wired server carries no new field."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = load_config(tmp_path, {"CA_PHP_CMD": "php run", "CA_TYPESCRIPT_CMD": "node run"})
    status = get_index_status.create(config, (STATUS,))(detail_level="standard")
    assert "unconfigured_adapters" not in status


def test_minimal_status_never_carries_the_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """061: the cheap path stays cheap — availability is a standard/verbose fact."""
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", _plant_adapters(tmp_path, "php", "typescript"))
    config = load_config(tmp_path, {"CA_PHP_CMD": "php run"})
    status = get_index_status.create(config, (STATUS,))(detail_level="minimal")
    assert "unconfigured_adapters" not in status
