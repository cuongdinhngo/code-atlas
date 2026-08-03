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
from code_atlas.tools.reach_shared import NO_ROOTS, entry_seeds
from code_atlas.tools.reachable_from import NAME as REACHABLE_FROM

ENTRY = "entry.php"
LIB = "lib.php"
DEAD = "dead.php"
ENTRY_FN = "\\Entry\\main"
CALLEE = "\\Lib\\Helper"
CHILD = "\\Lib\\Child"
ORPHAN = "\\Dead\\Unused"
HEURISTIC = "\\Lib\\Maybe"
METHOD = "\\Lib\\Service::run"
SERVICE = "\\Lib\\Service"


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
            edge("CALLS", ENTRY_FN, METHOD, ENTRY, line=4),
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
            node("Class", "Service", SERVICE, LIB, line=50),
            node("Method", "run", METHOD, LIB, line=51),
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


def plant_chain(store: GraphStore, hops: int) -> None:
    """Linear CALLS chain — entry seeds only ``main``; callees live in ``lib.php`` (W1)."""
    entry = "src/entry.php"
    lib = "src/lib.php"
    methods: list[str] = []
    lib_nodes: list[dict[str, object]] = [node("File", lib, lib, lib)]
    for i in range(hops):
        name = chr(ord("A") + i)
        method = f"\\{name}::{name.lower()}"
        methods.append(method)
        lib_nodes.append(node("Class", name, f"\\{name}", lib, line=10 + i))
        lib_nodes.append(node("Method", name.lower(), method, lib, line=20 + i))
    lib_edges = [
        edge("CALLS", methods[i - 1], methods[i], lib, line=30 + i)
        for i in range(1, hops)
    ]
    seed_file(
        store,
        entry,
        [
            node("File", entry, entry, entry),
            node("Function", "main", "\\main", entry),
        ],
        [
            edge("CALLS", "\\main", methods[0], entry, line=2),
            edge("INCLUDES", entry, lib, entry, line=3),
        ],
    )
    seed_file(store, lib, lib_nodes, lib_edges)


def config_for(
    tmp_path: Path, *, entry_points: tuple[str, ...] = (ENTRY,)
):
    return replace(
        load_config(tmp_path, {}),
        db_path=tmp_path / "graph.db",
        entry_points=entry_points,
        impact_max_nodes=50,
    )


def test_tools_are_registered_in_tool_names() -> None:
    assert REACHABLE_FROM in TOOL_NAMES
    assert FIND_ORPHANS in TOOL_NAMES


def test_reachable_from_matches_hand_traced_planted_graph(
    store: GraphStore, tmp_path: Path
) -> None:
    plant_graph(store)
    payload = reachable_from_tool.create(config_for(tmp_path))()
    assert payload["status"] == "ok"
    assert payload["authoritative"] is False
    assert payload["depth_exhausted"] is False
    assert payload["depth"] is None  # closure by default
    # Hand-traced RESOLVED forward + containers of reached members (Service via ::run).
    assert {str(r["qname"]) for r in payload["results"]} == {
        ENTRY,
        ENTRY_FN,
        CALLEE,
        CHILD,
        LIB,
        "\\Lib\\Impl",
        "\\Lib\\IFace",
        METHOD,
        SERVICE,
    }
    assert {str(r["qname"]) for r in payload["unproven"]} == {HEURISTIC}
    assert "edge_health" in payload


def test_find_orphans_hand_traced(store: GraphStore, tmp_path: Path) -> None:
    plant_graph(store)
    payload = find_orphans_tool.create(config_for(tmp_path))()
    assert payload["status"] == "ok"
    by_qname = {str(r["qname"]): r for r in payload["results"]}
    assert set(by_qname) == {DEAD, ORPHAN}
    assert by_qname[ORPHAN]["why"] == "no_inbound"
    assert by_qname[DEAD]["why"] == "no_inbound"
    assert SERVICE not in by_qname  # container of live method
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
    config = config_for(tmp_path)
    orphans = {
        str(r["qname"]) for r in find_orphans_tool.create(config)()["results"]
    }
    unproven = {
        str(r["qname"]) for r in reachable_from_tool.create(config)()["unproven"]
    }
    assert HEURISTIC in unproven
    assert HEURISTIC not in orphans


def test_default_closure_does_not_orphan_deep_chain(
    store: GraphStore, tmp_path: Path
) -> None:
    plant_chain(store, hops=4)
    config = replace(
        load_config(tmp_path, {}),
        db_path=tmp_path / "graph.db",
        entry_points=("src/entry.php",),
        impact_max_nodes=50,
    )
    orphans = find_orphans_tool.create(config)()
    assert orphans["depth_exhausted"] is False
    assert orphans["truncated"] is False
    assert orphans["results"] == []
    shallow = find_orphans_tool.create(config)(depth=2)
    assert shallow["depth_exhausted"] is True
    assert shallow["truncated"] is True
    why = {str(r["qname"]) for r in shallow["results"]}
    assert "\\C::c" in why
    assert "\\D::d" in why


def test_called_method_keeps_declaring_class_alive(
    store: GraphStore, tmp_path: Path
) -> None:
    plant_graph(store)
    orphans = {
        str(r["qname"]) for r in find_orphans_tool.create(config_for(tmp_path))()["results"]
    }
    assert SERVICE not in orphans
    assert METHOD not in orphans


def test_entry_globs_respect_path_segments(store: GraphStore, tmp_path: Path) -> None:
    seed_file(
        store,
        "src/entry.php",
        [node("File", "src/entry.php", "src/entry.php", "src/entry.php")],
        [],
    )
    seed_file(
        store,
        "src/deep/nested/lib.php",
        [
            node(
                "File",
                "src/deep/nested/lib.php",
                "src/deep/nested/lib.php",
                "src/deep/nested/lib.php",
            )
        ],
        [],
    )
    seeds = entry_seeds(store, ("src/*.php",))
    assert seeds == ["src/entry.php"]
    deep = entry_seeds(store, ("src/**/*.php",))
    assert set(deep) == {"src/entry.php", "src/deep/nested/lib.php"}
