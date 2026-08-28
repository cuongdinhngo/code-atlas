"""Task 168: `find_references` gets 165's twin disclosure — the tool 7-A was filed against.

165 shipped `sibling_definitions` + `authoritative: false` on `find_callers`, and round 11 measured
the *other* tool: 16 hits, 4 in `src/`, `reason: "ok"`, no `authoritative` field at all, against 19
real sites — a 4.7x under-report at a confident `ok`. Two tools answer the same twin-shaped
question; one disclosed the partition and one presented it as whole.
"""

from __future__ import annotations

from pathlib import Path

from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references
from code_atlas.tools.nav_result import (
    AUTHORITATIVE,
    AUTHORITATIVE_CAVEATS,
    CAVEAT_ALL_HITS_DYNAMIC,
    CAVEAT_SIBLING_DEFINITIONS,
    SIBLING_DEFINITIONS,
)
from tests.test_nav_tools import (  # noqa: F401 — pytest fixtures
    db_config,
    edge,
    node,
    seed_file,
    store,
)


def twin_repo(store: GraphStore, root: Path, *, tier: str = "RESOLVED") -> None:  # noqa: F811
    """Two same-named classes in different subtrees, one reference to each."""
    seed_file(
        store,
        "src/east/Plan.php",
        [node("Class", "Plan", "\\East\\Plan", "src/east/Plan.php")],
        [],
        root=root,
    )
    seed_file(
        store,
        "src/west/Plan.php",
        [node("Class", "Plan", "\\West\\Plan", "src/west/Plan.php")],
        [],
        root=root,
    )
    seed_file(
        store,
        "src/east/UsesEast.php",
        [node("Class", "UsesEast", "\\East\\UsesEast", "src/east/UsesEast.php")],
        [
            edge(
                "NEW",
                "\\East\\UsesEast",
                "Plan",
                "src/east/UsesEast.php",
                target_qname="\\East\\Plan",
                tier=tier,
            )
        ],
        root=root,
    )
    seed_file(
        store,
        "src/west/UsesWest.php",
        [node("Class", "UsesWest", "\\West\\UsesWest", "src/west/UsesWest.php")],
        [
            edge(
                "NEW",
                "\\West\\UsesWest",
                "Plan",
                "src/west/UsesWest.php",
                target_qname="\\West\\Plan",
                tier=tier,
            )
        ],
        root=root,
    )


def lone_repo(store: GraphStore, root: Path) -> None:  # noqa: F811
    """One class, one reference — the subject 165 called clean."""
    seed_file(
        store,
        "src/Only.php",
        [node("Class", "Only", "\\App\\Only", "src/Only.php")],
        [],
        root=root,
    )
    seed_file(
        store,
        "src/UsesOnly.php",
        [node("Class", "UsesOnly", "\\App\\UsesOnly", "src/UsesOnly.php")],
        [
            edge(
                "NEW",
                "\\App\\UsesOnly",
                "Only",
                "src/UsesOnly.php",
                target_qname="\\App\\Only",
            )
        ],
        root=root,
    )


