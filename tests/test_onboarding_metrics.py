"""Task 083 — deterministic graph-metrics substrate (fan-in/out, entry points, direction).

The metric logic is pure, so the fixture graph is plain Python — no database (AC3). A separate
DB-backed section proves the two read-only store pulls feed it the right shape. The determinism
claim (AC1, R4.2) is proven by computing twice over shuffled input and byte-comparing the JSON.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import onboarding
from code_atlas.onboarding import metrics
from code_atlas.onboarding.metrics import compute_metrics, direction
from code_atlas.store import GraphStore

FIXED_CLOCK = "2026-07-29T00:00:00+00:00"

# A → {B, C}, B ⇄ C (a cycle), D isolated. One node per file so the two grains mirror each other.
FIXTURE_NODES = [
    ("A", "a.php"),
    ("B", "b.php"),
    ("C", "c.php"),
    ("D", "d.php"),
]
FIXTURE_EDGES = [
    ("A", "B"),
    ("A", "C"),
    ("B", "C"),
    ("C", "B"),
]


@pytest.fixture
def computed() -> metrics.GraphMetrics:
    return compute_metrics(FIXTURE_NODES, FIXTURE_EDGES)


def _by_key(computed: metrics.GraphMetrics) -> dict[str, metrics.NodeMetric]:
    return {m.key: m for m in computed.symbols}


def test_fan_out_is_exact_over_the_fixture(computed: metrics.GraphMetrics) -> None:
    fan_out = {m.key: m.fan_out for m in computed.symbols}
    assert fan_out == {"A": 2, "B": 1, "C": 1, "D": 0}


def test_fan_in_is_exact_over_the_fixture(computed: metrics.GraphMetrics) -> None:
    fan_in = {m.key: m.fan_in for m in computed.symbols}
    assert fan_in == {"A": 0, "B": 2, "C": 2, "D": 0}


def test_entry_points_are_the_zero_inbound_roots(computed: metrics.GraphMetrics) -> None:
    # A (a true root) and D (isolated) are the only zero-inbound nodes; order is stable.
    assert computed.entry_points == ("A", "D")
    assert computed.module_entry_points == ("a.php", "d.php")


def test_a_node_in_a_cycle_is_labelled_mixed(computed: metrics.GraphMetrics) -> None:
    by_key = _by_key(computed)
    assert by_key["B"].direction == "mixed"
    assert by_key["C"].direction == "mixed"
    assert by_key["A"].direction == "source"
    assert by_key["D"].direction == "isolated"


def test_metrics_are_byte_stable_across_two_runs() -> None:
    first = compute_metrics(FIXTURE_NODES, FIXTURE_EDGES).to_json()
    shuffled_nodes = list(reversed(FIXTURE_NODES))
    shuffled_edges = list(reversed(FIXTURE_EDGES))
    second = compute_metrics(shuffled_nodes, shuffled_edges).to_json()
    assert first == second


def test_every_direction_label_comes_from_the_exported_set(
    computed: metrics.GraphMetrics,
) -> None:
    used = {m.direction for m in computed.symbols} | {m.direction for m in computed.modules}
    assert used <= set(metrics.DIRECTION_LABELS)


def test_direction_labels_are_derived_not_listed() -> None:
    # The guard can fail: add a label to DIRECTION_LABELS (or a branch to direction()) without the
    # other and the set equality breaks (R6.7 / derived-not-listed-invariant; 093-C3).
    produced = {direction(i, o) for i in (0, 1) for o in (0, 1)}
    assert produced == set(metrics.DIRECTION_LABELS)


def test_no_new_tool_surface() -> None:
    # G1: 083 adds no MCP tool; the onboarding package exposes only the compute layer.
    assert not hasattr(onboarding, "TOOL_NAMES")


# --- DB-backed: the two read-only store pulls feed compute_metrics -------------------------------


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    db_path = tmp_path / ".code-atlas" / "graph.db"
    with GraphStore(db_path, now=lambda: FIXED_CLOCK) as opened:
        yield opened


def _edge(source: str, target_qname: str, path: str) -> dict[str, object]:
    return {
        "kind": "CALLS",
        "source_qname": source,
        "target_raw": target_qname,
        "target_qname": target_qname,
        "file_path": path,
        "line": 7,
    }


def _node(qname: str, path: str) -> dict[str, object]:
    return {
        "kind": "Class",
        "name": qname.strip("\\"),
        "qualified_name": qname,
        "file_path": path,
        "line_start": 1,
    }


def test_dependency_edges_excludes_self_loops_and_unresolved(store: GraphStore) -> None:
    store.upsert_file("a.php", "h", "php")
    store.replace_file_rows(
        "a.php",
        [_node("\\A", "a.php"), _node("\\B", "a.php")],
        [
            _edge("\\A", "\\B", "a.php"),
            _edge("\\A", "\\A", "a.php"),  # self-loop: excluded
            {"kind": "ALIASES", "source_qname": "\\A", "target_raw": "\\B", "file_path": "a.php",
             "line": 1},  # unresolved (no target_qname): excluded, no kind branch
        ],
    )
    assert store.dependency_edges() == [("\\A", "\\B")]


def test_node_universe_is_sorted_qname_file_pairs(store: GraphStore) -> None:
    store.upsert_file("a.php", "h", "php")
    store.replace_file_rows("a.php", [_node("\\B", "a.php"), _node("\\A", "a.php")], [])
    assert store.node_universe() == [("\\A", "a.php"), ("\\B", "a.php")]


def test_store_pulls_drive_the_pure_metrics(store: GraphStore) -> None:
    store.upsert_file("a.php", "h", "php")
    store.replace_file_rows(
        "a.php",
        [_node("\\A", "a.php"), _node("\\B", "a.php")],
        [_edge("\\A", "\\B", "a.php")],
    )
    computed = compute_metrics(store.node_universe(), store.dependency_edges())
    assert computed.entry_points == ("\\A",)
    assert {m.key: m.fan_out for m in computed.symbols} == {"\\A": 1, "\\B": 0}
