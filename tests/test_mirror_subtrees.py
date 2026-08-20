"""Task 115 — sibling subtrees holding near-copies, discovered rather than configured.

Each test names the acceptance criterion it proves. Every fixture is path shape only: no tree
prefix, no region name and no configured pair appears here or in the module under test (R2.2).
"""

from __future__ import annotations

import re
from pathlib import Path

from code_atlas.onboarding.mirrors import (
    COUNTERPART,
    MIN_OVERLAP,
    MIN_SHARED_PATHS,
    NO_COUNTERPART,
    OUTSIDE_MIRROR,
    PATH_NOT_CONTENT,
    find_mirror_subtrees,
    resolve_counterpart,
)

# Low thresholds expose the arithmetic on a tiny fixture; the shipped defaults get their own tests
# below, so no test both sets a threshold and claims the default is right.
_OPEN = {"min_shared": 1, "min_overlap": 0.1}


def test_ac1_reports_shared_and_each_side() -> None:
    """AC1 (R6.5) — the proving test: one shared path and one on each side."""
    # AC1 lists `a/x`, `a/y`, `b/x`, which can only give one side an exclusive path; `b/z` is the
    # fourth path AC1's own wording ("one on each side") requires. Both shapes are asserted.
    report = find_mirror_subtrees(
        ["a/x", "a/y", "b/x", "b/z"], sample_limit=5, **_OPEN  # type: ignore[arg-type]
    )
    pair = report.pairs[0]
    assert (pair.left, pair.right) == ("a", "b")
    assert pair.shared == 1 and pair.left_only == 1 and pair.right_only == 1
    assert pair.overlap == round(1 / 3, 3)
    assert pair.sample == ("x",)


def test_ac1_the_literal_three_path_fixture_reports_an_asymmetric_pair() -> None:
    """AC1 as literally listed — one shared, one on the left, none on the right."""
    report = find_mirror_subtrees(
        ["a/x", "a/y", "b/x"], sample_limit=5, **_OPEN  # type: ignore[arg-type]
    )
    pair = report.pairs[0]
    assert pair.shared == 1 and pair.left_only == 1 and pair.right_only == 0
    assert pair.overlap == 0.5


def test_ac1_counts_reproduce_the_anchor_numbers() -> None:
    """AC1 — the arithmetic at the anchor's measured shape: 4,244 / 1,522 / 1,134 is 62 %."""
    paths = (
        [f"one/m/f{index}.x" for index in range(4244 + 1522)]
        + [f"two/m/f{index}.x" for index in range(4244)]
        + [f"two/m/g{index}.x" for index in range(1134)]
    )
    pair = find_mirror_subtrees(paths, sample_limit=3).pairs[0]
    assert (pair.shared, pair.left_only, pair.right_only) == (4244, 1522, 1134)
    assert pair.overlap == 0.615


def test_ac2_resolution_is_symmetric() -> None:
    """AC2 — swapping the pair's prefixes is its own inverse, so the lookup works both ways."""
    paths = ["a/x", "a/y", "b/x", "b/z"]
    pairs = find_mirror_subtrees(paths, sample_limit=5, **_OPEN).pairs  # type: ignore[arg-type]
    forward = resolve_counterpart("a/x", pairs, set(paths))
    backward = resolve_counterpart("b/x", pairs, set(paths))
    assert forward.status == COUNTERPART and forward.path == "b/x"
    assert backward.status == COUNTERPART and backward.path == "a/x"
    # Symmetry proper: resolving the answer returns the question.
    assert resolve_counterpart(forward.path, pairs, set(paths)).path == "a/x"


def test_ac2_a_path_outside_any_mirror_is_a_clean_negative() -> None:
    """AC2 — no guess: a path in no detected pair says so and names nothing."""
    paths = ["a/x", "a/y", "b/x", "b/z"]
    pairs = find_mirror_subtrees(paths, sample_limit=5, **_OPEN).pairs  # type: ignore[arg-type]
    answer = resolve_counterpart("elsewhere/thing.x", pairs, set(paths))
    assert answer.status == OUTSIDE_MIRROR
    assert answer.path == "" and answer.pair is None


def test_ac2_a_diverged_path_is_the_divergence_marker() -> None:
    """AC2 — inside a mirror but with no parallel file: the answer the ticket calls most useful."""
    paths = ["a/x", "a/y", "b/x", "b/z"]
    pairs = find_mirror_subtrees(paths, sample_limit=5, **_OPEN).pairs  # type: ignore[arg-type]
    answer = resolve_counterpart("a/y", pairs, set(paths))
    assert answer.status == NO_COUNTERPART
    assert answer.pair == ("a", "b") and answer.qualified is False


def test_ac2_a_negative_from_an_incomplete_path_set_is_qualified() -> None:
    """AC2/H6 — a capped index cannot tell a diverged file from a trimmed one, so it says so."""
    paths = ["a/x", "a/y", "b/x", "b/z"]
    pairs = find_mirror_subtrees(paths, sample_limit=5, **_OPEN).pairs  # type: ignore[arg-type]
    trimmed = {"a/x", "a/y", "b/x"}  # `b/z` trimmed by a cap
    answer = resolve_counterpart("a/y", pairs, trimmed, complete=False)
    assert answer.status == NO_COUNTERPART and answer.qualified is True
    # With the full set the same question is answered unqualified.
    assert resolve_counterpart("a/y", pairs, set(paths)).qualified is False


