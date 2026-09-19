"""Task 298 — SQL omits undecided is_test so path convention fills."""

from __future__ import annotations

from pathlib import Path

from code_atlas.store import GraphStore
from code_atlas.symbol_role import apply_test_role
from code_atlas.tools import find_callers
from tests.sql_adapter_cli import needs_node, parse_file
from tests.test_nav_tools import db_config, seed_file
from tests.test_nav_tools import store as store  # noqa: F401


@needs_node
def test_sql_adapter_emits_no_is_test_key() -> None:
    """AC2 — no is_test literal on nodes from the SQL adapter."""
    result = parse_file("tests/fixtures/sql/exec_call.sql")
    assert result["ok"] is True
    for n in result["nodes"]:
        assert "is_test" not in n
    scan = Path("adapters/sql/src/scan.js").read_text(encoding="utf-8")
    assert "is_test" not in scan


def test_omitted_is_test_under_test_path_gets_path_convention() -> None:
    """AC pin — any adapter that omits is_test under a test path is classified."""
    rows: list[dict[str, object]] = [
        {"file_path": "tests/foo.sql", "qualified_name": "dbo.P"},
        {"file_path": "src/foo.sql", "qualified_name": "dbo.Q", "is_test": 0},
    ]
    apply_test_role(rows)
    assert rows[0].get("is_test") == 1
    assert rows[1].get("is_test") == 0  # adapter-decided false still wins


@needs_node
def test_sql_fixture_under_test_path_gets_path_convention() -> None:
    """AC1 — adapter output for a tests/ fixture is classified by path convention."""
    # Repo-relative path under tests/ so path_indicates_test fires after omit.
    result = parse_file("tests/fixtures/sql/tests/calls_proc.sql")
    assert result["ok"] is True
    for n in result["nodes"]:
        assert "is_test" not in n
        n["file_path"] = "tests/fixtures/sql/tests/calls_proc.sql"
    apply_test_role(result["nodes"])
    assert any(n.get("is_test") == 1 for n in result["nodes"])


@needs_node
def test_sql_test_path_caller_is_not_production(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1 — find_callers: only test-path SQL callers ⇒ production_count 0."""
    prod_result = parse_file("tests/fixtures/sql/prod_proc.sql")
    test_result = parse_file("tests/fixtures/sql/tests/calls_proc.sql")
    assert prod_result["ok"] and test_result["ok"]
    prod_path = "src/prod_proc.sql"
    test_path = "tests/calls_proc.sql"

    def _retarget(result: dict, new_path: str) -> tuple[list, list]:
        nodes = []
        for n in result["nodes"]:
            row = dict(n)
            if row["kind"] == "File":
                row["name"] = new_path.split("/")[-1]
                row["qualified_name"] = new_path
            row["file_path"] = new_path
            nodes.append(row)
        edges = []
        for e in result.get("edges") or []:
            row = dict(e)
            row["file_path"] = new_path
            if row.get("kind") == "CONTAINS":
                row["source_qname"] = new_path
            if row.get("kind") == "CALLS" and row.get("target_raw"):
                row["target_qname"] = row["target_raw"]
            edges.append(row)
        return nodes, edges

    prod_nodes, prod_edges = _retarget(prod_result, prod_path)
    test_nodes, test_edges = _retarget(test_result, test_path)
    seed_file(store, prod_path, prod_nodes, prod_edges, root=tmp_path)
    seed_file(store, test_path, test_nodes, test_edges, root=tmp_path)
    payload = find_callers.create(db_config(tmp_path))(qname="dbo.ProdProc", depth=1)
    assert payload.get("results"), payload
    assert int(payload.get("production_count", -1)) == 0
    assert payload.get("test_role_source") == "path_convention"
    assert int(payload.get("test_count", 0)) >= 1
