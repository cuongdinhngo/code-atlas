"""Task 180 — exactness is the primary search key, ahead of BM25.

Round 12's only harmful answer: `search_symbol` returned two substring near-misses in small files
above six exact matches in large ones, with `reason: ok` — the label was right and the order was
wrong. BM25 scores a shorter document better, so the fix bands the result set on the same predicate
`reason` is decided by (`store.is_direct_match`, R6.7) and keeps the old full ordering as the
tie-break inside each band (R4.2). The band orders the **whole** result set, so `offset` walks it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from time import perf_counter

from code_atlas import store as store_module
from code_atlas.store import GraphStore, is_direct_match
from code_atlas.tools import search_symbol
from code_atlas.tools.nav_result import REASON_OK, REASON_SUBSTRING_MATCH
from tests.test_nav_tools import (  # noqa: F401 — store is a fixture
    db_config,
    node,
    seed_file,
    store,
)

REPO = Path(__file__).resolve().parent.parent

QUERY = "loadReport"
NEAR = "preloadReport"  # holds the query as a substring: neither exact nor a prefix (167)


def _seed_field_shape(
    graph: GraphStore, root: Path, *, exact: int = 6, near: int = 2
) -> None:
    """The round-12 shape: short-document near-misses, long-document exact matches.

    Near-misses are planted FIRST and in short files, so they lead under **both** default orders —
    BM25 rank and insert order — and a passing assertion cannot come from either (171-C1).
    """
    for i in range(near):
        path = f"n{i}.js"
        seed_file(graph, path, [node("Function", NEAR, NEAR, path)], [], root=root)
    for i in range(exact):
        path = f"src/deep/nested/module/area/view/list_{i}.php"
        qname = f"\\Ns\\Area\\Module{i}\\{QUERY}"
        seed_file(graph, path, [node("Function", QUERY, qname, path)], [], root=root)


def _names(payload: dict[str, object]) -> list[str]:
    return [str(row["qname"]) for row in payload["results"]]  # type: ignore[index]


def test_the_fixture_defeats_both_default_orders(tmp_path: Path, store) -> None:  # noqa: F811
    """The guard's own guard (R6.5/171-C1): unbanded, the near-misses lead — so red is reachable."""
    _seed_field_shape(store, tmp_path)
    unbanded = store._conn.execute(
        "SELECT nodes.qualified_name FROM nodes JOIN nodes_fts ON nodes_fts.rowid = nodes.id "
        "WHERE nodes_fts MATCH ? "
        "ORDER BY nodes_fts.rank, nodes.qualified_name, nodes.file_path, nodes.id",
        (store_module.fts_term(QUERY),),
    ).fetchall()
    assert [row[0] for row in unbanded][:2] == [NEAR, NEAR]