def test_ac3_a_repo_with_no_mirror_reports_none() -> None:
    """AC3 — a flat, unmirrored layout yields nothing rather than manufacturing structure."""
    paths = [f"src/Thing{index}.x" for index in range(40)] + [
        f"src/sub/Other{index}.x" for index in range(40)
    ]
    assert find_mirror_subtrees(paths, sample_limit=5).pairs == ()


def test_ac4_thresholds_reject_the_measured_false_positive() -> None:
    """AC4 — the regression a pinned public repo handed us: a PERFECT overlap on ONE shared file.

    Overlap fraction alone accepts this. The shared-count gate is what rejects it, which is why the
    detector has two gates and not one.
    """
    paths = ["t/Feature/ExampleTest.x", "t/Unit/ExampleTest.x"]
    report = find_mirror_subtrees(paths, sample_limit=5)
    assert report.pairs == ()
    # The pair really does score a perfect overlap — the count is doing the rejecting.
    open_report = find_mirror_subtrees(
        paths, sample_limit=5, **_OPEN  # type: ignore[arg-type]
    )
    assert open_report.pairs[0].overlap == 1.0 and open_report.pairs[0].shared == 1


def test_ac4_each_gate_is_load_bearing_on_its_own() -> None:
    """AC4 — both boundaries are real: enough overlap but too few paths, and vice versa."""
    # Enough shared paths, overlap too low: the trees are adjacent, not mirrored.
    wide = (
        [f"a/s{index}.x" for index in range(MIN_SHARED_PATHS)]
        + [f"b/s{index}.x" for index in range(MIN_SHARED_PATHS)]
        + [f"a/only{index}.x" for index in range(400)]
    )
    assert find_mirror_subtrees(wide, sample_limit=3).pairs == ()
    # High overlap, too few shared paths: one file in common is not a mirror.
    thin = [f"a/s{index}.x" for index in range(3)] + [f"b/s{index}.x" for index in range(3)]
    assert find_mirror_subtrees(thin, sample_limit=3).pairs == ()
    # Both cleared: detected.
    both = [
        f"{side}/s{index}.x" for side in ("a", "b") for index in range(MIN_SHARED_PATHS)
    ]
    assert len(find_mirror_subtrees(both, sample_limit=3).pairs) == 1
    assert MIN_SHARED_PATHS == 25 and MIN_OVERLAP == 0.30


def test_ac5_the_caveat_ships_with_the_report() -> None:
    """AC5 — the report states it compares paths, and never asserts the files are copies."""
    report = find_mirror_subtrees(["a/x", "b/x"], sample_limit=5, **_OPEN)  # type: ignore[arg-type]
    assert report.caveat == PATH_NOT_CONTENT
    assert "not file contents" in PATH_NOT_CONTENT
    assert "not that the two files are copies" in PATH_NOT_CONTENT


def test_ac5_no_renderer_can_print_counts_without_the_caveat() -> None:
    """AC5 — the caveat rides inside the serialised shape, beside the pairs, not alongside it."""
    payload = find_mirror_subtrees(
        ["a/x", "b/x"], sample_limit=5, **_OPEN  # type: ignore[arg-type]
    ).as_dict()
    assert set(payload) == {"caveat", "pairs"}
    assert payload["caveat"] == PATH_NOT_CONTENT


def test_no_tree_prefix_region_or_configured_pair_in_the_detector() -> None:
    """R2.2 — the CI gate's unit twin; the prototype's own literals must not have come along."""
    source = Path("code_atlas/onboarding/mirrors.py").read_text(encoding="utf-8")
    denied = re.compile(r"laravel|symfony|wordpress|drupal|magento|legacy/|\baus\b|\bnz\b", re.I)
    assert denied.search(source) is None


def test_vendored_and_test_paths_are_excluded_using_113s_signals() -> None:
    """Mirrored test scaffolding is not a mirrored application — the false positive's class."""
    mirrored_tests = [
        f"{side}/s{index}.x" for side in ("tests/one", "tests/two") for index in range(40)
    ]
    assert find_mirror_subtrees(mirrored_tests, sample_limit=3).pairs == ()
    vendored = [
        f"vendor/{side}/s{index}.x" for side in ("one", "two") for index in range(40)
    ]
    assert find_mirror_subtrees(vendored, sample_limit=3).pairs == ()


def test_a_declared_stub_root_is_excluded_too() -> None:
    """The operator's own dependency declaration is honoured as an EXCLUSION, never as a pair."""
    declared = [f"libs/{side}/s{index}.x" for side in ("one", "two") for index in range(40)]
    assert find_mirror_subtrees(declared, sample_limit=3, stub_roots=("libs",)).pairs == ()


def test_pairs_are_ranked_by_shared_count_and_output_is_byte_stable() -> None:
    """R4.2 — largest pair first, and identical input yields an identical report in any order."""
    paths = (
        [f"{side}/big{index}.x" for side in ("a", "b") for index in range(40)]
        + [f"{side}/small{index}.x" for side in ("m/p", "m/q") for index in range(30)]
    )
    report = find_mirror_subtrees(paths, sample_limit=3)
    assert [pair.shared for pair in report.pairs] == sorted(
        (pair.shared for pair in report.pairs), reverse=True
    )
    assert report.as_dict() == find_mirror_subtrees(
        list(reversed(paths)), sample_limit=3
    ).as_dict()


def test_the_sample_is_bounded() -> None:
    """Every list in this server is capped; the shared-path sample is no exception."""
    paths = [f"{side}/s{index}.x" for side in ("a", "b") for index in range(60)]
    pair = find_mirror_subtrees(paths, sample_limit=4).pairs[0]
    assert pair.shared == 60 and len(pair.sample) == 4
