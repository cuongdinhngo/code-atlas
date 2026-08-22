"""Task 124: ``find_orphans`` must page, name its walk budget, and stay transport-safe."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import find_orphans, get_index_status
from tests.test_reachability import config_for, node, seed_file

ENTRY = "entry.php"
TARGET = "\\Shim\\Orphan"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def _plant_many_orphans(
    store: GraphStore, tmp_path: Path, *, n: int, entry_points: tuple[str, ...] = (ENTRY,)
) -> list[str]:
    """One reachable entry file and ``n`` orphan classes in stable qname order."""
    seed_file(
        store,
        ENTRY,
        [
            node("File", ENTRY, ENTRY, ENTRY),
            node("Function", "main", "\\Entry\\main", ENTRY),
        ],
        [],
    )
    order: list[str] = []
    for i in range(n):
        path = f"legacy/orphan{i:04d}.php"
        qname = f"\\Orphan\\O{i:04d}"
        if i == n // 2:
            path = "legacy/shim.php"
            qname = TARGET
        seed_file(store, path, [node("Class", f"O{i:04d}", qname, path)], [])
        order.append(qname)
    return sorted(order)


def test_total_count_is_orphan_population_not_page_length(
    store: GraphStore, tmp_path: Path
) -> None:
    """Proving test / AC4: ``total_count`` names the capped population, not the page."""
    order = _plant_many_orphans(store, tmp_path, n=12)
    config = replace(config_for(tmp_path), max_results=10, orphans_max_nodes=500)
    result = find_orphans.create(config)(detail_level="minimal")
    assert len(result["results"]) == 10
    assert result["total_count"] == 12
    assert result["truncated"] is True
    assert result["total_count"] > len(result["results"])
    assert {hit["qname"] for hit in result["results"]} <= set(order)


def test_paged_walk_visits_each_orphan_once(store: GraphStore, tmp_path: Path) -> None:
    """AC2: 057 walk shape over the orphan list."""
    order = _plant_many_orphans(store, tmp_path, n=5)
    config = replace(config_for(tmp_path), max_results=2, orphans_max_nodes=500)
    tool = find_orphans.create(config)

    def walk() -> list[str]:
        seen: list[str] = []
        offset = 0
        while True:
            page = tool(detail_level="minimal", limit=2, offset=offset)
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


def test_known_orphan_on_page_two(store: GraphStore, tmp_path: Path) -> None:
    """AC6: the round-6 shim class is reachable only via ``offset``."""
    order = _plant_many_orphans(store, tmp_path, n=12)
    assert TARGET in order
    config = replace(config_for(tmp_path), max_results=10, orphans_max_nodes=500)
    tool = find_orphans.create(config)
    page1 = tool(detail_level="minimal")
    page2 = tool(detail_level="minimal", offset=10)
    assert page1["total_count"] == 12
    assert TARGET not in {hit["qname"] for hit in page1["results"]}
    assert TARGET in {hit["qname"] for hit in page2["results"]}
    assert page2["truncated"] is False


def test_orphans_budget_is_independent_of_impact_max_nodes(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC3: ``impact_max_nodes`` does not govern which orphans are returned."""
    _plant_many_orphans(store, tmp_path, n=8)
    base = replace(
        config_for(tmp_path),
        max_results=50,
        orphans_max_nodes=500,
    )
    low_impact = replace(base, impact_max_nodes=1)
    high_impact = replace(base, impact_max_nodes=999)
    from_low = find_orphans.create(low_impact)(detail_level="minimal")
    from_high = find_orphans.create(high_impact)(detail_level="minimal")
    assert from_low["results"] == from_high["results"]
    assert from_low["total_count"] == 8


def test_orphans_max_nodes_governs_the_walk(store: GraphStore, tmp_path: Path) -> None:
    """AC3: the named ``orphans_max_nodes`` knob binds the reachability walk."""
    from tests.test_reachability import plant_chain

    plant_chain(store, hops=4)
    config = replace(
        load_config(tmp_path, {}),
        db_path=tmp_path / "graph.db",
        entry_points=("src/entry.php",),
        orphans_max_nodes=2,
        impact_max_nodes=999,
        max_results=50,
    )
    tight = find_orphans.create(config)(detail_level="minimal")
    loose = find_orphans.create(replace(config, orphans_max_nodes=50))(
        detail_level="minimal"
    )
    assert tight["walk_truncated"] is True
    assert "walk_truncated" not in loose
    assert len(tight["results"]) > len(loose["results"])
    # Both pages hold every orphan they found: page truncation is the pager's signal, and it
    # must not inherit the walk's — a budget-bound walk would otherwise never stop paging (124).
    assert tight["truncated"] is False
    assert loose["truncated"] is False


def test_minimal_payload_stays_small_at_scale(store: GraphStore, tmp_path: Path) -> None:
    """AC1 (reduced scale): ``minimal`` stays under a transport-sized JSON envelope."""
    _plant_many_orphans(store, tmp_path, n=200)
    config = replace(config_for(tmp_path), max_results=50, orphans_max_nodes=500)
    payload = find_orphans.create(config)(detail_level="minimal")
    size = len(json.dumps(payload))
    assert size < 80_000
    assert payload["unproven_total"] == 0
    assert "unproven" not in payload or payload["unproven"] == []


def test_status_reports_orphans_max_nodes(store: GraphStore, tmp_path: Path) -> None:
    """Walk budget is discoverable from ``get_index_status``."""
    _plant_many_orphans(store, tmp_path, n=3)
    config = replace(config_for(tmp_path), orphans_max_nodes=123)
    status = get_index_status.create(config, ["find_orphans"])(detail_level="standard")
    assert status["orphans_max_nodes"] == {
        "value": 123,
        "governs": ["orphans_reachability_walk"],
    }


def test_bad_offset_fails_loud_when_unindexed(tmp_path: Path) -> None:
    config = replace(load_config(tmp_path, {}), db_path=tmp_path / "missing.db")
    tool = find_orphans.create(config)
    with pytest.raises(ValueError, match="offset"):
        tool(offset=-1, detail_level="minimal")


def test_pager_terminates_when_the_walk_hit_its_budget(
    store: GraphStore, tmp_path: Path
) -> None:
    """124: a budget-bound walk must not keep the pager alive after the last page.

    ``truncated`` is the page's own flag; folding the walk's budget into it made every page of
    the 19k-file repo this ticket is about report ``truncated: true`` forever.
    """
    _plant_many_orphans(store, tmp_path, n=12)
    config = replace(config_for(tmp_path), max_results=50, orphans_max_nodes=1)
    tool = find_orphans.create(config)
    offset, pages, seen = 0, 0, []
    while pages < 5:
        page = tool(detail_level="minimal", limit=50, offset=offset)
        pages += 1
        seen += [str(hit["qname"]) for hit in page["results"]]
        assert page["walk_truncated"] is True  # the over-estimate is still disclosed
        if not page["truncated"]:
            break
        offset += len(page["results"])
    assert pages == 1
    assert len(seen) == page["total_count"]
