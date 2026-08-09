"""Task 073: miss-driven freshness — zero hits can repair the sole dirty indexed file."""

from __future__ import annotations

import subprocess
from pathlib import Path

from code_atlas.indexer import file_is_current, full_build
from code_atlas.store import GraphStore
from code_atlas.tools import (
    file_outline,
    find_callers,
    find_implementations,
    find_references,
    find_view_data,
    read_symbol,
    search_symbol,
)
from code_atlas.tools.freshness import FreshnessGuard, dirty_indexed_paths
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_OK,
    TRY_INSTEAD_FILE_OUTLINE,
)
from tests.test_read_through_freshness import config_for, write


def _git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=root,
        check=True,
        capture_output=True,
    )


def test_search_miss_repairs_sole_dirty_indexed_file(tmp_path: Path) -> None:
    """Cell A with one dirty file: miss-repair finds the new symbol (073)."""
    write(tmp_path, "src/Widget.aa", "class Widget {}\n")
    _git_init(tmp_path)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    write(tmp_path, "src/Widget.aa", "class Widget {}\n# symbol: atlasProbeZq7\n")

    result = search_symbol.create(config)("atlasProbeZq7", detail_level="minimal")
    assert result["reason"] == REASON_OK
    assert result["total_count"] == 1
    assert result["results"][0]["qname"] == "src/Widget.aa::atlasProbeZq7"


def test_abc_multi_dirty_outline_then_search(tmp_path: Path) -> None:
    """Classic A/B/C under multi-dirty: A signals stale, B path-repairs, C finds via FTS."""
    write(tmp_path, "src/Widget.aa", "class Widget {}\n")
    write(tmp_path, "src/Other.aa", "class Other {}\n")
    _git_init(tmp_path)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    write(tmp_path, "src/Widget.aa", "class Widget {}\n# symbol: atlasProbeZq7\n")
    write(tmp_path, "src/Other.aa", "class Other { /* drift */ }\n")

    search = search_symbol.create(config)
    cell_a = search("atlasProbeZq7", detail_level="minimal")
    assert cell_a["reason"] == REASON_INDEX_STALE
    assert cell_a["total_count"] == 0
    assert cell_a["try_instead"] == TRY_INSTEAD_FILE_OUTLINE

    cell_b = file_outline.create(config)("src/Widget.aa", detail_level="minimal")
    assert any(
        hit.get("qname") == "src/Widget.aa::atlasProbeZq7" for hit in cell_b["results"]
    )

    cell_c = search("atlasProbeZq7", detail_level="minimal")
    assert cell_c["reason"] == REASON_OK
    assert cell_c["total_count"] == 1
    assert cell_c["results"][0]["qname"] == "src/Widget.aa::atlasProbeZq7"


def test_six_consumers_share_ensure_qname_miss_path(tmp_path: Path) -> None:
    """ensure_qname no-rows + search miss: all six consumers honour multi-dirty stale."""
    write(tmp_path, "src/a.aa", "class A {}\n")
    write(tmp_path, "src/b.aa", "class B {}\n")
    _git_init(tmp_path)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    write(tmp_path, "src/a.aa", "class A { /* d */ }\n")
    write(tmp_path, "src/b.aa", "class B { /* d */ }\n")

    qname = "src/a.aa::NeverIndexed"
    qname_tools = (
        find_callers.create(config),
        find_references.create(config),
        find_implementations.create(config),
        find_view_data.create(config),
        read_symbol.create(config),
    )
    for tool in qname_tools:
        result = tool(qname, detail_level="minimal")
        assert result["reason"] == REASON_INDEX_STALE, tool
        assert result["try_instead"] == TRY_INSTEAD_FILE_OUTLINE, tool

    search = search_symbol.create(config)("NeverIndexed", detail_level="minimal")
    assert search["reason"] == REASON_INDEX_STALE
    assert search["try_instead"] == TRY_INSTEAD_FILE_OUTLINE


def test_ensure_qname_miss_then_symbol_indexed(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    _git_init(tmp_path)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    write(tmp_path, "src/a.aa", "class Thing {}\n# symbol: NewSym\n")
    qname = "src/a.aa::NewSym"
    for factory in (
        find_callers.create,
        find_references.create,
        find_implementations.create,
        find_view_data.create,
    ):
        result = factory(config)(qname, detail_level="minimal")
        assert result["reason"] in {REASON_NO_MATCHES, REASON_OK}
        assert result["reason"] != REASON_NO_SUCH_SYMBOL
    assert read_symbol.create(config)(qname, detail_level="minimal")["found"] is True


def test_empty_page_past_the_end_is_not_a_miss(tmp_path: Path) -> None:
    """An offset past the end is an empty page, not an empty answer (057) — no miss-repair.

    Without the `offset == 0` guard this returned `index_stale` beside `total_count: 2`, so the
    freshness verdict flipped with pagination, and one dirty file spent the cap on a hit query.
    """
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    write(tmp_path, "src/b.aa", "class Other {}\n")
    _git_init(tmp_path)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    write(tmp_path, "src/a.aa", "class Thing {}\n# symbol: atlasProbeZq7\n")
    write(tmp_path, "src/b.aa", "class Other { /* drift */ }\n")

    search = search_symbol.create(config)
    page = search("Thing", detail_level="minimal", limit=1, offset=9)
    assert page["results"] == []
    assert int(page["total_count"]) > 0
    assert page["reason"] == REASON_OK, "an empty page must not claim staleness"
    assert "try_instead" not in page

    # The cap is unspent: a hit query paging past its end reparses nothing.
    with GraphStore(config.db_path) as store:
        assert not file_is_current(store, tmp_path, "src/a.aa")


def test_dirty_indexed_paths_ignores_non_indexed_suffixes(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class A {}\n")
    write(tmp_path, "README.md", "hi\n")
    _git_init(tmp_path)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        write(tmp_path, "src/a.aa", "class A { /* d */ }\n")
        write(tmp_path, "README.md", "bye\n")
        assert dirty_indexed_paths(store, config) == ["src/a.aa"]
        assert FreshnessGuard(config, store).ensure_miss() == "repaired"
