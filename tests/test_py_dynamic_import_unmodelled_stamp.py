"""Task 295 — Python importlib/__import__ stamp File.extra.unmodelled_resolution."""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas.contract import RESOLUTION_DYNAMIC_IMPORT, UNMODELLED_RESOLUTION
from code_atlas.store import (
    UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY,
    GraphStore,
)
from code_atlas.tools import find_orphans
from tests.python_adapter_cli import needs_python, parse_file
from tests.test_find_orphans_refuses_what_it_cannot_answer import config_for, plant_islands
from tests.test_reachability import store as store  # noqa: F401

_FIXTURES = Path("tests/fixtures/python/unmodelled_resolution")


@needs_python
def test_py_import_module_stamps_file_extra() -> None:
    """AC1 — importlib.import_module stamps File.extra unmodelled_resolution."""
    result = parse_file(_FIXTURES / "import_module.py")
    assert result["ok"] is True
    files = [n for n in result["nodes"] if n["kind"] == "File"]
    assert files
    extra = files[0].get("extra") or {}
    assert RESOLUTION_DYNAMIC_IMPORT in (extra.get(UNMODELLED_RESOLUTION) or [])


@needs_python
def test_py_dunder_import_stamps() -> None:
    result = parse_file(_FIXTURES / "dunder_import.py")
    assert result["ok"] is True
    files = [n for n in result["nodes"] if n["kind"] == "File"]
    extra = files[0].get("extra") or {}
    assert RESOLUTION_DYNAMIC_IMPORT in (extra.get(UNMODELLED_RESOLUTION) or [])


@needs_python
def test_py_spec_from_file_location_stamps() -> None:
    result = parse_file(_FIXTURES / "spec_from_file.py")
    assert result["ok"] is True
    files = [n for n in result["nodes"] if n["kind"] == "File"]
    extra = files[0].get("extra") or {}
    assert RESOLUTION_DYNAMIC_IMPORT in (extra.get(UNMODELLED_RESOLUTION) or [])


@needs_python
def test_py_statement_imports_do_not_stamp() -> None:
    """AC1 negative — statement imports alone produce no unmodelled_resolution key."""
    result = parse_file(_FIXTURES / "statement_only.py")
    assert result["ok"] is True
    files = [n for n in result["nodes"] if n["kind"] == "File"]
    extra = (files[0].get("extra") or {}) if files else {}
    assert UNMODELLED_RESOLUTION not in extra


@needs_python
def test_py_dynamic_import_emits_no_new_imports_edge() -> None:
    """AC3 — stamp does not invent IMPORTS edges."""
    result = parse_file(_FIXTURES / "import_module.py")
    assert result["ok"] is True
    imports = [e for e in result["edges"] if e["kind"] == "IMPORTS"]
    # Only the top-level `import importlib` statement — not the call.
    assert all(
        not str(e.get("target_raw", "")).endswith("name") for e in imports
    )
    assert len(imports) == 1


def _stamp_py(store: GraphStore, path: str = "src/load.py") -> dict[str, list[str]]:
    store.upsert_file(path, "h", "python")
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
    assert census.get("python") == [RESOLUTION_DYNAMIC_IMPORT]
    store.set_meta(UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY, json.dumps(census, sort_keys=True))
    return census


def test_find_orphans_refuses_when_py_resolution_is_stamped(
    store: GraphStore, tmp_path: Path
) -> None:
    plant_islands(store, count=3)
    census = _stamp_py(store)
    payload = find_orphans.create(config_for(tmp_path))(detail_level="standard")
    assert payload["status"] == find_orphans.RESOLUTION_UNMODELLED
    assert payload["results"] == []
    assert payload["unmodelled_resolution_by_language"] == census


def test_find_orphans_unstamped_py_still_returns_orphans(
    store: GraphStore, tmp_path: Path
) -> None:
    plant_islands(store, count=3)
    payload = find_orphans.create(config_for(tmp_path))(detail_level="standard")
    assert payload["status"] == "ok"
    assert int(payload["total_count"]) >= 3
