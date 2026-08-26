"""Task 163 — ``read_symbol`` ``minimal`` drops the docblock; ``standard`` keeps it.

Before 163 the two levels were byte-identical. The knob is now real at the slice layer, which is
deterministic and needs no adapter, so it is unit-tested here (the PHP integration path lives in
``test_search_read_outline``).
"""

from __future__ import annotations

from pathlib import Path

from code_atlas.source_slice import declaration_slice

_SRC = (
    "<?php\n"          # 1
    "namespace App;\n"  # 2
    "class Doc\n"       # 3
    "{\n"               # 4
    "    /**\n"          # 5
    "     * Saves the doc.\n"  # 6
    "     */\n"          # 7
    "    public function save(): void\n"  # 8
    "    {\n"            # 9
    "    }\n"            # 10
    "}\n"               # 11
)


def _plant(tmp_path: Path) -> Path:
    php = tmp_path / "Doc.php"
    php.write_text(_SRC, encoding="utf-8")
    return php


def test_standard_slice_carries_the_docblock(tmp_path: Path) -> None:
    """AC1: the full shape includes the contiguous comment block above the declaration."""
    php = _plant(tmp_path)
    standard = declaration_slice(php, 8, 10, include_comments=True)
    assert "Saves the doc" in standard
    assert "function save" in standard


def test_minimal_slice_drops_the_docblock_and_matches_its_range(tmp_path: Path) -> None:
    """AC1 + 8-H: minimal is the declaration range alone, so it matches ``line_start…line_end``."""
    php = _plant(tmp_path)
    minimal = declaration_slice(php, 8, 10, include_comments=False)
    assert "Saves the doc" not in minimal
    assert "function save" in minimal
    # lines 8..10 inclusive == 3 lines, and nothing above them.
    assert len(minimal.splitlines()) == 3


def test_minimal_is_measurably_smaller_than_standard(tmp_path: Path) -> None:
    """AC1: the documented knob now changes the payload — no longer a no-op (061)."""
    php = _plant(tmp_path)
    standard = declaration_slice(php, 8, 10, include_comments=True)
    minimal = declaration_slice(php, 8, 10, include_comments=False)
    assert len(minimal) < len(standard)


def test_include_comments_defaults_true_for_the_onboarding_caller(tmp_path: Path) -> None:
    """R7.1 / 118: the default is unchanged, so read-through enrichment keeps its docblocks."""
    php = _plant(tmp_path)
    assert declaration_slice(php, 8, 10) == declaration_slice(php, 8, 10, include_comments=True)
