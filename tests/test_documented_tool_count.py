"""Every doc that states a tool count states the same one, derived from ``TOOL_NAMES``.

The count was hand-kept in four files and drifted three ways: `README.md` said 22, `AGENTS.md` 21,
`docs/BACKLOG.md` and `docs/PLAN.md` 17, while the server registered 22. A retro reading the docs to
name its own subject would have been told the wrong surface size by three of the four.

R6.7 is the rule this breaks — a documented count is a duplicate of ``len(TOOL_NAMES)`` with no
derivation. The number stays in the prose because that is where a reader needs it; this test is what
makes it a copy that cannot rot.
"""

import re
from pathlib import Path

import pytest

from code_atlas.main import TOOL_NAMES

REPO = Path(__file__).resolve().parent.parent
# Every doc allowed to state the surface size. A new one either matches or is added here.
DOCS = ("README.md", "AGENTS.md", "docs/PLAN.md", "docs/BACKLOG.md")
COUNT = re.compile(r"(\d+)[ \t]+tools\b")  # same-line only: `\s+` spanned newlines and caught prose


def _claims(name: str) -> list[int]:
    return [int(m) for m in COUNT.findall((REPO / name).read_text(encoding="utf-8"))]


@pytest.mark.parametrize("name", DOCS)
def test_every_documented_tool_count_is_the_registered_one(name: str) -> None:
    registered = len(TOOL_NAMES)
    for claimed in _claims(name):
        assert claimed == registered, f"{name} says {claimed} tools; server registers {registered}"


def test_the_sweep_is_not_vacuous() -> None:
    # R6.5: a regex that matches nothing would pass the parametrised test in silence.
    found = {name: _claims(name) for name in DOCS}
    assert all(found.values()), f"no tool count found in: {[n for n, c in found.items() if not c]}"
