"""Task 112: the compact aggregate dataset that is the contract behind every renderer (M11).

Two halves. The pure half builds ``OnboardingDataset`` from hand-made rows — no store, no ``fcntl``,
no PHP adapter — proving byte-stability (AC2), the dataset-only renderer (AC5), and the path-index
cap (AC6). The store half seeds a small graph and proves every aggregate is a bounded ``store.py``
query and that hub fan-in equals the module metric fan-in by construction (AC1/AC4/H4).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from code_atlas.onboarding import dataset as dataset_module
from code_atlas.onboarding.dataset import (
    DATASET_VERSION,
    ClassStat,
    Hub,
    KindCount,
    LayerStat,
    MatrixEdge,
    OnboardingDataset,
    PathIndex,
    build_dataset,
    dataset_json,
    render_dataset_overview,
)
from code_atlas.onboarding.metrics import compute_metrics
from code_atlas.onboarding.mirrors import MirrorReport
from code_atlas.onboarding.modules import ModuleMap
from code_atlas.onboarding.reachability import ReachabilitySplit
from code_atlas.store import GraphStore

# A three-module chain across two responsibility directories: A → B → C.
_NODES = [("\\A", "app/http/A.aa"), ("\\B", "app/services/B.aa"), ("\\C", "app/services/C.aa")]
_EDGES = [("\\A", "\\B"), ("\\B", "\\C")]


def _build(**over: object) -> OnboardingDataset:
    kwargs: dict[str, object] = {
        "files": 3,
        "parsed": 3,
        "node_kind_counts": [("Class", 3)],
        "edge_kind_counts": [("CALLS", 2)],
        "confidence": {"RESOLVED": 2},
        "hubs": [("app/services/B.aa", 1, 1), ("app/services/C.aa", 1, 0)],
        "classes": [("\\B", "app/services/B.aa", 2)],
        "file_symbol_counts": [
            ("app/http/A.aa", 1),
            ("app/services/B.aa", 1),
            ("app/services/C.aa", 1),
        ],
        "file_paths": ["app/http/A.aa", "app/services/B.aa", "app/services/C.aa"],
        "path_index_max": 1000,
    }
    kwargs.update(over)
    return build_dataset(_NODES, _EDGES, **kwargs)  # type: ignore[arg-type]


# --- AC2: byte-stable given the same input ---------------------------------------------------


def test_ac2_dataset_is_byte_stable() -> None:
    assert dataset_json(_build()) == dataset_json(_build())
    assert _build().as_dict() == _build().as_dict()


def test_ac2_dataset_json_has_no_wall_clock() -> None:
    """Sorted keys, and nothing time-like — the whole reason two runs compare equal (R4.2)."""
    text = dataset_json(_build())
    assert '"version":' in text
    for stamp in ("built_at", "timestamp", "generated_at", "202"):
        assert stamp not in text


# --- AC5: a renderer needs only the dataset — no GraphStore -----------------------------------


def test_ac5_renderer_from_dataset_alone() -> None:
    from code_atlas.onboarding.dataset import DirStat

    fixture = OnboardingDataset(
        version=DATASET_VERSION,
        files=12,
        parsed=11,
        method="dominant-subtree",
        commit="0f1e2d3c4b5a",
        dir_symbol_threshold=400,
        node_counts=(KindCount("Class", 9),),
        edge_counts=(KindCount("CALLS", 14),),
        confidence=(KindCount("RESOLVED", 14),),
        layers=(
            LayerStat("http", 0, 3, 0, 5, 3, "the entry layer"),
            LayerStat("services", 1, 4, 5, 2, 0, "the services layer"),
        ),
        matrix=(MatrixEdge("http", "services", 5),),
        hubs=(Hub("app/services/B.aa", "services", 5, 2),),
        classes=(ClassStat("\\B", "app/services/B.aa", "services", 7),),
        tree=(DirStat("app/services", 27, 4, "services"),),
        path_index=PathIndex(("app",), ((0, "x.aa"),), 42, 20, True),
        reachability=ReachabilitySplit(0, (), ()),
        modules=ModuleMap((), (), (), 0, 0, 0, False),
        mirrors=MirrorReport(()),
    )
    text = render_dataset_overview(fixture)
    assert "# Architecture overview" in text
    assert "## Layers" in text and "## Layer matrix" in text and "## Hubs" in text
    assert "`http`" in text and "`services`" in text
    assert "`http` → `services` (5)" in text
    assert "`app/services/B.aa`" in text
    assert "truncated: true" in text  # the path-index incompleteness is surfaced


def test_ac5_dataset_module_never_touches_the_store() -> None:
    """The contract module reaches no store: a renderer built on it needs no DB (AC5)."""
    source = inspect.getsource(dataset_module)
    assert "GraphStore" not in source
    assert "sqlite3" not in source
    assert "import store" not in source and "store import" not in source


# --- AC6: the path-index cap trims, and states both numbers -----------------------------------


def test_ac6_path_index_cap_trims_and_carries_both_numbers() -> None:
    trimmed = _build(path_index_max=2).path_index
    assert trimmed.truncated is True
    assert trimmed.total == 3
    assert trimmed.shown == 2
    assert len(trimmed.entries) == 2


def test_path_index_uncapped_is_complete() -> None:
    full = _build(path_index_max=1000).path_index
    assert full.truncated is False
    assert full.total == full.shown == 3


def test_path_index_front_codes_shared_directories() -> None:
    full = _build().path_index
    # Two files share ``app/services``, so it appears once in ``dirs`` and both entries point to it.
    assert full.dirs == ("app/http", "app/services")
    assert [name for _, name in full.entries] == ["A.aa", "B.aa", "C.aa"]
    assert [index for index, _ in full.entries] == [0, 1, 1]


# --- assembly: layer labels, matrix, tree pruning ---------------------------------------------


def test_hubs_and_classes_carry_the_assigned_layer() -> None:
    built = _build()
    assert all(hub.layer for hub in built.hubs)
    assert all(cls.layer for cls in built.classes)
    # The matrix is 110's crossings: A→B→C is one directed chain across the layer boundary.
    assert built.matrix
    assert all(edge.source != edge.target for edge in built.matrix)


def test_tree_prunes_below_the_symbol_threshold() -> None:
    below = _build(dir_symbol_threshold=1000).tree
    assert below == ()  # every directory holds fewer than 1000 symbols
    above = _build(dir_symbol_threshold=1).tree
    paths = {row.path for row in above}
    assert "app" in paths and "app/services" in paths
    assert all(row.layer for row in above)


# --- store aggregates: bounded, and consistent with the module metric (AC1/AC4/H4) ------------


def _seeded(tmp_path: Path):
    from tests.test_nav_tools import db_config, edge, node, seed_file

    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            "app/http/A.aa",
            [node("Class", "A", "\\A", "app/http/A.aa")],
            [edge("CALLS", "\\A", "\\B", "app/http/A.aa", target_qname="\\B")],
            root=tmp_path,
        )
        seed_file(
            store,
            "app/services/B.aa",
            [
                node("Class", "B", "\\B", "app/services/B.aa"),
                node("Method", "run", "\\B::run", "app/services/B.aa"),
            ],
            [edge("CALLS", "\\B", "\\C", "app/services/B.aa", target_qname="\\C")],
            root=tmp_path,
        )
        seed_file(
            store,
            "app/services/C.aa",
            [node("Class", "C", "\\C", "app/services/C.aa")],
            [],
            root=tmp_path,
        )
    return config


def test_kind_counts_are_grouped_in_sql(tmp_path: Path) -> None:
    config = _seeded(tmp_path)
    with GraphStore(config.db_path) as store:
        nodes = dict(store.node_kind_counts())
        edges = dict(store.edge_kind_counts())
    assert nodes["Class"] == 3
    assert nodes["Method"] == 1
    assert edges["CALLS"] == 2


def test_module_hubs_match_the_module_metric_fan_in(tmp_path: Path) -> None:
    """H4: the SQL hub ranking uses the same distinct-file-pair grain as ``compute_metrics``."""
    config = _seeded(tmp_path)
    with GraphStore(config.db_path) as store:
        hubs = store.module_hubs(limit=100)
        metrics = compute_metrics(store.node_universe(), store.dependency_edges())
    fan_in = {metric.key: metric.fan_in for metric in metrics.modules}
    fan_out = {metric.key: metric.fan_out for metric in metrics.modules}
    for file, hub_in, hub_out in hubs:
        assert hub_in == fan_in[file]
        assert hub_out == fan_out[file]
    # B and C each have one inbound module edge; A has none, so it is not a hub.
    assert dict((f, fi) for f, fi, _ in hubs) == {"app/services/B.aa": 1, "app/services/C.aa": 1}


def test_file_kind_counts_group_by_file_and_kind(tmp_path: Path) -> None:
    """116: the composition bar's substrate — one GROUP BY, bounded by files x kinds (R4.3)."""
    config = _seeded(tmp_path)
    with GraphStore(config.db_path) as store:
        rows = store.file_kind_counts()
        symbols = dict(store.file_symbol_counts())
    assert rows == tuple(sorted(rows)), "stable ORDER BY (R4.2)"
    per_file: dict[str, int] = {}
    for path, _kind, count in rows:
        per_file[path] = per_file.get(path, 0) + count
    # Derived, not listed: the per-kind split must reconcile with the per-file total (R6.7).
    assert per_file == symbols
    assert ("app/services/B.aa", "Method", 1) in rows
    assert ("app/services/B.aa", "Class", 1) in rows


