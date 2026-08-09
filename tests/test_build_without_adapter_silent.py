"""Task 064: a build with no usable adapter must fail loud, not write an empty index."""

from __future__ import annotations

import shlex
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.adapter import AdapterError
from code_atlas.config import load_config
from code_atlas.indexer import full_build, incremental_update
from code_atlas.store import INDEXED_SUFFIXES_KEY, LAST_COMMIT_KEY, GraphStore
from code_atlas.tools import build_or_update_index

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / ".code-atlas" / "graph.db") as opened:
        yield opened


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=root,
        check=True,
        capture_output=True,
    )


def test_empty_adapter_cmds_refuses_without_meta(tmp_path: Path, store: GraphStore) -> None:
    """AC1: no CA_*_CMD / [adapter_cmd] → AdapterError; no last_commit / indexed_suffixes."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.aa").write_text("x\n", encoding="utf-8")
    _git_init(tmp_path)
    config = load_config(tmp_path, {"CA_WORKERS": "1"})
    assert config.adapter_cmds == {}

    with pytest.raises(AdapterError, match=r"CA_<LANG>_CMD.*\[adapter_cmd\]"):
        full_build(config, store)

    assert store.get_meta(LAST_COMMIT_KEY) is None
    assert store.get_meta(INDEXED_SUFFIXES_KEY) is None


def test_empty_adapter_cmds_refuses_incremental(tmp_path: Path, store: GraphStore) -> None:
    (tmp_path / "src").mkdir()
    _git_init(tmp_path)
    config = load_config(tmp_path, {"CA_WORKERS": "1"})
    with pytest.raises(AdapterError, match="no adapters configured"):
        incremental_update(config, store, ["src/a.aa"])


def test_build_or_update_index_surfaces_empty_adapters(tmp_path: Path) -> None:
    """AC2: tool path raises — not a files:0 success report."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / ".keep").write_text("", encoding="utf-8")
    _git_init(tmp_path)
    config = load_config(
        tmp_path,
        {"CA_WORKERS": "1", "CA_DB_PATH": str(tmp_path / ".code-atlas" / "graph.db")},
    )
    tool = build_or_update_index.create(config)
    with pytest.raises(AdapterError, match="no adapters configured"):
        tool(full=True)


def test_the_contract_rejects_an_empty_extension_list() -> None:
    """AC3 mechanism: the handshake validator is what makes an empty suffix union impossible."""
    meta = {"name": "fake", "extensions": [], "capabilities": {}, "contract_version": 5}
    assert any("meta.extensions" in error for error in contract.validate_meta(meta))


def test_empty_suffix_union_refuses(tmp_path: Path, store: GraphStore) -> None:
    """AC3: an adapter announcing no ``extensions`` fails at the handshake, leaving no meta."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.aa").write_text("x\n", encoding="utf-8")
    _git_init(tmp_path)
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "empty-extensions"]),
        },
    )
    with pytest.raises(AdapterError, match=r"invalid handshake: meta\.extensions"):
        full_build(config, store)
    assert store.get_meta(LAST_COMMIT_KEY) is None
    assert store.get_meta(INDEXED_SUFFIXES_KEY) is None


def test_zero_files_with_suffixes_is_success(tmp_path: Path, store: GraphStore) -> None:
    """Boundary: adapters claim suffixes but nothing matches → success (data, not config)."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "readme.txt").write_text("no claimed suffix\n", encoding="utf-8")
    _git_init(tmp_path)
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
        },
    )
    report = full_build(config, store)
    assert report.files == 0
    assert report.failed == 0
    assert store.get_meta(LAST_COMMIT_KEY) is not None
    suffixes = store.get_meta(INDEXED_SUFFIXES_KEY)
    assert suffixes is not None and suffixes != ""
