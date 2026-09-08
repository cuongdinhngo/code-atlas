"""Task 123: ``file_outline`` must report the real symbol count and page like its siblings.

Proving path is integration: seed a store, then call the real tool — the layer where a wrong
``total_count`` or a terminal truncation would mislead a reader porting a large file.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import Config
from code_atlas.store import GraphStore
from code_atlas.tools import file_outline
from tests.test_nav_tools import db_config, node, seed_file


def _config(tmp_path: Path, *, max_results: int = 10) -> Config:
    return replace(db_config(tmp_path), root=tmp_path, max_results=max_results)


def _plant_symbols(
    store: GraphStore, root: Path, path: str, *, n: int, kinds: tuple[str, ...] = ("Method",)
) -> list[str]:
    """Plant ``n`` symbols on ``path``; return qnames in store order."""
    nodes = [
        node(
            kinds[i % len(kinds)],
            f"sym{i:02d}",
            f"\\Ns\\sym{i:02d}",
            path,
        )
        for i in range(n)
    ]
    for i, row in enumerate(nodes):
        row["line_start"] = i + 1
        row["line_end"] = i + 1
    seed_file(store, path, nodes, [], root=root)
    with GraphStore(root / "graph.db") as reopened:
        return [str(row["qualified_name"]) for row in reopened.nodes_by_file(path, limit=n)]


@pytest.fixture
def store(tmp_path: Path) -> GraphStore:
    path = tmp_path / "graph.db"
    opened = GraphStore(path)
    opened.__enter__()
    yield opened
    opened.__exit__(None, None, None)


def test_total_count_is_the_file_symbol_count_not_the_page(
    store: GraphStore, tmp_path: Path
) -> None:
    """Proving test / AC1: ``total_count`` and ``truncated`` cannot contradict each other."""
    path = "src/Large.php"
    _plant_symbols(store, tmp_path, path, n=12)
    config = _config(tmp_path, max_results=10)
    result = file_outline.create(config)(path, detail_level="minimal")
    assert result["found"] is True
    assert len(result["results"]) == 10
    assert result["total_count"] == 12
    assert result["truncated"] is True
    assert result["total_count"] > len(result["results"])


def test_paged_walk_visits_each_symbol_once(store: GraphStore, tmp_path: Path) -> None:
    """AC3: 057's walk shape — every symbol once, last page not truncated."""
    path = "src/Page.php"
    order = _plant_symbols(store, tmp_path, path, n=5)
    config = _config(tmp_path, max_results=2)
    tool = file_outline.create(config)

    def walk() -> list[str]:
        seen: list[str] = []
        offset = 0
        while True:
            page = tool(path, detail_level="minimal", limit=2, offset=offset)
            assert page["total_count"] == 5
            for hit in page["results"]:
                seen.append(str(hit["qname"]))
            if not page["truncated"]:
                break
            offset += len(page["results"])
            assert len(page["results"]) > 0
        return seen

    first = walk()
    second = walk()
    assert first == second == order
    assert len(set(first)) == 5


def test_round6_regression_symbol_on_page_two(store: GraphStore, tmp_path: Path) -> None:
    """AC5: a symbol beyond the first page is reachable and the payload discloses the rest."""
    path = "src/Repair.php"
    order = _plant_symbols(store, tmp_path, path, n=12, kinds=("Method", "Property"))
    missing = order[10]
    config = _config(tmp_path, max_results=10)
    tool = file_outline.create(config)
    page1 = tool(path, detail_level="minimal")
    page2 = tool(path, detail_level="minimal", offset=10)
    assert page1["total_count"] == 12
    assert page1["truncated"] is True
    assert missing not in {hit["qname"] for hit in page1["results"]}
    assert missing in {hit["qname"] for hit in page2["results"]}
    assert page2["truncated"] is False
    assert "result_kinds" in page1


def test_single_page_payload_unchanged(store: GraphStore, tmp_path: Path) -> None:
    """AC6: a file that fits in one page stays byte-identical to the pre-123 shape."""
    path = "src/Small.php"
    _plant_symbols(store, tmp_path, path, n=3)
    config = _config(tmp_path, max_results=10)
    result = file_outline.create(config)(path, detail_level="minimal")
    assert result == {
        "indexed": True,
        "path": path,
        "found": True,
        "results": result["results"],
        "truncated": False,
        "index_root": config.index_root,
        "reason": "ok",
        "total_count": 3,
    }
    assert "server_version" not in result  # 223: minimal omits identity
    assert "result_kinds" not in result
    assert "limit_capped_to" not in result


def test_bad_offset_fails_loud_when_unindexed(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert not config.db_path.is_file()
    tool = file_outline.create(config)
    with pytest.raises(ValueError, match="offset"):
        tool("src/x.php", offset=-1, detail_level="minimal")
