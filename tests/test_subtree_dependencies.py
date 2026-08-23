"""Task 120 — subtree dependency with duplicate-declaration attribution.

Proving path is integration: seed the store with duplicate declarations and crossing edges, then
call the real tool — the layer where naive first-declaration attribution would inflate counts.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from code_atlas.config import Config, load_config
from code_atlas.store import GraphStore
from code_atlas.tools import subtree_dependencies

# Three src callers hit a symbol declared only in legacy (attributable).
ONLY_LEGACY = "\\App\\LegacyOnly"
# Two src callers hit a symbol declared in both trees (unattributable).
BOTH_TREES = "\\App\\BothTrees"
# One dynamic alias bridge with no static edge.
ALIAS_FILE = "config/legacy_aliases.php"
BRIDGE_TARGET = "\\App\\BridgeOnly"


def _node(qname: str, path: str) -> dict[str, object]:
    return {
        "kind": "Class",
        "name": qname.rsplit("\\", 1)[-1],
        "qualified_name": qname,
        "file_path": path,
        "line_start": 1,
    }


def _edge(
    source: str, target: str, path: str, *, tier: str = "RESOLVED"
) -> dict[str, object]:
    return {
        "kind": "CALLS",
        "source_qname": source,
        "target_qname": target,
        "target_raw": target.rsplit("\\", 1)[-1],
        "file_path": path,
        "line": 10,
        "confidence_tier": tier,
    }


def _seed(db_path: Path) -> None:
    with GraphStore(db_path) as store:
        files = {
            "legacy/alpha/Foo.php": [ONLY_LEGACY],
            "legacy/beta/Foo.php": [ONLY_LEGACY],
            "legacy/alpha/Shared.php": [BOTH_TREES],
            "src/App/Shared.php": [BOTH_TREES],
            "legacy/alpha/Bridge.php": [BRIDGE_TARGET],
            ALIAS_FILE: [],
        }
        for path in files:
            store.upsert_file(path, "h", "php")
        for path, qnames in files.items():
            store.replace_file_rows(path, [_node(q, path) for q in qnames], [])
        edges: list[dict[str, object]] = []
        for i in range(3):
            edges.append(
                _edge(f"src/App/A{i}.php", ONLY_LEGACY, f"src/App/A{i}.php")
            )
        for i in range(2):
            edges.append(
                _edge(f"src/App/B{i}.php", BOTH_TREES, f"src/App/B{i}.php")
            )
        edges.append(_edge(ALIAS_FILE, BRIDGE_TARGET, ALIAS_FILE, tier="DYNAMIC"))
        for path in ("src/App/A0.php", "src/App/A1.php", "src/App/A2.php",
                     "src/App/B0.php", "src/App/B1.php", ALIAS_FILE):
            store.upsert_file(path, "h", "php")
        for edge in edges:
            store.upsert_file(edge["file_path"], "h", "php")
            store.insert_edges([edge])


def _config(tmp_path: Path) -> Config:
    return replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")


def test_attributable_and_unattributable_split(tmp_path: Path) -> None:
    """AC1/AC2: duplicate declarations split counts; both totals always present."""
    db = tmp_path / "graph.db"
    _seed(db)
    result = subtree_dependencies.create(_config(tmp_path))(
        "legacy/", counterpart="src/", detail_level="standard", limit=50
    )
    inbound = result["inbound"]
    assert isinstance(inbound, dict)
    assert inbound["attributable"] == 3
    assert inbound["unattributable"] == 2
    assert inbound["by_tier"]["RESOLVED"]["attributable"] == 3
    assert inbound["by_tier"]["RESOLVED"]["unattributable"] == 2
    assert result["dependent_file_total"] == 5


def test_unattributable_is_structurally_paired(tmp_path: Path) -> None:
    """AC2: inbound always carries attributable beside unattributable."""
    db = tmp_path / "graph.db"
    _seed(db)
    result = subtree_dependencies.create(_config(tmp_path))(
        "legacy/", counterpart="src/", detail_level="minimal"
    )
    inbound = result["inbound"]
    assert isinstance(inbound, dict)
    assert "attributable" in inbound and "unattributable" in inbound
    assert inbound["attributable"] + inbound["unattributable"] == 5


def test_dynamic_bridge_surfaces(tmp_path: Path) -> None:
    """AC4: alias file with only DYNAMIC edges is reported, not silently absent."""
    db = tmp_path / "graph.db"
    _seed(db)
    result = subtree_dependencies.create(_config(tmp_path))(
        "legacy/", detail_level="standard", limit=50
    )
    bridges = result["dynamic_bridges"]
    assert isinstance(bridges, list)
    assert any(row["path"] == ALIAS_FILE for row in bridges)
    assert result["dynamic_bridge_total"] == 1


def test_depended_on_paths_lists_inside_targets(tmp_path: Path) -> None:
    """Inbound crossing lists declaration paths inside the subtree."""
    db = tmp_path / "graph.db"
    _seed(db)
    result = subtree_dependencies.create(_config(tmp_path))(
        "legacy/", counterpart="src/", detail_level="standard", limit=50
    )
    paths = {row["path"] for row in result["depended_on_paths"]}
    assert "legacy/alpha/Foo.php" in paths
    assert "legacy/alpha/Shared.php" in paths


def test_mirror_collapse_merges_sibling_paths() -> None:
    """AC1 path grain: mirror map sums edge counts onto one canonical path."""
    from code_atlas.tools.subtree_dependencies import _collapse_paths

    rows = [
        {"path": "legacy/alpha/Foo.php", "edges": 3},
        {"path": "legacy/beta/Foo.php", "edges": 2},
        {"path": "legacy/alpha/Only.php", "edges": 1},
    ]
    mirror_map = {
        "legacy/beta/Foo.php": "legacy/alpha/Foo.php",
    }
    collapsed = _collapse_paths(rows, mirror_map)
    by_path = {row["path"]: row["edges"] for row in collapsed}
    assert by_path["legacy/alpha/Foo.php"] == 5
    assert by_path["legacy/alpha/Only.php"] == 1


def test_tier_not_flattened(tmp_path: Path) -> None:
    """AC3: HEURISTIC and RESOLVED stay separate in by_tier."""
    db = tmp_path / "graph.db"
    with GraphStore(db) as store:
        store.upsert_file("legacy/x.php", "h", "php")
        store.upsert_file("src/y.php", "h", "php")
        store.replace_file_rows("legacy/x.php", [_node("\\T", "legacy/x.php")], [])
        store.replace_file_rows("src/y.php", [], [])
        store.insert_edges(
            [_edge("src/y.php", "\\T", "src/y.php", tier="HEURISTIC")]
        )
    result = subtree_dependencies.create(_config(tmp_path))(
        "legacy/", counterpart="src/", detail_level="standard", limit=50
    )
    tiers = result["inbound"]["by_tier"]
    assert "HEURISTIC" in tiers
    assert tiers["HEURISTIC"]["attributable"] == 1


def test_truncation_disclosed(tmp_path: Path) -> None:
    """AC5/R4.3: ranked lists cap and truncated flag is set."""
    db = tmp_path / "graph.db"
    _seed(db)
    result = subtree_dependencies.create(_config(tmp_path))(
        "legacy/", counterpart="src/", detail_level="standard", limit=2
    )
    assert len(result["dependent_files"]) <= 2
    assert result["truncated"] is True


def _seed_outbound(db_path: Path) -> None:
    """Sources inside ``legacy/`` reaching out: one target only in src, one declared in both."""
    with GraphStore(db_path) as store:
        for path in ("legacy/a.php", "legacy/b.php", "src/x.php", "src/dup.php",
                     "legacy/dup.php"):
            store.upsert_file(path, "h", "php")
        store.replace_file_rows("src/x.php", [_node("\\SrcOnly", "src/x.php")], [])
        store.replace_file_rows("src/dup.php", [_node("\\Dup", "src/dup.php")], [])
        store.replace_file_rows("legacy/dup.php", [_node("\\Dup", "legacy/dup.php")], [])
        store.insert_edges(
            [
                _edge("legacy/a.php", "\\SrcOnly", "legacy/a.php"),
                _edge("legacy/b.php", "\\SrcOnly", "legacy/b.php"),
                _edge("legacy/a.php", "\\Dup", "legacy/a.php"),
                _edge("legacy/b.php", "\\Dup", "legacy/b.php", tier="HEURISTIC"),
            ]
        )


def test_outbound_splits_attribution_per_tier(tmp_path: Path) -> None:
    """Scope "and out of it": the reverse direction attributes and tiers like inbound does."""
    _seed_outbound(tmp_path / "graph.db")
    result = subtree_dependencies.create(_config(tmp_path))(
        "legacy/", counterpart="src/", detail_level="standard", limit=50
    )
    outbound = result["outbound"]
    assert isinstance(outbound, dict)
    assert outbound["attributable"] == 2  # both hits on the src-only symbol
    assert outbound["unattributable"] == 2  # \Dup is declared in both trees
    assert outbound["by_tier"]["RESOLVED"] == {"attributable": 2, "unattributable": 1}
    assert outbound["by_tier"]["HEURISTIC"] == {"attributable": 0, "unattributable": 1}
    assert result["inbound"]["attributable"] == 0  # nothing crosses inward here


def test_truncated_tracks_only_the_lists_actually_returned(tmp_path: Path) -> None:
    """AC5: outbound carries no list, so its size must not raise the truncation flag."""
    _seed_outbound(tmp_path / "graph.db")
    result = subtree_dependencies.create(_config(tmp_path))(
        "legacy/", detail_level="standard", limit=1
    )
    assert result["dependent_files"] == []
    assert result["depended_on_paths"] == []
    assert result["dynamic_bridges"] == []
    assert result["truncated"] is False
