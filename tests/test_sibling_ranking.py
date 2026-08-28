"""Task 171: a caveat that fires on 83% of calls must say which site to open first.

165's disclosure made a mandated cross-check survivable but could not retire it as a policy: nine
files with equal weight, one of which was the one the evaluator needed. Ranking is the difference
between a signal and a standing instruction.
"""

from __future__ import annotations

import time
from pathlib import Path

from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references
from code_atlas.tools.nav_result import (
    RANK_PATH,
    RANK_SHARED_SUBTREE,
    SIBLING_DEFINITIONS,
    SIBLING_RANKED_BY,
    rank_sibling_sites,
)
from tests.test_nav_tools import (  # noqa: F401 — pytest fixtures
    db_config,
    edge,
    node,
    seed_file,
    store,
)

# The subject lives in src/app/east/core; the twins sit at decreasing shared depth. The names are
# chosen so nearest-first is NOT the store's lexicographic order — otherwise the test could not tell
# ranking from no ranking at all.
SUBJECT = "src/app/east/core/Plan.php"
TWINS = (
    "src/app/east/core/zz_legacy/Plan.php",  # 4 shared components — nearest
    "src/app/east/zz_other/Plan.php",  # 3
    "src/app/zz_west/Plan.php",  # 2
    "src/zz_compat/Plan.php",  # 1
    "aaa_vendor/Plan.php",  # 0 — furthest, and FIRST alphabetically
)
LEXICOGRAPHIC = tuple(sorted(TWINS))


def plant_twins(
    store: GraphStore, root: Path, *, files: tuple[str, ...] = TWINS  # noqa: F811
) -> None:
    seed_file(
        store,
        SUBJECT,
        [node("Class", "Plan", "\\East\\Core\\Plan", SUBJECT)],
        [],
        root=root,
    )
    # Planted in LEXICOGRAPHIC order, which is the store's own row order — so a test that passes
    # only because the rows arrive pre-sorted cannot pass here.
    for index, path in enumerate(sorted(files)):
        seed_file(
            store,
            path,
            [node("Class", "Plan", f"\\Twin{index}\\Plan", path)],
            [],
            root=root,
        )


def test_siblings_come_back_nearest_subtree_first_and_the_basis_is_named(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC1: a stated, deterministic order — and the payload says what it ranked by."""
    plant_twins(store, tmp_path)
    result = find_references.create(db_config(tmp_path))("\\East\\Core\\Plan")

    assert TWINS != LEXICOGRAPHIC, "the fixture must not let path order pass for ranking"
    assert [site["file"] for site in result[SIBLING_DEFINITIONS]] == list(TWINS)
    assert result[SIBLING_RANKED_BY] == RANK_SHARED_SUBTREE


def test_ranking_drops_nothing(store: GraphStore, tmp_path: Path) -> None:  # noqa: F811
    """AC2: the eight noise sites were noise for one question, not for every question."""
    plant_twins(store, tmp_path)
    result = find_references.create(db_config(tmp_path))("\\East\\Core\\Plan")

    assert len(result[SIBLING_DEFINITIONS]) == len(TWINS)
    assert {site["file"] for site in result[SIBLING_DEFINITIONS]} == set(TWINS)


def test_the_order_is_deterministic_for_identical_input(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC7/R4.2: ties break on the path, so two runs cannot disagree."""
    plant_twins(store, tmp_path)
    references = find_references.create(db_config(tmp_path))
    first = references("\\East\\Core\\Plan")[SIBLING_DEFINITIONS]
    second = references("\\East\\Core\\Plan")[SIBLING_DEFINITIONS]

    assert first == second


def test_one_sibling_does_not_grow_a_basis_field(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC4/061: with one sibling there is no order to explain, so nothing is added."""
    plant_twins(store, tmp_path, files=(TWINS[0],))
    result = find_references.create(db_config(tmp_path))("\\East\\Core\\Plan")

    assert len(result[SIBLING_DEFINITIONS]) == 1
    assert SIBLING_RANKED_BY not in result


def test_no_sibling_is_byte_identical(store: GraphStore, tmp_path: Path) -> None:  # noqa: F811
    """AC4/061: the clean subject pays nothing at all."""
    seed_file(
        store,
        SUBJECT,
        [node("Class", "Plan", "\\East\\Core\\Plan", SUBJECT)],
        [],
        root=tmp_path,
    )
    result = find_references.create(db_config(tmp_path))("\\East\\Core\\Plan")

    assert SIBLING_DEFINITIONS not in result
    assert SIBLING_RANKED_BY not in result


def test_find_callers_uses_the_same_ordering(store: GraphStore, tmp_path: Path) -> None:  # noqa: F811
    """AC3: one definition site for the ordering, shared with find_references (R6.7)."""
    subject = "src/app/east/core/Svc.php"
    near = "src/app/east/core/zz_legacy/Svc.php"
    far = "aaa_vendor/Svc.php"  # first alphabetically, last by subtree
    for path, namespace in ((subject, "\\East\\Core"), (near, "\\Legacy"), (far, "\\Vendor")):
        seed_file(
            store,
            path,
            [
                node("Class", "Svc", f"{namespace}\\Svc", path),
                node("Method", "run", f"{namespace}\\Svc::run", path),
            ],
            [],
            root=tmp_path,
        )
    result = find_callers.create(db_config(tmp_path))("\\East\\Core\\Svc::run")

    assert [site["file"] for site in result[SIBLING_DEFINITIONS]] == [near, far]
    assert result[SIBLING_RANKED_BY] == RANK_SHARED_SUBTREE


def test_the_fallback_basis_is_named_too() -> None:
    """A subject with no known file still gets a stated order, not an arbitrary one."""
    sites = [{"file": "b.php"}, {"file": "a.php"}]
    ordered, basis = rank_sibling_sites(sites, subject_file=None)

    assert basis == RANK_PATH
    assert [site["file"] for site in ordered] == ["a.php", "b.php"]


def test_ranking_adds_no_query_and_no_measurable_cost(
    store: GraphStore, tmp_path: Path  # noqa: F811
) -> None:
    """AC5: ranking reuses rows already fetched — it is a sort, not a lookup."""
    plant_twins(store, tmp_path)
    references = find_references.create(db_config(tmp_path))
    references("\\East\\Core\\Plan")

    started = time.perf_counter()
    for _ in range(200):
        references("\\East\\Core\\Plan")
    per_call = (time.perf_counter() - started) / 200
    assert per_call < 0.00135, f"{per_call * 1000:.3f} ms/call against 165's ~1.35 ms budget"
