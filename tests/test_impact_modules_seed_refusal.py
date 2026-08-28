"""Task 179 — `impact_modules` inherits the whole seed decision, not half of it.

169 AC6 required this inheritance to be *"confirmed or filed"*, and filed it: both tools called
`resolve_seeds`, so the rollup got the classification and the `seeds_dropped` accounting — and
neither refusal. 161's shared-**qname** split and 169's shared-**trailing-name** split lived
inside `impact`, so a rollup over a twinned file walked both twins and merged their modules.

**That is worse in the rollup than in `impact`.** `impact` names symbols, so a reader can see
`\\West\\Plan::createPlan` in an answer about `east/`. The rollup names *modules*, so the
twin's module appears in a list with a count — indistinguishable from a real dependency.
"""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path
from time import perf_counter

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import impact as impact_tool
from code_atlas.tools import impact_modules
from code_atlas.tools.nav_result import (
    AUTHORITATIVE,
    REASON_SUBJECT_AMBIGUOUS,
    SIBLING_DEFINITIONS,
)
from tests.test_impact import edge, node, seed_file, store  # noqa: F401 — pytest fixtures

REPO = Path(__file__).resolve().parent.parent
SUBJECT = "src/east/Plan.php"
TWIN = "src/west/Plan.php"
LONE = "src/east/Unique.php"


def config_for(tmp_path: Path):
    return replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")


def plant_twins(graph: GraphStore) -> None:
    """Two subtrees hold the same trailing names — 165's shape, which is the repo's real one."""
    for path, ns in ((SUBJECT, "East"), (TWIN, "West")):
        seed_file(
            graph,
            path,
            [
                node("Class", "Plan", f"\\{ns}\\Plan", path),
                node("Method", "createPlan", f"\\{ns}\\Plan::createPlan", path),
            ],
            [],
        )
    # A dependent in each subtree, so a walk of the twin WOULD roll up a second module.
    for path, ns in (("src/east/Caller.php", "East"), ("src/west/Caller.php", "West")):
        seed_file(
            graph,
            path,
            [node("Method", "run", f"\\{ns}\\Caller::run", path)],
            [edge("CALLS", f"\\{ns}\\Caller::run", f"\\{ns}\\Plan::createPlan", path)],
        )


def plant_lone(graph: GraphStore) -> None:
    seed_file(
        graph,
        LONE,
        [
            node("Class", "Unique", "\\East\\Unique", LONE),
            node("Method", "only", "\\East\\Unique::only", LONE),
        ],
        [],
    )


