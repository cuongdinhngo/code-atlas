"""First-run nomination of entry/stub globs — list only, never apply (268 / 119)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from code_atlas.ignore import translate_path_pattern

# Ecosystem-neutral entry-ish and stub-ish path shapes — not a language branch (R1.1 / R2).
CANDIDATE_ENTRY_GLOBS: tuple[str, ...] = (
    "public/**",
    "bin/**",
    "cmd/**",
    "**/main.*",
    "**/index.*",
    "**/app.*",
)
CANDIDATE_STUB_GLOBS: tuple[str, ...] = (
    "vendor/**",
    "node_modules/**",
)


def _count_matches(paths: Sequence[str], pattern: str) -> int:
    rule = re.compile(f"{translate_path_pattern(pattern)}$")
    return sum(1 for path in paths if rule.match(path))


def nominate_globs(
    paths: Sequence[str],
    *,
    patterns: Sequence[str],
) -> list[dict[str, object]]:
    """One row per pattern with ``files_matched`` — zeros stay visible (119 / 268)."""
    return [
        {"glob": pattern, "files_matched": _count_matches(paths, pattern)}
        for pattern in patterns
    ]


def filesystem_paths(root: Path, *, limit: int = 50_000) -> list[str]:
    """Repo-relative POSIX paths under ``root`` for first-run nomination (no index yet)."""
    found: list[str] = []
    root = root.resolve()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(".git/") or "/.git/" in rel:
            continue
        found.append(rel)
        if len(found) >= limit:
            break
    return found


def entry_point_nominations(paths: Sequence[str]) -> list[dict[str, object]]:
    return nominate_globs(paths, patterns=CANDIDATE_ENTRY_GLOBS)


def stub_root_nominations(paths: Sequence[str]) -> list[dict[str, object]]:
    return nominate_globs(paths, patterns=CANDIDATE_STUB_GLOBS)


__all__ = [
    "CANDIDATE_ENTRY_GLOBS",
    "CANDIDATE_STUB_GLOBS",
    "entry_point_nominations",
    "filesystem_paths",
    "nominate_globs",
    "stub_root_nominations",
]
