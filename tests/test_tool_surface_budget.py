"""Task 434: the model-facing tool surface stays small, and its text carries no ticket references.

Descriptions are read through a built server's ``list_tools()`` — the text a client pays for. The
edge cases a short description drops live in ``docs/TOOLS.md`` *Behaviour by tool*.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

from fastmcp import Client

from code_atlas.main import TOOL_NAMES, build_server
from tests.test_nav_tools import db_config

# 24 tools at 434. compute + verify_refs: the measured minimum after 443 cut both to one line;
# whether to keep this or trim the 24 back under 434's caps is PLAN §19's 443 decision.
TOTAL_DESCRIPTION_CAP = 10_100 + 300
PER_TOOL_CAP = 600
LARGE_TOOL_CAP = 900
LARGE_TOOLS = frozenset({"find_callers", "find_references", "impact"})
# 59,088 chars (json.dumps default separators) before 434; the ticket asks for a 60% cut.
SURFACE_CAP = 23_635 + 2_170  # + compute and verify_refs, mostly their closed schemas (443)

# (NNN), (NNN/NNN), "task NNN", a rule id R1.2 or a plan section sign — never a bare number.
_REFERENCE = re.compile(
    r"\(\d{2,4}(?:\s*[/,;]\s*\d{2,4})*\)|\btask\s+\d{2,3}\b|\bR\d\.\d+\b|§\s*\d+"
)

REPO = Path(__file__).resolve().parent.parent


def _tools(tmp_path: Path) -> list[Any]:
    async def once() -> list[Any]:
        async with Client(build_server(db_config(tmp_path))) as client:
            return list(await client.list_tools())

    return asyncio.run(once())


def over_budget(descriptions: dict[str, str]) -> list[str]:
    """Names of tools over their cap, plus ``<total>`` when the sum is over."""
    bad = [
        n
        for n, d in descriptions.items()
        if len(d) > (LARGE_TOOL_CAP if n in LARGE_TOOLS else PER_TOOL_CAP)
    ]
    if sum(len(d) for d in descriptions.values()) > TOTAL_DESCRIPTION_CAP:
        bad.append("<total>")
    return bad


def references(text: str) -> list[str]:
    return [m.group(0) for m in _REFERENCE.finditer(text)]


def test_the_budget_check_flags_a_planted_over_budget_description() -> None:
    """R6.5: each arm is seen red — a long tool, a long large tool, and a total over the cap."""
    assert over_budget({"search_symbol": "x" * (PER_TOOL_CAP + 1)}) == ["search_symbol"]
    assert over_budget({"impact": "x" * LARGE_TOOL_CAP}) == []
    assert over_budget({"impact": "x" * (LARGE_TOOL_CAP + 1)}) == ["impact"]
    spread = {f"t{i}": "x" * 500 for i in range(23)}
    assert over_budget(spread) == ["<total>"]


def test_the_reference_lint_flags_ticket_and_rule_references_only() -> None:
    """R6.5: forms are matched; a limit or a line count is not a reference."""
    assert references("pages in store order (123)")
    assert references("a union (278/328) of rows")
    assert references("see R5.6 for the shape")
    assert references("carried since task 101")
    assert references("per §19 of the plan")
    assert references("a (1234) ref")
    assert references("a default of limit 100") == []
    assert references("bodies above 600 lines elide") == []
    assert references("capped at 1000 rows") == []


def test_the_descriptions_fit_the_budget_and_carry_no_references(tmp_path: Path) -> None:
    descriptions = {t.name: t.description or "" for t in _tools(tmp_path)}
    assert set(descriptions) == set(TOOL_NAMES)
    assert over_budget(descriptions) == [], {n: len(d) for n, d in descriptions.items()}
    for name, description in descriptions.items():
        assert references(description) == [], f"{name} carries {references(description)}"


def test_the_whole_surface_with_schemas_stays_under_its_cap(tmp_path: Path) -> None:
    """A schema that grows shows up here, not only in the descriptions."""
    total = sum(len(t.description or "") + len(json.dumps(t.inputSchema)) for t in _tools(tmp_path))
    assert total <= SURFACE_CAP, total


def test_the_checks_fail_on_the_surface_before_434() -> None:
    """R6.5: seen red on the real pre-434 descriptions, kept verbatim in TOOLS.md (Behaviour)."""
    tools_md = (REPO / "docs" / "TOOLS.md").read_text(encoding="utf-8")
    section = tools_md.split("## Behaviour by tool", 1)[1].split("\n## ", 1)[0]
    blocks = re.findall(r"### `(\w+)`\n.*?```text\n(.*?)\n```", section, re.DOTALL)
    before = dict(blocks)
    assert len(before) == 24, sorted(before)
    assert "<total>" in over_budget(before)
    assert len(over_budget(before)) > 10
    assert any(references(d) for d in before.values())
