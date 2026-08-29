"""Task 187: one empty-case contract for the reach walk.

``retain_temps=True`` promises the walk's temp tables are still there to read. ``reachable_from``
had a second way out — an empty seed list returned *before* the ``try`` block that creates them —
so ``store.find_orphans`` read tables that were never made. Same defect facing the other way: that
return also skipped the drop, so an empty walk could not clear a previous retained walk's rows.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import store as store_module
from code_atlas.store import _REACH_RETAINED_TEMPS, GraphStore

ENTRY = "entry.php"
DEAD = "dead.php"
ENTRY_FN = "\\Entry\\main"
CALLEE = "\\Lib\\Helper"
ORPHAN = "\\Dead\\Unused"

# The `retain_temps=True` call sites this file covers, derived from source below (R6.7). A new one
# fails the enumeration guard rather than crashing in the field, as this ticket's did.
COVERED_CONSUMERS = {("store.py", "find_orphans")}


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def node(kind: str, name: str, qname: str, path: str) -> dict[str, object]:
    return {
        "kind": kind,
        "name": name,
        "qualified_name": qname,
        "file_path": path,
        "line_start": 1,
    }


def edge(source: str, target: str, path: str) -> dict[str, object]:
    return {
        "kind": "CALLS",
        "source_qname": source,
        "target_raw": target,
        "target_qname": target,
        "file_path": path,
        "line": 1,
        "confidence_tier": "RESOLVED",
    }


@pytest.fixture
def graph(store: GraphStore) -> GraphStore:
    store.upsert_file(ENTRY, "h", "php")
    store.replace_file_rows(
        ENTRY,
        [node("function", "main", ENTRY_FN, ENTRY), node("class", "Helper", CALLEE, ENTRY)],
        [edge(ENTRY_FN, CALLEE, ENTRY)],
    )
    store.upsert_file(DEAD, "h", "php")
    store.replace_file_rows(DEAD, [node("class", "Unused", ORPHAN, DEAD)], [])
    return store


def temp_tables(store: GraphStore) -> set[str]:
    rows = store._conn.execute(
        "SELECT name FROM temp.sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def test_orphans_over_seeds_that_resolve_to_nothing_answer_instead_of_raising(
    graph: GraphStore,
) -> None:
    """AC1 — the empty seed list `entry_seeds` hands over when every glob misses.

    Red on the pre-fix tree: `OperationalError: no such table: temp.reach_seen`.
    """
    outcome = graph.find_orphans([], depth=None, max_nodes=100, limit=10)

    assert outcome.reached == 0
    assert outcome.nodes_total == 3
    # Nothing was walked, so nothing is excluded: every node falls out as an orphan. That is the
    # mechanical truth at this layer, and `reached=0` is what lets the tool above refuse it (R5.6).
    assert outcome.orphan_total == 3
    assert {row["qname"] for row in outcome.orphans} == {ENTRY_FN, CALLEE, ORPHAN}


def test_retain_temps_leaves_every_promised_table_readable_on_the_empty_path(
    graph: GraphStore,
) -> None:
    """AC3 — the postcondition is total: it holds on the empty path as on the walked one."""
    for seeds in ([], [ENTRY_FN]):
        graph.reachable_from(seeds, depth=None, max_nodes=100, retain_temps=True)
        for table in _REACH_RETAINED_TEMPS:
            rows = graph._conn.execute(f"SELECT COUNT(*) FROM temp.{table}").fetchone()
            assert rows is not None, f"{table} is not readable after seeds={seeds!r}"
        graph._reach_drop_temps()


def test_an_empty_walk_clears_a_previous_retained_walks_tables(graph: GraphStore) -> None:
    """The silent half — red on the pre-fix tree, where the early return skipped the drop.

    A stale `reach_seen` outliving the walk that filled it serves the previous question's rows.
    """
    graph.reachable_from([ENTRY_FN], depth=None, max_nodes=100, retain_temps=True)
    assert "reach_seen" in temp_tables(graph)

    graph.reachable_from([], depth=None, max_nodes=100)

    assert temp_tables(graph) & set(_REACH_RETAINED_TEMPS) == set()


def test_the_empty_walk_returns_what_the_special_case_used_to_hardcode(
    graph: GraphStore,
) -> None:
    """AC5 — `reachable_from`'s answer is unchanged; only the resource contract moved."""
    result = graph.reachable_from([], depth=None, max_nodes=100)

    assert (result.reachable, result.unproven) == ([], [])
    assert result.frontier_skipped_non_resolved == 0
    assert (result.truncated, result.depth_exhausted, result.budget_exhausted) == (
        False,
        False,
        False,
    )


def test_every_retain_temps_consumer_in_the_core_is_covered_here() -> None:
    """AC3 / R6.7 — the consumer set is read out of the core's syntax, never re-typed from memory.

    Parsed, not grepped: a text sweep also matches the word in a comment, which is how 190's
    envelope condition reported a defect that was only prose.
    """
    core = Path(store_module.__file__).parent
    found: set[tuple[str, str]] = set()
    for path in sorted(core.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for parent in ast.walk(tree):
            if not isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for child in ast.walk(parent):
                if not isinstance(child, ast.Call):
                    continue
                for keyword in child.keywords:
                    retained = (
                        keyword.arg == "retain_temps"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                    )
                    if retained:
                        found.add((path.name, parent.name))

    assert found == COVERED_CONSUMERS, (
        f"the retain_temps consumers in the core are {sorted(found)}, but this file covers "
        f"{sorted(COVERED_CONSUMERS)} — extend the empty-path coverage above before adding one"
    )