def test_an_exact_match_outranks_a_better_scoring_near_miss(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """AC1: the exact match is row 1, though the near-miss scores better under BM25."""
    _seed_field_shape(store, tmp_path)
    payload = search_symbol.create(db_config(tmp_path))(QUERY, limit=8)
    names = _names(payload)
    assert names[0] == f"\\Ns\\Area\\Module0\\{QUERY}"
    assert names[-2:] == [NEAR, NEAR]
    assert payload["total_count"] == 8


def test_the_band_reaches_beyond_the_fetched_page(tmp_path: Path, store) -> None:  # noqa: F811
    """AC6: an exact match ranked past page 1 by BM25 reaches page 1 — not a page-local re-rank."""
    _seed_field_shape(store, tmp_path, exact=3, near=12)
    payload = search_symbol.create(db_config(tmp_path))(QUERY, limit=3)
    assert _names(payload) == [f"\\Ns\\Area\\Module{i}\\{QUERY}" for i in range(3)]
    assert payload["total_count"] == 15
    assert payload["truncated"] is True


def test_offset_walks_the_banded_order_and_page_two_does_not_repeat_page_one(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """AC4 (057): the order `offset` pages in is the banded one, so the pages stay disjoint."""
    _seed_field_shape(store, tmp_path, exact=3, near=4)
    tool = search_symbol.create(db_config(tmp_path))
    page1 = _names(tool(QUERY, limit=3, offset=0))
    page2 = _names(tool(QUERY, limit=3, offset=3))
    assert page1 == [f"\\Ns\\Area\\Module{i}\\{QUERY}" for i in range(3)]
    assert page2 == [NEAR, NEAR, NEAR]
    assert set(page1).isdisjoint(page2)
    whole = _names(tool(QUERY, limit=7))
    assert page1 + page2 == whole[:6]


def test_a_page_of_only_exact_matches_is_byte_identical(tmp_path: Path, store) -> None:  # noqa: F811
    """AC5 (061): a homogeneous page cannot be reordered — the band is constant across it."""
    _seed_field_shape(store, tmp_path, near=0)
    payload = search_symbol.create(db_config(tmp_path))(QUERY, limit=8)
    assert _names(payload) == [f"\\Ns\\Area\\Module{i}\\{QUERY}" for i in range(6)]
    assert payload["reason"] == REASON_OK


def test_a_page_of_only_near_misses_is_byte_identical(tmp_path: Path, store) -> None:  # noqa: F811
    """AC5 (061) + AC2: all near-misses keeps BM25 order *and* keeps 167's label."""
    _seed_field_shape(store, tmp_path, exact=0, near=3)
    payload = search_symbol.create(db_config(tmp_path))(QUERY, limit=8)
    assert _names(payload) == [NEAR, NEAR, NEAR]
    assert payload["reason"] == REASON_SUBSTRING_MATCH


def test_reason_is_unchanged_by_banding(tmp_path: Path, store) -> None:  # noqa: F811
    """AC2: 167's rule is untouched — `ok` when a direct match is on the page, else near-miss."""
    _seed_field_shape(store, tmp_path, exact=1, near=2)
    tool = search_symbol.create(db_config(tmp_path))
    assert tool(QUERY, limit=8)["reason"] == REASON_OK
    # A page of one that the band fills with the exact match is still `ok`; drop it and 167 fires.
    assert tool(NEAR, limit=8)["reason"] == REASON_OK
    assert tool("eport", limit=8)["reason"] == REASON_SUBSTRING_MATCH


def test_the_band_predicate_has_one_definition_site(tmp_path: Path) -> None:
    """AC3 (R6.7): the band and `reason` share one predicate — derived by grep, not by eye."""
    found = subprocess.run(
        ["grep", "-rl", "def is_direct_match", "code_atlas/"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert found == ["code_atlas/store.py"]
    absent = subprocess.run(
        ["grep", "-rn", "def _is_direct_match", "code_atlas/"], cwd=REPO, capture_output=True
    )
    assert absent.returncode == 1, "the tool-side copy of the predicate is back"
    assert search_symbol.is_direct_match is is_direct_match


def test_the_sql_band_and_the_python_predicate_cannot_disagree(tmp_path: Path, store) -> None:  # noqa: F811
    """AC3: the scalar SQLite reads for the band IS the predicate — same answers, no second rule."""
    cases = [
        (QUERY, QUERY, QUERY),
        (QUERY, NEAR, NEAR),
        (QUERY.upper(), QUERY.lower(), "x"),
        (QUERY, "x", f"\\Ns\\{QUERY}"),
        (QUERY, "x", f"{QUERY}Extra"),
    ]
    for query, name, qname in cases:
        banded = store._conn.execute(
            f"SELECT {store_module.DIRECT_MATCH_SQL_FN}(?, ?, ?)", (query, name, qname)
        ).fetchone()[0]
        assert bool(banded) is is_direct_match(query, name, qname), (query, name, qname)


def test_the_banded_order_is_deterministic(tmp_path: Path, store) -> None:  # noqa: F811
    """AC8 (R4.2): the pre-existing full ordering is the in-band tie-break, so runs agree."""
    _seed_field_shape(store, tmp_path)
    tool = search_symbol.create(db_config(tmp_path))
    assert tool(QUERY, limit=8) == tool(QUERY, limit=8)


def test_banding_adds_no_query_and_no_measurable_cost(tmp_path: Path, store) -> None:  # noqa: F811
    """AC7: still ONE statement per search — no per-row query — and the added time is ~free."""
    _seed_field_shape(store, tmp_path, exact=40, near=40)
    traced: list[str] = []
    store._conn.set_trace_callback(traced.append)
    rows = store.search_nodes(QUERY, limit=20)
    store._conn.set_trace_callback(None)
    assert len(rows) == 20
    # fts5 traces its own segment reads with a `-- ` prefix; ours are the un-prefixed statements.
    issued = [sql for sql in traced if not sql.startswith("--")]
    assert len(issued) == 1, issued
    assert store_module.DIRECT_MATCH_SQL_FN in issued[0]

    started = perf_counter()
    for _ in range(200):
        store.search_nodes(QUERY, limit=20)
    per_call_ms = (perf_counter() - started) / 200 * 1000
    assert per_call_ms < 5.0, f"{per_call_ms:.3f} ms/call"