def test_a_twinned_rollup_does_not_roll_up_the_twins_modules(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC1: the twin's module never enters the answer, and the refusal is named."""
    plant_twins(store)
    rollup = impact_modules.create(config_for(tmp_path))(paths=[SUBJECT], depth=2)

    assert rollup["results"] == [], "nothing walkable, so nothing rolled up"
    assert rollup["modules_total"] == 0
    assert rollup["symbols_total"] == 0
    assert rollup["reason"] == REASON_SUBJECT_AMBIGUOUS
    assert rollup["seeds_dropped"] == 2, "AC2: every refused seed is accounted for (102)"
    assert SIBLING_DEFINITIONS in rollup
    assert rollup[AUTHORITATIVE] is False
    assert rollup["try_instead"] == "file_outline"


def test_the_twin_really_would_have_been_rolled_up(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """The guard's own guard: without the refusal, the fixture reaches BOTH subtrees.

    Asserted by walking the twin's qname directly — if this returns one subtree, the fixture has
    stopped exhibiting the defect and the test above proves nothing (R6.5 / 171-C1).
    """
    plant_twins(store)
    config = config_for(tmp_path)
    east = impact_modules.create(config)(qnames=["\\East\\Plan::createPlan"], depth=2)
    west = impact_modules.create(config)(qnames=["\\West\\Plan::createPlan"], depth=2)
    # A caller in each subtree, reachable from its own twin: two distinct rollups exist to conflate.
    assert east["symbols_total"] > 0 and west["symbols_total"] > 0
    east_modules = {str(row["module"]) for row in east["results"]}  # type: ignore[index]
    west_modules = {str(row["module"]) for row in west["results"]}  # type: ignore[index]
    assert east_modules and west_modules


def test_a_shared_qname_seed_is_refused_too(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """161's half, which `impact_modules` never had at all — not even before 169."""
    for path in ("src/a/Dup.php", "src/b/Dup.php"):
        seed_file(store, path, [node("Class", "Dup", "\\Shared\\Dup", path)], [])
    rollup = impact_modules.create(config_for(tmp_path))(qnames=["\\Shared\\Dup"], depth=1)

    assert rollup["reason"] == REASON_SUBJECT_AMBIGUOUS
    assert rollup["ambiguous_definitions"]
    assert rollup["seeds_dropped"] == 1
    assert rollup["results"] == []


def test_an_untwinned_rollup_is_byte_identical(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC4/061: the common case gains nothing — no caveat, no route, no reason change."""
    plant_lone(store)
    rollup = impact_modules.create(config_for(tmp_path))(paths=[LONE], depth=1)

    assert rollup["reason"] == "ok"
    assert rollup["seeds_dropped"] == 0
    assert rollup["symbols_total"] == 2
    for absent in (SIBLING_DEFINITIONS, "ambiguous_definitions", "try_instead", AUTHORITATIVE):
        assert absent not in rollup, f"{absent} must not appear on an untwinned rollup (061)"


def test_the_rollup_says_how_far_one_path_expanded(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """169's third disclosure, inherited here too: one file became N seeds, and the payload says so.

    Beyond the AC list and recorded as such — leaving it out would have reproduced this ticket's own
    complaint one field over, on the surface where the expansion is hardest to see.
    """
    plant_lone(store)
    rollup = impact_modules.create(config_for(tmp_path))(paths=[LONE], depth=1)
    assert rollup["seed_expansion"] == {"paths": 1, "seeds": 2}

    by_qname = impact_modules.create(config_for(tmp_path))(qnames=["\\East\\Unique"], depth=1)
    assert "seed_expansion" not in by_qname, "a qname caller asked for that qname (061)"


def test_both_tools_agree_on_which_seeds_are_walkable(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC3's behavioural half: one decision means the two tools cannot diverge on it."""
    plant_twins(store)
    config = config_for(tmp_path)
    symbols = impact_tool.create(config)(paths=[SUBJECT], depth=2)
    rollup = impact_modules.create(config)(paths=[SUBJECT], depth=2)

    assert symbols["reason"] == rollup["reason"] == REASON_SUBJECT_AMBIGUOUS
    assert symbols["seeds_dropped"] == rollup["seeds_dropped"]
    assert symbols[SIBLING_DEFINITIONS] == rollup[SIBLING_DEFINITIONS]
    assert symbols["try_instead"] == rollup["try_instead"]


def test_the_splits_have_one_definition_site() -> None:
    """AC3 (R6.7/R1.8): derived by grep — a copy would pass every payload test in this file."""
    for symbol in ("def _split_ambiguous", "def _split_twinned", "def plan_seeds",
                   "def attach_seed_refusals"):
        found = subprocess.run(
            ["grep", "-rl", symbol, "code_atlas/"],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout.split()
        assert found == ["code_atlas/tools/impact.py"], f"{symbol}: {found}"
    callers = subprocess.run(
        ["grep", "-rl", "plan_seeds(", "code_atlas/tools/"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert sorted(callers) == [
        "code_atlas/tools/impact.py",
        "code_atlas/tools/impact_modules.py",
    ]


def test_the_refusal_adds_no_per_rolled_up_node_query(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC5 / 140's budget: the split costs one bounded query per SEED, never per rolled-up row."""
    for index in range(40):
        path = f"src/east/File{index}.php"
        rows = [node("Method", f"m{index}", f"\\East\\C{index}::m{index}", path)]
        seed_file(store, path, rows, [])
    config = config_for(tmp_path)
    tool = impact_modules.create(config)

    started = perf_counter()
    for _ in range(20):
        tool(paths=["src/east/File0.php"], depth=1)
    per_call_ms = (perf_counter() - started) / 20 * 1000
    assert per_call_ms < 250.0, f"{per_call_ms:.1f} ms/call"


def test_the_decision_is_deterministic(tmp_path: Path, store: GraphStore) -> None:  # noqa: F811
    """AC5 (R4.2): identical input, identical bytes."""
    plant_twins(store)
    tool = impact_modules.create(config_for(tmp_path))
    assert tool(paths=[SUBJECT], depth=2) == tool(paths=[SUBJECT], depth=2)
