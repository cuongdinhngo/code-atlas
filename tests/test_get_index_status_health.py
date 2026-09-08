"""Task 028: index-health fields on ``get_index_status`` (standard only)."""

from __future__ import annotations

from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status
from tests.test_store import an_edge, nodes_for

# Frozen minimal key set — task 071 adds ``index_root`` on every status detail level.
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
        "last_ref",
        "head_ref",
        "staleness",
        "index_root",
        "server_version",
        "server_build",
        "server_stale_process",
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
        "linked": 2,
        "unlinked": 2,
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


def test_minimal_payload_stays_byte_identical_to_the_pre_health_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3: health fields stay standard-only; stubs (039) is on both levels."""
    # Isolate from an enclosing git worktree so live head_ref stays null (077).
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.resolve()))
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    _plant_health_graph(db_path)
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    tool = get_index_status.create(config, (get_index_status.NAME,))

    minimal = tool(detail_level="minimal")
    standard = tool(detail_level="standard")

    assert set(minimal) == _MINIMAL_KEYS
    assert "next_tool_suggestions" not in minimal  # empty → omitted (223)
    for key in (
        "indexed", "files", "parsed", "failed", "nodes", "edges", "stubs",
        "last_commit", "last_ref", "head_ref", "staleness", "index_root",
    ):
        assert key in minimal
    assert minimal["indexed"] is True
    assert minimal["files"] == 2
    assert minimal["index_root"] == str(config.root.resolve())
    assert "server_version" in minimal and "server_build" in minimal
    # standard still carries every minimal field
    for key, value in minimal.items():
        if key.startswith("server_"):
            continue  # standard also has them via enriched path
        assert standard[key] == value
    assert "edge_health" not in minimal and "parse_failures" not in minimal
    assert "edge_health" in standard and "parse_failures" in standard


def test_unbuilt_standard_still_opens_no_database(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert not config.db_path.is_file()
    tool = get_index_status.create(config, (get_index_status.NAME,))

    status = tool(detail_level="standard")

    assert status["indexed"] is False
    assert "edge_health" not in status
    assert "parse_failures" not in status
    assert not config.db_path.is_file()
