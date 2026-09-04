"""Task 060: build tool payload separates run writes from graph totals."""

from __future__ import annotations

from pathlib import Path

from code_atlas import gitutil
from code_atlas.main import build_server
from code_atlas.store import LAST_COMMIT_KEY, GraphStore
from code_atlas.tools.build_or_update_index import NAME as BUILD
from code_atlas.tools.get_index_status import NAME as STATUS
from tests.test_build_report_counts import MULTI_CANDIDATE, config_for
from tests.test_incremental import committed
from tests.test_mcp_server import call

_REPORT_KEYS = frozenset(
    {
        "files",
        "parsed",
        "failed",
        "removed",
        "nodes",
        "edges",
        "stubs",
        "fingerprint_skipped",
    }
)
_GRAPH_KEYS = frozenset({"files", "parsed", "failed", "nodes", "edges", "stubs"})


def test_incremental_tool_payload_cannot_be_read_as_graph_size(tmp_path: Path) -> None:
    """Proving test: old flat ``edges``/``nodes`` shape would fail; wrote ≠ graph on delta."""
    committed(tmp_path, MULTI_CANDIDATE)
    config = config_for(tmp_path)
    server = build_server(config)

    full = call(server, BUILD, {"full": True, "detail_level": "standard"})
    assert full["mode"] == "full"
    assert set(full["wrote"]) >= _REPORT_KEYS
    assert set(full["graph"]) >= _GRAPH_KEYS
    assert full["wrote"]["edges"] == full["graph"]["edges"]
    assert _REPORT_KEYS.isdisjoint(full)  # no bare report fields at top level

    with GraphStore(config.db_path) as store:
        last = store.get_meta(LAST_COMMIT_KEY)
    assert last is not None
    committed(tmp_path, {"twin/a.aa": "run a v2\n"}, message="edit twin a")
    assert gitutil.changed_paths(tmp_path, last) == ("twin/a.aa",)

    delta = call(server, BUILD, {"full": False, "detail_level": "standard"})
    status = call(server, STATUS, {})

    assert delta["mode"] == "incremental"
    assert _REPORT_KEYS.isdisjoint(delta)
    assert "wrote" in delta and "graph" in delta
    assert delta["wrote"]["edges"] < delta["graph"]["edges"]
    assert delta["graph"]["edges"] == status["edges"]
    assert delta["graph"]["nodes"] == status["nodes"]
    # Scale is labelled — distinguishable without consulting ``mode``.
    assert delta["wrote"]["edges"] != delta["graph"]["edges"]
    assert full["wrote"]["edges"] == full["graph"]["edges"]


def test_minimal_omits_graph_and_keeps_wrote_nesting(tmp_path: Path) -> None:
    """``graph`` stays off the cheap path; ``wrote`` alone still blocks the flat misread."""
    committed(tmp_path, MULTI_CANDIDATE)
    config = config_for(tmp_path)
    server = build_server(config)

    minimal = call(server, BUILD, {"full": True, "detail_level": "minimal"})

    assert "wrote" in minimal
    assert "graph" not in minimal
    assert _REPORT_KEYS.isdisjoint(minimal)
    assert "last_commit" not in minimal and "db_path" not in minimal
