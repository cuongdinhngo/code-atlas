"""Task 017: impact engine — SQL best-score blast radius (§12 / M6)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.store import IMPACT_DECAY, IMPACT_FLOOR, IMPACT_WEIGHTS, GraphStore
from code_atlas.tools import impact as impact_tool
from code_atlas.tools.nav_result import (
    REASON_NAME_NOT_QUALIFIED,
    REASON_NO_SUCH_SYMBOL,
    TRY_INSTEAD_SEARCH_SYMBOL,
)

# Hand-traced scores (A1): seed 1.0; CALLS weight 1.0; EXTENDS 0.9; decay ×0.7.
SEED = "\\Changed"
CALLER = "\\Caller"
NEW_CALLER = "\\NewCaller"
CHILD = "\\Child"
IMPL = "\\Impl"
INCLUDER = "\\Includer"
GRAND = "\\GrandCaller"
HEURISTIC = "\\HeuristicCaller"
DYNAMIC = "\\DynamicCaller"
CONTAINER = "\\FileContainer"

SCORE_CALLER = 1.0 * IMPACT_WEIGHTS["CALLS"] * IMPACT_DECAY  # 0.7
SCORE_NEW = 1.0 * IMPACT_WEIGHTS["NEW"] * IMPACT_DECAY  # 0.7
SCORE_CHILD = 1.0 * IMPACT_WEIGHTS["EXTENDS"] * IMPACT_DECAY  # 0.63
SCORE_IMPL = 1.0 * IMPACT_WEIGHTS["IMPLEMENTS"] * IMPACT_DECAY  # 0.63
SCORE_INCLUDER = 1.0 * IMPACT_WEIGHTS["INCLUDES"] * IMPACT_DECAY  # 0.56
SCORE_GRAND = SCORE_CALLER * IMPACT_WEIGHTS["CALLS"] * IMPACT_DECAY  # 0.49


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def seed_file(store: GraphStore, path: str, nodes: list[dict], edges: list[dict]) -> None:
    store.upsert_file(path, "h", "lang")
    store.replace_file_rows(path, nodes, edges)


def node(kind: str, name: str, qname: str, path: str, *, line: int = 1) -> dict[str, object]:
    return {
        "kind": kind,
        "name": name,
        "qualified_name": qname,
        "file_path": path,
        "line_start": line,
    }


def edge(
    kind: str,
    source: str,
    target: str,
    path: str,
    *,
    tier: str = "RESOLVED",
    line: int = 1,
) -> dict[str, object]:
    return {
        "kind": kind,
        "source_qname": source,
        "target_raw": target,
        "target_qname": target,
        "file_path": path,
        "line": line,
        "confidence_tier": tier,
    }


def plant_graph(store: GraphStore) -> None:
    """Tiny graph whose blast radius is hand-traced in the proving test."""
    path = "a.php"
    seed_file(
        store,
        path,
        [
            node("Class", "Changed", SEED, path, line=10),
            node("Class", "Caller", CALLER, path, line=20),
            node("Class", "NewCaller", NEW_CALLER, path, line=25),
            node("Class", "Child", CHILD, path, line=30),
            node("Class", "Impl", IMPL, path, line=35),
            node("File", "Includer", INCLUDER, path, line=36),
            node("Class", "GrandCaller", GRAND, path, line=40),
            node("Class", "HeuristicCaller", HEURISTIC, path, line=50),
            node("Class", "DynamicCaller", DYNAMIC, path, line=60),
            node("File", "a.php", CONTAINER, path, line=1),
        ],
        [
            edge("CALLS", CALLER, SEED, path, line=21),
            edge("NEW", NEW_CALLER, SEED, path, line=26),
            edge("EXTENDS", CHILD, SEED, path, line=31),
            edge("IMPLEMENTS", IMPL, SEED, path, line=35),
            edge("INCLUDES", INCLUDER, SEED, path, line=36),
            edge("CALLS", GRAND, CALLER, path, line=41),
            edge("CALLS", HEURISTIC, SEED, path, tier="HEURISTIC", line=51),
            edge("CALLS", DYNAMIC, SEED, path, tier="DYNAMIC", line=61),
            edge("CONTAINS", CONTAINER, SEED, path, line=1),
        ],
    )


def test_impact_matches_hand_traced_planted_graph(store: GraphStore) -> None:
    """AC2 / proving test: planted set+scores match the A1 hand trace."""
    plant_graph(store)
    outcome = store.impact_radius([SEED], depth=2, max_nodes=50)
    rows = outcome.rows
    by_qname = {str(r["qname"]): r for r in rows}

    assert set(by_qname) == {
        SEED,
        CALLER,
        NEW_CALLER,
        CHILD,
        IMPL,
        INCLUDER,
        GRAND,
        HEURISTIC,
        DYNAMIC,
    }
    assert by_qname[SEED]["score"] == pytest.approx(1.0)
    assert by_qname[SEED]["depth"] == 0
    assert by_qname[SEED]["confidence_tier"] == "RESOLVED"
    assert by_qname[CALLER]["score"] == pytest.approx(SCORE_CALLER)
    assert by_qname[NEW_CALLER]["score"] == pytest.approx(SCORE_NEW)
    assert by_qname[CHILD]["score"] == pytest.approx(SCORE_CHILD)
    assert by_qname[IMPL]["score"] == pytest.approx(SCORE_IMPL)
    assert by_qname[INCLUDER]["score"] == pytest.approx(SCORE_INCLUDER)
    assert by_qname[GRAND]["score"] == pytest.approx(SCORE_GRAND)
    assert by_qname[GRAND]["depth"] == 2
    assert by_qname[HEURISTIC]["confidence_tier"] == "HEURISTIC"
    assert by_qname[DYNAMIC]["confidence_tier"] == "DYNAMIC"
    assert CONTAINER not in by_qname
    assert outcome.frontier_skipped_non_resolved == 2

    ordered = [str(r["qname"]) for r in rows]
    assert ordered == [
        SEED,
        CALLER,
        DYNAMIC,
        HEURISTIC,
        NEW_CALLER,
        CHILD,
        IMPL,
        INCLUDER,
        GRAND,
    ]


def test_depth_cap_excludes_second_hop(store: GraphStore) -> None:
    plant_graph(store)
    rows = store.impact_radius([SEED], depth=1, max_nodes=50).rows
    assert {str(r["qname"]) for r in rows} == {
        SEED,
        CALLER,
        NEW_CALLER,
        CHILD,
        IMPL,
        INCLUDER,
        HEURISTIC,
        DYNAMIC,
    }


def test_max_nodes_keeps_highest_scores(store: GraphStore) -> None:
    plant_graph(store)
    rows = store.impact_radius([SEED], depth=2, max_nodes=2).rows
    assert [str(r["qname"]) for r in rows] == [SEED, CALLER]


def test_heuristic_is_returned_but_does_not_expand_frontier(store: GraphStore) -> None:
    path = "h.php"
    mid = "\\Mid"
    leaf = "\\Leaf"
    seed_file(
        store,
        path,
        [
            node("Class", "Changed", SEED, path),
            node("Class", "Mid", mid, path),
            node("Class", "Leaf", leaf, path),
        ],
        [
            edge("CALLS", mid, SEED, path, tier="HEURISTIC"),
            edge("CALLS", leaf, mid, path),
        ],
    )
    outcome = store.impact_radius([SEED], depth=2, max_nodes=50)
    by_qname = {str(r["qname"]): r for r in outcome.rows}
    assert set(by_qname) == {SEED, mid}
    assert by_qname[mid]["confidence_tier"] == "HEURISTIC"
    assert leaf not in by_qname
    assert outcome.frontier_skipped_non_resolved == 1


def test_floor_drops_weak_hops(store: GraphStore) -> None:
    assert IMPACT_FLOOR == 0.05
    path = "f.php"
    # 0.7**8 ≈ 0.0576 (kept); 0.7**9 ≈ 0.0403 (below floor).
    names = [f"\\N{i}" for i in range(10)]
    nodes = [node("Class", f"N{i}", names[i], path) for i in range(10)]
    edges = [edge("CALLS", names[i + 1], names[i], path) for i in range(9)]
    seed_file(store, path, nodes, edges)
    rows = store.impact_radius([names[0]], depth=20, max_nodes=50).rows
    qnames = {str(r["qname"]) for r in rows}
    assert names[8] in qnames
    assert names[9] not in qnames
    assert all(float(r["score"]) >= IMPACT_FLOOR for r in rows)


def test_path_seeds_union_all_file_nodes(tmp_path: Path, store: GraphStore) -> None:
    plant_graph(store)
    config = replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")
    payload = impact_tool.create(config)(paths=["a.php"], depth=0)
    qnames = {str(r["qname"]) for r in payload["results"]}
    assert SEED in qnames and CALLER in qnames
    assert payload["indexed"] is True


def test_paths_and_qnames_union(tmp_path: Path, store: GraphStore) -> None:
    path_a = "a.php"
    path_b = "b.php"
    extra = "\\Extra"
    seed_file(
        store,
        path_a,
        [node("Class", "Changed", SEED, path_a)],
        [],
    )
    seed_file(
        store,
        path_b,
        [node("Class", "Extra", extra, path_b)],
        [],
    )
    config = replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")
    payload = impact_tool.create(config)(paths=[path_a], qnames=[extra], depth=0)
    assert {str(r["qname"]) for r in payload["results"]} == {SEED, extra}


def test_unknown_seed_is_empty_success(tmp_path: Path) -> None:
    config = replace(load_config(tmp_path, {}), db_path=tmp_path / "missing.db")
    payload = impact_tool.create(config)(qnames=["\\Nope"])
    assert payload["indexed"] is False
    assert payload["results"] == []


def test_missing_qname_with_db_is_empty_success(store: GraphStore, tmp_path: Path) -> None:
    plant_graph(store)
    config = replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")
    payload = impact_tool.create(config)(qnames=["\\Missing"], depth=0)
    assert payload["indexed"] is True
    assert payload["results"] == []


def test_exact_max_nodes_fill_is_not_truncated(store: GraphStore, tmp_path: Path) -> None:
    plant_graph(store)
    config = replace(
        load_config(tmp_path, {}),
        db_path=tmp_path / "graph.db",
        impact_max_nodes=1,
    )
    payload = impact_tool.create(config)(qnames=[SEED], depth=0)
    assert len(payload["results"]) == 1
    assert payload["truncated"] is False


def test_seed_overflow_keeps_seeds_over_discovered(store: GraphStore) -> None:
    path = "s.php"
    seeds = ["\\S", "\\A", "\\B"]
    disc = "\\Disc"
    seed_file(
        store,
        path,
        [
            node("Class", "S", seeds[0], path),
            node("Class", "A", seeds[1], path),
            node("Class", "B", seeds[2], path),
            node("Class", "Disc", disc, path),
        ],
        [edge("CALLS", disc, seeds[0], path)],
    )
    outcome = store.impact_radius(seeds, depth=1, max_nodes=2)
    qnames = [str(r["qname"]) for r in outcome.rows]
    # Seeds outrank discovered; among seeds, qname ASC keeps \\A and \\B, drops \\S.
    assert qnames == ["\\A", "\\B"]
    assert disc not in qnames
    assert outcome.seeds_dropped == 1


def test_cycles_converge_to_best_score(store: GraphStore) -> None:
    path = "c.php"
    a, b = "\\A", "\\B"
    seed_file(
        store,
        path,
        [node("Class", "A", a, path), node("Class", "B", b, path)],
        [
            edge("CALLS", b, a, path),
            edge("CALLS", a, b, path),
        ],
    )
    outcome = store.impact_radius([a], depth=5, max_nodes=50)
    by_qname = {str(r["qname"]): r for r in outcome.rows}
    assert set(by_qname) == {a, b}
    assert by_qname[a]["score"] == pytest.approx(1.0)
    assert by_qname[b]["score"] == pytest.approx(SCORE_CALLER)
    assert by_qname[b]["depth"] == 1


def test_best_score_wins_across_multiple_paths(store: GraphStore) -> None:
    """A shorter strong path must beat a longer weak path to the same node."""
    path = "m.php"
    seed, mid, target = "\\Seed", "\\Mid", "\\Target"
    seed_file(
        store,
        path,
        [
            node("Class", "Seed", seed, path),
            node("Class", "Mid", mid, path),
            node("Class", "Target", target, path),
        ],
        [
            # Direct CALLS: score 0.7 at depth 1
            edge("CALLS", target, seed, path),
            # Longer path Seed ← Mid ← Target via INCLUDES then CALLS would be weaker,
            # but Target→Seed direct already wins. Plant Mid→Seed and Target→Mid so a
            # depth-2 path also reaches Target; best must stay the direct 0.7 / depth 1.
            edge("CALLS", mid, seed, path),
            edge("CALLS", target, mid, path),
        ],
    )
    outcome = store.impact_radius([seed], depth=3, max_nodes=50)
    by_qname = {str(r["qname"]): r for r in outcome.rows}
    assert by_qname[target]["score"] == pytest.approx(SCORE_CALLER)
    assert by_qname[target]["depth"] == 1


# --- 102: an absent subject is a dropped seed, never a modelled zero -------------------------

ABSENT = "\\App\\Nope"


def configured(tmp_path: Path, **overrides: object) -> Config:
    return replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db", **overrides)


def test_absent_subject_and_modelled_zero_differ_on_seeds_dropped(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC1/AC2 (proving test) — the one number that tells a failed query from a modelled zero.

    Before task 102 both answers reported ``seeds_dropped: 0``, so the strongest claim this tool
    makes was indistinguishable from its weakest. They must now differ on the same fixture.
    """
    plant_graph(store)
    tool = impact_tool.create(configured(tmp_path))

    absent = tool(qnames=[ABSENT], depth=1)
    modelled_zero = tool(qnames=[GRAND], depth=1)

    assert absent["results"] == []
    assert absent["seeds_dropped"] == 1
    assert absent["reason"] == REASON_NO_SUCH_SYMBOL
    assert [str(r["qname"]) for r in modelled_zero["results"]] == [GRAND]
    assert modelled_zero["seeds_dropped"] == 0
    # The common answer is untouched: no reason, no new key (061).
    assert "reason" not in modelled_zero
    assert absent["seeds_dropped"] != modelled_zero["seeds_dropped"]


