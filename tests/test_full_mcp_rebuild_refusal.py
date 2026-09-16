"""Task 291 — refuse explicit full rebuilds over MCP on an existing index."""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from code_atlas.config import load_config
from code_atlas.indexer import (
    FULL_REBUILD_ROUTE,
    FULL_REBUILD_USE_SHELL,
    IN_BAND_FULL_REBUILD,
)
from code_atlas.tools.build_or_update_index import create as build_tool

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"


def _env() -> dict[str, str]:
    return {
        "CA_WORKERS": "1",
        "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
    }


def _cfg(root: Path):
    return load_config(root, {**_env(), "CA_DB_PATH": str(root / ".code-atlas" / "graph.db")})


def _seed(root: Path) -> None:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "a.aa").write_text("class Thing {}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    # First build: no last_commit yet — still allowed without the opt-in.
    assert build_tool(_cfg(root))(full=True)["mode"] == "full"


def test_full_on_existing_index_is_refused_with_shell_route(tmp_path: Path) -> None:
    """AC1 + AC4: refused payload names the CLI route and how to observe a live build."""
    _seed(tmp_path)

    def never(*_a: object, **_k: object) -> None:
        raise AssertionError("full build must not start")

    with patch("code_atlas.tools.build_or_update_index.full_build", never):
        payload = build_tool(_cfg(tmp_path))(full=True)
    assert payload["mode"] == "refused"
    assert payload["performed"] is False
    assert payload["reason"] == FULL_REBUILD_USE_SHELL
    assert payload["route"] == FULL_REBUILD_ROUTE
    assert payload["in_band_option"] == IN_BAND_FULL_REBUILD
    assert "status" in str(payload["hint"]).lower()
    assert "last_commit" in str(payload["hint"])
    assert "code-atlas-build" in str(payload["hint"])


def test_allow_full_rebuild_still_runs(tmp_path: Path) -> None:
    """AC2: allow_full_rebuild=true runs the build exactly as today."""
    _seed(tmp_path)
    payload = build_tool(_cfg(tmp_path))(full=True, allow_full_rebuild=True)
    assert payload["mode"] == "full"
    assert "wrote" in payload


def test_incremental_on_current_index_is_unchanged(tmp_path: Path) -> None:
    """AC3: full=false on a current index stays the incremental no-op shape."""
    _seed(tmp_path)
    payload = build_tool(_cfg(tmp_path))(full=False)
    assert payload["mode"] == "incremental"


def test_contract_rebuild_refusal_still_fires(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5: 201's contract_rebuild_required path is untouched."""
    from code_atlas import contract
    from code_atlas.store import CONTRACT_VERSION_KEY, GraphStore

    _seed(tmp_path)
    cfg = _cfg(tmp_path)
    with GraphStore(cfg.db_path) as store:
        store.set_meta(CONTRACT_VERSION_KEY, str(contract.CONTRACT_VERSION - 1))

    def never(*_a: object, **_k: object) -> None:
        raise AssertionError("contract rebuild must refuse before building")

    monkeypatch.setattr("code_atlas.tools.build_or_update_index.full_build", never)
    monkeypatch.setattr("code_atlas.tools.build_or_update_index.incremental_update", never)
    payload = build_tool(cfg)(full=False)
    assert payload["mode"] == "refused"
    assert payload["reason"] == "contract_rebuild_required"
