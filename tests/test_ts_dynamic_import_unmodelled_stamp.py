"""Task 294 — TS dynamic import()/require() stamp File.extra.unmodelled_resolution."""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas.contract import RESOLUTION_DYNAMIC_IMPORT, UNMODELLED_RESOLUTION
from code_atlas.store import (
    UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY,
    GraphStore,
)
from code_atlas.tools import find_orphans
from tests.test_find_orphans_refuses_what_it_cannot_answer import config_for, plant_islands
from tests.test_reachability import store as store  # noqa: F401
from tests.ts_adapter_cli import needs_node, parse_file

_FIXTURES = Path("tests/fixtures/typescript/unmodelled_resolution")


@needs_node
def test_ts_dynamic_import_stamps_file_extra() -> None:
    """AC1 — await import(name) produces File.extra unmodelled_resolution."""
    result = parse_file(_FIXTURES / "dynamic_import.ts")
    assert result["ok"] is True
    files = [n for n in result["nodes"] if n["kind"] == "File"]
    assert files, "adapter must emit a File node"
    extra = files[0].get("extra") or {}
    assert UNMODELLED_RESOLUTION in extra
    assert RESOLUTION_DYNAMIC_IMPORT in extra[UNMODELLED_RESOLUTION]


@needs_node
def test_ts_dynamic_require_stamps_file_extra() -> None:
    """AC1 — require(name) stamps the same strategy token."""
    result = parse_file(_FIXTURES / "dynamic_require.js")
    assert result["ok"] is True
    files = [n for n in result["nodes"] if n["kind"] == "File"]
    extra = files[0].get("extra") or {}
    assert RESOLUTION_DYNAMIC_IMPORT in (extra.get(UNMODELLED_RESOLUTION) or [])


@needs_node
def test_ts_literal_specifiers_do_not_stamp() -> None:
    """AC1 negative — literal import() produces no unmodelled_resolution key."""
    result = parse_file(_FIXTURES / "literal_only.ts")
    assert result["ok"] is True
    files = [n for n in result["nodes"] if n["kind"] == "File"]
    extra = (files[0].get("extra") or {}) if files else {}
    assert UNMODELLED_RESOLUTION not in extra


def _stamp_dynamic_import(
    store: GraphStore, path: str = "src/load.ts"
) -> dict[str, list[str]]:
    store.upsert_file(path, "h", "typescript")
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
                    {UNMODELLED_RESOLUTION: [RESOLUTION_DYNAMIC_IMPORT]}, sort_keys=True
                ),
            }
        ],
        [],
    )
    census = store.unmodelled_resolution_by_language()
    assert census.get("typescript") == [RESOLUTION_DYNAMIC_IMPORT]
    store.set_meta(UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY, json.dumps(census, sort_keys=True))
    return census


def test_find_orphans_refuses_when_ts_resolution_is_stamped(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC2 — stamped typescript index cannot return a bare orphan population."""
    plant_islands(store, count=3)
    census = _stamp_dynamic_import(store)
    payload = find_orphans.create(config_for(tmp_path))(detail_level="standard")
    assert payload["status"] == find_orphans.RESOLUTION_UNMODELLED
    assert payload["results"] == []
    assert "unmeasured" in str(payload["message"]).lower()
    assert payload.get("try_instead_hint")
    assert payload["unmodelled_resolution_by_language"] == census


def test_find_orphans_unstamped_ts_still_returns_orphans(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC2 — no stamp ⇒ orphans still returned under status=ok."""
    plant_islands(store, count=3)
    assert store.get_meta(UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY) is None
    payload = find_orphans.create(config_for(tmp_path))(detail_level="standard")
    assert payload["status"] == "ok"
    assert int(payload["total_count"]) >= 3
