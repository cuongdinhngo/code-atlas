"""Deterministic architectural drift between two 112 datasets (task 139).

A pure function over two snapshots — no second pipeline, no store, no LLM (PLAN §1 / R4).
Compares the fields a reviewer signs off on: modules, layer labels, cross-layer pairs, hub
rank, entry-point set, reachability buckets, and one-sided caveats (127). Identical input
yields an identical report (R4.2). Schema mismatches are direction-aware (050), not corruption.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from code_atlas.onboarding.dataset import derive_caveats
from code_atlas.onboarding.reachability import BUCKETS

# Operational keys ``generate_onboarding`` adds beside the dataset — stripped on load.
# ``pages`` stays although 205 stopped writing it: a pre-205 snapshot still carries the key, and a
# diff against one must strip it rather than read 500 page paths as architectural drift.
_MANIFEST_KEYS: frozenset[str] = frozenset(
    {"overview", "pages", "tour", "truncated", "viewer"}
)

# This module's refusal vocabulary. The payload REASON codes are the fixed nav vocabulary in
# ``tools/nav_result.py`` — onboarding never imports a tool, so a pin test ties these to it.
REFUSAL_INDEX_ROOT_MISMATCH = "index_root_mismatch"
REFUSAL_SCHEMA_MISMATCH = "dataset_schema_mismatch"
REFUSAL_INCOMPLETE = "incomplete_snapshot"
REFUSALS: tuple[str, ...] = (
    REFUSAL_INDEX_ROOT_MISMATCH,
    REFUSAL_SCHEMA_MISMATCH,
    REFUSAL_INCOMPLETE,
)

DIRECTION_OLDER = "before_older_than_after"
DIRECTION_NEWER = "before_newer_than_after"
DIRECTION_UNRECOGNISED = "dataset_version_unrecognised"

_REQUIRED: frozenset[str] = frozenset(
    {"version", "index_root", "last_ref", "modules", "layers", "matrix", "hubs", "reachability"}
)

__all__ = [
    "ArchitectureDiff",
    "DiffRefusal",
    "REFUSALS",
    "REFUSAL_INCOMPLETE",
    "REFUSAL_INDEX_ROOT_MISMATCH",
    "REFUSAL_SCHEMA_MISMATCH",
    "diff_architecture",
    "load_architecture_snapshot",
    "render_architecture_diff",
]


@dataclass(frozen=True, slots=True)
class DiffRefusal:
    """Why two snapshots cannot be compared — never rendered as an empty diff."""

    reason: str
    message: str
    direction: str | None = None
    before_version: int | None = None
    after_version: int | None = None
    before_root: str | None = None
    after_root: str | None = None


@dataclass(frozen=True, slots=True)
class ArchitectureDiff:
    """Counted architectural deltas between two named revisions of one tree."""

    before_ref: str
    after_ref: str
    index_root: str
    modules_added: tuple[str, ...]
    modules_removed: tuple[str, ...]
    layer_reassignments: tuple[tuple[str, str, str], ...]
    matrix_added: tuple[tuple[str, str, int], ...]
    matrix_removed: tuple[tuple[str, str, int], ...]
    hub_movements: tuple[tuple[str, int, int, int, int], ...]
    entry_points_added: tuple[str, ...]
    entry_points_removed: tuple[str, ...]
    entry_points_sampled: bool
    reachability_deltas: tuple[tuple[str, int, int], ...]
    caveats_before_only: tuple[tuple[str, str], ...]
    caveats_after_only: tuple[tuple[str, str], ...]

    @property
    def unchanged(self) -> bool:
        """True when every architectural section is empty — AC2's non-empty statement."""
        return not (
            self.modules_added
            or self.modules_removed
            or self.layer_reassignments
            or self.matrix_added
            or self.matrix_removed
            or self.hub_movements
            or self.entry_points_added
            or self.entry_points_removed
            or self.entry_points_sampled
            or self.reachability_deltas
            or self.caveats_before_only
            or self.caveats_after_only
        )


