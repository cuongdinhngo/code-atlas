"""Task 280 — parse_failures is a floor on adapter parse inability, not a fatal surface."""

from __future__ import annotations

from pathlib import Path

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status
from code_atlas.tools.get_index_status import PARSE_FAILURES_NOTE, PARSE_FAILURES_NOTE_KEY
from tests.php_adapter_cli import needs_php, parse_file
from tests.test_get_index_status_health import _plant_health_graph
from tests.test_store import nodes_for


def test_parse_failures_note_rides_standard_and_verbose(tmp_path: Path) -> None:
    """AC — disclaimer present wherever parse_failures is served."""
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    _plant_health_graph(db_path)
    tool = get_index_status.create(
        load_config(tmp_path, {"CA_DB_PATH": str(db_path)}),
        (get_index_status.NAME,),
    )
    standard = tool(detail_level="standard")
    verbose = tool(detail_level="verbose")
    minimal = tool(detail_level="minimal")
    assert PARSE_FAILURES_NOTE_KEY not in minimal
    assert standard[PARSE_FAILURES_NOTE_KEY] == PARSE_FAILURES_NOTE
    assert verbose[PARSE_FAILURES_NOTE_KEY] == PARSE_FAILURES_NOTE
    assert "fatal" in PARSE_FAILURES_NOTE.lower()
    assert "compiler" in PARSE_FAILURES_NOTE.lower() or "linter" in PARSE_FAILURES_NOTE.lower()
    for banned in ("php -l", "python -m", "tsc ", "mypy"):
        assert banned not in PARSE_FAILURES_NOTE.lower()


def test_parse_ok_compile_fail_fixture_still_counts_as_parsed(tmp_path: Path) -> None:
    """AC — a file the adapter accepts but the runtime rejects is not a parse_failure."""
    needs_php()
    fixture = (
        Path(__file__).parent
        / "fixtures"
        / "php"
        / "parse_floor"
        / "abstract_method_with_body.php"
    )
    assert parse_file(fixture)["ok"] is True
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    path = "src/abstract_method_with_body.php"
    with GraphStore(db_path) as store:
        store.upsert_file(path, "h", "php", parsed_ok=True)
        store.replace_file_rows(path, nodes_for(path), [])
    payload = get_index_status.create(
        load_config(tmp_path, {"CA_DB_PATH": str(db_path)}),
        (get_index_status.NAME,),
    )(detail_level="standard")
    assert payload["parse_failures"] == 0
    assert payload["failed"] == 0
    assert payload[PARSE_FAILURES_NOTE_KEY] == PARSE_FAILURES_NOTE