def test_largest_classes_and_symbol_counts(tmp_path: Path) -> None:
    config = _seeded(tmp_path)
    with GraphStore(config.db_path) as store:
        classes = store.largest_classes(limit=10)
        symbols = dict(store.file_symbol_counts())
    # B's file carries a Method, so class B ranks first by member count.
    assert classes[0][0] == "\\B"
    assert classes[0][2] == 1
    assert symbols["app/services/B.aa"] == 2


def test_bounded_aggregates_reject_a_non_positive_limit(tmp_path: Path) -> None:
    config = _seeded(tmp_path)
    with GraphStore(config.db_path) as store:
        for bad in (0, -1):
            with pytest.raises(ValueError):
                store.module_hubs(limit=bad)
            with pytest.raises(ValueError):
                store.largest_classes(limit=bad)


# --- 116: the three fields that let the map render from the dataset alone ----------------------


def test_the_commit_and_prune_threshold_ride_with_the_dataset() -> None:
    """116/AC3: the map's stamp and its empty-state sentence must be derived, not passed in."""
    built = _build(commit="abcdef123456", dir_symbol_threshold=7)
    assert built.commit == "abcdef123456"
    assert built.dir_symbol_threshold == 7
    payload = built.as_dict()
    assert payload["commit"] == "abcdef123456"
    assert payload["dir_symbol_threshold"] == 7
    # Absent repo or no commit yet is a normal state, not a configuration error (gitutil).
    assert _build().commit == ""


