"""Task 061: payload weight — db_path off nav, reactive suggestions, File/Class dedupe."""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools.find_callers import create as callers_create
from code_atlas.tools.get_index_status import NAME as STATUS
from code_atlas.tools.nav_result import list_result, nav_result
from code_atlas.tools.search_symbol import _suppress_redundant_file_hits
from tests.test_mcp_server import (
    BUILD,
    build_server,
    call,
    committed_repo,
    fake_env,
    served_config,
)


def test_nav_helpers_omit_db_path() -> None:
    empty = nav_result(
        "\\A",
        [],
        detail_level="standard",
        db_path="/secret/graph.db",
        index_root="/trees/main",
        truncated=False,
        reason="no_matches",
        total_count=0,
    )
    listed = list_result(
        [],
        detail_level="standard",
        db_path="/secret/graph.db",
        index_root="/trees/main",
        truncated=False,
        reason="no_matches",
        total_count=0,
    )
    assert "db_path" not in empty and "db_path" not in listed
    assert empty["index_root"] == listed["index_root"] == "/trees/main"


def test_status_keeps_db_path_while_nav_drops_it(tmp_path: Path) -> None:
    committed_repo(tmp_path, "src/a.aa")
    config = served_config(tmp_path)
    server = build_server(config)
    call(server, BUILD, {})
    status = call(server, STATUS, {})
    callers = call(server, "find_callers", {"qname": "\\Missing"})
    assert "db_path" in status
    assert "db_path" not in callers


def test_suggestions_vary_across_current_and_behind(tmp_path: Path) -> None:
    committed_repo(tmp_path, "src/a.aa")
    config = served_config(tmp_path)
    server = build_server(config)
    call(server, BUILD, {})
    # Since 223 AC4 a current index omits the key rather than shipping an empty array.
    current = call(server, STATUS, {}).get("next_tool_suggestions", [])
    path = tmp_path / "src" / "a.aa"
    path.write_text(path.read_text(encoding="utf-8") + "x\n", encoding="utf-8")
    behind = call(server, STATUS, {})["next_tool_suggestions"]
    assert current == []
    assert behind == [BUILD]
    assert current != behind


def test_file_class_overlap_is_suppressed() -> None:
    rows = [
        {"qname": "Foo.php", "kind": "File", "file": "src/Foo.php", "line": 1},
        {"qname": "\\Foo", "kind": "Class", "file": "src/Foo.php", "line": 3},
        {"qname": "Other.php", "kind": "File", "file": "src/Other.php", "line": 1},
    ]
    out = _suppress_redundant_file_hits(rows)
    assert [r["kind"] for r in out] == ["Class", "File"]
    assert out[1]["file"] == "src/Other.php"


def test_subject_refreshed_only_absent_when_nothing_repaired(tmp_path: Path) -> None:
    committed_repo(tmp_path, "src/a.aa")
    config = load_config(tmp_path, fake_env())
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    payload = callers_create(config)(qname="\\DoesNotExist")
    assert "subject_refreshed_only" not in payload


def test_payload_size_before_after_recorded_shape(tmp_path: Path) -> None:
    """Representative sizes for Outcome — after 061, nav omits db_path."""
    committed_repo(tmp_path, "src/a.aa")
    config = served_config(tmp_path)
    server = build_server(config)
    call(server, BUILD, {})
    status = call(server, STATUS, {"detail_level": "standard"})
    callers = call(server, "find_callers", {"qname": "\\Missing", "detail_level": "standard"})
    search = call(server, "search_symbol", {"query": "Missing", "detail_level": "standard"})
    sizes = {
        "get_index_status": len(json.dumps(status, separators=(",", ":"))),
        "find_callers": len(json.dumps(callers, separators=(",", ":"))),
        "search_symbol": len(json.dumps(search, separators=(",", ":"))),
    }
    assert sizes["get_index_status"] > sizes["find_callers"]
    assert "db_path" in status and "db_path" not in callers and "db_path" not in search
    assert "index_root" in status and "index_root" in callers and "index_root" in search
    # Soft ceiling after 071; raised 500→560 for adapter #4 (python) — one more
    # unconfigured_adapters row rides every find_callers payload (task 020 Gate 2).
    assert sizes["find_callers"] < 560