def test_partial_loss_counts_the_seed_that_was_lost(
    store: GraphStore, tmp_path: Path
) -> None:
    """AC3 — one subject resolves and one does not, in both subject shapes."""
    plant_graph(store)
    tool = impact_tool.create(configured(tmp_path))

    by_qname = tool(qnames=[SEED, ABSENT], depth=1)
    by_path = tool(paths=["a.php", "no/such/file.php"], depth=0)

    assert by_qname["results"] and by_qname["seeds_dropped"] == 1
    assert by_path["results"] and by_path["seeds_dropped"] == 1
    # A partial answer still answers, so it keeps the common shape.
    assert "reason" not in by_qname and "reason" not in by_path


def test_a_path_subject_that_resolves_uniquely_is_a_seed_not_a_drop(
    store: GraphStore, tmp_path: Path
) -> None:
    """Review finding 1 — both subject slots treat a resolvable subject the same way.

    ``classify_missing_subject`` re-points an under-anchored subject (075/076), and it is reached
    from the ``paths`` slot too. Counting what it resolved as *lost* would re-create, inside this
    fix, the very defect the fix removes.
    """
    plant_graph(store)
    tool = impact_tool.create(configured(tmp_path))

    by_path = tool(paths=["Changed"], depth=1)
    by_qname = tool(qnames=["Changed"], depth=1)

    assert by_path["seeds_dropped"] == 0
    assert "reason" not in by_path
    assert SEED in {str(r["qname"]) for r in by_path["results"]}
    # The same subject, whichever argument carried it.
    assert by_path["results"] == by_qname["results"]


