"""Task 174 — `skipped.suffix` says what it is MADE OF, so the total names a cost.

159 made the unwired adapter visible. Rounds 8–11 then recorded **four consecutive zero
contributions** from one absent env var, all four disclosed as
`[{"language": "typescript", "enable": "CA_TYPESCRIPT_CMD"}]` and none acted on. *"An adapter
exists"* is a fact about the product. *"2,831 `.js` files in **this** repo are invisible"* is a fact
about the reader's own cost, and it is the one that gets a switch flipped.

The core names no language (R1.1) and cannot: an unwired adapter is never launched, so its
extensions are unknowable. So the join is inverted — the census publishes the **extensions** it
skipped, and the reader joins them with `unconfigured_adapters`. Spec-driven suffixes (R2).
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path
from time import perf_counter

import pytest

from code_atlas import adapter
from code_atlas.config import load_config
from code_atlas.store import SKIPPED_SUFFIX_COUNTS_KEY, GraphStore
from code_atlas.tools import get_index_status
from code_atlas.tools.build_or_update_index import create as build_tool
from code_atlas.tools.collection import SKIPPED_SUFFIX_TOP_N, collection_field

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"


def fake_cmd(mode: str = "ok") -> str:
    return shlex.join([sys.executable, str(FAKE), mode])


ONE_ADAPTER = {"CA_WORKERS": "1", "CA_FAKE_CMD": fake_cmd()}


@pytest.fixture(autouse=True)
def only_the_fixture_adapter_ships(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "shipped"
    for name in ("fake", "second"):
        (root / name / "src").mkdir(parents=True)
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", root)


def write(root: Path, path: str, body: str = "x\n") -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def build(root: Path, tree: dict[str, int]):
    """`tree` maps a suffix to how many files of it to plant. `.aa` is the only indexed one."""
    for suffix, count in tree.items():
        for index in range(count):
            write(root, f"src/f{index}{suffix}")
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    env = {**ONE_ADAPTER, "CA_DB_PATH": str(root / ".code-atlas" / "graph.db")}
    config = load_config(root, env)
    build_tool(config)(full=True)
    return config


def block(config) -> dict[str, object]:
    with GraphStore(config.db_path) as store:
        found = collection_field(store, ignore_sources=True)
    assert found is not None
    return found


def test_the_total_says_what_it_is_made_of(tmp_path: Path) -> None:
    """AC1: a histogram whose entries sum to no more than `skipped.suffix`."""
    config = build(tmp_path, {".aa": 2, ".cc": 7, ".dd": 3, ".ee": 1})
    skipped = block(config)["skipped"]

    assert skipped["suffix_top"] == {".cc": 7, ".dd": 3, ".ee": 1}  # type: ignore[index]
    assert skipped["suffix_kinds"] == 3  # type: ignore[index]
    top = dict(skipped["suffix_top"])  # type: ignore[index,arg-type]
    assert sum(top.values()) <= skipped["suffix"]  # type: ignore[index,operator]


def test_the_reader_can_join_it_with_the_unwired_adapter(tmp_path: Path) -> None:
    """The whole point (AC1's motivation): the two halves of the answer are in one payload.

    `unconfigured_adapters` names the switch; `suffix_top` names how many files that switch would
    make visible. Neither half needs the core to know that `.cc` belongs to any language.
    """
    config = build(tmp_path, {".aa": 1, ".cc": 5})
    payload = get_index_status.create(config, (get_index_status.NAME,))(detail_level="verbose")

    assert payload["unconfigured_adapters"] == [{"language": "second", "enable": "CA_SECOND_CMD"}]
    skipped = payload["collection"]["skipped"]  # type: ignore[index]
    assert skipped["suffix_top"][".cc"] == 5  # type: ignore[index]


def test_the_identity_still_reconciles(tmp_path: Path) -> None:
    """AC2/082: the histogram is a breakdown of one term, never a replacement for it."""
    config = build(tmp_path, {".aa": 4, ".cc": 6, ".dd": 2})
    found = block(config)
    skipped = found["skipped"]

    assert (
        found["collected"] - skipped["suffix"] - skipped["ignore"]  # type: ignore[index,operator]
        == found["kept"]
    )
    assert skipped["suffix"] == 8  # type: ignore[index]
    assert sum(dict(skipped["suffix_top"]).values()) == skipped["suffix"]  # type: ignore[index,arg-type]


def test_it_is_omitted_when_every_suffix_is_indexed(tmp_path: Path) -> None:
    """AC3/061: a repo with nothing skipped adds nothing."""
    config = build(tmp_path, {".aa": 3})
    skipped = block(config)["skipped"]

    assert skipped["suffix"] == 0  # type: ignore[index]
    assert "suffix_top" not in skipped  # type: ignore[operator]
    assert "suffix_kinds" not in skipped  # type: ignore[operator]


def test_it_appears_wherever_skipped_suffix_appears(tmp_path: Path) -> None:
    """AC3: the same detail levels as the term it breaks down — inside `collection`."""
    config = build(tmp_path, {".aa": 1, ".cc": 2})
    tool = get_index_status.create(config, (get_index_status.NAME,))

    standard = tool(detail_level="standard")
    assert "collection" not in standard, "collection is verbose-only on status (082)"
    verbose = tool(detail_level="verbose")
    assert "suffix_top" in verbose["collection"]["skipped"]  # type: ignore[index,operator]

    # build_or_update_index publishes `collection` at standard — the histogram rides that too.
    refresh = build_tool(config)()
    assert "suffix_top" in refresh["collection"]["skipped"]  # type: ignore[index,operator]


def test_the_output_is_bounded_and_says_so(tmp_path: Path) -> None:
    """Cost constraint: a repo with many extensions cannot inflate the payload.

    The walk counts the WHOLE tally and only the publisher cuts it, so the cap has one definition
    site (R6.7) and `suffix_kinds` stays the true denominator rather than a capped one.
    """
    tree = {".aa": 1, **{f".x{index:02d}": index + 1 for index in range(SKIPPED_SUFFIX_TOP_N + 8)}}
    config = build(tmp_path, tree)
    skipped = block(config)["skipped"]

    assert len(dict(skipped["suffix_top"])) == SKIPPED_SUFFIX_TOP_N  # type: ignore[index,arg-type]
    assert skipped["suffix_kinds"] == SKIPPED_SUFFIX_TOP_N + 8  # type: ignore[index]
    # The cut is visible: the published entries are a strict subset of the total.
    assert sum(dict(skipped["suffix_top"]).values()) < skipped["suffix"]  # type: ignore[index,arg-type]


def test_the_order_and_the_tie_break_are_deterministic(tmp_path: Path) -> None:
    """AC6/R4.2: count descending, suffix ascending — equal counts cannot reorder between runs."""
    # `.bb` is one of the fixture adapter's OWN suffixes, so it is indexed, not skipped.
    config = build(tmp_path, {".aa": 1, ".zz": 4, ".gg": 4, ".mm": 4})
    first = dict(block(config)["skipped"]["suffix_top"])  # type: ignore[index,arg-type]
    second = dict(block(config)["skipped"]["suffix_top"])  # type: ignore[index,arg-type]

    assert first == second
    assert list(first) == [".gg", ".mm", ".zz"], "equal counts fall back to the suffix, ascending"


def test_a_suffix_less_file_gets_its_own_bucket(tmp_path: Path) -> None:
    """An empty key nothing can read is worse than a named bucket."""
    write(tmp_path, "src/f0.aa")
    write(tmp_path, "Makefile")
    write(tmp_path, "LICENSE")
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=tmp_path, check=True, capture_output=True)
    config = load_config(
        tmp_path, {**ONE_ADAPTER, "CA_DB_PATH": str(tmp_path / ".code-atlas" / "graph.db")}
    )
    build_tool(config)(full=True)

    skipped = block(config)["skipped"]
    assert skipped["suffix_top"]["(none)"] == 2  # type: ignore[index]


def test_a_pre_174_index_says_nothing(tmp_path: Path) -> None:
    """R5.6: no stamp means the breakdown was never measured — not that nothing was skipped."""
    config = build(tmp_path, {".aa": 1, ".cc": 3})
    with GraphStore(config.db_path) as store:
        store.delete_meta(SKIPPED_SUFFIX_COUNTS_KEY)
        assert store.skipped_suffix_counts() == {}
        store.set_meta(SKIPPED_SUFFIX_COUNTS_KEY, "not json")
        assert store.skipped_suffix_counts() == {}
        found = collection_field(store, ignore_sources=True)
    assert found is not None
    assert "suffix_top" not in found["skipped"]  # type: ignore[operator]
    assert found["skipped"]["suffix"] == 3, "the total is unaffected"  # type: ignore[index]


def test_no_suffix_to_language_mapping_entered_the_core() -> None:
    """AC5/R1.1: the core publishes extensions and names no language for them."""
    hits = subprocess.run(
        ["grep", "-rn", "-e", "\\.js", "-e", "\\.ts\\b", "-e", "\\.php", "code_atlas/"],
        cwd=REPO,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    offenders = [line for line in hits if "SKIPPED_SUFFIX" in line or "suffix_top" in line]
    assert offenders == [], offenders


def test_the_added_build_cost_is_one_counter_increment(tmp_path: Path) -> None:
    """AC4: counted inside the existing walk — no second pass, and no answer-time query."""
    config = build(tmp_path, {".aa": 20, ".cc": 400, ".dd": 400})

    with GraphStore(config.db_path) as store:
        traced: list[str] = []
        store._conn.set_trace_callback(traced.append)
        store.skipped_suffix_counts()
        store._conn.set_trace_callback(None)
    assert len(traced) == 1, traced
    assert "GROUP BY" not in traced[0]

    started = perf_counter()
    for _ in range(50):
        block(config)
    per_call_ms = (perf_counter() - started) / 50 * 1000
    assert per_call_ms < 25.0, f"{per_call_ms:.3f} ms per collection block"

    with GraphStore(config.db_path) as store:
        raw = store.get_meta(SKIPPED_SUFFIX_COUNTS_KEY)
    assert raw is not None
    assert json.loads(raw) == {".cc": 400, ".dd": 400}
