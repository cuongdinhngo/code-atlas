"""Task 337 — the elision hint names the cap that elided the body, not the default threshold."""

from __future__ import annotations

from pathlib import Path

from code_atlas.source_slice import BODY_LINE_THRESHOLD
from tests.test_read_symbol_body_elision import _plant_method, _tool


def test_max_lines_hint_names_the_caller_cap(tmp_path: Path) -> None:
    """AC1: max_lines=3 on a 7-line body → the hint names 3 and max_lines, not the default."""
    db, qname = _plant_method(tmp_path, lines=7)
    payload = _tool(tmp_path, db)(qname, max_lines=3)
    assert payload["body_elided"] is True
    hint = str(payload["try_instead_hint"])
    assert hint.startswith("body elided above max_lines=3 lines "), hint
    assert str(BODY_LINE_THRESHOLD) not in hint


def test_default_cap_hint_is_byte_identical(tmp_path: Path) -> None:
    """AC2: a 700-line body with no max_lines keeps today's hint, byte for byte (061)."""
    db, qname = _plant_method(tmp_path, lines=700)
    payload = _tool(tmp_path, db)(qname)
    start, end = 5, 5 + 700 - 1
    assert payload["try_instead_hint"] == (
        f"body elided above {BODY_LINE_THRESHOLD} lines "
        f"(declaration {start}–{end}); pass full_body=true for the whole "
        "declaration, or line_start/line_end for a range within the symbol"
    )
