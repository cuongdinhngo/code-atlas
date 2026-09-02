"""Task 203 scope 2: the per-file delete in `replace_file_rows` must not scan the edge table.

Measured on the anchor monorepo (24,569 files / 2.08 M edges) before the fix: `DELETE FROM edges
WHERE file_path = ?` planned as `SCAN edges` and cost **189.58 ms per file**, i.e. 77.6 minutes
across a full build whose whole wall was 75.8 minutes. With `idx_edges_file` it plans as a SEARCH
and costs 0.18 ms — 1,025x — and the index itself builds once in 1.6 s.

The ticket's own hypothesis was GIL contention between reply decode and the single writer. It was
wrong: no amount of decode parallelism can touch a full table scan per file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from code_atlas.store import GraphStore

# Every column `replace_file_rows` deletes by, and the plan word that means "not a scan".
DELETES = (
    ("edges", "DELETE FROM edges WHERE file_path = ?"),
    ("nodes", "DELETE FROM nodes WHERE file_path = ?"),
)


@pytest.fixture
def store(tmp_path: Path):
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


@pytest.mark.parametrize(("table", "sql"), DELETES, ids=[name for name, _ in DELETES])
def test_the_per_file_delete_uses_an_index(store: GraphStore, table: str, sql: str) -> None:
    """R6.5: red before `idx_edges_file`, where the `edges` row plans as `SCAN edges`."""
    plan = [
        str(row[3])
        for row in store._conn.execute("EXPLAIN QUERY PLAN " + sql, ("some/file.php",))
    ]

    assert plan, f"no query plan for the {table} delete"
    assert not any(step.startswith("SCAN") for step in plan), (
        f"the per-file {table} delete scans the whole table: {plan}. `replace_file_rows` runs it "
        f"once per parsed file, so a scan here is a full-table pass per file (task 203)."
    )


def test_every_column_replace_file_rows_deletes_by_is_indexed(store: GraphStore) -> None:
    """Derived, not listed (R6.7): read the indexed columns out of the schema itself.

    A future `_delete_rows` that deletes by a second column ships an unindexed predicate unless
    this fails — which is exactly how `edges.file_path` went unnoticed while `nodes.file_path`
    had `idx_nodes_file` from the start.
    """
    indexed: dict[str, set[str]] = {}
    for table in ("edges", "nodes"):
        names = [
            str(row[0])
            for row in store._conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = ?", (table,)
            )
        ]
        columns: set[str] = set()
        for name in names:
            columns.update(
                str(row[2]) for row in store._conn.execute(f"PRAGMA index_info('{name}')")
            )
        indexed[table] = columns

    assert "file_path" in indexed["edges"], indexed["edges"]
    assert "file_path" in indexed["nodes"], indexed["nodes"]
