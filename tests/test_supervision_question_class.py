"""The supervision question-class exists and is measured on both axes — task 142.

121 measured the onboarding class one phase after the tools shipped; 138-141 proposed four answers
to a *supervision* question class the harness had never seen — *does this rule still hold*, *what
changed architecturally*, *which modules does this reach*, *can this be split*. Done last this
repeats 121 exactly, so the baseline lands first. These guards keep it from disappearing: it is
present at class size, every recipe answers with a tool, every supervision tool is exercised, the
one question no tool can answer is LABELLED (never scored as a zero), and — because a rule-closure,
drift, rollup or split has no fair grep — the class carries no ratio-eligible question, so it cannot
move the cost ratio the existing classes are gated on (AC5).
"""

from __future__ import annotations

import shlex
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "scripts"
for _p in (str(_REPO), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tokens_to_answer as harness  # noqa: E402 — dev tooling under scripts/

# The four already-shipped tools the class exercises (138 / 139 / 140 / 120). No tool is BUILT here.
SUPERVISION_TOOLS = (
    "check_architecture_rules",
    "diff_architecture",
    "impact_modules",
    "subtree_dependencies",
)
# §5's lesson: a class, not a token — the ticket asks for at least six.
MIN_SUPERVISION_QUESTIONS = 6

PHP = shutil.which("php")
PHP_ENTRY = _REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = _REPO / "adapters" / "php" / "vendor" / "autoload.php"
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)


def _questions() -> list[dict[str, Any]]:
    return harness.load_questions()


def _supervision() -> list[dict[str, Any]]:
    return [q for q in _questions() if q.get("tier") == "supervision"]


def _steps(question: dict[str, Any]) -> list[dict[str, Any]]:
    return list(question.get("atlas_path") or question.get("session_path") or [])


def test_supervision_class_is_present_and_at_size() -> None:
    """The class is in the harness, at class size, gateable from committed fixtures."""
    supervision = _supervision()
    assert len(supervision) >= MIN_SUPERVISION_QUESTIONS, (
        f"the supervision question-class holds {len(supervision)} questions; task 142 needs "
        f"at least {MIN_SUPERVISION_QUESTIONS}"
    )
    sources = {str(q.get("source", "fixture")) for q in supervision}
    assert "fixture" in sources, "the class must be gateable from committed fixtures"


def test_every_supervision_question_answers_with_a_tool() -> None:
    """A recipe that only asks for index status measures nothing (task 121)."""
    for question in _supervision():
        answering = {str(step["tool"]) for step in _steps(question)} - {"get_index_status"}
        assert answering, f"{question['id']} calls no tool that could answer it"


def test_the_class_exercises_every_supervision_tool() -> None:
    """138-141 name four tools; a class that measures three of them is not the class's baseline."""
    covered = {
        str(step["tool"]) for question in _supervision() for step in _steps(question)
    }
    missing = [name for name in SUPERVISION_TOOLS if name not in covered]
    assert not missing, f"the class never exercises: {', '.join(missing)}"


def test_every_supervision_recipe_step_is_a_bindable_tool() -> None:
    """A recipe naming an unbound tool fails at run time, not review time (140/120 bound here)."""
    bindable = set(harness._TOOL_NAMES) | set(harness._NATIVE_TOOLS)
    for question in _supervision():
        for step in _steps(question):
            name = str(step["tool"])
            assert name in bindable, f"{question['id']} names unbindable tool {name!r}"


def test_the_class_is_measured_on_both_axes() -> None:
    """AC3: recall AND precision must each score at least one supervision question.

    A class that declares neither axis is 121's failure again — green while measuring nothing.
    """
    recall_scored = [q for q in _supervision() if q.get("expected_set")]
    precision_scored = [q for q in _supervision() if q.get("precision_scope")]
    assert recall_scored, "no supervision question declares expected_set — recall scores nothing"
    assert precision_scored, "no supervision question declares precision_scope — nothing scored"


def test_the_unanswerable_row_is_labelled_not_scored() -> None:
    """AC3/R4: a question no tool can answer is labelled unanswerable, never scored as a zero."""
    unanswerable = [q for q in _supervision() if q.get("unanswerable")]
    assert unanswerable, (
        "the class must carry the one question no tool answers (141's cut-edge set), "
        "labelled — that is the point of measuring this class"
    )
    for question in unanswerable:
        assert str(question.get("unanswerable_note", "")).strip(), (
            f"{question['id']} is unanswerable but records no reason"
        )
        assert not question.get("expected_set"), (
            f"{question['id']} is unanswerable yet declares an expected_set — nothing to recall"
        )


def test_supervision_class_cannot_move_the_cost_ratio() -> None:
    """AC5: a rule-closure / drift / rollup / split has no fair grep, so every supervision question
    is ratio-ineligible — the class adds zero ratio-eligible rows and cannot move the existing
    classes' cost ratio. Proven empirically in docs/benchmarks/142; asserted here as invariant."""
    for question in _supervision():
        assert question.get("ratio_eligible") is False, (
            f"{question['id']} is ratio-eligible; a supervision question with a grep baseline "
            "would move the cost ratio the existing classes are gated on (AC5)"
        )
        assert str(question.get("ratio_note", "")).strip(), (
            f"{question['id']} is out of the ratio and states no reason (AC3)"
        )


@needs_php
def test_supervision_class_present_and_measured() -> None:
    """Proving test: build the fixtures, run the class end to end, and assert both axes plus the
    labelled-unanswerable row — the recall+precision rows land at 1.0 and nothing is confidently
    wrong, so the baseline this ticket produces is real, not merely declared."""
    php_cmd = shlex.join([PHP or "php", str(PHP_ENTRY), "--server"])
    questions = [q for q in _questions() if q.get("tier") == "supervision"]
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        rows = harness.run_fixture_questions(questions, workdir=Path(td), php_cmd=php_cmd)

    by_id = {str(r["id"]): r for r in rows}
    assert len(rows) == sum(1 for q in questions if q.get("source", "fixture") == "fixture")

    wrong = [r["id"] for r in rows if not r["atlas_correct"]]
    assert wrong == [], f"supervision answers incorrect: {wrong}"

    recall_rows = [r for r in rows if r.get("recall") is not None]
    assert recall_rows, "no supervision row was recall-scored"
    assert all(float(r["recall"]) == 1.0 for r in recall_rows), {
        r["id"]: r["recall"] for r in recall_rows
    }
    assert not any(r.get("confidently_wrong") for r in rows)

    precision_rows = [r for r in rows if r.get("precision") is not None]
    assert precision_rows, "no supervision row was precision-scored"
    assert all(float(r["precision"]) == 1.0 for r in precision_rows), {
        r["id"]: r["precision"] for r in precision_rows
    }

    unanswerable = by_id["sup_can_split_unanswerable"]
    assert unanswerable.get("unanswerable") is True
    assert unanswerable.get("recall") is None  # labelled, not scored as a zero
    assert unanswerable["atlas_correct"] is True
