"""Task 387 — the agent surfaces name the route subject (385) and the shell route (382–384)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import gen_skill  # noqa: E402

SKILLS = (gen_skill.SKILL_PATH, gen_skill.PLUGIN_SKILL_PATH)


def _query_flags() -> list[str]:
    """Every long flag `code-atlas query` declares, read from its parser (R6.7 — never listed)."""
    tree = ast.parse((REPO / "code_atlas" / "query.py").read_text(encoding="utf-8"))
    return [
        call.args[0].value
        for call in ast.walk(tree)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "add_argument"
        and isinstance(call.args[0], ast.Constant)
        and str(call.args[0].value).startswith("--")
    ]


def _route_lines() -> list[str]:
    return [
        line
        for line in gen_skill.recognition_map()
        if "-> trace_capability" in line and "route=" in line
    ]


def test_which_tool_routes_a_reported_url_to_trace_capability() -> None:
    """AC1: the map carries a route row, and both committed skills carry it verbatim."""
    lines = _route_lines()
    assert len(lines) == 1, f"want one route row naming trace_capability, got {lines}"
    for path in SKILLS:
        assert lines[0] in path.read_text(encoding="utf-8").splitlines(), path


def test_the_brief_and_both_skills_teach_every_query_flag() -> None:
    """AC2: the shell route reaches the brief and the skills — every flag the parser declares."""
    flags = _query_flags()
    assert "--batch" in flags and "--changed-since" in flags, flags
    for path in (gen_skill.AGENT_BRIEF_PATH, *SKILLS):
        text = path.read_text(encoding="utf-8")
        assert "code-atlas query" in text, path
        missing = [flag for flag in flags if f"`{flag}" not in text and f" {flag} " not in text]
        assert not missing, f"{path.name} never names {missing}"


def test_the_brief_has_a_url_occasion_that_selects_trace_capability() -> None:
    """AC2: an occasion for a reported URL, its prose naming route= and routes=."""
    brief = gen_skill.AGENT_BRIEF_PATH.read_text(encoding="utf-8")
    occasions = {title: tools for title, tools in gen_skill.OCCASIONS}
    url = [title for title in occasions if "URL" in title]
    assert url and "trace_capability" in occasions[url[0]], occasions
    assert f"### {url[0]}" in brief
    assert "route=" in brief and "routes=" in brief
