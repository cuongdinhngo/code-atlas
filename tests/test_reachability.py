"""Task 031: reachability / orphan detection (inverse of impact)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.main import TOOL_NAMES
from code_atlas.store import GraphStore
from code_atlas.tools import find_orphans as find_orphans_tool
from code_atlas.tools import reachable_from as reachable_from_tool
from code_atlas.tools.find_orphans import NAME as FIND_ORPHANS
from code_atlas.tools.reachable_from import NAME as REACHABLE_FROM
from code_atlas.tools.reachable_from import NO_ROOTS

ENTRY = "entry.php"
LIB = "lib.php"
DEAD = "dead.php"
ENTRY_FN = "\\Entry\\main"
CALLEE = "\\Lib\\Helper"
CHILD = "\\Lib\\Child"
ORPHAN = "\\Dead\\Unused"
HEURISTIC = "\\Lib\\Maybe"


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
    """entry.php seeds → lib via CALLS/NEW/INCLUDES; Maybe only HEURISTIC; dead orphan."""
    iface = "\\Lib\\IFace"
    impl = "\\Lib\\Impl"
    seed_file(
        store,
        ENTRY,
        [
            node("File", ENTRY, ENTRY, ENTRY),
            node("Function", "main", ENTRY_FN, ENTRY),
        ],
        [
            edge("CALLS", ENTRY_FN, CALLEE, ENTRY),
            edge("NEW", ENTRY_FN, CALLEE, ENTRY, line=2),
            edge("INCLUDES", ENTRY, LIB, ENTRY, line=3),
        ],
    )
    seed_file(
        store,
        LIB,
        [
            node("File", LIB, LIB, LIB),
            node("Class", "Helper", CALLEE, LIB),
            node("Class", "Child", CHILD, LIB, line=10),
            node("Class", "Maybe", HEURISTIC, LIB, line=20),
            node("Interface", "IFace", iface, LIB, line=30),
            node("Class", "Impl", impl, LIB, line=40),
        ],
        [
            edge("CALLS", CALLEE, CHILD, LIB),
            edge("EXTENDS", CHILD, CALLEE, LIB),
            edge("IMPLEMENTS", impl, iface, LIB, line=41),
            edge("CALLS", CALLEE, HEURISTIC, LIB, tier="HEURISTIC"),
            edge("CALLS", CALLEE, impl, LIB, line=42),
        ],
    )
    seed_file(
        store,
        DEAD,
        [
            node("File", DEAD, DEAD, DEAD),
            node("Class", "Unused", ORPHAN, DEAD),
        ],
        [],
    )


def test_tools_are_registered_in_tool_names() -> None:
    assert REACHABLE_FROM in TOOL_NAMES
    assert FIND_ORPHANS in TOOL_NAMES


def test_reachable_from_matches_hand_traced_planted_graph(
    store: GraphStore, tmp_path: Path
) -> None:
    plant_graph(store)
    config = replace(
        load_config(tmp_path, {}),
        db_path=tmp_path / "graph.db",
        entry_points=(ENTRY,),
        impact_depth=5,
        impact_max_nodes=50,
    )
    payload = reachable_from_tool.create(config)()
    assert payload["status"] == "ok"
    assert payload["authoritative"] is False
    # Hand-traced RESOLVED forward from entry.php nodes:
    # ENTRY, ENTRY_FN → CALLEE (CALLS/NEW) → CHILD, Impl; ENTRY → LIB (INCLUDES).
    # Impl → IFace (IMPLEMENTS). Maybe is HEURISTIC-only.
    assert {str(r["qname"]) for r in payload["results"]} == {
        ENTRY,
        ENTRY_FN,
        CALLEE,
        CHILD,
        LIB,
        "\\Lib\\Impl",
        "\\Lib\\IFace",
    }
    assert {str(r["qname"]) for r in payload["unproven"]} == {HEURISTIC}
    assert "edge_health" in payload


def test_find_orphans_hand_traced(store: GraphStore, tmp_path: Path) -> None:
    plant_graph(store)
    config = replace(
        load_config(tmp_path, {}),
        db_path=tmp_path / "graph.db",
        entry_points=(ENTRY,),
        impact_depth=5,
        impact_max_nodes=50,
    )
    payload = find_orphans_tool.create(config)()
    assert payload["status"] == "ok"
    by_qname = {str(r["qname"]): r for r in payload["results"]}
    assert set(by_qname) == {DEAD, ORPHAN}
    assert by_qname[ORPHAN]["why"] == "no_inbound"
    assert by_qname[DEAD]["why"] == "no_inbound"
    assert {str(r["qname"]) for r in payload["unproven"]} == {HEURISTIC}


def test_unset_entry_points_is_no_roots(tmp_path: Path) -> None:
    config = replace(load_config(tmp_path, {}), db_path=tmp_path / "missing.db")
    assert config.entry_points is None
    for tool in (reachable_from_tool.create(config), find_orphans_tool.create(config)):
        payload = tool()
        assert payload["status"] == NO_ROOTS
        assert payload["results"] == []
        assert "no roots configured" in str(payload["message"])


def test_heuristic_only_is_unproven_not_orphan(store: GraphStore, tmp_path: Path) -> None:
    plant_graph(store)
    config = replace(
        load_config(tmp_path, {}),
        db_path=tmp_path / "graph.db",
        entry_points=(ENTRY,),
    )
    orphans = {
        str(r["qname"]) for r in find_orphans_tool.create(config)()["results"]
    }
    unproven = {
        str(r["qname"]) for r in reachable_from_tool.create(config)()["unproven"]
    }
    assert HEURISTIC in unproven
    assert HEURISTIC not in orphans
