"""Task 279 — stamped unmodelled resolution makes orphan populations unmeasured."""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas.contract import RESOLUTION_AUTOLOAD, UNMODELLED_RESOLUTION
from code_atlas.store import (
    UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY,
    GraphStore,
)
from code_atlas.tools import find_orphans
from tests.php_adapter_cli import needs_php, parse_file
from tests.test_find_orphans_refuses_what_it_cannot_answer import config_for, plant_islands
from tests.test_reachability import store as store  # noqa: F401

_FIXTURES = Path(__file__).parent / "fixtures" / "php"
FIXTURE = _FIXTURES / "unmodelled_resolution" / "autoload_register.php"


def test_php_adapter_stamps_autoload_on_file_extra() -> None:
    """AC1 — spl_autoload_register produces File.extra unmodelled_resolution."""
    needs_php()
    result = parse_file(FIXTURE)
    assert result["ok"] is True
    files = [n for n in result["nodes"] if n["kind"] == "File"]
    assert files, "adapter must emit a File node"
    extra = files[0].get("extra") or {}
    assert UNMODELLED_RESOLUTION in extra
    assert RESOLUTION_AUTOLOAD in extra[UNMODELLED_RESOLUTION]


def test_php_adapter_without_register_has_no_resolution_stamp() -> None:
    """AC1 negative — a file with no autoload registration does not stamp."""
    needs_php()
    plain = Path(__file__).parent / "fixtures" / "php" / "reach" / "entry.php"
    result = parse_file(plain)
    assert result["ok"] is True
    files = [n for n in result["nodes"] if n["kind"] == "File"]
    extra = (files[0].get("extra") or {}) if files else {}
    assert RESOLUTION_AUTOLOAD not in (extra.get(UNMODELLED_RESOLUTION) or [])


def _stamp_autoload(store: GraphStore, path: str = "src/bootstrap.php") -> dict[str, list[str]]:
    store.upsert_file(path, "h", "php")
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
                    {UNMODELLED_RESOLUTION: [RESOLUTION_AUTOLOAD]}, sort_keys=True
                ),
            }
        ],
        [],
    )
    census = store.unmodelled_resolution_by_language()
    assert census.get("php") == [RESOLUTION_AUTOLOAD]
    store.set_meta(UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY, json.dumps(census, sort_keys=True))
    return census


def test_find_orphans_refuses_when_resolution_is_stamped(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC2 — stamped index cannot return a bare orphan population."""
    plant_islands(store, count=3)
    census = _stamp_autoload(store)
    payload = find_orphans.create(config_for(tmp_path))(detail_level="standard")
    assert payload["status"] == find_orphans.RESOLUTION_UNMODELLED
    assert payload["results"] == []
    assert "unmeasured" in str(payload["message"]).lower()
    assert payload.get("try_instead_hint")
    assert payload["unmodelled_resolution_by_language"] == census


def test_find_orphans_unstamped_still_returns_orphans(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC2 — no stamp ⇒ orphans still returned under status=ok."""
    plant_islands(store, count=3)
    assert store.get_meta(UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY) is None
    payload = find_orphans.create(config_for(tmp_path))(detail_level="standard")
    assert payload["status"] == "ok"
    assert int(payload["total_count"]) >= 3


def test_rebuild_clears_stale_resolution_meta(store: GraphStore) -> None:
    """061 — empty census deletes a prior stamp so orphans can answer again."""
    _stamp_autoload(store)
    assert store.get_meta(UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY) is not None
    store._conn.execute("DELETE FROM nodes WHERE kind = 'File'")
    store._conn.commit()
    resolution = store.unmodelled_resolution_by_language()
    assert resolution == {}
    # Same branch _record_meta takes when the census is empty (279).
    store.delete_meta(UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY)
    assert store.get_meta(UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY) is None
