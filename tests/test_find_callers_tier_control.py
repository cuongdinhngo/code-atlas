"""Task 251 — ``find_callers`` tier predicate + census, so RESOLVED is not off-page by alphabet.

Proving shape: a common method name whose one RESOLVED caller sorts after enough HEURISTIC
noise that page 1 of the unfiltered answer never contains it. The tier filter recovers it in
one call; the unfiltered page carries ``tier_census`` so the reader can tell "none on this
page" from "none exist".
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from code_atlas.tools.nav_result import (
    CAVEAT_CROSS_LANGUAGE_UNMODELLED,
    CAVEAT_LIMIT_CROSS_LANGUAGE,
    CAVEAT_LIMITS_KEY,
)
from tests.test_find_callers_cross_language_unmodelled import _cross_language_repo
from tests.test_nav_tools import db_config, edge, node, seed_file

SUBJECT = "\\App\\Model::build"
SUBJECT_FILE = "app/Model.php"
RESOLVED_CALLER = "\\App\\ZeeLast::run"
HEURISTIC_PREFIX = "\\App\\AaaNoise"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def _plant_buried_resolved(store: GraphStore, root: Path, *, noise: int) -> None:
    """``noise`` HEURISTIC callers that sort before the one RESOLVED caller."""
    nodes = [
        node("Method", "build", SUBJECT, SUBJECT_FILE),
        node("Method", "run", f"{RESOLVED_CALLER}", "app/ZeeLast.php"),
    ]
    edges = [
        edge(
            "CALLS",
            RESOLVED_CALLER,
            "build",
            "app/ZeeLast.php",
            target_qname=SUBJECT,
            tier="RESOLVED",
        )
    ]
    for i in range(noise):
        qname = f"{HEURISTIC_PREFIX}{i:02d}::build"
        nodes.append(node("Method", "build", qname, f"legacy/noise{i:02d}.php"))
        edges.append(
            edge(
                "CALLS",
                qname,
                "build",
                f"legacy/noise{i:02d}.php",
                target_qname=SUBJECT,
                tier="HEURISTIC",
            )
        )
    seed_file(store, SUBJECT_FILE, nodes[:1], [], root=root)
    seed_file(
        store,
        "app/ZeeLast.php",
        [nodes[1]],
        [edges[0]],
        root=root,
    )
    for i in range(noise):
        seed_file(
            store,
            f"legacy/noise{i:02d}.php",
            [nodes[2 + i]],
            [edges[1 + i]],
            root=root,
        )


def test_resolved_caller_off_page_one_recovered_by_tier_filter(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC1 (proving): RESOLVED caller absent from unfiltered page 1; present under tier filter."""
    _plant_buried_resolved(store, tmp_path, noise=5)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=3)
    tool = find_callers.create(config)

    page = tool(SUBJECT, detail_level="minimal", limit=3, offset=0)
    assert page["total_count"] == 6
    assert page["truncated"] is True
    page_qnames = [str(hit["qname"]) for hit in page["results"]]
    assert RESOLVED_CALLER not in page_qnames
    assert all(hit["confidence_tier"] == "HEURISTIC" for hit in page["results"])

    filtered = tool(
        SUBJECT, detail_level="minimal", limit=3, offset=0, confidence_tier="RESOLVED"
    )
    assert filtered["total_count"] == 1
    assert filtered["tier_filter"] == "RESOLVED"
    assert [str(hit["qname"]) for hit in filtered["results"]] == [RESOLVED_CALLER]
    assert filtered["results"][0]["confidence_tier"] == "RESOLVED"


def test_tier_filter_names_itself_and_counts_matches(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC2: total_count under a tier request counts that request; payload names the filter."""
    _plant_buried_resolved(store, tmp_path, noise=4)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=50)
    tool = find_callers.create(config)
    filtered = tool(SUBJECT, detail_level="minimal", confidence_tier="RESOLVED")
    assert filtered["tier_filter"] == "RESOLVED"
    assert filtered["total_count"] == 1
    unfiltered = tool(SUBJECT, detail_level="minimal")
    assert "tier_filter" not in unfiltered
    assert unfiltered["total_count"] == 5


def test_unfiltered_tier_census_distinguishes_absent_from_off_page(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC3: unfiltered page carries tier_census so off-page RESOLVED is visible without paging."""
    _plant_buried_resolved(store, tmp_path, noise=5)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=3)
    tool = find_callers.create(config)
    page = tool(SUBJECT, detail_level="minimal", limit=3)
    assert RESOLVED_CALLER not in [str(hit["qname"]) for hit in page["results"]]
    assert page["tier_census"] == {"HEURISTIC": 5, "RESOLVED": 1}


def test_all_resolved_omits_tier_census(store: GraphStore, tmp_path: Path) -> None:
    """061: census on an all-RESOLVED answer adds nothing and is not emitted."""
    nodes = [
        node("Method", "build", SUBJECT, SUBJECT_FILE),
        node("Method", "run", RESOLVED_CALLER, "app/ZeeLast.php"),
    ]
    edges = [
        edge(
            "CALLS",
            RESOLVED_CALLER,
            "build",
            "app/ZeeLast.php",
            target_qname=SUBJECT,
            tier="RESOLVED",
        )
    ]
    seed_file(store, SUBJECT_FILE, nodes[:1], [], root=tmp_path)
    seed_file(store, "app/ZeeLast.php", [nodes[1]], edges, root=tmp_path)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=50)
    payload = find_callers.create(config)(SUBJECT, detail_level="minimal")
    assert "tier_census" not in payload
    assert "tier_filter" not in payload


def test_cross_language_caveat_states_reader_limit(tmp_path: Path) -> None:
    """AC4: cross_language caveat carries caveat_limits with the operational cost."""
    config = _cross_language_repo(tmp_path, tmp_path / "graph.db", link_the_crossing=False)
    payload = find_callers.create(config)(
        "dbo.getUnplannedChange", detail_level="minimal"
    )
    assert payload["authoritative_caveats"] == [CAVEAT_CROSS_LANGUAGE_UNMODELLED]
    assert payload[CAVEAT_LIMITS_KEY] == {
        CAVEAT_CROSS_LANGUAGE_UNMODELLED: CAVEAT_LIMIT_CROSS_LANGUAGE
    }


def test_tier_control_off_is_byte_identical(store: GraphStore, tmp_path: Path) -> None:
    """AC5: omitting the tier control matches an explicit None (022 AC3 shape)."""
    _plant_buried_resolved(store, tmp_path, noise=2)
    config = replace(db_config(tmp_path), root=tmp_path, max_results=50)
    tool = find_callers.create(config)
    first = tool(SUBJECT, detail_level="minimal")
    second = tool(SUBJECT, detail_level="minimal")
    assert first == second
    assert tool(SUBJECT, detail_level="minimal", confidence_tier=None) == first
