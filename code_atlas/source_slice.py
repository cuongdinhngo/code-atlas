"""On-disk declaration slices shared by ``read_symbol`` and onboarding read-through (118).

The comment heuristic matches ``read_symbol`` — union of common comment leaders, not a
language-specific parse (R1.1). Identical paths and line numbers yield byte-identical slices (R4.2).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from code_atlas.containment import resolves_inside

# One site for the body-size default (288 / R6.7). Above this, ``read_symbol`` elides by default.
# 600 keeps the field's decisive 508-line read whole and degrades the wasteful 720-line case.
BODY_LINE_THRESHOLD = 600

_COMMENT = re.compile(r"^\s*(#|//|/\*|\*|\*/)")


def declaration_line_count(line_start: int, line_end: int) -> int:
    """Inclusive span of a node's declaration range (1-based)."""
    if line_end < line_start:
        return 0
    return line_end - line_start + 1


def clamp_line_range(
    line_start: int, line_end: int, *, from_line: int, to_line: int
) -> tuple[int, int]:
    """Clamp a caller range to the node's parse bounds (288)."""
    lo = max(line_start, min(from_line, to_line))
    hi = min(line_end, max(from_line, to_line))
    if hi < lo:
        return line_start, line_start
    return lo, hi


def comment_block(path: Path, line_start: int, *, root: Path) -> str:
    """Contiguous comment lines immediately above ``line_start`` (1-based), joined with newlines."""
    if not readable(root, path) or line_start < 1:
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    if line_start > len(lines):
        return ""
    top = _comment_top(lines, line_start)
    if top >= line_start:
        return ""
    return "".join(lines[top - 1 : line_start - 1])


def declaration_slice(
    path: Path, line_start: int, line_end: int, *, root: Path, include_comments: bool = True
) -> str:
    """Lines ``line_start…line_end`` (1-based, inclusive), with the contiguous comment block above.

    ``include_comments=False`` returns the declaration range alone — no docblock — so the slice
    matches its own ``line_start``/``line_end`` (read_symbol's ``minimal``, task 163 / 8-H).
    """
    if not readable(root, path):
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    if line_start < 1 or line_start > len(lines):
        return ""
    end = min(max(line_end, line_start), len(lines))
    top = _comment_top(lines, line_start) if include_comments else line_start
    return "".join(lines[top - 1 : end])


def readable(root: Path, path: Path) -> bool:
    """A file whose text may leave: it exists and resolves inside ``root``, symlinks followed (375).

    Containment is checked at index time too, but an indexed file can become a link out later.
    """
    return path.is_file() and resolves_inside(root, path)


def _comment_top(lines: Sequence[str], line_start: int) -> int:
    """Walk upward from the line above ``line_start`` while lines look like comments."""
    top = line_start
    index = line_start - 1
    while index >= 1:
        text = lines[index - 1]
        if not text.strip():
            break
        if not _COMMENT.match(text):
            break
        top = index
        index -= 1
    return top
