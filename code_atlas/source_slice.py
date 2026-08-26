"""On-disk declaration slices shared by ``read_symbol`` and onboarding read-through (118).

The comment heuristic matches ``read_symbol`` — union of common comment leaders, not a
language-specific parse (R1.1). Identical paths and line numbers yield byte-identical slices (R4.2).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

_COMMENT = re.compile(r"^\s*(#|//|/\*|\*|\*/)")


def comment_block(path: Path, line_start: int) -> str:
    """Contiguous comment lines immediately above ``line_start`` (1-based), joined with newlines."""
    if not path.is_file() or line_start < 1:
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    if line_start > len(lines):
        return ""
    top = _comment_top(lines, line_start)
    if top >= line_start:
        return ""
    return "".join(lines[top - 1 : line_start - 1])


def declaration_slice(
    path: Path, line_start: int, line_end: int, *, include_comments: bool = True
) -> str:
    """Lines ``line_start…line_end`` (1-based, inclusive), with the contiguous comment block above.

    ``include_comments=False`` returns the declaration range alone — no docblock — so the slice
    matches its own ``line_start``/``line_end`` (read_symbol's ``minimal``, task 163 / 8-H).
    """
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    if line_start < 1 or line_start > len(lines):
        return ""
    end = min(max(line_end, line_start), len(lines))
    top = _comment_top(lines, line_start) if include_comments else line_start
    return "".join(lines[top - 1 : end])


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
