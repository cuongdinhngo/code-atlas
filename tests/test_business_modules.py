"""Task 114 — the capability table that bridges "fix screen X" to a file path.

Each test names the acceptance criterion it proves. Every fixture is path shape only: no container
word, no region name, no library name appears here or in the module under test (AC6).
"""

from __future__ import annotations

import re
from pathlib import Path

from code_atlas.onboarding.modules import (
    COVERAGE_NOTE,
    MIN_CONTAINER_MODULES,
    MIN_MODULE_FILES,
    REFUSED_ROLE_ORGANISED,
    find_business_modules,
)


def _paths(container: str, modules: dict[str, int]) -> list[str]:
    """`container/<name>/fN.x` paths, `count` files per module."""
    return [
        f"{container}/{name}/f{index}.x"
        for name, count in modules.items()
        for index in range(count)
    ]


def _find(paths: list[str], **kwargs: object) -> object:
    classes = {path: 1 for path in paths}
    fan_in = {path: 0 for path in paths}
    return find_business_modules(
        paths, class_counts=classes, fan_in=fan_in, limit=50, **kwargs  # type: ignore[arg-type]
    )


# AC1's fixture was amended at Gate 1: two module directories cannot pass the shipped
# MIN_CONTAINER_MODULES gate, and lowering that gate makes a real pinned library report its
# `Exception`/`Internal` split as business modules. Four modules exercises the shipped default.
_FOUR = {"billing": 4, "audit": 4, "roster": 5, "catering": 3}


def test_ac1_container_yields_its_modules_with_counts() -> None:
    """AC1 (R6.5) — the proving test: a container's children become modules, with correct counts."""
    result = _find(_paths("app/application", _FOUR))
    assert result.containers == ("app/application",)  # type: ignore[attr-defined]
    rows = {row.module: row for row in result.modules}  # type: ignore[attr-defined]
    assert set(rows) == set(_FOUR)
    for name, count in _FOUR.items():
        assert rows[name].files == count, name
        assert rows[name].classes == count, name  # one class per file in the fixture
    # Largest first is the table's reading order (R4.2).
    assert [row.module for row in result.modules] == [  # type: ignore[attr-defined]
        "roster", "audit", "billing", "catering",
    ]


def test_ac1_boundary_a_three_module_container_is_refused() -> None:
    """AC1 boundary — one below the gate yields nothing, so the threshold is real."""
    below = _find(_paths("app/application", {"billing": 4, "audit": 4, "roster": 4}))
    assert below.modules == () and below.containers == ()  # type: ignore[attr-defined]
    assert MIN_CONTAINER_MODULES == 4


def test_ac1_a_child_below_the_file_floor_is_not_a_peer() -> None:
    """AC1 — a directory holding less than MIN_MODULE_FILES is not a module."""
    paths = _paths("app/application", {"billing": 4, "audit": 4, "roster": 4, "thin": 1})
    result = _find(paths)
    assert "thin" not in {row.module for row in result.modules}  # type: ignore[attr-defined]
    assert MIN_MODULE_FILES == 3


def test_ac2_coverage_is_reported_and_correct() -> None:
    """AC2 — half the files outside any module directory reports ~50 %."""
    inside = _paths("app/application", {"billing": 4, "audit": 4, "roster": 4, "catering": 4})
    outside = [f"web/page{index}.x" for index in range(len(inside))]
    result = _find(inside + outside)
    assert result.covered == 16 and result.total == 32  # type: ignore[attr-defined]
    assert result.percent == 50.0  # type: ignore[attr-defined]


def test_ac2_the_coverage_note_points_at_the_remainder() -> None:
    """AC2 — the map carries its own caveat, so no renderer can print the table without it."""
    result = _find(_paths("app/application", _FOUR))
    assert result.as_dict()["coverage"]["note"] == COVERAGE_NOTE  # type: ignore[index]
    assert "worse than a smaller honest one" in COVERAGE_NOTE


def test_ac3_single_tree_module_is_flagged_and_a_shared_one_is_not() -> None:
    """AC3 — the divergence signal: present under one tree, absent under its sibling."""
    left = _paths("one/application", {"billing": 4, "audit": 4, "roster": 4, "catering": 4})
    right = _paths("two/application", {"billing": 4, "audit": 4, "roster": 4, "onlyhere": 4})
    result = _find(left + right)
    rows = {row.module: row for row in result.modules}  # type: ignore[attr-defined]
    assert rows["billing"].trees == ("one", "two") and rows["billing"].single_tree is False
    assert rows["onlyhere"].trees == ("two",) and rows["onlyhere"].single_tree is True
    assert rows["catering"].trees == ("one",) and rows["catering"].single_tree is True


def test_ac3_divergence_is_not_claimed_with_one_container() -> None:
    """AC3 — one container makes every module trivially single-tree, so nothing is flagged."""
    result = _find(_paths("app/application", _FOUR))
    assert all(not row.single_tree for row in result.modules)  # type: ignore[attr-defined]


def test_ac4_a_role_organised_container_yields_no_modules() -> None:
    """AC4 — the `symfony/demo` shape: a container whose children name roles is refused, with
    reason."""
    paths = _paths(
        "src", {"controller": 4, "entity": 4, "form": 7, "repository": 3, "command": 3}
    )
    result = _find(paths)
    assert result.modules == ()  # type: ignore[attr-defined]
    assert result.refused == (("src", REFUSED_ROLE_ORGANISED),)  # type: ignore[attr-defined]
    assert "not by capability" in REFUSED_ROLE_ORGANISED


