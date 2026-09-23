"""Capability table sources for onboarding — never an empty table (task 263).

Source order: human ``capabilities.toml`` → structural modules (114) → entry-point rows →
an explained refusal with candidate globs. Directory names never invent business meaning (R2.2);
a human-authored name may resolve to paths the graph already holds.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from code_atlas.ignore import translate_path_pattern
from code_atlas.onboarding.layers import READING_SEED_LAYER_RANK, reading_seed_rank
from code_atlas.onboarding.modules import (
    BusinessModule,
    ModuleMap,
    find_business_modules,
)
from code_atlas.tools.nominate_roots import CANDIDATE_ENTRY_GLOBS, nominate_globs

SOURCE_TOML = "capabilities_toml"
SOURCE_STRUCTURAL = "structural"
SOURCE_ENTRY = "entry_points"
SOURCE_EMPTY = "empty_explained"

CAPABILITIES_TOML = Path("docs/onboarding/capabilities.toml")
_HTTP_RANK = READING_SEED_LAYER_RANK["HTTP / Entry"]

EMPTY_REASON = (
    "no capabilities.toml, no structural capability layout, and no entry-point rows — "
    "set docs/onboarding/capabilities.toml and/or CA_ENTRY_POINTS (or entry_points in "
    ".code-atlas.toml); candidate globs below show files_matched on this index"
)

__all__ = [
    "CAPABILITIES_TOML",
    "EMPTY_REASON",
    "SOURCE_EMPTY",
    "SOURCE_ENTRY",
    "SOURCE_STRUCTURAL",
    "SOURCE_TOML",
    "resolve_capability_map",
]


@dataclass(frozen=True)
class _TomlCapability:
    name: str
    paths: tuple[str, ...]


def resolve_capability_map(
    file_paths: Sequence[str],
    *,
    class_counts: Mapping[str, int],
    fan_in: Mapping[str, int],
    stub_roots: Sequence[str] | None = None,
    working_roots: Sequence[str] | None = None,
    limit: int,
    declared_entry_points: Sequence[str] | None = None,
    graph_entry_files: Sequence[str] | None = None,
    repo_root: Path | None = None,
    outbound: Mapping[str, tuple[str, ...]] | None = None,
    prose: object = None,
) -> ModuleMap:
    """Pick the first non-empty capability source; never emit a silent empty table."""
    toml_rows, toml_covered, toml_cut, refused = _from_toml(
        repo_root,
        file_paths,
        class_counts=class_counts,
        fan_in=fan_in,
        limit=limit,
    )
    # Present-but-empty (or unreadable) toml must fall through — never a silent empty section.
    if toml_rows:
        return _map(
            toml_rows,
            source=SOURCE_TOML,
            file_paths=file_paths,
            covered=toml_covered,
            truncated=toml_cut,
            refused=refused,
        )

    structural = find_business_modules(
        file_paths,
        class_counts=class_counts,
        fan_in=fan_in,
        stub_roots=stub_roots,
        working_roots=working_roots,
        limit=limit,
        prose=prose,  # type: ignore[arg-type]
    )
    if structural.modules:
        return replace(
            structural, source=SOURCE_STRUCTURAL, refused=structural.refused + refused
        )

    entry_rows, entry_cut = _from_entries(
        file_paths,
        declared_entry_points=declared_entry_points or (),
        graph_entry_files=graph_entry_files or (),
        fan_in=fan_in,
        class_counts=class_counts,
        outbound=outbound or {},
        limit=limit,
    )
    if entry_rows:
        return _map(
            entry_rows,
            source=SOURCE_ENTRY,
            file_paths=file_paths,
            covered=len(entry_rows),
            truncated=entry_cut,
            refused=refused,
        )

    candidates = tuple(
        (str(row["glob"]), int(str(row["files_matched"])))
        for row in nominate_globs(file_paths, patterns=CANDIDATE_ENTRY_GLOBS)
    )
    return ModuleMap(
        modules=(),
        containers=(),
        refused=refused,
        covered=0,
        total=len(file_paths),
        excluded=0,
        truncated=False,
        source=SOURCE_EMPTY,
        empty_reason=EMPTY_REASON,
        candidate_globs=candidates,
    )


def _map(
    rows: tuple[BusinessModule, ...],
    *,
    source: str,
    file_paths: Sequence[str],
    covered: int,
    truncated: bool = False,
    refused: tuple[tuple[str, str], ...] = (),
) -> ModuleMap:
    return ModuleMap(
        modules=rows,
        containers=(),
        refused=refused,
        covered=covered,
        total=len(file_paths),
        excluded=0,
        truncated=truncated,
        source=source,
        empty_reason=None,
        candidate_globs=(),
    )


def _from_toml(
    repo_root: Path | None,
    file_paths: Sequence[str],
    *,
    class_counts: Mapping[str, int],
    fan_in: Mapping[str, int],
    limit: int,
) -> tuple[tuple[BusinessModule, ...], int, bool, tuple[tuple[str, str], ...]]:
    """Rows, files covered (deduplicated), whether rows were cut, and a read refusal."""
    if repo_root is None:
        return (), 0, False, ()
    path = repo_root / CAPABILITIES_TOML
    if not path.is_file():
        return (), 0, False, ()
    try:
        caps = _parse_toml(path)
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as exc:
        # A typo in a hand-written file falls through to the next source, named not swallowed.
        return (), 0, False, ((str(CAPABILITIES_TOML), f"unreadable capabilities file: {exc}"),)
    if not caps:
        return (), 0, False, ()
    rows: list[tuple[BusinessModule, tuple[str, ...]]] = []
    for cap in caps:
        matched = _match_paths(file_paths, cap)
        if not matched:
            rows.append((
                BusinessModule(
                    module=cap.name,
                    label=cap.name,
                    files=0,
                    classes=0,
                    trees=(),
                    directories=(),
                    hub="",
                    hub_fan_in=0,
                    single_tree=True,
                ),
                (),
            ))
            continue
        hub, hub_fan = _busiest(matched, fan_in)
        dirs = tuple(sorted({"/".join(p.split("/")[:-1]) or "(root)" for p in matched}))
        rows.append((
            BusinessModule(
                module=cap.name,
                label=cap.name,
                files=len(matched),
                classes=sum(class_counts.get(p, 0) for p in matched),
                trees=("(repo)",),
                directories=dirs,
                hub=hub,
                hub_fan_in=hub_fan,
                single_tree=True,
            ),
            matched,
        ))
    rows.sort(key=lambda pair: (-pair[0].files, pair[0].module))
    kept = rows[:limit]
    covered = len({path for _, paths in kept for path in paths})
    return tuple(row for row, _ in kept), covered, len(rows) > limit, ()


def _parse_toml(path: Path) -> tuple[_TomlCapability, ...]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    raw = data.get("capability") or data.get("capabilities") or []
    if isinstance(raw, dict):
        # [capabilities.billing] tables
        return tuple(
            _TomlCapability(
                name=str(name), paths=tuple(str(p) for p in (body or {}).get("paths", ()))
            )
            for name, body in sorted(raw.items())
            if isinstance(body, dict) or body is None
        )
    out: list[_TomlCapability] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                out.append(_TomlCapability(name=item, paths=()))
            elif isinstance(item, dict) and "name" in item:
                paths = item.get("paths") or ()
                out.append(
                    _TomlCapability(
                        name=str(item["name"]),
                        paths=tuple(str(p) for p in paths),
                    )
                )
    return tuple(out)


def _match_paths(file_paths: Sequence[str], cap: _TomlCapability) -> tuple[str, ...]:
    if cap.paths:
        rules = [re.compile(f"{translate_path_pattern(pattern)}$") for pattern in cap.paths]
        return tuple(sorted(p for p in file_paths if any(r.match(p) for r in rules)))
    # Human name → same-named path segment (not inventing a name from the tree).
    needle = cap.name.lower()
    matched = [p for p in file_paths if any(seg.lower() == needle for seg in p.split("/")[:-1])]
    return tuple(sorted(matched))


def _busiest(paths: Sequence[str], fan_in: Mapping[str, int]) -> tuple[str, int]:
    if not paths:
        return "", 0
    best = max(paths, key=lambda p: (fan_in.get(p, 0), p))
    return best, fan_in.get(best, 0)


def _from_entries(
    file_paths: Sequence[str],
    *,
    declared_entry_points: Sequence[str],
    graph_entry_files: Sequence[str],
    fan_in: Mapping[str, int],
    class_counts: Mapping[str, int],
    outbound: Mapping[str, tuple[str, ...]],
    limit: int,
) -> tuple[tuple[BusinessModule, ...], bool]:
    seeds = _entry_files(file_paths, declared_entry_points)
    if not seeds:
        # HTTP-layer zero-inbound files from the graph (ticket: "every HTTP-layer entry").
        indexed = set(file_paths)
        seeds = tuple(
            sorted(
                p
                for p in graph_entry_files
                if p in indexed and reading_seed_rank(p) == _HTTP_RANK
            )
        )
    rows: list[BusinessModule] = []
    for path in seeds[:limit]:
        hops = outbound.get(path, ())
        name = Path(path).stem or path
        rows.append(
            BusinessModule(
                module=name,
                label=name,
                files=1,
                classes=class_counts.get(path, 0),
                trees=hops[:8],
                directories=(str(Path(path).parent.as_posix()),),
                hub=path,
                hub_fan_in=fan_in.get(path, 0),
                single_tree=True,
            )
        )
    return tuple(rows), len(seeds) > limit


def _entry_files(file_paths: Sequence[str], patterns: Sequence[str]) -> tuple[str, ...]:
    if not patterns:
        return ()
    rules = [re.compile(f"{translate_path_pattern(p)}$") for p in patterns]
    return tuple(sorted(p for p in file_paths if any(r.match(p) for r in rules)))
