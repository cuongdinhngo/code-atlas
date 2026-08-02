"""Task 017: impact engine — SQL best-score blast radius (§12 / M6)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.store import IMPACT_DECAY, IMPACT_FLOOR, IMPACT_WEIGHTS, GraphStore
from code_atlas.tools import impact as impact_tool

# Hand-traced scores (A1): seed 1.0; CALLS weight 1.0; EXTENDS 0.9; decay ×0.7.
SEED = "\\Changed"
CALLER = "\\Caller"
NEW_CALLER = "\\NewCaller"
CHILD = "\\Child"
IMPL = "\\Impl"
INCLUDER = "\\Includer"
GRAND = "\\GrandCaller"
HEURISTIC = "\\HeuristicCaller"
DYNAMIC = "\\DynamicCaller"
CONTAINER = "\\FileContainer"

SCORE_CALLER = 1.0 * IMPACT_WEIGHTS["CALLS"] * IMPACT_DECAY  # 0.7
SCORE_NEW = 1.0 * IMPACT_WEIGHTS["NEW"] * IMPACT_DECAY  # 0.7
SCORE_CHILD = 1.0 * IMPACT_WEIGHTS["EXTENDS"] * IMPACT_DECAY  # 0.63
SCORE_IMPL = 1.0 * IMPACT_WEIGHTS["IMPLEMENTS"] * IMPACT_DECAY  # 0.63
SCORE_INCLUDER = 1.0 * IMPACT_WEIGHTS["INCLUDES"] * IMPACT_DECAY  # 0.56
SCORE_GRAND = SCORE_CALLER * IMPACT_WEIGHTS["CALLS"] * IMPACT_DECAY  # 0.49


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def seed_file(store: GraphStore, path: str, nodes: list[dict], edges: list[dict]) -> None:
    store.upsert_file(path, "h", "lang")
    store.replace_file_rows(path, nodes, edges)


def node(kind: str, name: str, qname: str, path: str, *, line: int = 1) -> dict[str, object]:
    return {
        "kind": kind,
        "name": name,
        "qualified_name": qname,
        "file_path": path,
        "line_start": line,
    }


def edge(
    kind: str,
    source: str,
    target: str,
    path: str,
    *,
    tier: str = "RESOLVED",
    line: int = 1,
) -> dict[str, object]:
    return {
        "kind": kind,
        "source_qname": source,
        "target_raw": target,
        "target_qname": target,
        "file_path": path,
        "line": line,
        "confidence_tier": tier,
    }


def plant_graph(store: GraphStore) -> None:
    """Tiny graph whose blast radius is hand-traced in the proving test."""
    path = "a.php"
    seed_file(
        store,
        path,
        [
            node("Class", "Changed", SEED, path, line=10),
            node("Class", "Caller", CALLER, path, line=20),
            node("Class", "NewCaller", NEW_CALLER, path, line=25),
            node("Class", "Child", CHILD, path, line=30),
            node("Class", "Impl", IMPL, path, line=35),
            node("File", "Includer", INCLUDER, path, line=36),
            node("Class", "GrandCaller", GRAND, path, line=40),
            node("Class", "HeuristicCaller", HEURISTIC, path, line=50),
            node("Class", "DynamicCaller", DYNAMIC, path, line=60),
            node("File", "a.php", CONTAINER, path, line=1),
        ],
        [
            edge("CALLS", CALLER, SEED, path, line=21),
            edge("NEW", NEW_CALLER, SEED, path, line=26),
            edge("EXTENDS", CHILD, SEED, path, line=31),
            edge("IMPLEMENTS", IMPL, SEED, path, line=35),
            edge("INCLUDES", INCLUDER, SEED, path, line=36),
            edge("CALLS", GRAND, CALLER, path, line=41),
            edge("CALLS", HEURISTIC, SEED, path, tier="HEURISTIC", line=51),
            edge("CALLS", DYNAMIC, SEED, path, tier="DYNAMIC", line=61),
            edge("CONTAINS", CONTAINER, SEED, path, line=1),
        ],
    )


def test_impact_matches_hand_traced_planted_graph(store: GraphStore) -> None:
    """AC2 / proving test: planted set+scores match the A1 hand trace."""
    plant_graph(store)
    rows = store.impact_radius([SEED], depth=2, max_nodes=50)
    by_qname = {str(r["qname"]): r for r in rows}

    assert set(by_qname) == {SEED, CALLER, NEW_CALLER, CHILD, IMPL, INCLUDER, GRAND}
    assert by_qname[SEED]["score"] == pytest.approx(1.0)
    assert by_qname[SEED]["depth"] == 0
    assert by_qname[CALLER]["score"] == pytest.approx(SCORE_CALLER)
    assert by_qname[NEW_CALLER]["score"] == pytest.approx(SCORE_NEW)
    assert by_qname[CHILD]["score"] == pytest.approx(SCORE_CHILD)
    assert by_qname[IMPL]["score"] == pytest.approx(SCORE_IMPL)
    assert by_qname[INCLUDER]["score"] == pytest.approx(SCORE_INCLUDER)
    assert by_qname[GRAND]["score"] == pytest.approx(SCORE_GRAND)
    assert by_qname[GRAND]["depth"] == 2
    assert HEURISTIC not in by_qname and DYNAMIC not in by_qname and CONTAINER not in by_qname

    ordered = [str(r["qname"]) for r in rows]
    assert ordered == [SEED, CALLER, NEW_CALLER, CHILD, IMPL, INCLUDER, GRAND]


def test_depth_cap_excludes_second_hop(store: GraphStore) -> None:
    plant_graph(store)
    rows = store.impact_radius([SEED], depth=1, max_nodes=50)
    assert {str(r["qname"]) for r in rows} == {
        SEED,
        CALLER,
        NEW_CALLER,
        CHILD,
        IMPL,
        INCLUDER,
    }


def test_max_nodes_keeps_highest_scores(store: GraphStore) -> None:
    plant_graph(store)
    rows = store.impact_radius([SEED], depth=2, max_nodes=2)
    assert [str(r["qname"]) for r in rows] == [SEED, CALLER]


def test_heuristic_does_not_expand_frontier(store: GraphStore) -> None:
    path = "h.php"
    mid = "\\Mid"
    leaf = "\\Leaf"
    seed_file(
        store,
        path,
        [
            node("Class", "Changed", SEED, path),
            node("Class", "Mid", mid, path),
            node("Class", "Leaf", leaf, path),
        ],
        [
            edge("CALLS", mid, SEED, path, tier="HEURISTIC"),
            edge("CALLS", leaf, mid, path),
        ],
    )
    rows = store.impact_radius([SEED], depth=2, max_nodes=50)
    assert {str(r["qname"]) for r in rows} == {SEED}


def test_floor_drops_weak_hops(store: GraphStore) -> None:
    assert IMPACT_FLOOR == 0.05
    path = "f.php"
    # 0.7**8 ≈ 0.0576 (kept); 0.7**9 ≈ 0.0403 (below floor).
    names = [f"\\N{i}" for i in range(10)]
    nodes = [node("Class", f"N{i}", names[i], path) for i in range(10)]
    edges = [edge("CALLS", names[i + 1], names[i], path) for i in range(9)]
    seed_file(store, path, nodes, edges)
    rows = store.impact_radius([names[0]], depth=20, max_nodes=50)
    qnames = {str(r["qname"]) for r in rows}
    assert names[8] in qnames
    assert names[9] not in qnames
    assert all(float(r["score"]) >= IMPACT_FLOOR for r in rows)


def test_path_seeds_union_all_file_nodes(tmp_path: Path, store: GraphStore) -> None:
    plant_graph(store)
    config = replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")
    payload = impact_tool.create(config)(paths=["a.php"], depth=0)
    qnames = {str(r["qname"]) for r in payload["results"]}
    assert SEED in qnames and CALLER in qnames
    assert payload["indexed"] is True


def test_unknown_seed_is_empty_success(tmp_path: Path) -> None:
    config = replace(load_config(tmp_path, {}), db_path=tmp_path / "missing.db")
    payload = impact_tool.create(config)(qnames=["\\Nope"])
    assert payload["indexed"] is False
    assert payload["results"] == []


def test_missing_qname_with_db_is_empty_success(store: GraphStore, tmp_path: Path) -> None:
    plant_graph(store)
    config = replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")
    payload = impact_tool.create(config)(qnames=["\\Missing"], depth=0)
    assert payload["indexed"] is True
    assert payload["results"] == []


def test_exact_max_nodes_fill_is_not_truncated(store: GraphStore, tmp_path: Path) -> None:
    plant_graph(store)
    # depth=0 → only seeds from one qname → exactly 1 row; must not claim truncation.
    config = replace(
        load_config(tmp_path, {}),
        db_path=tmp_path / "graph.db",
        impact_max_nodes=1,
    )
    payload = impact_tool.create(config)(qnames=[SEED], depth=0)
    assert len(payload["results"]) == 1
    assert payload["truncated"] is False
