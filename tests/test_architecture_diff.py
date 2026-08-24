"""Task 139 — architectural drift is a two-revision fact over 112 datasets."""

from __future__ import annotations

import copy
from pathlib import Path

from code_atlas.onboarding.architecture_diff import (
    DIRECTION_UNRECOGNISED,
    REFUSAL_INDEX_ROOT_MISMATCH,
    REFUSAL_SCHEMA_MISMATCH,
    REFUSALS,
    ArchitectureDiff,
    DiffRefusal,
    diff_architecture,
    load_architecture_snapshot,
    render_architecture_diff,
)
from code_atlas.tools import diff_architecture as tool
from code_atlas.tools.nav_result import NAV_REASONS, REASON_NO_ARCHITECTURAL_CHANGE
from tests.test_nav_tools import db_config

FIXTURE = Path("tests/fixtures/architecture_diff")


def test_ac1_known_delta_is_reported() -> None:
    report = diff_architecture(
        load_architecture_snapshot(FIXTURE / "before.json"),
        load_architecture_snapshot(FIXTURE / "after.json"),
    )
    assert isinstance(report, ArchitectureDiff)
    assert report.before_ref == "rev-a"
    assert report.after_ref == "rev-b"
    assert report.modules_added == ("c",)
    assert report.layer_reassignments == (("src/b/B.aa", "Domain", "HTTP / Entry"),)
    assert ("Domain", "HTTP / Entry", 2) in report.matrix_added
    assert report.hub_movements  # B rank/fan_in moved
    assert "src/b/B.aa" in report.entry_points_added
    assert ("isolated", 1, 0) in report.reachability_deltas
    assert ("web_entry", 1, 2) in report.reachability_deltas
    md = render_architecture_diff(report)
    assert "| Domain | HTTP / Entry | 2 |" in md
    assert report.unchanged is False


def test_ac2_identical_architecture_states_no_change() -> None:
    report = diff_architecture(
        load_architecture_snapshot(FIXTURE / "before.json"),
        load_architecture_snapshot(FIXTURE / "after_same.json"),
    )
    assert isinstance(report, ArchitectureDiff)
    assert report.unchanged is True
    md = render_architecture_diff(report)
    assert "No architectural change between these revisions." in md
    assert md.strip()  # never an empty artifact


def test_ac3_different_index_roots_are_refused() -> None:
    report = diff_architecture(
        load_architecture_snapshot(FIXTURE / "before.json"),
        load_architecture_snapshot(FIXTURE / "other_root.json"),
    )
    assert isinstance(report, DiffRefusal)
    assert report.reason == REFUSAL_INDEX_ROOT_MISMATCH
    assert report.before_root == "/repo"
    assert report.after_root == "/other"


def test_ac4_one_sided_caveat_is_reported() -> None:
    report = diff_architecture(
        load_architecture_snapshot(FIXTURE / "before.json"),
        load_architecture_snapshot(FIXTURE / "after.json"),
    )
    assert isinstance(report, ArchitectureDiff)
    assert ("path_index", "path caveat before") in report.caveats_before_only
    assert ("path_index", "path caveat after") in report.caveats_after_only


def test_ac5_schema_mismatch_is_direction_aware() -> None:
    report = diff_architecture(
        load_architecture_snapshot(FIXTURE / "schema_v6.json"),
        load_architecture_snapshot(FIXTURE / "before.json"),
    )
    assert isinstance(report, DiffRefusal)
    assert report.reason == REFUSAL_SCHEMA_MISMATCH
    assert report.direction == "before_older_than_after"
    assert report.before_version == 6
    assert report.after_version == 7


def test_ac5_byte_identical_ordering() -> None:
    a = diff_architecture(
        load_architecture_snapshot(FIXTURE / "before.json"),
        load_architecture_snapshot(FIXTURE / "after.json"),
    )
    b = diff_architecture(
        load_architecture_snapshot(FIXTURE / "before.json"),
        load_architecture_snapshot(FIXTURE / "after.json"),
    )
    assert render_architecture_diff(a) == render_architecture_diff(b)


