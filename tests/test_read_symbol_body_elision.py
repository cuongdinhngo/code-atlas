"""Task 288 — large ``read_symbol`` bodies elide by default; full body and ranges stay reachable."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.source_slice import BODY_LINE_THRESHOLD
from code_atlas.store import CAPABILITIES_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import read_symbol


def _plant_method(tmp_path: Path, *, lines: int, name: str = "fat") -> tuple[Path, str]:
    """Plant a PHP method whose declaration span is exactly ``lines`` lines."""
    if lines < 3:
        raise ValueError("need at least signature + braces")
    db = tmp_path / "graph.db"
    rel = "Fat.php"
    body_n = lines - 3  # signature, opening `{`, closing `}`
    src = (
        "<?php\n"
        "namespace App;\n"
        "class Fat\n"
        "{\n"
        f"    public function {name}(): void\n"
        "    {\n" + ("        $x = 1;\n" * body_n) + "    }\n"
        "}\n"
    )
    target = tmp_path / rel
    target.write_text(src, encoding="utf-8")
    text_lines = src.splitlines()
    decl_start = next(i for i, line in enumerate(text_lines, start=1) if f"function {name}" in line)
    decl_end = next(
        i for i in range(decl_start + 1, len(text_lines) + 1) if text_lines[i - 1] == "    }"
    )
    assert decl_end - decl_start + 1 == lines, (decl_start, decl_end, lines)
    digest = hashlib.sha256(src.encode()).hexdigest()
    node = {
        "kind": "Method",
        "name": name,
        "qualified_name": f"\\App\\Fat::{name}",
        "file_path": rel,
        "line_start": decl_start,
        "line_end": decl_end,
        "params": [],
    }
    with GraphStore(db) as store:
        store.upsert_file(rel, digest, "php")
        store.replace_file_rows(rel, [node], [])
        store.set_meta(CAPABILITIES_BY_LANGUAGE_KEY, json.dumps({"php": {"params": True}}))
    return db, f"\\App\\Fat::{name}"


def _tool(tmp_path: Path, db: Path):
    return read_symbol.create(replace(load_config(tmp_path, {}), db_path=db))


def test_below_threshold_byte_identical_at_both_detail_levels(tmp_path: Path) -> None:
    """AC4 + AC7: under the threshold, no elision fields; minimal still drops only the docblock."""
    lines = BODY_LINE_THRESHOLD  # at threshold stays whole ("above", not "at or above")
    db, qname = _plant_method(tmp_path, lines=lines)
    tool = _tool(tmp_path, db)
    standard = tool(qname)
    minimal = tool(qname, detail_level="minimal")
    assert standard["found"] is True
    assert "body_elided" not in standard
    assert "line_count" not in standard
    assert "$x = 1" in str(standard["source"])
    assert len(str(minimal["source"]).splitlines()) == lines
    assert "body_elided" not in minimal


def test_above_threshold_elides_with_route_and_count(tmp_path: Path) -> None:
    """AC1 + AC5 + AC6: elided answer is distinguishable and names a route."""
    lines = BODY_LINE_THRESHOLD + 1
    db, qname = _plant_method(tmp_path, lines=lines)
    tool = _tool(tmp_path, db)
    payload = tool(qname)
    assert payload["body_elided"] is True
    assert payload["line_count"] == lines
    assert payload["try_instead"] == "file_outline"
    assert str(BODY_LINE_THRESHOLD) in str(payload["try_instead_hint"])
    assert "$x = 1" not in str(payload["source"])
    assert "function fat" in str(payload["source"])
    # 163: even when elided, minimal's source matches its reported range.
    minimal = tool(qname, detail_level="minimal")
    assert minimal["body_elided"] is True
    assert minimal["line_start"] == minimal["line_end"]
    assert len(str(minimal["source"]).splitlines()) == 1


def test_full_body_opt_in_returns_whole_declaration(tmp_path: Path) -> None:
    """AC2: the whole body stays reachable in one call."""
    lines = BODY_LINE_THRESHOLD + 50
    db, qname = _plant_method(tmp_path, lines=lines)
    tool = _tool(tmp_path, db)
    payload = tool(qname, full_body=True)
    assert "body_elided" not in payload
    assert str(payload["source"]).count("$x = 1") == lines - 3


def test_line_range_inside_symbol_returns_exact_lines(tmp_path: Path) -> None:
    """AC3: a clamped range returns exactly those lines from the parse bounds."""
    lines = BODY_LINE_THRESHOLD + 20
    db, qname = _plant_method(tmp_path, lines=lines)
    tool = _tool(tmp_path, db)
    # Ask for a middle band of the method body (past the signature + open brace).
    payload = tool(qname, line_start=10, line_end=14)
    assert "body_elided" not in payload
    assert payload["line_start"] == 10
    assert payload["line_end"] == 14
    got = str(payload["source"]).splitlines()
    assert len(got) == 5
    assert all("$x = 1" in line for line in got)


def test_max_lines_caller_cap_elides_earlier(tmp_path: Path) -> None:
    """Design: optional max_lines is a caller cap beside the automatic route."""
    db, qname = _plant_method(tmp_path, lines=50)
    tool = _tool(tmp_path, db)
    payload = tool(qname, max_lines=10)
    assert payload["body_elided"] is True
    assert payload["line_count"] == 50


def test_threshold_named_in_tool_description(tmp_path: Path) -> None:
    """AC6: the threshold is stated in the tool description and defined once."""
    tool = _tool(tmp_path, tmp_path / "missing.db")
    assert str(BODY_LINE_THRESHOLD) in (tool.__doc__ or "")
