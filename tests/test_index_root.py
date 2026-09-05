"""Task 071: every answer names the source tree it describes (`index_root`)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.tools.explain_path import create as explain_create
from code_atlas.tools.file_outline import create as outline_create
from code_atlas.tools.find_callers import create as callers_create
from code_atlas.tools.get_index_status import create as status_create
from code_atlas.tools.nav_result import list_result, nav_result
from code_atlas.tools.search_symbol import create as search_create
from tests.test_mcp_server import (
    BUILD,
    build_server,
    call,
    committed_repo,
    fake_env,
    served_config,
)


def test_nav_helpers_require_and_emit_index_root() -> None:
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
    assert empty["index_root"] == listed["index_root"] == "/trees/main"
    assert "db_path" not in empty and "db_path" not in listed


def test_index_root_is_configured_root_not_process_cwd(tmp_path: Path) -> None:
    """Server root ≠ cwd: payloads still report config.root (AC proving test)."""
    repo = tmp_path / "indexed-tree"
    repo.mkdir()
    committed_repo(repo, "src/a.aa")
    elsewhere = tmp_path / "agent-cwd"
    elsewhere.mkdir()
    config = load_config(repo, fake_env())
    assert config.root.resolve() == repo.resolve()

    previous = Path.cwd()
    try:
        os.chdir(elsewhere)
        assert Path.cwd().resolve() == elsewhere.resolve()
        assert Path.cwd().resolve() != config.root.resolve()
        server = build_server(config)
        call(server, BUILD, {})
        expected = str(config.root.resolve())
        status = call(server, "get_index_status", {"detail_level": "minimal"})
        search = call(server, "search_symbol", {"query": "Missing"})
        callers = call(server, "find_callers", {"qname": "\\Missing"})
        outline = call(server, "file_outline", {"path": "src/a.aa"})
    finally:
        os.chdir(previous)

    for payload in (status, search, callers, outline):
        assert payload["index_root"] == expected
    assert "db_path" not in search and "db_path" not in callers and "db_path" not in outline
    assert status["last_ref"] == status["head_ref"]
    assert status["head_ref"] is not None


def test_status_reports_index_root_beside_db_path(tmp_path: Path) -> None:
    committed_repo(tmp_path, "src/a.aa")
    config = served_config(tmp_path)
    server = build_server(config)
    call(server, BUILD, {})
    expected = str(config.root.resolve())
    minimal = call(server, "get_index_status", {"detail_level": "minimal"})
    standard = call(server, "get_index_status", {"detail_level": "standard"})
    assert minimal["index_root"] == expected
    assert standard["index_root"] == expected
    assert "db_path" not in minimal
    assert standard["db_path"] == str(config.db_path)


def test_index_root_weight_before_after_recorded(tmp_path: Path) -> None:
    """061 weight check: index_root adds one path field; nav still omits db_path."""
    committed_repo(tmp_path, "src/a.aa")
    config = served_config(tmp_path)
    server = build_server(config)
    call(server, BUILD, {})
    status = call(server, "get_index_status", {"detail_level": "standard"})
    callers = call(server, "find_callers", {"qname": "\\Missing", "detail_level": "standard"})
    search = call(server, "search_symbol", {"query": "Missing", "detail_level": "standard"})
    sizes = {
        "get_index_status": len(json.dumps(status, separators=(",", ":"))),
        "find_callers": len(json.dumps(callers, separators=(",", ":"))),
        "search_symbol": len(json.dumps(search, separators=(",", ":"))),
    }
    # Synthetic prior (061): same payloads without index_root.
    prior_callers = {k: v for k, v in callers.items() if k != "index_root"}
    prior_search = {k: v for k, v in search.items() if k != "index_root"}
    delta_callers = sizes["find_callers"] - len(
        json.dumps(prior_callers, separators=(",", ":"))
    )
    delta_search = sizes["search_symbol"] - len(
        json.dumps(prior_search, separators=(",", ":"))
    )
    assert "index_root" in callers and "index_root" in search and "index_root" in status
    assert "db_path" not in callers and "db_path" not in search
    assert delta_callers > 0 and delta_search > 0
    # Soft ceiling after 071; raised 500→560 for adapter #4 (python) — one more
    # unconfigured_adapters row rides every find_callers payload (task 020 Gate 2).
    assert sizes["find_callers"] < 560
    assert delta_callers == len(f',"index_root":{json.dumps(callers["index_root"])}')
    assert delta_search == len(f',"index_root":{json.dumps(search["index_root"])}')
    # Pin measured sizes for the working-doc 061 reconciliation.
    assert isinstance(sizes["get_index_status"], int)


def test_direct_tool_closures_emit_index_root(tmp_path: Path) -> None:
    committed_repo(tmp_path, "src/a.aa")
    config = load_config(tmp_path, fake_env())
    expected = str(config.root.resolve())
    assert status_create(config, ("get_index_status",))(detail_level="minimal")[
        "index_root"
    ] == expected
    assert search_create(config)(query="x")["index_root"] == expected
    assert callers_create(config)(qname="\\X")["index_root"] == expected
    assert outline_create(config)(path="missing.aa")["index_root"] == expected
    assert explain_create(config)(from_qname="\\A", to_qname="\\B")["index_root"] == expected
