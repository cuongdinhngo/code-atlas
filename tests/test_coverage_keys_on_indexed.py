"""Task 173: coverage claims must key on what the graph HOLDS, not on what is configured.

Wiring a second adapter used to empty the coverage note and move `indexed_suffixes` to the new
language — while the graph still held zero files of it. A confident zero for an unindexed language
is 8-A's "false negative wearing a modelled zero's clothes", arriving as a consequence of the
roll-out.
"""

from __future__ import annotations

import shlex
import sys
import time
from pathlib import Path

import pytest

from code_atlas import adapter
from code_atlas.config import load_config
from code_atlas.store import COVERED_LANGUAGES_KEY, COVERED_SUFFIXES_KEY, GraphStore
from code_atlas.tools import coverage
from code_atlas.tools.build_or_update_index import create as build_tool
from code_atlas.tools.collection import collection_field
from code_atlas.tools.search_symbol import create as search_tool

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
SERVABLE = ("build_or_update_index", "search_symbol")


def fake_cmd(mode: str = "ok") -> str:
    return shlex.join([sys.executable, str(FAKE), mode])


def write(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def config_for(root: Path, env: dict[str, str]):
    return load_config(root, {**env, "CA_DB_PATH": str(root / ".code-atlas" / "graph.db")})


ONE_ADAPTER = {"CA_WORKERS": "1", "CA_FAKE_CMD": fake_cmd()}


@pytest.fixture(autouse=True)
def only_these_adapters_ship(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ship exactly the two fixture adapters, so 159's unwired note cannot muddy 173's."""
    root = tmp_path / "shipped"
    for name in ("fake", "second"):
        (root / name / "src").mkdir(parents=True)
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", root)
TWO_ADAPTERS = {**ONE_ADAPTER, "CA_SECOND_CMD": fake_cmd("second")}


def test_a_configured_but_unindexed_language_still_carries_a_note(tmp_path: Path) -> None:
    """AC1: the switch is on and the graph holds nothing — the zero must still say so."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    build_tool(config_for(tmp_path, ONE_ADAPTER))(full=True)

    # The second adapter is now wired, but nothing of its language has been indexed.
    config = config_for(tmp_path, TWO_ADAPTERS)
    answer = search_tool(config)(query="NoSuchSymbol")

    assert answer["reason"] == "token_candidates"
    assert answer[coverage.UNINDEXED_KEY] == [
        {"language": "second", "rebuild": "build_or_update_index(full=true)"}
    ]


def test_indexed_suffixes_does_not_claim_a_suffix_the_graph_has_no_files_for(
    tmp_path: Path,
) -> None:
    """AC2: the claim keys on rows, and 082's identity still reconciles."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    build_tool(config_for(tmp_path, ONE_ADAPTER))(full=True)
    config = config_for(tmp_path, TWO_ADAPTERS)
    build_tool(config)(full=True)

    with GraphStore(config.db_path) as store:
        block = collection_field(store)
    assert block is not None

    assert block["indexed_suffixes"] == [".aa"], "the graph holds only .aa files"
    assert ".cc" in block["claimed_suffixes"], "the build did claim the second adapter's suffix"
    # 082: collected - skipped.suffix - skipped.ignore == kept, and kept + stubs == files.
    skipped = block["skipped"]
    assert (
        block["collected"] - skipped["suffix"] - skipped["ignore"] == block["kept"]
    )


def test_a_fully_indexed_wired_server_says_nothing_extra(tmp_path: Path) -> None:
    """AC3/061: both languages wired and both present — no note, and no suffix pair."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    write(tmp_path, "src/b.bb", "class Other {}\n")
    write(tmp_path, "src/c.cc", "class Third {}\n")
    config = config_for(tmp_path, TWO_ADAPTERS)
    build_tool(config)(full=True)

    answer = search_tool(config)(query="NoSuchSymbol")
    assert coverage.UNINDEXED_KEY not in answer
    assert coverage.COVERAGE_KEY not in answer

    with GraphStore(config.db_path) as store:
        block = collection_field(store)
    assert block is not None
    assert "claimed_suffixes" not in block, "identical sets must not grow a second name (061)"
    assert sorted(block["indexed_suffixes"]) == [".aa", ".bb", ".cc"]


def test_the_note_is_self_gating_and_idempotent_across_the_sweep_envelope(
    tmp_path: Path,
) -> None:
    """AC4/160 AC1e: the envelope carries it once and never per subject — 061's payload weight.

    192 reverses only the last line: a confident answer DOES now carry it, because the gap is a
    property of the index rather than of how many rows came back. The per-subject rule above is
    untouched, which is what keeps the sweep from paying for the note N times.
    """
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    build_tool(config_for(tmp_path, ONE_ADAPTER))(full=True)
    config = config_for(tmp_path, TWO_ADAPTERS)
    search = search_tool(config)

    sweep = search(queries=["NoSuchSymbol", "AlsoMissing"])
    assert coverage.UNINDEXED_KEY in sweep
    for answer in sweep["subjects"]:
        assert coverage.UNINDEXED_KEY not in answer, "call-level, never per subject (061)"

    confident = search(query="Thing")
    assert confident["results"]
    assert coverage.UNINDEXED_KEY in confident, "192: a partial answer says so, results or not"


def test_the_claim_is_read_from_meta_not_scanned_per_answer(tmp_path: Path) -> None:
    """AC5: the cost is a meta read; the row scan happens once, at build time."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    build_tool(config_for(tmp_path, ONE_ADAPTER))(full=True)
    config = config_for(tmp_path, TWO_ADAPTERS)
    search = search_tool(config)

    started = time.perf_counter()
    for _ in range(200):
        search(query="NoSuchSymbol")
    per_call = (time.perf_counter() - started) / 200
    assert per_call < 0.05, f"{per_call * 1000:.3f} ms per zero answer"

    with GraphStore(config.db_path) as store:
        assert store.get_meta(COVERED_SUFFIXES_KEY) == ".aa"
        assert store.get_meta(COVERED_LANGUAGES_KEY) == "fake"


def test_a_pre_173_index_says_nothing_rather_than_guessing(tmp_path: Path) -> None:
    """R5.6: with no stamp we cannot know the gap, so we do not claim one."""
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    config = config_for(tmp_path, TWO_ADAPTERS)
    build_tool(config)(full=True)
    with GraphStore(config.db_path) as store:
        store.set_meta(COVERED_LANGUAGES_KEY, None)  # type: ignore[arg-type]

    assert coverage.unindexed_languages(config, None) == []