def load_architecture_snapshot(path: Path | str) -> dict[str, Any]:
    """Read a dataset or onboarding manifest JSON into a comparable snapshot."""
    text = Path(path).read_text(encoding="utf-8")
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError(f"architecture snapshot must be a JSON object, got {type(raw).__name__}")
    return {key: value for key, value in raw.items() if key not in _MANIFEST_KEYS}


def diff_architecture(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> ArchitectureDiff | DiffRefusal:
    """Compare two snapshots. Refusals are returned, never raised, so callers stay deterministic."""
    missing = _missing_fields(before, after)
    if missing is not None:
        return missing
    before_root = str(before["index_root"])
    after_root = str(after["index_root"])
    if before_root != after_root:
        return DiffRefusal(
            reason=REFUSAL_INDEX_ROOT_MISMATCH,
            message=(
                f"refusing to diff different trees: before={before_root!r} after={after_root!r}"
            ),
            before_root=before_root,
            after_root=after_root,
        )
    versions = _versions(before, after)
    if isinstance(versions, DiffRefusal):
        return versions
    before_ver, after_ver = versions
    if before_ver != after_ver:
        direction = _dataset_direction(before_ver, after_ver)
        action = (
            "before is an older dataset schema than after — regenerate the older side"
            if direction == DIRECTION_OLDER
            else "before is a newer dataset schema than after — regenerate the older side"
        )
        return DiffRefusal(
            reason=REFUSAL_SCHEMA_MISMATCH,
            message=action,
            direction=direction,
            before_version=before_ver,
            after_version=after_ver,
        )
    return _compute(before, after)


def render_architecture_diff(report: ArchitectureDiff | DiffRefusal) -> str:
    """Markdown table report — never an empty file when nothing moved (AC2)."""
    if isinstance(report, DiffRefusal):
        lines = [
            "# Architecture diff — refused",
            "",
            f"- reason: `{report.reason}`",
            f"- {report.message}",
        ]
        if report.direction is not None:
            lines.append(f"- direction: `{report.direction}`")
        if report.before_version is not None and report.after_version is not None:
            lines.append(
                f"- versions: before={report.before_version} after={report.after_version}"
            )
        return "\n".join(lines) + "\n"
    lines = [
        "# Architecture diff",
        "",
        f"- index_root: `{report.index_root}`",
        f"- before: `{report.before_ref}`",
        f"- after: `{report.after_ref}`",
        "",
    ]
    if report.entry_points_sampled:
        lines.append(
            "- entry-point comparison **skipped**: a truncated `web_entry` sample is not the "
            "population, so a sample difference is not drift."
        )
        lines.append("")
    if report.unchanged and not report.entry_points_sampled:
        lines.append("No architectural change between these revisions.")
        lines.append("")
        return "\n".join(lines)
    if report.unchanged:
        lines.append("No architectural change in the sections that could be compared.")
        lines.append("")
        return "\n".join(lines)
    lines.extend(_table("Modules added", ("module",), [(m,) for m in report.modules_added]))
    lines.extend(_table("Modules removed", ("module",), [(m,) for m in report.modules_removed]))
    lines.extend(
        _table(
            "Layer reassignments",
            ("file", "before", "after"),
            report.layer_reassignments,
        )
    )
    lines.extend(
        _table(
            "Cross-layer pairs added",
            ("source", "target", "count"),
            [(s, t, str(c)) for s, t, c in report.matrix_added],
        )
    )
    lines.extend(
        _table(
            "Cross-layer pairs removed",
            ("source", "target", "count"),
            [(s, t, str(c)) for s, t, c in report.matrix_removed],
        )
    )
    lines.extend(
        _table(
            "Hub rank movement",
            ("file", "before_rank", "after_rank", "before_fan_in", "after_fan_in"),
            [(f, str(br), str(ar), str(bf), str(af)) for f, br, ar, bf, af in report.hub_movements],
        )
    )
    lines.extend(
        _table("Entry points added", ("path",), [(p,) for p in report.entry_points_added])
    )
    lines.extend(
        _table("Entry points removed", ("path",), [(p,) for p in report.entry_points_removed])
    )
    lines.extend(
        _table(
            "Reachability bucket deltas",
            ("bucket", "before", "after"),
            [(b, str(bf), str(af)) for b, bf, af in report.reachability_deltas],
        )
    )
    lines.extend(
        _table(
            "Caveats on before only",
            ("section", "text"),
            report.caveats_before_only,
        )
    )
    lines.extend(
        _table(
            "Caveats on after only",
            ("section", "text"),
            report.caveats_after_only,
        )
    )
    return "\n".join(lines).rstrip() + "\n"


def _missing_fields(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> DiffRefusal | None:
    for label, side in (("before", before), ("after", after)):
        absent = sorted(key for key in _REQUIRED if key not in side)
        if absent:
            return DiffRefusal(
                reason=REFUSAL_INCOMPLETE,
                message=f"{label} snapshot missing required fields: {', '.join(absent)}",
            )
    return None


def _dataset_direction(before: int, after: int) -> str:
    """Which side is behind — direction-aware refusal, never 'corruption' (050 / AC5)."""
    return DIRECTION_OLDER if before < after else DIRECTION_NEWER


def _versions(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> tuple[int, int] | DiffRefusal:
    """Both schema versions as ints, or the refusal a non-numeric one earns (never a raise)."""
    try:
        return int(before["version"]), int(after["version"])
    except (TypeError, ValueError):
        return DiffRefusal(
            reason=REFUSAL_SCHEMA_MISMATCH,
            message=(
                "dataset schema versions are unrecognised — inspect both snapshots by hand"
            ),
            direction=DIRECTION_UNRECOGNISED,
        )


def _compute(before: Mapping[str, Any], after: Mapping[str, Any]) -> ArchitectureDiff:
    before_modules = _module_names(before)
    after_modules = _module_names(after)
    before_layers = _file_layers(before)
    after_layers = _file_layers(after)
    reassignments = tuple(
        sorted(
            (path, before_layers[path], after_layers[path])
            for path in sorted(set(before_layers) & set(after_layers))
            if before_layers[path] != after_layers[path]
        )
    )
    before_matrix = _matrix_map(before)
    after_matrix = _matrix_map(after)
    matrix_added = tuple(
        sorted(
            (source, target, after_matrix[(source, target)])
            for source, target in sorted(set(after_matrix) - set(before_matrix))
        )
    )
    matrix_removed = tuple(
        sorted(
            (source, target, before_matrix[(source, target)])
            for source, target in sorted(set(before_matrix) - set(after_matrix))
        )
    )
    before_hubs = _hub_ranks(before)
    after_hubs = _hub_ranks(after)
    hub_movements = tuple(
        sorted(
            (
                path,
                before_hubs[path][0],
                after_hubs[path][0],
                before_hubs[path][1],
                after_hubs[path][1],
            )
            for path in sorted(set(before_hubs) & set(after_hubs))
            if before_hubs[path] != after_hubs[path]
        )
    )
    before_entries, before_sampled = _entry_points(before)
    after_entries, after_sampled = _entry_points(after)
    # A bounded sample is not the population: two truncated samples of one unchanged bucket
    # differ, and that difference is not drift. State that the comparison was not made.
    entry_points_sampled = before_sampled or after_sampled
    before_reach = _reachability_counts(before)
    after_reach = _reachability_counts(after)
    reach_deltas = tuple(
        (bucket, before_reach.get(bucket, 0), after_reach.get(bucket, 0))
        for bucket in BUCKETS
        if before_reach.get(bucket, 0) != after_reach.get(bucket, 0)
    )
    before_caveats = set(derive_caveats(before))
    after_caveats = set(derive_caveats(after))
    return ArchitectureDiff(
        before_ref=str(before["last_ref"]),
        after_ref=str(after["last_ref"]),
        index_root=str(before["index_root"]),
        modules_added=tuple(sorted(after_modules - before_modules)),
        modules_removed=tuple(sorted(before_modules - after_modules)),
        layer_reassignments=reassignments,
        matrix_added=matrix_added,
        matrix_removed=matrix_removed,
        hub_movements=hub_movements,
        entry_points_added=(
            () if entry_points_sampled else tuple(sorted(after_entries - before_entries))
        ),
        entry_points_removed=(
            () if entry_points_sampled else tuple(sorted(before_entries - after_entries))
        ),
        entry_points_sampled=entry_points_sampled,
        reachability_deltas=reach_deltas,
        caveats_before_only=tuple(sorted(before_caveats - after_caveats)),
        caveats_after_only=tuple(sorted(after_caveats - before_caveats)),
    )


def _module_names(snapshot: Mapping[str, Any]) -> set[str]:
    modules = snapshot.get("modules")
    if not isinstance(modules, Mapping):
        return set()
    rows = modules.get("modules")
    if not isinstance(rows, list):
        return set()
    names: set[str] = set()
    for row in rows:
        if isinstance(row, Mapping) and isinstance(row.get("module"), str):
            names.add(row["module"])
    return names


def _file_layers(snapshot: Mapping[str, Any]) -> dict[str, str]:
    """File→layer from hubs and classes — the dataset's published path labels."""
    out: dict[str, str] = {}
    for key in ("hubs", "classes"):
        rows = snapshot.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            path = row.get("file")
            layer = row.get("layer")
            if isinstance(path, str) and isinstance(layer, str) and layer:
                out[path] = layer
    return out


def _matrix_map(snapshot: Mapping[str, Any]) -> dict[tuple[str, str], int]:
    rows = snapshot.get("matrix")
    if not isinstance(rows, list):
        return {}
    out: dict[tuple[str, str], int] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        source = row.get("source")
        target = row.get("target")
        count = row.get("count")
        if isinstance(source, str) and isinstance(target, str) and isinstance(count, int):
            out[(source, target)] = count
    return out


def _hub_ranks(snapshot: Mapping[str, Any]) -> dict[str, tuple[int, int]]:
    """1-based rank by published hub order (already heaviest-first) plus fan_in."""
    rows = snapshot.get("hubs")
    if not isinstance(rows, list):
        return {}
    out: dict[str, tuple[int, int]] = {}
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            continue
        path = row.get("file")
        fan_in = row.get("fan_in")
        if isinstance(path, str) and isinstance(fan_in, int):
            out[path] = (index, fan_in)
    return out


def _entry_points(snapshot: Mapping[str, Any]) -> tuple[set[str], bool]:
    """The web_entry sample, and whether it was truncated — a capped sample is not a set.

    113 publishes ``sample_truncated`` beside the sample precisely because the sample is
    bounded; dropping that flag turns a re-paged sample into reported drift.
    """
    reach = snapshot.get("reachability")
    if not isinstance(reach, Mapping):
        return set(), False
    buckets = reach.get("buckets")
    if not isinstance(buckets, list):
        return set(), False
    for row in buckets:
        if not isinstance(row, Mapping):
            continue
        if row.get("bucket") != "web_entry":
            continue
        sample = row.get("sample")
        count = row.get("count")
        paths: set[str] = set()
        if isinstance(sample, list):
            paths = {path for path in sample if isinstance(path, str)}
        truncated = bool(row.get("sample_truncated")) or (
            isinstance(count, int) and count > len(paths)
        )
        return paths, truncated
    return set(), False


def _reachability_counts(snapshot: Mapping[str, Any]) -> dict[str, int]:
    reach = snapshot.get("reachability")
    if not isinstance(reach, Mapping):
        return {}
    buckets = reach.get("buckets")
    if not isinstance(buckets, list):
        return {}
    out: dict[str, int] = {}
    for row in buckets:
        if not isinstance(row, Mapping):
            continue
        name = row.get("bucket")
        count = row.get("count")
        if isinstance(name, str) and isinstance(count, int):
            out[name] = count
    return out


def _table(title: str, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    if not rows:
        return []
    header = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    lines = [f"## {title}", "", header, rule]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    return lines
