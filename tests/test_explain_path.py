"""Task 038: explain_path — shortest control-flow path between two qnames."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.main import TOOL_NAMES
from code_atlas.store import (
    PATH_STATUS_INCOMPLETE,
    PATH_STATUS_NO_PATH,
    PATH_STATUS_PATH,
    PATH_STATUS_UNKNOWN,
    PATH_STATUS_UNPROVEN,
    GraphStore,
)
from code_atlas.tools import explain_path as explain_path_tool
from code_atlas.tools.explain_path import NAME as EXPLAIN_PATH

A = "\\App\\A"
B = "\\App\\B"
C = "\\App\\C"
D = "\\App\\D"
HEUR = "\\App\\Maybe"
MISSING = "\\App\\Missing"


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


def plant_chain(store: GraphStore) -> None:
    """A → B → C RESOLVED; A → Maybe HEURISTIC → C; D unreachable from A."""
    path = "app.php"
    seed_file(
        store,
        path,
        [
            node("Class", "A", A, path),
            node("Class", "B", B, path, line=2),
            node("Class", "C", C, path, line=3),
            node("Class", "D", D, path, line=4),
            node("Class", "Maybe", HEUR, path, line=5),
        ],
        [
            edge("CALLS", A, B, path, line=10),
            edge("CALLS", B, C, path, line=11),
            edge("CALLS", A, HEUR, path, tier="HEURISTIC", line=12),
            edge("CALLS", HEUR, C, path, tier="HEURISTIC", line=13),
        ],
    )


@pytest.fixture
def planted(store: GraphStore, tmp_path: Path):
    plant_chain(store)
    cfg = replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")
    return store, cfg


def test_explain_path_registered() -> None:
    assert EXPLAIN_PATH in TOOL_NAMES


def test_planted_chain_returns_exact_resolved_path(planted: tuple) -> None:
    """Proving test: A→B→C is the asserted path, not a count."""
    _store, cfg = planted
    payload = explain_path_tool.create(cfg)(A, C)
    assert payload["status"] == PATH_STATUS_PATH
    hops = payload["path"]
    assert [(h["source_qname"], h["target_qname"], h["kind"]) for h in hops] == [
        (A, B, "CALLS"),
        (B, C, "CALLS"),
    ]
    assert all(h["confidence_tier"] == "RESOLVED" for h in hops)


def test_unreachable_pair_is_no_path_not_empty_proof(planted: tuple) -> None:
    _store, cfg = planted
    payload = explain_path_tool.create(cfg)(A, D)
    assert payload["status"] == PATH_STATUS_NO_PATH
    assert payload["path"] == []


def test_heuristic_only_path_is_unproven(store: GraphStore, tmp_path: Path) -> None:
    """A→Maybe→C with only HEURISTIC edges — unproven, never conflated with path/no_path."""
    path = "h.php"
    seed_file(
        store,
        path,
        [
            node("Class", "A", A, path),
            node("Class", "Maybe", HEUR, path, line=2),
            node("Class", "C", C, path, line=3),
        ],
        [
            edge("CALLS", A, HEUR, path, tier="HEURISTIC"),
            edge("CALLS", HEUR, C, path, tier="HEURISTIC", line=2),
        ],
    )
    cfg = replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")
    payload = explain_path_tool.create(cfg)(A, C)
    assert payload["status"] == PATH_STATUS_UNPROVEN
    assert len(payload["path"]) == 2
    assert all(h["confidence_tier"] == "HEURISTIC" for h in payload["path"])


def test_missing_endpoint_is_unknown(planted: tuple) -> None:
    _store, cfg = planted
    payload = explain_path_tool.create(cfg)(A, MISSING)
    assert payload["status"] == PATH_STATUS_UNKNOWN
    assert payload["path"] == []


def test_depth_budget_incomplete_not_no_path(planted: tuple) -> None:
    _store, cfg = planted
    payload = explain_path_tool.create(cfg)(A, C, depth=1)
    assert payload["status"] == PATH_STATUS_INCOMPLETE
    assert payload["path"] == []
    assert payload["truncated"] is True
    assert payload["depth_exhausted"] is True


def test_same_qname_is_empty_proven_path(planted: tuple) -> None:
    _store, cfg = planted
    payload = explain_path_tool.create(cfg)(A, A)
    assert payload["status"] == PATH_STATUS_PATH
    assert payload["path"] == []


def test_store_explain_path_prefers_resolved_over_shorter_heuristic(
    store: GraphStore,
) -> None:
    plant_chain(store)
    outcome = store.explain_path(A, C, depth=None, max_nodes=50)
    assert outcome.status == PATH_STATUS_PATH
    assert [h["target_qname"] for h in outcome.hops] == [B, C]
