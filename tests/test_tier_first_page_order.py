"""Task 265 — tier-first default inbound page order; RESOLVED is on page 1 by default.

Proving shape: the sole RESOLVED caller sorts last alphabetically among HEURISTIC noise;
page 1 of the unfiltered answer still carries it because the store orders by tier before
truncation. Companion ACs: ordering is in SQL (not a post-filter), a filtered-empty page
may return zero rows with ``authoritative: false`` + census (still ``no_matches``), and class-level ``via_members``
pages in one ``IN`` read.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from code_atlas.store import _EDGE_ORDER_TIER_FIRST, GraphStore
from code_atlas.tools import find_callers
from code_atlas.tools.nav_result import CAVEAT_TIER_PARTITION
from tests.test_find_callers_tier_control import (
    HEURISTIC_PREFIX,
    RESOLVED_CALLER,
    SUBJECT,
    SUBJECT_FILE,
    _plant_buried_resolved,
)
from tests.test_nav_tools import db_config, edge, node, seed_file


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def test_resolved_caller_on_page_one_under_tier_first_order(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC1 (proving): alphabetically-last RESOLVED caller is on unfiltered page 1."""
    _plant_buried_resolved(store, tmp_path, noise=5)
    config = replace(db_config(tmp_path), root=tmp_path, page_limit=3)
    page = find_callers.create(config)(SUBJECT, detail_level="minimal", limit=3, offset=0)
    assert page["total_count"] == 6
    assert page["truncated"] is True
    page_qnames = [str(hit["qname"]) for hit in page["results"]]
    assert RESOLVED_CALLER in page_qnames
    assert page["results"][0]["confidence_tier"] == "RESOLVED"
    assert page["tier_census"] == {"HEURISTIC": 5, "RESOLVED": 1}
    assert page["authoritative"] is False
    assert CAVEAT_TIER_PARTITION in page["authoritative_caveats"]


def test_tier_order_is_applied_in_the_store_query_not_after_truncation(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC2: ``edges_by_target`` asks ``_edges`` for tier-first ORDER BY before LIMIT."""
    _plant_buried_resolved(store, tmp_path, noise=2)
    seen: list[str] = []
    real = store._edges

    def spy(*args: object, **kwargs: object) -> object:
        seen.append(str(kwargs.get("order", "")))
        return real(*args, **kwargs)

    with patch.object(store, "_edges", side_effect=spy):
        store.edges_by_target(SUBJECT, kinds=("CALLS", "NEW"), limit=3, offset=0)
    assert seen == [_EDGE_ORDER_TIER_FIRST]


def test_filtered_empty_page_returns_zero_rows_with_census(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC3: RESOLVED filter over HEURISTIC-only callers → zero rows + census, not silence.

    The zero stays ``no_matches`` — 264 removed the override that answered ``ok`` over an empty
    filtered page; the census beside it is what says which tier the filter removed (R5.6).
    """
    nodes = [
        node("Method", "build", SUBJECT, SUBJECT_FILE),
        node("Method", "build", f"{HEURISTIC_PREFIX}00::build", "legacy/noise00.php"),
    ]
    edges = [
        edge(
            "CALLS",
            f"{HEURISTIC_PREFIX}00::build",
            "build",
            "legacy/noise00.php",
            target_qname=SUBJECT,
            tier="HEURISTIC",
        )
    ]
    seed_file(store, SUBJECT_FILE, nodes[:1], [], root=tmp_path)
    seed_file(store, "legacy/noise00.php", [nodes[1]], edges, root=tmp_path)
    config = replace(db_config(tmp_path), root=tmp_path, page_limit=50)
    page = find_callers.create(config)(
        SUBJECT, detail_level="minimal", confidence_tier="RESOLVED"
    )
    assert page["results"] == []
    assert page["total_count"] == 0
    assert page["reason"] == "no_matches"
    assert page["authoritative"] is False
    assert page["tier_census"] == {"HEURISTIC": 1}
    assert CAVEAT_TIER_PARTITION in page["authoritative_caveats"]


def test_class_via_members_pages_in_one_store_read(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC4: union cost scales with the page — one IN query, not one walk per member."""
    class_q = "\\App\\Svc"
    m1, m2 = f"{class_q}::a", f"{class_q}::b"
    caller = "\\App\\Zee::run"
    nodes = [
        node("Class", "Svc", class_q, "app/Svc.php"),
        node("Method", "a", m1, "app/Svc.php"),
        node("Method", "b", m2, "app/Svc.php"),
        node("Method", "run", caller, "app/Zee.php"),
    ]
    edges = [
        edge("CONTAINS", class_q, "a", "app/Svc.php", target_qname=m1, tier="RESOLVED"),
        edge("CONTAINS", class_q, "b", "app/Svc.php", target_qname=m2, tier="RESOLVED"),
        edge("CALLS", caller, "a", "app/Zee.php", target_qname=m1, tier="RESOLVED"),
        edge("CALLS", caller, "b", "app/Zee.php", target_qname=m2, tier="HEURISTIC"),
    ]
    seed_file(store, "app/Svc.php", nodes[:3], edges[:2], root=tmp_path)
    seed_file(store, "app/Zee.php", [nodes[3]], edges[2:], root=tmp_path)

    calls = {"by_target": 0, "by_targets": 0}
    real_by_target = store.edges_by_target
    real_by_targets = store.edges_by_targets

    def count_by_target(*args: object, **kwargs: object) -> object:
        calls["by_target"] += 1
        return real_by_target(*args, **kwargs)

    def count_by_targets(*args: object, **kwargs: object) -> object:
        calls["by_targets"] += 1
        return real_by_targets(*args, **kwargs)

    from code_atlas.tools.find_references import _member_caller_union

    with (
        patch.object(store, "edges_by_target", side_effect=count_by_target),
        patch.object(store, "edges_by_targets", side_effect=count_by_targets),
    ):
        page, total = _member_caller_union(  # type: ignore[misc]
            store, class_q, "Class", cap=10, offset=0
        )
    assert total == 2
    assert len(page) == 2
    assert calls["by_targets"] == 1
    assert calls["by_target"] == 0
    # RESOLVED member caller leads under tier-first IN order.
    assert page[0]["confidence_tier"] == "RESOLVED"