def test_tool_surfaces_markdown_and_reason(tmp_path: Path) -> None:
    config = db_config(tmp_path)
    fn = tool.create(config)
    payload = fn(
        before=str((FIXTURE / "before.json").resolve()),
        after=str((FIXTURE / "after_same.json").resolve()),
    )
    assert payload["reason"] == REASON_NO_ARCHITECTURAL_CHANGE
    assert payload["unchanged"] is True
    assert "No architectural change" in payload["markdown"]


# ------------------------------------------------------------------------------------------------
# The fixtures publish untruncated samples and integer versions, so none of the cases below is
# reachable through them.


def _with_web_entry(snapshot: dict, sample: list[str], count: int, truncated: bool) -> dict:
    """Re-publish the web_entry bucket with a chosen sample/count/truncation flag."""
    out = copy.deepcopy(snapshot)
    for row in out["reachability"]["buckets"]:
        if row["bucket"] == "web_entry":
            row["sample"] = sample
            row["count"] = count
            row["sample_truncated"] = truncated
    return out


def test_a_repaged_truncated_sample_is_not_reported_as_entry_point_drift() -> None:
    """113 caps the sample; two cappings of ONE unchanged bucket differ, and that is not drift."""
    base = load_architecture_snapshot(FIXTURE / "before.json")
    before = _with_web_entry(base, [f"src/e{i:02d}.aa" for i in range(0, 10)], 50, True)
    after = _with_web_entry(base, [f"src/e{i:02d}.aa" for i in range(5, 15)], 50, True)
    after["last_ref"] = "rev-b"
    report = diff_architecture(before, after)
    assert isinstance(report, ArchitectureDiff)
    assert report.reachability_deltas == ()  # the population itself never moved
    assert report.entry_points_added == ()
    assert report.entry_points_removed == ()
    assert report.entry_points_sampled is True
    md = render_architecture_diff(report)
    assert "entry-point comparison **skipped**" in md


def test_an_untruncated_sample_still_diffs_the_entry_point_set() -> None:
    """The suppression is scoped to a capped sample — a complete one is still a set (AC1)."""
    report = diff_architecture(
        load_architecture_snapshot(FIXTURE / "before.json"),
        load_architecture_snapshot(FIXTURE / "after.json"),
    )
    assert isinstance(report, ArchitectureDiff)
    assert report.entry_points_sampled is False
    assert "src/b/B.aa" in report.entry_points_added


def test_a_count_above_the_sample_length_counts_as_truncated() -> None:
    """A snapshot that omits sample_truncated still says so by count vs sample length."""
    base = load_architecture_snapshot(FIXTURE / "before.json")
    before = _with_web_entry(base, ["src/a/A.aa"], 9, False)
    after = _with_web_entry(base, ["src/b/B.aa"], 9, False)
    report = diff_architecture(before, after)
    assert isinstance(report, ArchitectureDiff)
    assert report.entry_points_sampled is True
    assert report.entry_points_added == ()


def test_a_non_numeric_schema_version_is_refused_not_raised() -> None:
    """diff_architecture promises refusals are returned; int() on 'six' would have raised."""
    before = load_architecture_snapshot(FIXTURE / "before.json")
    after = copy.deepcopy(before)
    after["version"] = "six"
    report = diff_architecture(before, after)
    assert isinstance(report, DiffRefusal)
    assert report.reason == REFUSAL_SCHEMA_MISMATCH
    assert report.direction == DIRECTION_UNRECOGNISED


def test_every_refusal_reason_is_in_the_pinned_nav_vocabulary() -> None:
    """R6.7 pin: onboarding cannot import a tool, so nothing else stops these two forking."""
    assert set(REFUSALS) <= set(NAV_REASONS)
