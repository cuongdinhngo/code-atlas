"""Task 258 — one unresolved CALL site; candidates at query time (no build cartesian product)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.resolver import resolve_edges
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from code_atlas.tools.nav_result import REASON_PROXIMITY_CANDIDATES
from tests.test_nav_tools import db_config, edge, node, seed_file

ZEND_FILE = "vendor/Zend/Cache/Backend/Memcached.php"
APP_A = "application/LedgerAPIController.php"
APP_B = "application/LeaveAPIController.php"
LOCAL_CALLER = "application/services/CacheUser.php"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def _plant_zend_get(store: GraphStore, root: Path) -> None:
    """Zend ``->get`` plus two alphabetically early application ``get`` Methods (AC3 shape)."""
    seed_file(
        store,
        ZEND_FILE,
        [node("Method", "load", f"{ZEND_FILE}::load", ZEND_FILE)],
        [edge("CALLS", f"{ZEND_FILE}::load", "get", ZEND_FILE, tier="HEURISTIC")],
        root=root,
    )
    seed_file(
        store,
        APP_A,
        [node("Method", "get", "\\LedgerAPIController::get", APP_A)],
        [],
        root=root,
    )
    seed_file(
        store,
        APP_B,
        [node("Method", "get", "\\LeaveAPIController::get", APP_B)],
        [],
        root=root,
    )
    seed_file(
        store,
        LOCAL_CALLER,
        [node("Method", "run", "\\App\\Services\\CacheUser::run", LOCAL_CALLER)],
        [
            edge(
                "CALLS",
                "\\App\\Services\\CacheUser::run",
                "get",
                LOCAL_CALLER,
                tier="HEURISTIC",
            )
        ],
        root=root,
    )


def test_multi_match_stores_one_unresolved_site(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC1 fixture shape: one CALL site → one edge row, not N HEURISTIC siblings."""
    _plant_zend_get(store, tmp_path)
    resolve_edges(store, max_candidates=10)
    zend_edges = store.edges_by_source(f"{ZEND_FILE}::load", kinds=("CALLS",), limit=20)
    assert len(zend_edges) == 1
    assert zend_edges[0]["target_qname"] is None
    assert store.count_edges_by_target("\\LedgerAPIController::get", kinds=("CALLS",)) == 0


