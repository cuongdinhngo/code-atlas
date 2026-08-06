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
SAMPLE_PINS = REPO / "scripts" / "cross_repo_samples.json"
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


def test_verdict_markdown_reports_the_numbers_and_the_pass_verdict() -> None:
    agg = _h.aggregate([_row("a", atlas=100, grep=400)])
    body = _h.verdict_markdown(agg, min_ratio=1.0, failure=None, samples_skipped=2)
    assert _h.COMMENT_MARKER in body  # CI edits its own comment by this marker
    assert "| 4.0 | 100 | 400 | 1/1 | **PASS** (floor 1.0) |" in body
    assert "Sample-tier questions skipped: 2." in body


def test_verdict_markdown_shows_the_failure_reason_when_the_gate_trips() -> None:
    """A failed gate is exactly when the numbers must still render — not just an exit code."""
    rows = [_row("a", atlas=400, grep=100)]
    with pytest.raises(_h.BenchmarkRegressionError) as caught:
        _h.assert_benchmark(rows, min_ratio=1.0)
    body = _h.verdict_markdown(
        _h.aggregate(rows), min_ratio=1.0, failure=str(caught.value), samples_skipped=0
    )
    assert "**FAIL** (floor 1.0)" in body
    assert "below the floor" in body


def test_notice_line_is_a_single_actions_annotation() -> None:
    agg = _h.aggregate([_row("a", atlas=100, grep=400)])
    line = _h.notice_line(agg, min_ratio=1.0, failure=None)
    assert line.startswith("::notice title=Tokens-to-answer::")
    assert "\n" not in line
    assert "ratio=4.0" in line and "correct=1/1" in line
    assert "FAILED" in _h.notice_line(agg, min_ratio=9.0, failure="too low")


def test_markdown_and_notice_are_emitted_even_when_the_gate_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI contract CI depends on: exit 1 on a breach, and the report still lands."""
    degraded = [_row("a", atlas=400, grep=100)]
    monkeypatch.setattr(_h, "run_fixture_questions", lambda *a, **k: degraded)
    questions = tmp_path / "q.json"
    questions.write_text(json.dumps({"questions": [{"id": "a"}]}), encoding="utf-8")
    markdown = tmp_path / "verdict.md"
    code = _h.main(
        [
            "--questions", str(questions),
            "--report-out", str(tmp_path / "report.json"),
            "--workdir", str(tmp_path / "work"),
            "--min-ratio", "1.0",
            "--markdown", str(markdown),
            "--notice",
        ]
    )
    assert code == 1
    assert "**FAIL** (floor 1.0)" in markdown.read_text(encoding="utf-8")
    assert "::notice title=Tokens-to-answer::" in capsys.readouterr().out


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
    pins = {str(s["id"]) for s in json.loads(SAMPLE_PINS.read_text(encoding="utf-8"))["samples"]}
    seen_ids: set[str] = set()
    for q in questions:
        assert q["id"] not in seen_ids, f"duplicate id {q['id']}"
        seen_ids.add(q["id"])
        assert q["atlas_path"] and q["expected"]
        source = q.get("source", "fixture")
        if source == "fixture":
            assert (REPO / q["root"]).is_dir(), f"missing fixture root for {q['id']}"
        elif source == "sample":
            # A sample row names a pin in cross_repo_samples.json and states a grep evidence hit.
            assert q["sample"] in pins, f"{q['id']} names unknown pin {q.get('sample')!r}"
            assert q["grep_evidence"], f"sample {q['id']} needs grep_evidence"


def test_run_sample_questions_selects_and_routes_by_pin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Proving test (task 042): only source:sample rows run, grouped by pin, each built once."""
    questions = [
        {"id": "fix", "source": "fixture", "root": "x"},
        {"id": "a1", "source": "sample", "sample": "brick_math"},
        {"id": "a2", "source": "sample", "sample": "brick_math"},
        {"id": "b1", "source": "sample", "sample": "symfony_demo"},
    ]
    built: list[str] = []
    monkeypatch.setattr(
        _h.cross_repo_validate,
        "load_manifest",
        lambda *a, **k: [{"id": "brick_math"}, {"id": "symfony_demo"}],
    )
    monkeypatch.setattr(
        _h.cross_repo_validate,
        "_ensure_checkout",
        lambda sample, cache_root: cache_root / str(sample["id"]),
    )

    def fake_build(root: Path, db_path: Path, php_cmd: str) -> object:
        built.append(root.name)
        return object()  # sentinel config; evaluate_question is faked too

    monkeypatch.setattr(_h, "build_index", fake_build)
    monkeypatch.setattr(
        _h, "evaluate_question", lambda cfg, q: {"id": q["id"], "atlas_correct": True}
    )

    rows = _h.run_sample_questions(
        questions, cache_root=tmp_path, php_cmd="php", skip_clone=False
    )

    assert [r["id"] for r in rows] == ["a1", "a2", "b1"]  # fixture row excluded
    assert sorted(built) == ["brick_math", "symfony_demo"]  # each pin built exactly once


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
