"""The Phase-3 cost gate exists and is scored — task 121.

`PHASE3_ONBOARDING.md` §5 gated the whole onboarding phase on an onboarding question-class in
the tokens-to-answer harness plus the recall gate, and the class was never added: M10-M12
shipped unmeasured. These are the guards that keep it from silently disappearing again — the
class is present, every recipe it names is actually bindable, every question the recall gate
should score declares its ground truth, and a question excluded from the cost ratio says why
rather than carrying an invented baseline (AC1/AC3).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "scripts"
for _p in (str(_REPO), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tokens_to_answer as harness  # noqa: E402 — dev tooling under scripts/

ONBOARDING_TOOLS = ("architecture_overview", "guided_tour", "generate_onboarding")
# §5 asked for a class, not a token: three questions is a sample, ten is a class.
MIN_ONBOARDING_QUESTIONS = 8


def _questions() -> list[dict[str, Any]]:
    return harness.load_questions()


def _onboarding() -> list[dict[str, Any]]:
    return [q for q in _questions() if q.get("tier") == "onboarding"]


def _steps(question: dict[str, Any]) -> list[dict[str, Any]]:
    return list(question.get("atlas_path") or question.get("session_path") or [])


def test_onboarding_class_is_present() -> None:
    """§5's gate is in the harness, at class size, and not on one fixture only."""
    onboarding = _onboarding()
    assert len(onboarding) >= MIN_ONBOARDING_QUESTIONS, (
        f"the onboarding question-class holds {len(onboarding)} questions; §5's gate needs "
        f"at least {MIN_ONBOARDING_QUESTIONS} (task 121)"
    )
    sources = {str(q.get("source", "fixture")) for q in onboarding}
    assert "fixture" in sources, "the class must be gateable from committed fixtures"


def test_every_onboarding_question_answers_with_a_tool() -> None:
    """A recipe that only asks for index status measures nothing (task 121)."""
    for question in _onboarding():
        answering = {str(step["tool"]) for step in _steps(question)} - {"get_index_status"}
        assert answering, f"{question['id']} calls no tool that could answer it"


def test_the_class_exercises_every_onboarding_tool() -> None:
    """M10-M12 shipped three tools; a gate that measures two of them is not the phase's gate."""
    covered = {
        str(step["tool"])
        for question in _onboarding()
        for step in _steps(question)
    }
    missing = [name for name in ONBOARDING_TOOLS if name not in covered]
    assert not missing, f"the class never exercises: {', '.join(missing)}"


def test_every_recipe_step_is_a_bindable_tool() -> None:
    """A recipe naming an unbound tool fails at run time, not at review time."""
    bindable = set(harness._TOOL_NAMES) | set(harness._NATIVE_TOOLS)
    for question in _questions():
        for step in _steps(question):
            name = str(step["tool"])
            assert name in bindable, f"{question['id']} names unbindable tool {name!r}"


def test_onboarding_questions_declare_ground_truth_for_recall() -> None:
    """AC1: the recall gate scores the class, so every question pins its complete answer."""
    for question in _onboarding():
        members = question.get("expected_set")
        assert members, f"{question['id']} has no expected_set — recall cannot score it"


def test_a_question_out_of_the_ratio_states_why() -> None:
    """AC3: excluded for a stated reason, never quietly, and never with an invented baseline."""
    for question in _questions():
        eligible = bool(question.get("ratio_eligible", True)) and question.get("grep")
        if eligible:
            continue
        note = str(question.get("ratio_note", "")).strip()
        assert note, f"{question['id']} is out of the cost ratio and states no reason"


def test_recall_sees_an_identity_the_answer_carries_outside_results() -> None:
    """An onboarding answer keys its members on `layer`/`module`, nested below `results`.

    A scorer that reads only ``results`` finds nothing here and reports recall 0 for a
    complete answer — or, with a shorter expected_set, a green gate that measured nothing.
    """
    payload = {
        "tool": "architecture_overview",
        "results": [{"layer": "Shared Library", "modules": 1}],
        "modules": [{"module": "lib/Clock.php", "layer": "Shared Library"}],
        "summary": {"reachability": {"patterns": [{"pattern": "controllers/*.php"}]}},
    }
    found = harness.found_expected_members(
        [payload], ["Shared Library", "lib/Clock.php", "controllers/*.php"]
    )
    assert found == ["Shared Library", "lib/Clock.php", "controllers/*.php"]
