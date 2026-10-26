"""Task 418 — a contract refusal names which half is older and the step that moves it.

A core installed from a checkout on a release branch, then the checkout switched back to ``main``:
the adapters it launches spoke v19 to a v20 core. The refusal's hint said to fix ``CA_<LANG>_CMD``
and the session line said ``git pull``; neither command was at fault, and ``main`` was not behind.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import code_atlas.config
from code_atlas import adapter_skew, contract
from code_atlas.adapter import AdapterContractError
from code_atlas.config import load_config
from code_atlas.hooks import state
from code_atlas.hooks.refresh import refresh
from code_atlas.tools import get_index_status
from code_atlas.tools.build_or_update_index import create
from code_atlas.tools.get_index_status import REFRESH_REFUSED
from tests.test_incremental import committed
from tests.test_refused_refresh_in_status import _adapter, built  # noqa: F401 — the fixture

CORE = contract.CONTRACT_VERSION


class _Dist:
    def __init__(self, record: object) -> None:
        self.record = record

    def read_text(self, name: str) -> str | None:
        return None if self.record is None else json.dumps(self.record)


def _installed_from(monkeypatch: pytest.MonkeyPatch, record: object) -> Path | None:
    monkeypatch.setattr(adapter_skew.importlib.metadata, "distribution", lambda _: _Dist(record))
    return adapter_skew.installed_from()


def test_an_older_adapter_is_told_to_move_to_the_cores_release() -> None:
    fix = adapter_skew.contract_fix(AdapterContractError("php", CORE - 1), None, release="0.9.0")
    assert f"adapter 'php' is v{CORE - 1}, core is v{CORE}" in fix
    assert "`git checkout v0.9.0`" in fix
    assert "CA_<LANG>_CMD" not in fix


def test_an_older_core_is_told_to_reinstall() -> None:
    fix = adapter_skew.contract_fix(AdapterContractError("php", CORE + 1), None, release="0.9.0")
    assert f"core is v{CORE}, older than adapter 'php' (v{CORE + 1})" in fix
    assert "uv tool install --reinstall" in fix


def test_an_unknown_release_names_no_tag() -> None:
    fix = adapter_skew.contract_fix(AdapterContractError("php", CORE - 1), None, release="unknown")
    assert "git checkout" not in fix


def test_an_adapter_inside_the_install_source_names_the_shared_checkout(tmp_path: Path) -> None:
    checkout = tmp_path / "code-atlas"
    entry = checkout / "adapters" / "php" / "index.php"
    elsewhere = tmp_path / "other" / "index.php"
    refused = AdapterContractError("php", CORE - 1)
    command = ("php", str(entry), "--server")
    fix = adapter_skew.contract_fix(refused, command, source=checkout.resolve(), release="0.9.0")
    assert f"installed from this checkout ({checkout.resolve()}) at another revision" in fix
    assert not adapter_skew.same_checkout(("php", str(elsewhere)), checkout.resolve())
    assert not adapter_skew.same_checkout(("php", "adapters/php/index.php"), checkout.resolve())
    assert not adapter_skew.same_checkout(command, None)


def test_the_install_source_is_read_from_direct_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = tmp_path.resolve().as_uri()
    assert _installed_from(monkeypatch, {"url": url, "dir_info": {}}) == tmp_path.resolve()
    assert _installed_from(monkeypatch, {"url": url, "dir_info": {"editable": True}}) is None
    assert _installed_from(monkeypatch, {"url": "https://github.com/x/y.git"}) is None
    assert _installed_from(monkeypatch, None) is None


def test_a_refused_build_carries_the_directional_hint(
    built: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The payload, the CLI line's source, and the hook record all carry the same fix."""
    _adapter(monkeypatch, built, "stale-version")
    refused = create(load_config(built))(full=False)
    assert refused["mode"] == "refused"
    assert f"adapter 'fake' is v1, core is v{CORE}" in str(refused["hint"])

    committed(built, {"src/Widget.aa": "class Widget { }\n"}, message="edit")
    assert refresh(built) == 0
    block = get_index_status.create(load_config(built), ())()[REFRESH_REFUSED]
    assert isinstance(block, dict)
    assert block["hint"] == refused["hint"]


def test_a_newer_adapter_refusal_points_at_the_core(
    built: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _adapter(monkeypatch, built, "bad-version")
    refused = create(load_config(built))(full=False)
    assert "older than adapter 'fake' (v99)" in str(refused["hint"])


def _line(**kwargs: object) -> str:
    base: dict[str, object] = {
        "installed": "0.9.0",
        "expected": "0.9.0",
        "expected_contract": CORE,
        "windows": False,
    }
    line = state.install_line(**{**base, **kwargs})  # type: ignore[arg-type]
    assert line is not None
    return line


def test_a_shared_checkout_behind_the_core_is_told_its_revision_not_git_pull() -> None:
    line = _line(adapters={"php": CORE - 1}, same_checkout=True)
    assert "`git checkout v0.9.0`" in line and "git pull" not in line
    assert "git pull" in _line(adapters={"php": CORE - 1})


def test_a_shared_checkout_ahead_of_the_core_is_told_to_reinstall() -> None:
    for plugin_contract in (CORE, CORE + 1):
        line = _line(
            adapters={"php": CORE + 1}, expected_contract=plugin_contract, same_checkout=True
        )
        assert "uv tool install --reinstall --from <checkout>" in line, line
        assert "uv tool upgrade" not in line, line


def test_the_reported_install_names_the_revision() -> None:
    """The report: tool 0.9.0 from the checkout, plugin 0.8.0, adapters back on v19."""
    line = _line(
        expected="0.8.0",
        expected_contract=CORE - 1,
        adapters={"php": CORE - 1},
        same_checkout=True,
    )
    assert "git pull" not in line, line
    assert "`git checkout v0.9.0`" in line or state.UPGRADING_POINTER in line, line


def test_the_hook_detects_the_shared_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_install_skew`` reads the install source and every configured adapter's argv."""
    checkout = tmp_path / "checkout"
    entry = checkout / "adapters" / "fake.py"
    seen: dict[str, object] = {}
    config = SimpleNamespace(adapter_cmds={"fake": (sys.executable, str(entry))})
    monkeypatch.setattr(adapter_skew, "installed_from", lambda: checkout.resolve())
    monkeypatch.setattr(adapter_skew, "adapter_contracts", lambda _config: {"fake": CORE - 1})
    monkeypatch.setattr(code_atlas.config, "load_config", lambda _root: config)
    monkeypatch.setattr(state, "install_line", lambda **kwargs: seen.update(kwargs))
    state._install_skew(tmp_path, "0.9.0", CORE)
    assert seen["same_checkout"] is True
