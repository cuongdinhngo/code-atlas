"""Task 058: capped ``parse_failure_paths`` on ``get_index_status(detail_level=verbose)``."""

from __future__ import annotations

from pathlib import Path

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status
from tests.test_get_index_status_health import _MINIMAL_KEYS
from tests.test_store import nodes_for

_STANDARD_LIST_KEYS = frozenset({"parse_failure_paths", "parse_failures_truncated"})


def _plant_failures(db_path: Path, failed: tuple[str, ...], ok: str = "ok.php") -> None:
    with GraphStore(db_path) as store:
        store.upsert_file(ok, "h", "php")
        store.replace_file_rows(ok, nodes_for(ok), [])
        for path in failed:
            store.upsert_file(path, "h", "php", parsed_ok=False)
            store.replace_file_rows(path, [], [])


def test_verbose_lists_failed_paths_capped_stable(tmp_path: Path) -> None:
    """Proving test: paths retrievable, capped, truncated, ordered, stable (AC1, AC3, AC4)."""
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    failed = ("z.php", "a.php", "m.php")
    _plant_failures(db_path, failed)
    config = load_config(
        tmp_path, {"CA_DB_PATH": str(db_path), "CA_MAX_RESULTS": "2"}
    )
    tool = get_index_status.create(config, (get_index_status.NAME,))

    first = tool(detail_level="verbose")
    second = tool(detail_level="verbose")

    assert first["parse_failures"] == 3
    assert first["failed"] == 3
    assert first["parse_failure_paths"] == ["a.php", "m.php"]
    assert first["parse_failures_truncated"] is True
    assert first == second


def test_verbose_not_truncated_when_under_cap(tmp_path: Path) -> None:
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    _plant_failures(db_path, ("bad.php",))
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    tool = get_index_status.create(config, (get_index_status.NAME,))

    verbose = tool(detail_level="verbose")

    assert verbose["parse_failure_paths"] == ["bad.php"]
    assert verbose["parse_failures_truncated"] is False
    assert verbose["parse_failures"] == 1


def test_minimal_and_standard_payloads_omit_failure_list(tmp_path: Path) -> None:
    """AC2: existing callers that do not ask for the list see an unchanged shape."""
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    _plant_failures(db_path, ("bad.php",))
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    tool = get_index_status.create(config, (get_index_status.NAME,))

    minimal = tool(detail_level="minimal")
    standard = tool(detail_level="standard")
    verbose = tool(detail_level="verbose")

    assert set(minimal) == _MINIMAL_KEYS
    assert _STANDARD_LIST_KEYS.isdisjoint(standard)
    assert _STANDARD_LIST_KEYS <= set(verbose)
    assert "parse_failures" in standard
    assert standard["parse_failures"] == verbose["parse_failures"] == 1
    for key, value in standard.items():
        assert verbose[key] == value