def test_ac4_a_capability_container_keeps_a_role_named_member() -> None:
    """AC4's intent, not its literal per-word reading: the anchor's own `api` and `reports` are
    genuine capabilities, so a role-named child survives in a capability-organised container."""
    paths = _paths(
        "app/application", {"billing": 4, "audit": 4, "roster": 4, "api": 4, "reports": 4}
    )
    result = _find(paths)
    names = {row.module for row in result.modules}  # type: ignore[attr-defined]
    assert {"api", "reports"} <= names
    assert result.refused == ()  # type: ignore[attr-defined]


def test_ac4_container_and_tree_names_are_never_modules() -> None:
    """AC4 — structurally impossible: both sit above the module level, so no list is needed."""
    result = _find(_paths("region/application", _FOUR))
    names = {row.module for row in result.modules}  # type: ignore[attr-defined]
    assert "region" not in names and "application" not in names
    assert result.containers == ("region/application",)  # type: ignore[attr-defined]


def test_ac5_a_repo_with_no_capability_layout_reports_zero() -> None:
    """AC5 — a flat library reports no modules rather than inventing groups."""
    result = _find([f"src/File{index}.x" for index in range(20)])
    assert result.modules == () and result.containers == ()  # type: ignore[attr-defined]
    assert result.covered == 0 and result.percent == 0.0  # type: ignore[attr-defined]


def test_ac5_a_two_way_library_split_is_not_a_capability_layout() -> None:
    """AC5 — the measured `brick/math` shape: 10 + 7 files in two dirs is not a module table."""
    result = _find(_paths("src", {"exception": 10, "internal": 7}))
    assert result.modules == ()  # type: ignore[attr-defined]


def test_ac6_no_repo_or_library_name_in_the_module_finder() -> None:
    """AC6 — the CI gate's unit twin, extended to the library names the prototype listed."""
    source = Path("code_atlas/onboarding/modules.py").read_text(encoding="utf-8")
    denied = re.compile(
        r"laravel|symfony|wordpress|drupal|magento|tcpdf|mpdf|adodb|smarty|zend|phpexcel"
        r"|phpword|log4php|dompdf|fpdf|saml",
        re.I,
    )
    assert denied.search(source) is None
    # The container word list the prototype used must not have come along either.
    assert "application" not in source and "modules/" not in source


def test_vendored_and_test_paths_are_excluded_using_113s_signals() -> None:
    """A dependency directory must not be elected the widest container and reported as modules."""
    vendored = _paths("vendor", {"one": 4, "two": 4, "three": 4, "four": 4})
    tests = _paths("tests/unit", {"a": 4, "b": 4, "c": 4, "d": 4})
    real = _paths("app/application", _FOUR)
    result = _find(vendored + tests + real)
    assert result.containers == ("app/application",)  # type: ignore[attr-defined]
    assert result.excluded == len(vendored) + len(tests)  # type: ignore[attr-defined]


def test_a_declared_stub_root_is_excluded_too() -> None:
    """The operator's own dependency declaration is honoured, whatever the paths look like."""
    declared = _paths("libs", {"one": 4, "two": 4, "three": 4, "four": 4})
    real = _paths("app/application", _FOUR)
    result = _find(declared + real, stub_roots=("libs",))
    assert result.containers == ("app/application",)  # type: ignore[attr-defined]


def test_modules_never_nest_inside_modules() -> None:
    """A container inside a container is dropped, so the table has one level, not a tree."""
    inner = _paths("app/application/billing/sub", {"a": 4, "b": 4, "c": 4, "d": 4})
    outer = _paths("app/application", {"audit": 4, "roster": 4, "catering": 4})
    result = _find(inner + outer)
    assert result.containers == ("app/application",)  # type: ignore[attr-defined]
    assert "billing" in {row.module for row in result.modules}  # type: ignore[attr-defined]


def test_the_hub_is_the_busiest_file_in_the_module() -> None:
    """Per module, the highest-fan-in file — no SQL needed; 083's degrees already carry it."""
    paths = _paths("app/application", _FOUR)
    fan_in = {path: 0 for path in paths}
    fan_in["app/application/roster/f2.x"] = 9
    result = find_business_modules(
        paths, class_counts={}, fan_in=fan_in, limit=50
    )
    roster = next(row for row in result.modules if row.module == "roster")
    assert roster.hub == "app/application/roster/f2.x" and roster.hub_fan_in == 9


def test_output_is_byte_stable_regardless_of_input_order() -> None:
    """R4.2 — identical input yields an identical map, whatever order the paths arrive in."""
    paths = _paths("app/application", _FOUR) + ["web/page.x"]
    first = _find(paths).as_dict()  # type: ignore[attr-defined]
    assert first == _find(list(reversed(paths))).as_dict()  # type: ignore[attr-defined]


def test_the_module_list_is_capped_and_says_so() -> None:
    """Every list in this server is capped; a trimmed table states it (the shared convention)."""
    many = {f"cap{index}": 4 for index in range(10)}
    result = find_business_modules(
        _paths("app/application", many), class_counts={}, fan_in={}, limit=3
    )
    assert len(result.modules) == 3 and result.truncated is True
