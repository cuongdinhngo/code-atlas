"""Task 299 — a non-empty ``search_symbol`` page names same-stem unindexed suffixes.

160/192 cover adapter/language gaps. Round 30's lie was different: indexed ``.ts`` hits with
``reason: ok`` while a same-stem ``.js`` twin was never a candidate. The field is omit-when-empty
(061); ``reason`` stays a hit code, never ``language_not_indexed``.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import pytest

from code_atlas import adapter
from code_atlas.config import load_config
from code_atlas.tools import coverage
from code_atlas.tools.build_or_update_index import create as build_tool
from code_atlas.tools.search_symbol import create as search_tool

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"


def fake_cmd() -> str:
    return shlex.join([sys.executable, str(FAKE), "ok"])


def write(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def config_for(root: Path) -> object:
    return load_config(
        root,
        {
            "CA_WORKERS": "1",
            "CA_FAKE_CMD": fake_cmd(),
            "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
        },
    )


@pytest.fixture(autouse=True)
def only_fake_adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "shipped"
    (root / "fake" / "src").mkdir(parents=True)
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", root)


def test_hit_list_names_same_stem_unindexed_suffix(tmp_path: Path) -> None:
    """AC1: indexed hits stay; envelope names the unindexed twin suffix; not a miss reason."""
    write(tmp_path, "legacy/ReportGen.aa", "# symbol: initialReportNew\n")
    write(tmp_path, "public/ReportGen.js", "// live copy — never a candidate\n")
    config = config_for(tmp_path)
    build_tool(config)(full=True)

    answer = search_tool(config)(query="initialReportNew")
    assert answer["results"], "indexed .aa hit must remain"
    assert answer["reason"] not in (
        "no_matches",
        "no_such_symbol",
        "language_not_indexed",
        "token_candidates",
    )
    field = answer[coverage.SAME_BASENAME_KEY]
    assert field["suffixes"] == [".js"]
    assert field["count"] >= 1


def test_no_unindexed_twin_is_byte_identical(tmp_path: Path) -> None:
    """AC2/061: no same-stem unindexed file → no field."""
    write(tmp_path, "legacy/ReportGen.aa", "# symbol: initialReportNew\n")
    config = config_for(tmp_path)
    build_tool(config)(full=True)

    answer = search_tool(config)(query="initialReportNew")
    assert answer["results"]
    assert coverage.SAME_BASENAME_KEY not in answer


def test_empty_miss_path_unchanged(tmp_path: Path) -> None:
    """AC3: a true empty miss still follows 160/173 — this field stays off the zero path."""
    write(tmp_path, "legacy/ReportGen.aa", "# symbol: initialReportNew\n")
    write(tmp_path, "public/ReportGen.js", "// twin\n")
    config = config_for(tmp_path)
    build_tool(config)(full=True)

    miss = search_tool(config)(query="DefinitelyNoSuchSymbolZZZ")
    assert not miss["results"]
    assert coverage.SAME_BASENAME_KEY not in miss


def test_census_tests_the_basename_before_it_walks_the_ignore_rules() -> None:
    """The cheap filters gate `is_ignored`, which is O(rules) — 4.8 s on a 52k-file tree, else."""
    tree = [f"src/pkg{n}/mod{n}.php" for n in range(500)]
    tree += ["src/pkg1/target.js", "src/pkg1/target.md", "src/pkg1/other.js"]
    asked: list[str] = []

    class SpyMatcher:
        def is_ignored(self, path: str, *, is_dir: bool = False) -> bool:
            asked.append(path)
            return False

    root = Path("/nowhere")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(coverage, "load_ignore", lambda _root: SpyMatcher())
        patch.setattr(coverage.gitutil, "ls_files", lambda _root: tuple(tree))
        suffixes, count = coverage._unindexed_same_stem_census(
            root, frozenset({"target"}), frozenset({".php"})
        )

    assert (suffixes, count) == ((".js", ".md"), 2)
    # Only the two same-stem, unheld-suffix paths reach the rule walk — not all 503.
    assert asked == ["src/pkg1/target.js", "src/pkg1/target.md"]