def test_a_twin_partitioned_answer_discloses_the_sibling_and_is_not_authoritative(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC1: the 4.7x under-report now says it is a partition, and names where the rest is."""
    twin_repo(store, tmp_path)
    result = find_references.create(db_config(tmp_path))("\\East\\Plan")

    assert result["total_count"] == 1, "one reference binds to this qname"
    assert result[AUTHORITATIVE] is False
    assert result[AUTHORITATIVE_CAVEATS] == [CAVEAT_SIBLING_DEFINITIONS]
    assert result[SIBLING_DEFINITIONS] == [
        {"file": "src/west/Plan.php", "line": 1, "kind": "Class"}
    ]


def test_a_unique_trailing_name_is_byte_identical(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC2/061: no twin, no new field — the clean subject pays nothing."""
    lone_repo(store, tmp_path)
    result = find_references.create(db_config(tmp_path))("\\App\\Only")

    assert result["total_count"] == 1
    assert SIBLING_DEFINITIONS not in result
    assert AUTHORITATIVE not in result
    assert AUTHORITATIVE_CAVEATS not in result


def test_the_two_caveats_are_distinguishable(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC3: `authoritative: false` alone cannot say whether to widen or to distrust the tier."""
    twin_repo(store, tmp_path, tier="DYNAMIC")
    both = find_references.create(db_config(tmp_path))("\\East\\Plan")

    assert both[AUTHORITATIVE] is False
    assert both[AUTHORITATIVE_CAVEATS] == [
        CAVEAT_ALL_HITS_DYNAMIC,
        CAVEAT_SIBLING_DEFINITIONS,
    ], "both reasons fired and both are named"


def test_a_dynamic_only_answer_names_only_the_tier_caveat(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC3, the other side: a lone subject whose hits are all DYNAMIC is not twin-partitioned."""
    seed_file(
        store,
        "src/Only.php",
        [node("Class", "Only", "\\App\\Only", "src/Only.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "src/UsesOnly.php",
        [node("Class", "UsesOnly", "\\App\\UsesOnly", "src/UsesOnly.php")],
        [
            edge(
                "NEW",
                "\\App\\UsesOnly",
                "Only",
                "src/UsesOnly.php",
                target_qname="\\App\\Only",
                tier="DYNAMIC",
            )
        ],
        root=tmp_path,
    )
    result = find_references.create(db_config(tmp_path))("\\App\\Only")

    assert result[AUTHORITATIVE_CAVEATS] == [CAVEAT_ALL_HITS_DYNAMIC]
    assert SIBLING_DEFINITIONS not in result


def test_ambiguous_definitions_and_sibling_definitions_stay_distinct(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC4: exact-qname duplicates and other-qname twins are different facts, both reportable."""
    twin_repo(store, tmp_path)
    # A second definition of the SAME qname, in another file — 070's ambiguity, not 168's.
    seed_file(
        store,
        "src/east/PlanAgain.php",
        [node("Class", "Plan", "\\East\\Plan", "src/east/PlanAgain.php")],
        [],
        root=tmp_path,
    )
    result = find_references.create(db_config(tmp_path))("\\East\\Plan")

    assert len(result["ambiguous_definitions"]) == 2, "both sites of the same qname"
    assert result[SIBLING_DEFINITIONS] == [
        {"file": "src/west/Plan.php", "line": 1, "kind": "Class"}
    ], "the twin under another qname is separate"


def test_both_tools_now_answer_the_twin_question_the_same_way(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """The asymmetry 7-A named: one tool disclosed the partition, the other did not."""
    seed_file(
        store,
        "src/east/Svc.php",
        [
            node("Class", "Svc", "\\East\\Svc", "src/east/Svc.php"),
            node("Method", "run", "\\East\\Svc::run", "src/east/Svc.php"),
        ],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "src/west/Svc.php",
        [
            node("Class", "Svc", "\\West\\Svc", "src/west/Svc.php"),
            node("Method", "run", "\\West\\Svc::run", "src/west/Svc.php"),
        ],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "src/east/Caller.php",
        [node("Class", "Caller", "\\East\\Caller", "src/east/Caller.php")],
        [
            edge(
                "CALLS",
                "\\East\\Caller",
                "run",
                "src/east/Caller.php",
                target_qname="\\East\\Svc::run",
            )
        ],
        root=tmp_path,
    )
    config = db_config(tmp_path)
    callers = find_callers.create(config)("\\East\\Svc::run")
    references = find_references.create(config)("\\East\\Svc")

    for payload in (callers, references):
        assert payload[AUTHORITATIVE] is False
        assert payload[AUTHORITATIVE_CAVEATS] == [CAVEAT_SIBLING_DEFINITIONS]
        assert payload[SIBLING_DEFINITIONS]
