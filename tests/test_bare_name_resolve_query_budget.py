"""Task 283 — bare-name resolve uniqueness from batched fetch, not per-edge COUNT."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.resolver import resolve_edges
from code_atlas.store import GraphStore


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def seed_file(store: GraphStore, path: str, nodes: list[dict], edges: list[dict]) -> None:
    store.upsert_file(path, "h", "lang")
    store.replace_file_rows(path, nodes, edges)


def node(kind: str, name: str, qname: str, path: str) -> dict[str, object]:
    return {
        "kind": kind,
        "name": name,
        "qualified_name": qname,
        "file_path": path,
        "line_start": 1,
    }


def edge(
    kind: str,
    source: str,
    target_raw: str,
    path: str,
    *,
    tier: str | None = None,
    line: int = 3,
) -> dict[str, object]:
    row: dict[str, object] = {
        "kind": kind,
        "source_qname": source,
        "target_raw": target_raw,
        "file_path": path,
        "line": line,
    }
    if tier is not None:
        row["confidence_tier"] = tier
    return row


def test_bare_name_pass_issues_no_per_edge_count(store: GraphStore, monkeypatch) -> None:
    """AC1 — many CALLS of few names ⇒ zero count_nodes_by_name; uniqueness from fetch."""
    methods = [
        node("Method", "save", r"\A::save", "a.x"),
        node("Method", "unique", r"\A::unique", "a.x"),
        node("Method", "put", r"\A::put", "a.x"),
        node("Method", "put", r"\B::put", "a.x"),
    ]
    calls = [
        edge("CALLS", r"\A::save", "unique", "a.x", tier="HEURISTIC"),
        edge("CALLS", r"\A::save", "put", "a.x", tier="HEURISTIC"),
    ]
    for i in range(40):
        calls.append(
            edge("CALLS", r"\A::save", "unique", "a.x", tier="HEURISTIC", line=10 + i)
        )
        calls.append(
            edge("CALLS", r"\A::save", "put", "a.x", tier="HEURISTIC", line=100 + i)
        )
    seed_file(store, "a.x", methods, calls)

    counts = {"n": 0}
    real = store.count_nodes_by_name

    def spy(*args, **kwargs):
        counts["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(store, "count_nodes_by_name", spy)
    resolve_edges(store, max_candidates=2)
    assert counts["n"] == 0

    all_calls = store.edges_by_source(r"\A::save", kinds=("CALLS",), limit=500)
    unique_linked = [e for e in all_calls if e.get("target_qname") == r"\A::unique"]
    put_unresolved = [
        e for e in all_calls if e.get("target_raw") == "put" and e.get("target_qname") is None
    ]
    assert unique_linked, "unique name should link HEURISTIC"
    assert all(e["confidence_tier"] == "HEURISTIC" for e in unique_linked)
    assert put_unresolved, "multi-match put stays unresolved"


def test_many_matches_stay_unresolved_at_max_candidates_one(store: GraphStore) -> None:
    """258/283 — max_candidates=1 must not treat a truncated fetch as unique."""
    seed_file(
        store,
        "a.x",
        [
            node("Method", "save", r"\A::save", "a.x"),
            node("Method", "put", r"\A::put", "a.x"),
            node("Method", "put", r"\B::put", "a.x"),
        ],
        [edge("CALLS", r"\A::save", "put", "a.x", tier="HEURISTIC")],
    )
    resolve_edges(store, max_candidates=1)
    linked = store.edges_by_source(r"\A::save", kinds=("CALLS",), limit=10)
    assert len(linked) == 1
    assert linked[0]["target_qname"] is None
    assert linked[0]["target_raw"] == "put"