def test_budget_pruned_and_lost_seeds_are_summed(store: GraphStore, tmp_path: Path) -> None:
    """R1 — the tool's lost-subject count is ADDED to the store's budget-prune count."""
    plant_graph(store)
    tool = impact_tool.create(configured(tmp_path, impact_max_nodes=1))

    payload = tool(qnames=[SEED, CALLER, CHILD, ABSENT], depth=0)

    # 3 resolved seeds against a store budget of 2 prunes one; the 4th never resolved.
    assert payload["seeds_dropped"] == 2


def test_two_lost_subjects_carry_only_the_class_the_payload_can_prove(
    store: GraphStore, tmp_path: Path
) -> None:
    """A merged radius has no per-subject reason channel, so it states the base class only."""
    plant_graph(store)
    tool = impact_tool.create(configured(tmp_path))

    payload = tool(qnames=[ABSENT, "\\App\\AlsoNope"], depth=1)

    assert payload["seeds_dropped"] == 2
    assert payload["reason"] == REASON_NO_SUCH_SYMBOL
    assert "candidate_count" not in payload


def test_an_under_qualified_lost_subject_names_its_candidates(
    store: GraphStore, tmp_path: Path
) -> None:
    """W1/R2 — the empty answer routes the reader out, reusing 075/076's classification."""
    path = "u.php"
    seed_file(
        store,
        path,
        [
            node("Method", "isEnabled", "\\A::isEnabled", path),
            node("Method", "isEnabled", "\\B::isEnabled", path),
        ],
        [],
    )
    payload = impact_tool.create(configured(tmp_path))(qnames=["isEnabled"], depth=1)

    assert payload["results"] == []
    assert payload["seeds_dropped"] == 1
    assert payload["reason"] == REASON_NAME_NOT_QUALIFIED
    assert payload["candidate_count"] == 2
    assert payload["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL
