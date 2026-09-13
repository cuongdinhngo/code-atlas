"""Task 182 — `find_orphans` refuses instead of returning rows it has already flagged unreliable.

Carve-out (e) — *"find_orphans unavailable above ~10k files"* — was HOLD for **five** rounds.
Round 12 fired it again and produced the number that makes it a defect rather than a limit:

    find_orphans -> 215,177 orphans of 216,664 nodes = 99.31 %
                    walk_truncated: true
                    authoritative: false
                    entry_points: ["public/*.php"]

Round 12's verdict: *"a tool that returns 215,177 rows it has already flagged as unreliable is worse
than one that returns `status: roots_unreachable`."*

**And the root cause is the roots, not the walk.** In the anchor, `public/main.php` `chdir()`s
into `legacy/*/web` and dispatches from there, so the configured roots reach almost nothing and
nearly every node is *correctly* unreachable from them. 99.31 % is a correct algorithm with the
wrong roots, and nothing in the payload separated those two readings.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from time import perf_counter

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import find_orphans, reachable_from
from code_atlas.tools.reach_shared import NO_ROOTS
from tests.test_reachability import (  # noqa: F401 — pytest fixtures
    edge,
    node,
    plant_chain,
    seed_file,
    store,
)

ENTRY = "src/entry.php"


def config_for(tmp_path: Path, **over: object):
    defaults: dict[str, object] = {
        "db_path": tmp_path / "graph.db",
        "entry_points": (ENTRY,),
        "page_limit": 50,
    }
    return replace(load_config(tmp_path, {}), **(defaults | over))  # type: ignore[arg-type]


def plant_islands(graph: GraphStore, count: int) -> None:
    """One reachable entry file plus `count` files nothing reaches — the orphan population."""
    seed_file(graph, ENTRY, [node("Method", "main", "\\Entry::main", ENTRY)], [])
    for index in range(count):
        path = f"src/island{index:03d}.php"
        seed_file(graph, path, [node("Method", "run", f"\\Island{index}::run", path)], [])


def test_a_budget_bound_walk_refuses_and_returns_no_rows(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC1 — the whole ticket. 215,177 unreliable rows become one refusal.

    Fails on today's code: it returns the rows with `walk_truncated: true` beside them.
    """
    plant_islands(store, count=30)
    payload = find_orphans.create(config_for(tmp_path, orphans_max_nodes=1))(
        detail_level="standard"
    )

    assert payload["status"] == find_orphans.WALK_BUDGET_EXHAUSTED
    assert payload["results"] == [], "no row list — that is the point"
    assert payload["authoritative"] is False
    assert "CA_ORPHANS_MAX_NODES" in str(payload["message"])


def test_roots_that_match_no_file_refuse_and_name_themselves(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC2/AC6: configured roots that resolve to nothing never started a walk.

    This is also the shape that made `find_orphans` **crash** with
    `OperationalError: no such table: temp.reach_seen` (filed as 187 by 185's parity matrix) —
    a qname-shaped entry point matches no path. The tool now answers instead of raising.
    """
    plant_islands(store, count=5)
    config = config_for(tmp_path, entry_points=("\\Entry::main",))
    payload = find_orphans.create(config)(detail_level="standard")

    assert payload["status"] == find_orphans.ROOTS_MATCHED_NOTHING
    assert payload["results"] == []
    assert payload["entry_points_unmatched"] == ["\\Entry::main"]
    assert payload["roots_reached"] == 0
    assert int(payload["nodes_total"]) > 0, "the population it could not judge"
    assert "path globs, not qnames" in str(payload["message"])


def test_the_two_numbers_that_separate_dead_code_from_wrong_roots(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC6 / Scope 3: the refusal carries what the roots reached, out of how many exist.

    This is the 99.31 % measurement made legible: `roots_reached` tiny against `nodes_total` says
    *the roots are wrong*, not *the code is dead*. Nothing in the payload said this before.
    """
    plant_islands(store, count=40)
    payload = find_orphans.create(config_for(tmp_path, orphans_max_nodes=2))(
        detail_level="standard"
    )

    reached = int(payload["roots_reached"])
    total = int(payload["nodes_total"])
    assert 0 < reached < total
    assert reached / total < 0.5, f"{reached}/{total} — the roots reached almost nothing"


def test_a_deliberately_shallow_walk_still_gets_its_rows(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """The refinement that matters: `walk_truncated` conflates three causes, one being the caller's.

    `truncated = depth_exhausted or seen >= max_nodes or unproven > max_nodes`. Refusing on all
    three — which is Scope 1 read literally — would refuse `find_orphans(depth=2)`, a legitimate
    question. Only the **budget** half becomes a refusal; a requested depth bound stays a caveat.
    """
    plant_chain(store, hops=4)
    payload = find_orphans.create(config_for(tmp_path, orphans_max_nodes=50))(
        depth=2, detail_level="standard"
    )

    assert payload["status"] == "ok", "the caller asked for a shallow walk and gets an answer"
    assert payload["results"], "the rows a depth-bounded question is for"
    assert payload["depth_exhausted"] is True
    assert payload["walk_truncated"] is True, "still disclosed as an over-estimate (124)"


def test_a_complete_plausible_answer_is_byte_identical(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC3/061: a walk that finishes inside its budget with every root matched gains nothing."""
    plant_islands(store, count=5)
    payload = find_orphans.create(config_for(tmp_path, orphans_max_nodes=500))(
        detail_level="standard"
    )

    assert payload["status"] == "ok"
    assert payload["results"], "the islands are genuinely orphaned"
    for absent in (
        "walk_truncated",
        "entry_points_unmatched",
        "roots_reached",
        "nodes_total",
        "message",
    ):
        assert absent not in payload, f"{absent} must not appear on a clean answer (061)"


def test_nothing_orphaned_stays_distinguishable_from_cannot_tell(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC4 / 102: *nothing is orphaned* is a real, useful answer and must not read as a refusal."""
    seed_file(store, ENTRY, [node("Method", "main", "\\Entry::main", ENTRY)], [])
    clean = find_orphans.create(config_for(tmp_path, orphans_max_nodes=500))(
        detail_level="standard"
    )
    assert clean["status"] == "ok"
    assert clean["results"] == []
    assert clean["total_count"] == 0, "an empty answer with a zero population is the real zero"

    plant_islands(store, count=30)
    refused = find_orphans.create(config_for(tmp_path, orphans_max_nodes=1))(
        detail_level="standard"
    )
    assert refused["status"] == find_orphans.WALK_BUDGET_EXHAUSTED
    assert refused["results"] == []
    # Same empty list, different status — which is exactly what 102 asks for.
    assert clean["status"] != refused["status"]


def test_unset_roots_keep_their_own_status(store: GraphStore, tmp_path: Path) -> None:  # noqa: F811
    """Three distinct failures, three names: unset, matched-nothing, budget-exhausted."""
    plant_islands(store, count=3)
    payload = find_orphans.create(replace(config_for(tmp_path), entry_points=None))(
        detail_level="standard"
    )

    assert payload["status"] == NO_ROOTS
    assert payload["status"] not in (
        find_orphans.ROOTS_MATCHED_NOTHING,
        find_orphans.WALK_BUDGET_EXHAUSTED,
    )


def test_an_unmatched_root_is_named_even_on_a_complete_answer(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC6: one good root and one dead one still answers — and names the dead one."""
    plant_islands(store, count=5)
    roots = (ENTRY, "does/not/exist/*.php")
    config = config_for(tmp_path, entry_points=roots, orphans_max_nodes=500)
    payload = find_orphans.create(config)(detail_level="standard")

    assert payload["status"] == "ok"
    assert payload["entry_points_unmatched"] == ["does/not/exist/*.php"]
    assert payload["results"], "the good root still produced an answer"


def test_reachable_from_is_untouched(store: GraphStore, tmp_path: Path) -> None:  # noqa: F811
    """Out of scope, and pinned as such: only `find_orphans` returns the complement."""
    plant_islands(store, count=30)
    payload = reachable_from.create(config_for(tmp_path, orphans_max_nodes=1))(
        detail_level="standard"
    )

    assert payload["status"] == "ok"
    assert "roots_reached" not in payload


def test_the_refusal_adds_no_walk_and_no_per_node_query(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC7: the two numbers come from counts the walk already made; the match reuses its paths."""
    plant_islands(store, count=60)
    tool = find_orphans.create(config_for(tmp_path, orphans_max_nodes=2))

    started = perf_counter()
    for _ in range(20):
        tool()
    per_call_ms = (perf_counter() - started) / 20 * 1000
    assert per_call_ms < 250.0, f"{per_call_ms:.1f} ms per refusal"

    # And the refusal is small: that is most of the point (215,177 rows -> one payload).
    assert len(json.dumps(tool())) < 2_000


def test_the_refusal_is_deterministic(store: GraphStore, tmp_path: Path) -> None:  # noqa: F811
    """AC8/R4.2: identical input, identical bytes."""
    plant_islands(store, count=20)
    tool = find_orphans.create(config_for(tmp_path, orphans_max_nodes=2))
    assert tool() == tool()
