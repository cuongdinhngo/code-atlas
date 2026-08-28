"""Task 169: an `impact` path seed expanded to every symbol in the file and walked their twins.

Round 11 fired 10-G deliberately: `impact(paths=[…Plan.php])` returned 176 nodes spanning four
subtrees, against 6 correct nodes for the qname seed — a 29x over-report on the one tool whose
answer is acted on destructively. 161 fixed the qname half; the path seed still walked the twin.
"""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import impact as impact_tool
from code_atlas.tools.nav_result import (
    AUTHORITATIVE,
    REASON_SUBJECT_AMBIGUOUS,
    SIBLING_DEFINITIONS,
)
from tests.test_impact import node, seed_file, store  # noqa: F401 — pytest fixtures

SUBJECT_PATH = "src/east/Plan.php"
TWIN_PATH = "src/west/Plan.php"


def config_for(tmp_path: Path):
    return replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")


def plant_twinned_file(store: GraphStore) -> None:  # noqa: F811
    """A file whose symbols each have a same-named twin in another subtree."""
    seed_file(
        store,
        SUBJECT_PATH,
        [
            node("Class", "Plan", "\\East\\Plan", SUBJECT_PATH),
            node("Method", "createPlan", "\\East\\Plan::createPlan", SUBJECT_PATH),
        ],
        [],
    )
    seed_file(
        store,
        TWIN_PATH,
        [
            node("Class", "Plan", "\\West\\Plan", TWIN_PATH),
            node("Method", "createPlan", "\\West\\Plan::createPlan", TWIN_PATH),
        ],
        [],
    )


def plant_lone_file(store: GraphStore) -> None:  # noqa: F811
    seed_file(
        store,
        SUBJECT_PATH,
        [
            node("Class", "Unique", "\\East\\Unique", SUBJECT_PATH),
            node("Method", "only", "\\East\\Unique::only", SUBJECT_PATH),
        ],
        [],
    )


def test_a_twinned_path_seed_is_never_a_confident_walk_of_one(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC1: disclose the twins rather than walk one silently at RESOLVED-looking confidence."""
    plant_twinned_file(store)
    payload = impact_tool.create(config_for(tmp_path))(paths=[SUBJECT_PATH], depth=1)

    assert payload[AUTHORITATIVE] is False
    assert {site["file"] for site in payload[SIBLING_DEFINITIONS]} == {TWIN_PATH}
    assert payload["reason"] == REASON_SUBJECT_AMBIGUOUS, "nothing was left walkable"
    assert payload["results"] == []
    assert payload["seeds_dropped"] == 2, "both twinned seeds are counted, not forgotten"
    # A refusal with no route is the carve-out this repo keeps re-learning about (065/171).
    assert payload["try_instead"] == "file_outline"
    assert "qnames=[...]" in str(payload["try_instead_hint"])


def test_the_payload_names_the_seed_expansion(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC3: one file became N seeds and nothing said so."""
    plant_lone_file(store)
    payload = impact_tool.create(config_for(tmp_path))(paths=[SUBJECT_PATH], depth=0)

    assert payload["seed_expansion"] == {"paths": 1, "seeds": 2}


def test_a_qname_request_does_not_grow_the_expansion_field(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """061: the field belongs to a path request; a qname request is byte-identical."""
    plant_lone_file(store)
    payload = impact_tool.create(config_for(tmp_path))(qnames=["\\East\\Unique"], depth=0)

    assert "seed_expansion" not in payload


def test_an_untwinned_path_seed_still_walks(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC4/061: a file whose symbols have no twins answers exactly as before."""
    plant_lone_file(store)
    payload = impact_tool.create(config_for(tmp_path))(paths=[SUBJECT_PATH], depth=0)

    assert {str(row["qname"]) for row in payload["results"]} == {
        "\\East\\Unique",
        "\\East\\Unique::only",
    }
    assert SIBLING_DEFINITIONS not in payload
    assert AUTHORITATIVE not in payload
    assert payload["seeds_dropped"] == 0


def test_a_qname_seed_is_left_to_161(tmp_path: Path, store: GraphStore) -> None:  # noqa: F811
    """The twin check applies to seeds a PATH expanded into; a named qname was asked for."""
    plant_twinned_file(store)
    payload = impact_tool.create(config_for(tmp_path))(
        qnames=["\\East\\Plan::createPlan"], depth=0
    )

    assert {str(row["qname"]) for row in payload["results"]} == {
        "\\East\\Plan::createPlan"
    }
    assert SIBLING_DEFINITIONS not in payload


def test_a_path_that_resolves_to_nothing_is_still_counted_and_explained(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC2/102: a subject that produced no seed stays distinguishable from a modelled zero."""
    plant_lone_file(store)
    payload = impact_tool.create(config_for(tmp_path))(paths=["src/does/not/exist.php"], depth=0)

    assert payload["seeds_dropped"] == 1
    assert payload["seed_expansion"] == {"paths": 1, "seeds": 0}
    assert payload["results"] == []


def test_the_added_cost_is_one_bounded_query_per_seed(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC5: per seed, never per walked node — measured on a 40-symbol file."""
    rows = [
        node("Method", f"m{index}", f"\\East\\Big::m{index}", "src/east/Big.php")
        for index in range(40)
    ]
    seed_file(store, "src/east/Big.php", rows, [])
    impact = impact_tool.create(config_for(tmp_path))
    impact(paths=["src/east/Big.php"], depth=1)

    started = time.perf_counter()
    for _ in range(20):
        impact(paths=["src/east/Big.php"], depth=1)
    per_call = (time.perf_counter() - started) / 20
    assert per_call < 0.25, f"{per_call * 1000:.1f} ms/call for a 40-seed path"


def test_impact_modules_now_inherits_the_whole_seed_fix(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC6, closed by 179: the rollup inherits the refusal, not only the classification.

    This test used to pin the *gap* and carried the note "if this starts failing, 179 has landed".
    179 landed, so it now pins the inheritance from the other side — the seeds are refused, counted,
    and disclosed, and nothing is rolled up from a twin.
    """
    from code_atlas.tools import impact_modules

    plant_twinned_file(store)
    rollup = impact_modules.create(config_for(tmp_path))(paths=[SUBJECT_PATH], depth=0)

    assert rollup["seeds_dropped"] == 2, "both twinned seeds are accounted for (102)"
    assert SIBLING_DEFINITIONS in rollup, "the refusal is disclosed, not silent"
    assert rollup["symbols_total"] == 0, "nothing was walked, so no module was rolled up"
    assert rollup["reason"] == REASON_SUBJECT_AMBIGUOUS
