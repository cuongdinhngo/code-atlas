"""Task 087: the ``guided_tour`` tool over a fixture graph with a cycle (§12, PHASE3 §4).

Proving path is the tool itself — SCC maths is ``onboarding.tour``; what is unproven until here
is that a caller receives a finite, dependency-respecting stop list that honours the node budget.
The fixture uses the language-neutral ``.aa`` suffix (AC language-agnostic).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import Config
from code_atlas.onboarding.tour import (
    RATIONALE_ENTRY,
    RATIONALE_OUTSIDE,
    ordered_stops,
)
from code_atlas.store import GraphStore
from code_atlas.tools import guided_tour
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
)
from tests.test_nav_tools import db_config, edge, node, seed_file

ROUTES = "routes/web.aa"
A = "app/A.aa"
B = "app/B.aa"
LEAF = "app/Leaf.aa"
ENTRY = "app/Entry.aa"
ISO_X = "iso/X.aa"
ISO_Y = "iso/Y.aa"


def _cycle_repo(tmp_path: Path) -> Config:
    """Entry → A ⇄ B, plus a sink Leaf that A calls (so the budget has something to drop)."""
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            ROUTES,
            [node("Function", "web", "\\web", ROUTES)],
            [
                edge("CALLS", "\\web", "\\App\\A", ROUTES, target_qname="\\App\\A"),
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            A,
            [node("Class", "A", "\\App\\A", A)],
            [
                edge("CALLS", "\\App\\A", "\\App\\B", A, target_qname="\\App\\B"),
                edge("CALLS", "\\App\\A", "\\App\\Leaf", A, target_qname="\\App\\Leaf"),
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            B,
            [node("Class", "B", "\\App\\B", B)],
            [
                edge("CALLS", "\\App\\B", "\\App\\A", B, target_qname="\\App\\A"),
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            LEAF,
            [node("Class", "Leaf", "\\App\\Leaf", LEAF)],
            [],
            root=tmp_path,
        )
    return config


def _files(payload: dict[str, object]) -> list[str]:
    rows = payload["results"]
    assert isinstance(rows, list)
    return [str(row["file"]) for row in rows]


def test_guided_tour_orders_a_cycle_without_looping_and_honours_the_node_budget(
    tmp_path: Path,
) -> None:
    """Proving test: cycle is finite and ordered; max_nodes prunes."""
    config = _cycle_repo(tmp_path)
    tour = guided_tour.create(config)()

    assert tour["indexed"] is True
    assert tour["reason"] == REASON_OK
    files = _files(tour)
    assert files[0] == ROUTES
    assert files.count(A) == 1 and files.count(B) == 1
    assert len(files) == len(set(files))
    # Condensation: the cycle is one SCC, so A and B sit together after the entry.
    cycle = {A, B}
    assert set(files[1:3]) == cycle
    assert files.index(A) < files.index(LEAF)
    assert files.index(B) < files.index(LEAF)
    a_row = next(row for row in tour["results"] if row["file"] == A)
    assert a_row["rationale"].startswith("cycle with ")
    assert a_row["scc"] == [A, B]

    tight = guided_tour.create(replace(config, impact_max_nodes=2))()
    assert tight["truncated"] is True
    assert tight["total_count"] <= 2
    assert len(_files(tight)) <= 2
    assert len(_files(tight)) == len(set(_files(tight)))


def test_guided_tour_is_byte_stable_across_two_runs(tmp_path: Path) -> None:
    config = _cycle_repo(tmp_path)
    first = guided_tour.create(config)()
    second = guided_tour.create(config)()
    assert first == second


def test_guided_tour_minimal_omits_rationale(tmp_path: Path) -> None:
    config = _cycle_repo(tmp_path)
    minimal = guided_tour.create(config)(detail_level="minimal")
    standard = guided_tour.create(config)()
    assert _files(minimal) == _files(standard)
    assert "rationale" not in minimal["results"][0]
    assert "rationale" in standard["results"][0]


def test_guided_tour_unbuilt_is_not_indexed(tmp_path: Path) -> None:
    unbuilt = guided_tour.create(db_config(tmp_path))()
    assert unbuilt["indexed"] is False
    assert unbuilt["reason"] == REASON_NOT_INDEXED
    assert unbuilt["results"] == []
    assert unbuilt["index_root"] == db_config(tmp_path).index_root
    assert not (tmp_path / "graph.db").exists()


def test_guided_tour_empty_index_is_no_matches(tmp_path: Path) -> None:
    config = db_config(tmp_path)
    with GraphStore(config.db_path):
        pass
    empty = guided_tour.create(config)()
    assert empty["indexed"] is True
    assert empty["reason"] == REASON_NO_MATCHES
    assert empty["results"] == []


def _entry_plus_unreachable_cycle(tmp_path: Path) -> Config:
    """An entry point, plus a cycle X ⇄ Y that no zero-inbound file reaches."""
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        seed_file(store, ENTRY, [node("Function", "e", "\\e", ENTRY)], [], root=tmp_path)
        seed_file(
            store,
            ISO_X,
            [node("Class", "X", "\\Iso\\X", ISO_X)],
            [edge("CALLS", "\\Iso\\X", "\\Iso\\Y", ISO_X, target_qname="\\Iso\\Y")],
            root=tmp_path,
        )
        seed_file(
            store,
            ISO_Y,
            [node("Class", "Y", "\\Iso\\Y", ISO_Y)],
            [edge("CALLS", "\\Iso\\Y", "\\Iso\\X", ISO_Y, target_qname="\\Iso\\X")],
            root=tmp_path,
        )
    return config


def test_guided_tour_covers_a_component_no_entry_point_reaches(tmp_path: Path) -> None:
    """A cycle nothing enters is re-seeded, not silently absent with ``truncated: false``."""
    config = _entry_plus_unreachable_cycle(tmp_path)
    tour = guided_tour.create(config)()

    assert _files(tour) == [ENTRY, ISO_X, ISO_Y]
    assert tour["total_count"] == 3
    assert tour["truncated"] is False
    cycle = next(row for row in tour["results"] if row["file"] == ISO_X)
    assert cycle["scc"] == [ISO_X, ISO_Y]
    assert guided_tour.create(config)() == tour


def test_guided_tour_truncates_when_the_budget_leaves_an_indexed_file_out(
    tmp_path: Path,
) -> None:
    """The budget binds before the unreachable cycle: absence is reported, not implied."""
    config = _entry_plus_unreachable_cycle(tmp_path)
    tight = guided_tour.create(replace(config, impact_max_nodes=1))()

    assert _files(tight) == [ENTRY]
    assert tight["truncated"] is True


def test_guided_tour_offset_pages_the_rest_of_the_order(tmp_path: Path) -> None:
    """A page-capped tour is not a dead end — ``offset`` reaches the tail (086 convention)."""
    config = _cycle_repo(tmp_path)
    whole = _files(guided_tour.create(config)())
    paged = guided_tour.create(replace(config, max_results=2))
    first, second = paged(), paged(offset=2)

    assert first["results_offset"] == 0 and first["truncated"] is True
    assert second["results_offset"] == 2 and second["truncated"] is False
    assert _files(first) + _files(second) == whole
    assert paged(offset=99)["results"] == []
    with pytest.raises(ValueError):
        paged(offset=-1)


def test_ordered_stops_walks_a_chain_deeper_than_the_recursion_limit() -> None:
    """A raised ``CA_IMPACT_MAX_NODES`` must not turn a deep chain into a ``RecursionError``."""
    files = [f"f{i:05d}.aa" for i in range(1500)]
    edges = [(files[i], files[i + 1]) for i in range(len(files) - 1)]
    assert [stop.file for stop in ordered_stops(files, edges)] == files


def test_ordered_stops_does_not_claim_entry_point_when_a_predecessor_was_dropped() -> None:
    """Zero *visible* inbound is not zero inbound: only a proven entry point says so."""
    (dropped,) = ordered_stops(["b.aa"], [], entry_points=())
    assert dropped.rationale == RATIONALE_OUTSIDE
    (proven,) = ordered_stops(["b.aa"], [], entry_points=("b.aa",))
    assert proven.rationale == RATIONALE_ENTRY


def test_guided_tour_does_not_call_a_pruned_cycle_member_an_entry_point(
    tmp_path: Path,
) -> None:
    """A one-cycle graph has no entry point; a budget of 1 must not invent one."""
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        pair = ((ISO_X, "\\Iso\\X", "\\Iso\\Y"), (ISO_Y, "\\Iso\\Y", "\\Iso\\X"))
        for path, qname, target in pair:
            seed_file(
                store,
                path,
                [node("Class", path, qname, path)],
                [edge("CALLS", qname, target, path, target_qname=target)],
                root=tmp_path,
            )
    tour = guided_tour.create(replace(config, impact_max_nodes=1))()

    assert _files(tour) == [ISO_X] and tour["truncated"] is True
    assert tour["results"][0]["rationale"] == RATIONALE_OUTSIDE
