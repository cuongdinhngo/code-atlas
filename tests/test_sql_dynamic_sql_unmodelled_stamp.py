"""Task 296 — SQL dynamic EXEC / sp_executesql stamp File.extra.unmodelled_resolution."""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas.contract import RESOLUTION_DYNAMIC_SQL, UNMODELLED_RESOLUTION
from code_atlas.store import (
    UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY,
    GraphStore,
)
from code_atlas.tools import find_orphans
from tests.sql_adapter_cli import needs_node, parse_file
from tests.test_find_orphans_refuses_what_it_cannot_answer import config_for, plant_islands
from tests.test_reachability import store as store  # noqa: F401

DYNAMIC = Path("tests/fixtures/sql/unmodelled_resolution/exec_dynamic.sql")
STATIC = Path("tests/fixtures/sql/unmodelled_resolution/exec_static.sql")


@needs_node
def test_sql_dynamic_exec_stamps_file_extra() -> None:
    """AC1 — EXEC(@sql) / sp_executesql stamps dynamic_sql on File.extra."""
    result = parse_file(DYNAMIC)
    assert result["ok"] is True
    files = [n for n in result["nodes"] if n["kind"] == "File"]
    assert files
    extra = files[0].get("extra") or {}
    assert RESOLUTION_DYNAMIC_SQL in (extra.get(UNMODELLED_RESOLUTION) or [])


@needs_node
def test_sql_static_exec_does_not_stamp() -> None:
    """AC1 negative — static EXEC dbo.OtherProc produces no unmodelled_resolution key."""
    result = parse_file(STATIC)
    assert result["ok"] is True
    files = [n for n in result["nodes"] if n["kind"] == "File"]
    extra = (files[0].get("extra") or {}) if files else {}
    assert UNMODELLED_RESOLUTION not in extra


@needs_node
def test_sql_dynamic_stamp_does_not_change_edge_tiers() -> None:
    """AC3 — DYNAMIC confidence_tier on edges unchanged."""
    result = parse_file(DYNAMIC)
    calls = [e for e in result["edges"] if e["kind"] == "CALLS"]
    assert calls
    assert any(e.get("confidence_tier") == "DYNAMIC" for e in calls)


def _stamp_sql(store: GraphStore, path: str = "dbo/dyn.sql") -> dict[str, list[str]]:
    store.upsert_file(path, "h", "sql")
    store.replace_file_rows(
        path,
        [
            {
                "kind": "File",
                "name": path,
                "qualified_name": path,
                "file_path": path,
                "line_start": 1,
                "extra": json.dumps(
                    {UNMODELLED_RESOLUTION: [RESOLUTION_DYNAMIC_SQL]}, sort_keys=True
                ),
            }
        ],
        [],
    )
    census = store.unmodelled_resolution_by_language()
    assert census.get("sql") == [RESOLUTION_DYNAMIC_SQL]
    store.set_meta(UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY, json.dumps(census, sort_keys=True))
    return census


def test_find_orphans_refuses_when_sql_resolution_is_stamped(
    store: GraphStore, tmp_path: Path
) -> None:
    plant_islands(store, count=3)
    census = _stamp_sql(store)
    payload = find_orphans.create(config_for(tmp_path))(detail_level="standard")
    assert payload["status"] == find_orphans.RESOLUTION_UNMODELLED
    assert payload["results"] == []
    assert payload["unmodelled_resolution_by_language"] == census


def test_find_orphans_unstamped_sql_still_returns_orphans(
    store: GraphStore, tmp_path: Path
) -> None:
    plant_islands(store, count=3)
    payload = find_orphans.create(config_for(tmp_path))(detail_level="standard")
    assert payload["status"] == "ok"
    assert int(payload["total_count"]) >= 3
