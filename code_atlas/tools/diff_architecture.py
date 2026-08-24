"""``diff_architecture`` — what moved between two onboarding dataset snapshots (task 139)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal

from code_atlas.config import Config
from code_atlas.onboarding.architecture_diff import (
    ArchitectureDiff,
    DiffRefusal,
    load_architecture_snapshot,
    render_architecture_diff,
)
from code_atlas.onboarding.architecture_diff import (
    diff_architecture as diff_architecture_impl,
)
from code_atlas.tools.nav_result import (
    REASON_NO_ARCHITECTURAL_CHANGE,
    REASON_OK,
    REASON_SNAPSHOT_NOT_FOUND,
)

NAME = "diff_architecture"

DetailLevel = Literal["minimal", "standard"]

__all__ = ["NAME", "create"]


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration (paths resolve under ``index_root``)."""

    def diff_architecture(
        before: str,
        after: str,
        detail_level: DetailLevel = "standard",
    ) -> dict[str, object]:
        """Diff two 112 dataset (or onboarding manifest) JSON files for architectural drift.

        Both sides must name the same ``index_root`` and the same dataset ``version``; a mismatch
        is refused with a direction-aware reason rather than rendered. Identical architecture
        yields an explicit *no architectural change* statement — never an empty artifact.
        Paths are relative to the indexed tree unless absolute.
        """
        before_path = _resolve(config, before)
        after_path = _resolve(config, after)
        missing = [
            label
            for label, path in (("before", before_path), ("after", after_path))
            if not path.is_file()
        ]
        if missing:
            return {
                "index_root": config.index_root,
                "indexed": config.db_path.is_file(),
                "reason": REASON_SNAPSHOT_NOT_FOUND,
                "message": f"missing snapshot file(s): {', '.join(missing)}",
                "results": [],
                "total_count": 0,
                "truncated": False,
            }
        report = diff_architecture_impl(
            load_architecture_snapshot(before_path),
            load_architecture_snapshot(after_path),
        )
        if isinstance(report, DiffRefusal):
            payload: dict[str, object] = {
                "index_root": config.index_root,
                "indexed": True,
                "reason": report.reason,
                "message": report.message,
                "results": [],
                "total_count": 0,
                "truncated": False,
            }
            if report.direction is not None:
                payload["direction"] = report.direction
            if report.before_version is not None:
                payload["before_version"] = report.before_version
            if report.after_version is not None:
                payload["after_version"] = report.after_version
            if detail_level == "standard":
                payload["markdown"] = render_architecture_diff(report)
            return payload
        reason = REASON_NO_ARCHITECTURAL_CHANGE if report.unchanged else REASON_OK
        payload = {
            "index_root": report.index_root,
            "indexed": True,
            "reason": reason,
            "before_ref": report.before_ref,
            "after_ref": report.after_ref,
            "entry_points_sampled": report.entry_points_sampled,
            "unchanged": report.unchanged,
            "results": _sections(report) if not report.unchanged else [],
            "total_count": _change_count(report),
            "truncated": False,
        }
        if detail_level == "standard":
            payload["markdown"] = render_architecture_diff(report)
            payload["diff"] = _shape(report)
        return payload

    return diff_architecture



def _resolve(config: Config, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return Path(config.root) / path


def _change_count(report: ArchitectureDiff) -> int:
    return (
        len(report.modules_added)
        + len(report.modules_removed)
        + len(report.layer_reassignments)
        + len(report.matrix_added)
        + len(report.matrix_removed)
        + len(report.hub_movements)
        + len(report.entry_points_added)
        + len(report.entry_points_removed)
        + len(report.reachability_deltas)
        + len(report.caveats_before_only)
        + len(report.caveats_after_only)
    )


def _sections(report: ArchitectureDiff) -> list[dict[str, object]]:
    """One row per non-empty section — population for ``total_count`` when paging is N/A."""
    rows: list[dict[str, object]] = []
    mapping = (
        ("modules_added", report.modules_added),
        ("modules_removed", report.modules_removed),
        ("layer_reassignments", report.layer_reassignments),
        ("matrix_added", report.matrix_added),
        ("matrix_removed", report.matrix_removed),
        ("hub_movements", report.hub_movements),
        ("entry_points_added", report.entry_points_added),
        ("entry_points_removed", report.entry_points_removed),
        ("reachability_deltas", report.reachability_deltas),
        ("caveats_before_only", report.caveats_before_only),
        ("caveats_after_only", report.caveats_after_only),
    )
    for name, values in mapping:
        if values:
            rows.append({"section": name, "count": len(values)})
    return rows


def _shape(report: ArchitectureDiff) -> dict[str, object]:
    return {
        "after_ref": report.after_ref,
        "before_ref": report.before_ref,
        "caveats_after_only": [
            {"section": section, "text": text} for section, text in report.caveats_after_only
        ],
        "caveats_before_only": [
            {"section": section, "text": text} for section, text in report.caveats_before_only
        ],
        "entry_points_added": list(report.entry_points_added),
        "entry_points_removed": list(report.entry_points_removed),
        "hub_movements": [
            {
                "after_fan_in": af,
                "after_rank": ar,
                "before_fan_in": bf,
                "before_rank": br,
                "file": path,
            }
            for path, br, ar, bf, af in report.hub_movements
        ],
        "index_root": report.index_root,
        "layer_reassignments": [
            {"after": after, "before": before, "file": path}
            for path, before, after in report.layer_reassignments
        ],
        "matrix_added": [
            {"count": count, "source": source, "target": target}
            for source, target, count in report.matrix_added
        ],
        "matrix_removed": [
            {"count": count, "source": source, "target": target}
            for source, target, count in report.matrix_removed
        ],
        "modules_added": list(report.modules_added),
        "modules_removed": list(report.modules_removed),
        "reachability_deltas": [
            {"after": after, "before": before, "bucket": bucket}
            for bucket, before, after in report.reachability_deltas
        ],
        "unchanged": report.unchanged,
    }
