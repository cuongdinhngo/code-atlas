"""Task 028: index-health fields on ``get_index_status`` (standard only)."""

from __future__ import annotations

from pathlib import Path

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status
from tests.test_store import an_edge, nodes_for

# Frozen minimal key set as of task 010/028 pre-change — AC3 must not grow this.
_MINIMAL_KEYS = frozenset(
    {
        "indexed",
        "files",
        "parsed",
        "failed",
        "nodes",
        "edges",
        "stubs",
        "last_commit",
        "staleness",
        "next_tool_suggestions",
    }
)


def _plant_health_graph(db_path: Path) -> None:
    """Known mix: 2 RESOLVED (1 linked, 1 dangling), 1 HEURISTIC linked, 1 DYNAMIC dangling."""
    path = "a.php"
    with GraphStore(db_path) as store:
        store.upsert_file(path, "h", "php")
        store.upsert_file("bad.php", "h", "php", parsed_ok=False)
        store.replace_file_rows("bad.php", [], [])
        store.replace_file_rows(
            path,
            nodes_for(path),
            [
                an_edge(
                    "CALLS",
                    "\\App\\UserRepo::save",
                    "\\App\\Db::write",
                    path,
                    target_qname="\\App\\Db::write",
                    confidence_tier="RESOLVED",
                ),
                an_edge(
                    "CALLS",
                    "\\App\\UserRepo::save",
                    "save",
                    path,
                    target_qname="\\App\\Other::save",
                    confidence_tier="HEURISTIC",
                ),
                an_edge(
                    "CALLS",
                    "\\App\\UserRepo::save",
                    "$m",
                    path,
                    confidence_tier="DYNAMIC",
                ),
                an_edge(
                    "EXTENDS",
                    "\\App\\UserRepo",
                    "\\Vendor\\Base",
                    path,
                    confidence_tier="RESOLVED",
                ),
            ],
        )


def test_standard_reports_exact_edge_health_and_parse_failures(tmp_path: Path) -> None:
    """Proving test: planted tier/link mix and parse_failures match hand counts (AC1, AC2)."""
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    _plant_health_graph(db_path)
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    tool = get_index_status.create(config, (get_index_status.NAME,))

    standard = tool(detail_level="standard")

    assert standard["edge_health"] == {
        "by_tier": {"RESOLVED": 2, "HEURISTIC": 1, "DYNAMIC": 1},
        "resolved": 2,
        "unresolved": 2,
    }
    assert standard["parse_failures"] == 1
    assert standard["failed"] == 1


def test_parse_failures_is_zero_on_a_clean_graph(tmp_path: Path) -> None:
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    with GraphStore(db_path) as store:
        store.upsert_file("a.php", "h", "php")
        store.replace_file_rows("a.php", nodes_for("a.php"), [])
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    tool = get_index_status.create(config, (get_index_status.NAME,))

    assert tool(detail_level="standard")["parse_failures"] == 0


def test_minimal_payload_stays_byte_identical_to_the_pre_health_shape(tmp_path: Path) -> None:
    """AC3: health fields stay standard-only; stubs (039) is on both levels."""
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    _plant_health_graph(db_path)
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    tool = get_index_status.create(config, (get_index_status.NAME,))

    minimal = tool(detail_level="minimal")
    standard = tool(detail_level="standard")

    assert set(minimal) == _MINIMAL_KEYS
    assert minimal == {
        "indexed": True,
        "files": 2,
        "parsed": 1,
        "failed": 1,
        "nodes": 2,
        "edges": 4,
        "stubs": 0,
        "last_commit": None,
        "staleness": "unknown",
        "next_tool_suggestions": [],
    }
    assert "edge_health" not in minimal and "parse_failures" not in minimal
    assert "edge_health" in standard and "parse_failures" in standard
    for key, value in minimal.items():
        assert standard[key] == value


def test_unbuilt_standard_still_opens_no_database(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert not config.db_path.is_file()
    tool = get_index_status.create(config, (get_index_status.NAME,))

    status = tool(detail_level="standard")

    assert status["indexed"] is False
    assert "edge_health" not in status
    assert "parse_failures" not in status
    assert not config.db_path.is_file()