def test_each_layer_carries_its_node_kind_composition() -> None:
    """116: what makes a procedural layer visible as procedural.

    Module grain is file grain, so a layer's composition is the sum over its own files — and a
    file belonging to no layer contributes to none of them.
    """
    built = _build(
        file_kind_counts=[
            ("app/services/B.aa", "Class", 1),
            ("app/services/B.aa", "Method", 6),
            ("nowhere/Ghost.aa", "Class", 99),
        ]
    )
    by_layer = {row.layer: row for row in built.layers}
    owner = next(row for row in built.layers if row.kinds)
    assert [(k.kind, k.count) for k in owner.kinds] == [("Method", 6), ("Class", 1)]
    total = sum(k.count for row in by_layer.values() for k in row.kinds)
    assert total == 7, "a file belonging to no layer contributes to none"


def test_a_layer_with_no_kind_counts_reports_an_empty_composition() -> None:
    """No composition data is an empty bar, never a fabricated one."""
    for row in _build().layers:
        assert row.kinds == ()
    for row in _build().as_dict()["layers"]:  # type: ignore[index]
        assert row["kinds"] == []


# --- 117: the headline block rides with the dataset -------------------------------------------


def test_flows_ride_with_the_dataset_and_absent_is_not_a_false_zero() -> None:
    """197 — the key rides with the shape; an index without flows says None, not [].

    The version is asserted against the constant, never a literal: this test is about `flows`, and
    the second copy of the number went stale twice before a grep for `DATASET_VERSION` could see it.
    """
    payload = _build().as_dict()
    assert payload["version"] == DATASET_VERSION
    assert "flows" in payload, "a renderer cannot show what the shape does not declare"
    assert payload["flows"] is None, "no flows built => None, never an empty list"


def test_the_headline_facts_ride_with_the_dataset_and_the_version_says_so() -> None:
    """117 — one renderer-agnostic block, and the shape bump that announces it."""
    from code_atlas.onboarding.headlines import HEADLINE_FAMILIES

    payload = _build().as_dict()
    assert payload["version"] == DATASET_VERSION
    assert DATASET_VERSION == 15  # 225 — each flow step carries `line`
    headlines = payload["headlines"]
    assert isinstance(headlines, list) and headlines
    assert all(set(row) == {"key", "label", "text"} for row in headlines)
    keys = [row["key"] for row in headlines]
    assert keys == [family for family in HEADLINE_FAMILIES if family in keys]
    assert len(keys) <= len(HEADLINE_FAMILIES)


def test_a_headline_never_outnumbers_its_families_however_big_the_repo() -> None:
    """R4.3 — the block is bounded by the family set, not by anything the repo can grow."""
    from code_atlas.onboarding.headlines import HEADLINE_FAMILIES

    assert len(_build().headlines) <= len(HEADLINE_FAMILIES)
