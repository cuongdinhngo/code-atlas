"""Task 034: tokens-to-answer benchmark harness — gate + fixture proving path.

The pure-Python tests exercise the falsifiable gate and the grep/token machinery with no PHP
(a guard that cannot fail is not evidence — so the degraded case must actually raise). The
``@needs_php`` test builds a real fixture index and runs the committed questions end to end.
"""

from __future__ import annotations

import importlib.util
import json
import shlex
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "scripts" / "tokens_to_answer.py"
QUESTIONS = REPO / "scripts" / "tokens_to_answer_questions.json"
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"


def _load_harness():
    spec = importlib.util.spec_from_file_location("tokens_to_answer", HARNESS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_h = _load_harness()

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)


def _row(rid: str, *, atlas: int, grep: int, correct: bool = True) -> dict[str, object]:
    return {
        "id": rid,
        "atlas_tokens": atlas,
        "grep_tokens": grep,
        "atlas_correct": correct,
        "grep_correct": True,
        "ratio": round(grep / atlas, 3) if atlas else 0.0,
    }


def test_estimate_tokens_is_deterministic_and_zero_for_empty() -> None:
    assert _h.estimate_tokens("") == 0
    assert _h.estimate_tokens("abcd") == 1
    assert _h.estimate_tokens("abcde") == 2
    assert _h.estimate_tokens("x" * 40) == _h.estimate_tokens("y" * 40)


def test_aggregate_uses_only_atlas_correct_rows() -> None:
    rows = [
        _row("a", atlas=100, grep=400),
        _row("b", atlas=50, grep=50, correct=False),
    ]
    agg = _h.aggregate(rows)
    assert agg["questions"] == 2
    assert agg["atlas_correct"] == 1
    # The wrong row (b) must not dilute the ratio; only a counts: 400/100 = 4.0.
    assert agg["atlas_tokens"] == 100
    assert agg["ratio"] == 4.0


def test_gate_passes_on_baseline() -> None:
    rows = [_row("a", atlas=100, grep=400), _row("b", atlas=80, grep=240)]
    agg = _h.assert_benchmark(rows, min_ratio=1.5)
    assert agg["ratio"] >= 1.5


def test_gate_fails_when_ratio_regresses() -> None:
    """Deliberately degraded fixture: code-atlas now costs MORE than grep."""
    rows = [_row("a", atlas=400, grep=100)]
    with pytest.raises(_h.BenchmarkRegressionError, match="ratio"):
        _h.assert_benchmark(rows, min_ratio=1.0)


def test_gate_fails_when_atlas_answer_is_wrong() -> None:
    rows = [_row("a", atlas=100, grep=400, correct=False)]
    with pytest.raises(_h.BenchmarkRegressionError, match="wrong/incomplete"):
        _h.assert_benchmark(rows, min_ratio=1.0)


def test_run_grep_path_counts_matches_and_reads_matched_files(tmp_path: Path) -> None:
    (tmp_path / "a.php").write_text("<?php\nclass Repo {}\n", encoding="utf-8")
    (tmp_path / "b.php").write_text("<?php\n// nothing here\n", encoding="utf-8")
    tokens, seen = _h.run_grep_path(tmp_path, {"pattern": "class Repo"})
    assert tokens > 0
    assert "class Repo" in seen
    # b.php did not match, so its body is not part of what the agent read.
    assert "nothing here" not in seen


def test_answer_contains_matches_unescaped_backslash_qnames() -> None:
    """Regression: json-escaping doubled ``\\App`` and broke the substring match (CI #37)."""
    responses = [{"indexed": True, "results": [{"qname": "\\App\\User::save"}]}]
    assert _h.answer_contains(responses, ["\\App\\User::save"])
    assert not _h.answer_contains(responses, ["\\App\\Missing"])


def test_questions_file_is_well_formed() -> None:
    questions = _h.load_questions(QUESTIONS)
    assert len(questions) >= 8
    seen_ids: set[str] = set()
    for q in questions:
        assert q["id"] not in seen_ids, f"duplicate id {q['id']}"
        seen_ids.add(q["id"])
        assert q["atlas_path"] and q["expected"]
        if q.get("source", "fixture") == "fixture":
            assert (REPO / q["root"]).is_dir(), f"missing fixture root for {q['id']}"


def test_questions_file_is_valid_json_on_disk() -> None:
    data = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    assert "questions" in data


@needs_php
def test_harness_answers_fixture_questions_and_reports_ratio(tmp_path: Path) -> None:
    """Proving path: build the real fixtures, run every committed question end to end."""
    php_cmd = shlex.join([PHP or "php", str(PHP_ENTRY), "--server"])
    questions = _h.load_questions(QUESTIONS)
    rows = _h.run_fixture_questions(questions, workdir=tmp_path, php_cmd=php_cmd)

    fixture_count = sum(1 for q in questions if q.get("source", "fixture") == "fixture")
    assert len(rows) == fixture_count
    wrong = [r["id"] for r in rows if not r["atlas_correct"]]
    assert wrong == [], f"code-atlas failed to answer: {wrong}"
    for r in rows:
        assert r["atlas_tokens"] > 0 and r["grep_tokens"] > 0
    agg = _h.aggregate(rows)
    assert agg["atlas_correct"] == fixture_count
    assert agg["ratio"] > 0.0