def test_max_results_does_not_change_stored_graph(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC4: build at 10 and at 50 produce the same unresolved-site graph."""
    _plant_zend_get(store, tmp_path)
    resolve_edges(store, max_candidates=10)
    rows_10 = [
        (
            str(e["source_qname"]),
            e.get("target_qname"),
            str(e["target_raw"]),
            str(e["confidence_tier"]),
        )
        for e in store.edges_by_source(f"{ZEND_FILE}::load", kinds=("CALLS",), limit=50)
    ]
    # Re-resolve with a wider cap on the same rows (idempotent linking).
    resolve_edges(store, max_candidates=50)
    rows_50 = [
        (
            str(e["source_qname"]),
            e.get("target_qname"),
            str(e["target_raw"]),
            str(e["confidence_tier"]),
        )
        for e in store.edges_by_source(f"{ZEND_FILE}::load", kinds=("CALLS",), limit=50)
    ]
    assert rows_10 == rows_50
    assert len(rows_10) == 1


def test_zend_get_is_not_a_caller_of_application_get(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC3: Zend/get no longer appears as a caller of alphabetically early application gets."""
    _plant_zend_get(store, tmp_path)
    resolve_edges(store, max_candidates=10)
    tool = find_callers.create(replace(db_config(tmp_path), root=tmp_path, page_limit=50))
    for subject in ("\\LedgerAPIController::get", "\\LeaveAPIController::get"):
        payload = tool(subject, detail_level="minimal")
        callers = [str(hit["qname"]) for hit in payload["results"]]
        assert f"{ZEND_FILE}::load" not in callers
        assert payload["total_count"] == 0 or all(
            "Zend" not in name for name in callers
        )


def test_proximity_ranked_find_callers_reports_true_count(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC2: same-subtree unresolved sites rank in; total_count is not a capped prefix."""
    _plant_zend_get(store, tmp_path)
    # Many same-named Methods under application/ so the build would have capped alphabetically.
    for i in range(12):
        path = f"application/Extra{i:02d}.php"
        seed_file(
            store,
            path,
            [node("Method", "get", f"\\Extra{i:02d}::get", path)],
            [],
            root=tmp_path,
        )
    resolve_edges(store, max_candidates=10)
    tool = find_callers.create(replace(db_config(tmp_path), root=tmp_path, page_limit=3))
    # Local caller shares application/ with Extra* and CacheUser — proximity depth ≥ 1.
    page = tool("\\Extra00::get", detail_level="minimal", limit=3)
    assert page["total_count"] >= 1
    # The rows are candidates the resolver declined to link — the payload must say so (R5.6).
    assert page["reason"] == REASON_PROXIMITY_CANDIDATES
    assert all(hit["candidate_of"] == "\\Extra00::get" for hit in page["results"])
    assert "\\App\\Services\\CacheUser::run" in [
        str(hit["qname"]) for hit in page["results"]
    ]
    assert f"{ZEND_FILE}::load" not in [str(hit["qname"]) for hit in page["results"]]


def test_query_cost_saturating_name_is_one_scan_of_the_name(
    store: GraphStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5: the cost of proximity expansion, counted rather than timed.

    A wall-clock threshold is not evidence on a contended host — it fails when the host is
    busy and passes when a regression is merely slow. Count the store reads instead: the
    expansion must be one scan of the unresolved sites for the name, not one per candidate.
    """
    _plant_zend_get(store, tmp_path)
    for i in range(40):
        path = f"application/Extra{i:02d}.php"
        seed_file(
            store,
            path,
            [node("Method", "get", f"\\Extra{i:02d}::get", path)],
            [],
            root=tmp_path,
        )
    resolve_edges(store, max_candidates=10)
    tool = find_callers.create(replace(db_config(tmp_path), root=tmp_path, page_limit=50))
    scans = 0
    inner = GraphStore.unresolved_caller_sites

    def counting(self: GraphStore, *args: object, **kwargs: object) -> list[dict[str, object]]:
        nonlocal scans
        scans += 1
        return inner(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(GraphStore, "unresolved_caller_sites", counting)
    payload = tool("\\Extra00::get", detail_level="minimal")
    assert payload["indexed"] is True
    # One scan for the whole answer — 41 same-named candidates do not each cost a query.
    assert scans == 1


def test_a_linked_answer_never_pays_for_the_proximity_scan(
    store: GraphStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The expansion is the empty-answer path only — a subject with a linked caller skips it.

    Guarding the guard (R6.5): the scan used to run for every Method subject and be discarded
    unless the linked answer was empty, so a saturating name paid for it on every call.
    """
    _plant_zend_get(store, tmp_path)
    linked = "application/services/Direct.php"
    seed_file(
        store,
        linked,
        [node("Method", "call", "\\App\\Services\\Direct::call", linked)],
        [
            edge(
                "CALLS",
                "\\App\\Services\\Direct::call",
                "get",
                linked,
                target_qname="\\LedgerAPIController::get",
                tier="RESOLVED",
            )
        ],
        root=tmp_path,
    )
    scanned = False

    def forbidden(self: GraphStore, *args: object, **kwargs: object) -> list[dict[str, object]]:
        nonlocal scanned
        scanned = True
        return []

    monkeypatch.setattr(GraphStore, "unresolved_caller_sites", forbidden)
    tool = find_callers.create(replace(db_config(tmp_path), root=tmp_path, page_limit=50))
    payload = tool("\\LedgerAPIController::get", detail_level="minimal")
    assert payload["total_count"] == 1
    assert payload["reason"] != REASON_PROXIMITY_CANDIDATES
    assert scanned is False
