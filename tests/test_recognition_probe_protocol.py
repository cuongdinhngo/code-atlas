"""Task 097 — the recognition probe measures descriptions and recall, not just names.

Round 5 scored 14/14 off a name list while 7 descriptions were never loaded, and named
``file_outline`` then never called it. The protocol now records resident descriptions,
marks each answer, scores two rates, and Q4 is occasion-worded so a name list can miss.
Intended tools are derived from ``main.TOOL_NAMES`` (R1.1 / derived-not-listed).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from code_atlas.main import TOOL_NAMES

REPO = Path(__file__).resolve().parent.parent
PROBE = REPO / "docs" / "runbooks" / "tool-recognition-probe.md"
RETRO = REPO / "docs" / "runbooks" / "field-retro.md"
_ROW = re.compile(r"^\| (\d+) \| (.+) \| `([a-z_]+)` \|$", re.MULTILINE)


def _probe_rows(text: str) -> list[tuple[str, str, str]]:
    return [(num, question, name) for num, question, name in _ROW.findall(text)]


def _assert_probe_covers(tool_names: tuple[str, ...], text: str) -> None:
    intended = [name for _, _, name in _probe_rows(text)]
    missing = sorted(set(tool_names) - set(intended))
    extra = sorted(set(intended) - set(tool_names))
    assert not missing and not extra, (
        f"probe intended-tools drifted from TOOL_NAMES: missing={missing} extra={extra}"
    )
    dups = sorted({name for name in intended if intended.count(name) > 1})
    assert not dups, f"probe lists a tool more than once: {dups}"


def test_probe_requires_resident_marking_and_two_rates() -> None:
    """Proving: a name-only 14/14 cannot be read as an 081 score.

    Fails pre-097: the probe had one undifferentiated recognised/total and no markings.
    """
    text = PROBE.read_text(encoding="utf-8")
    assert "resident" in text.lower()
    assert "name-only" in text
    assert "description-backed" in text
    assert "NOT OBSERVED" in text


def test_file_outline_question_is_not_answerable_from_the_name() -> None:
    """Q4 is the discriminating shape: a bare name list that says 'outline' is a miss."""
    rows = _probe_rows(PROBE.read_text(encoding="utf-8"))
    question = next(q for _, q, name in rows if name == "file_outline")
    assert "outline" not in question.lower()
    assert "file_outline" not in question.lower()


def test_probe_intended_tools_are_exactly_the_surface() -> None:
    _assert_probe_covers(TOOL_NAMES, PROBE.read_text(encoding="utf-8"))


def test_the_probe_surface_guard_can_actually_fail() -> None:
    """A new tool without a probe row must trip the guard — else it is not a guard (093)."""
    text = PROBE.read_text(encoding="utf-8")
    with pytest.raises(AssertionError, match="not_a_real_tool"):
        _assert_probe_covers((*TOOL_NAMES, "not_a_real_tool"), text)


def test_retro_template_asks_for_resident_count_and_four_buckets() -> None:
    text = RETRO.read_text(encoding="utf-8")
    assert "0.a" in text
    assert "server_version" in text
    assert "server_build" in text
    assert "0.5" in text
    assert "name-only" in text
    assert "description-backed" in text
    assert "knew it, it fit, did not think of it" in text
    assert "workflow trigger" in text


def test_file_outline_description_names_the_occasion_after_the_opener() -> None:
    src = (REPO / "code_atlas" / "tools" / "file_outline.py").read_text(encoding="utf-8")
    opener = '"""What does this file define, and on what lines — without printing the source?'
    occasion = "Call this before you read or port a large file"
    assert opener in src
    assert occasion in src
    # 069 keeps the question first; the 097 occasion follows it, never replaces it.
    assert src.index(opener) < src.index(occasion)


def test_onboarding_names_the_file_outline_occasion() -> None:
    text = (REPO / "docs" / "runbooks" / "onboarding-a-repo.md").read_text(encoding="utf-8")
    assert "Before you read or port a large file, call `file_outline`" in text

