"""Task 034: tokens-to-answer benchmark harness — gate + fixture proving path.

The pure-Python tests exercise the falsifiable gate and the grep/token machinery with no PHP
(a guard that cannot fail is not evidence — so the degraded case must actually raise). The
``@needs_php`` test builds a real fixture index and runs the committed questions end to end.
"""

from __future__ import annotations

import importlib.util
import json
import re
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
    assert "| 4.0 | — | 0 | 100 | 400 | 1/1 | **PASS** (floor ratio 1.0) |" in body
    assert "Recall is a gate; cost is the win." in body
    assert "Sample-tier questions skipped: 2." in body


def test_verdict_markdown_shows_the_failure_reason_when_the_gate_trips() -> None:
    """A failed gate is exactly when the numbers must still render — not just an exit code."""
    rows = [_row("a", atlas=400, grep=100)]
    with pytest.raises(_h.BenchmarkRegressionError) as caught:
        _h.assert_benchmark(rows, min_ratio=1.0)
    body = _h.verdict_markdown(
        _h.aggregate(rows), min_ratio=1.0, failure=str(caught.value), samples_skipped=0
    )
    assert "**FAIL** (floor ratio 1.0)" in body
    assert "below the floor" in body


def test_notice_line_is_a_single_actions_annotation() -> None:
    agg = _h.aggregate([_row("a", atlas=100, grep=400)])
    line = _h.notice_line(agg, min_ratio=1.0, failure=None)
    assert line.startswith("::notice title=Tokens-to-answer::")
    assert "\n" not in line
    assert "ratio=4.0" in line and "correct=1/1" in line
    assert "FAILED" in _h.notice_line(agg, min_ratio=9.0, failure="too low")


def test_score_recall_separates_confidently_wrong_from_partial_miss() -> None:
    """Empty results with non-empty ground truth is confidently_wrong; a partial hit is not."""
    empty = [{"results": []}]
    partial = [{"results": [{"qname": "\\A"}]}]
    empty_score = _h.score_recall(empty, ["\\A", "\\B"])
    partial_score = _h.score_recall(partial, ["\\A", "\\B"])
    assert empty_score["confidently_wrong"] is True
    assert empty_score["recall"] == 0.0
    assert partial_score["confidently_wrong"] is False
    assert partial_score["recall"] == 0.5
    assert partial_score["missing"] == ["\\B"]
    # Native grep hits must not mask empty MCP nav answers on a session recipe.
    session_shaped = [
        {"tool": "grep", "results": ["User.php:12:$repo->put();"], "text": "hit"},
        {"tool": "find_callers", "results": []},
    ]
    session_score = _h.score_recall(session_shaped, ["\\App\\User::save"])
    assert session_score["confidently_wrong"] is True
    assert session_score["recall"] == 0.0
    # An earlier MCP hit must not hide an empty answering step (round-2 defect).
    masked = [
        {"tool": "grep", "results": ["a.php:1: ->put("], "text": "…"},
        {"tool": "search_symbol", "results": [{"qname": "\\App\\Repo::put"}]},
        {"tool": "find_callers", "results": []},
    ]
    masked_score = _h.score_recall(masked, ["\\App\\User::save"])
    assert masked_score["confidently_wrong"] is True
    assert masked_score["recall"] == 0.0
    # Grep text must not earn recall; parent qnames must not match via a child identity.
    leak = _h.score_recall(
        [
            {"tool": "grep", "results": ["x"], "text": "Legacy/Registry.php"},
            {"tool": "find_callers", "results": []},
        ],
        ["Legacy/Registry.php"],
    )
    assert leak["recall"] == 0.0 and leak["confidently_wrong"] is True
    nested = _h.score_recall(
        [{"tool": "find_orphans", "results": [{"qname": "\\Dead\\Unused"}]}],
        ["\\Dead", "\\Dead\\Unused"],
    )
    assert nested["found"] == ["\\Dead\\Unused"]
    assert nested["missing"] == ["\\Dead"]
    assert nested["recall"] == 0.5
    assert nested["confidently_wrong"] is False


def test_recall_gate_fails_when_nav_returns_empty_for_known_set() -> None:
    """Deliberately broken empty nav answer fails the recall floor (AC: broken resolver case)."""
    responses = [{"results": []}]  # empty callers — the 054 failure shape
    score = _h.score_recall(responses, ["\\App\\User::save", "\\App\\Other::touch"])
    row = {
        "id": "broken_empty_callers",
        "atlas_tokens": 10,
        "grep_tokens": 100,
        "atlas_correct": True,  # `expected` substring check can still pass on status crumbs
        "grep_correct": True,
        "ratio": 10.0,
        "ratio_eligible": True,
        **score,
    }
    with pytest.raises(_h.BenchmarkRegressionError, match="confidently_wrong|recall"):
        _h.assert_benchmark([row], min_ratio=None, min_recall=1.0, require_atlas_correct=False)


def test_recall_gate_fails_on_confidently_wrong_and_on_low_recall() -> None:
    rows = [
        {
            "id": "empty",
            "atlas_tokens": 10,
            "grep_tokens": 100,
            "atlas_correct": True,
            "grep_correct": True,
            "ratio": 10.0,
            "ratio_eligible": True,
            "recall": 0.0,
            "confidently_wrong": True,
        }
    ]
    with pytest.raises(_h.BenchmarkRegressionError, match="confidently_wrong|recall"):
        _h.assert_benchmark(rows, min_ratio=None, min_recall=1.0)


def test_recall_gate_passes_when_every_expected_set_is_complete() -> None:
    rows = [
        {
            "id": "ok",
            "atlas_tokens": 10,
            "grep_tokens": 100,
            "atlas_correct": True,
            "grep_correct": True,
            "ratio": 10.0,
            "ratio_eligible": True,
            "recall": 1.0,
            "confidently_wrong": False,
        }
    ]
    agg = _h.assert_benchmark(rows, min_ratio=None, min_recall=1.0)
    assert agg["recall"] == 1.0


def test_aggregate_excludes_ratio_ineligible_from_cost_but_counts_correctness() -> None:
    rows = [
        {**_row("a", atlas=100, grep=400), "ratio_eligible": True},
        {
            **_row("b", atlas=50, grep=0),
            "ratio_eligible": False,
            "grep_tokens": 0,
            "ratio": None,
        },
    ]
    agg = _h.aggregate(rows)
    assert agg["atlas_correct"] == 2
    assert agg["ratio_questions"] == 1
    assert agg["atlas_tokens"] == 100
    assert agg["ratio"] == 4.0


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
    assert "**FAIL** (floor ratio 1.0)" in markdown.read_text(encoding="utf-8")
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
        assert q.get("atlas_path") or q.get("session_path"), f"{q['id']} needs a recipe"
        assert q["expected"]
        source = q.get("source", "fixture")
        if source == "fixture":
            assert (REPO / q["root"]).is_dir(), f"missing fixture root for {q['id']}"
            if q.get("tier") == "symptom":
                assert q.get("session_path"), f"symptom {q['id']} needs session_path"
            if q.get("expected_set") is not None:
                assert q["expected_set"], f"{q['id']}: empty expected_set is not a complete set"
        elif source == "sample":
            # A sample row names a pin in cross_repo_samples.json and states a grep evidence hit.
            assert q["sample"] in pins, f"{q['id']} names unknown pin {q.get('sample')!r}"
            assert q["grep_evidence"], f"sample {q['id']} needs grep_evidence"
        else:
            # Task 045: a `local` row names somebody's machine, so it never lands in this repo.
            raise AssertionError(f"{q['id']}: unexpected source {source!r} in the committed set")
    assert any(q.get("tier") == "whole_graph" for q in questions)
    assert any(q.get("tier") == "symptom" for q in questions)

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
        "checkout_pinned",
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
        assert r["atlas_tokens"] > 0
        if r.get("ratio_eligible", True):
            assert r["grep_tokens"] > 0
    recall_ids = [r["id"] for r in rows if r.get("recall") is not None and r["recall"] < 1.0]
    assert recall_ids == [], f"fixture recall below 1.0: {recall_ids}"
    wrong_empty = [r["id"] for r in rows if r.get("confidently_wrong")]
    assert wrong_empty == [], f"confidently_wrong on fixtures: {wrong_empty}"
    symptom = next(r for r in rows if r["id"] == "symptom_persist_via_put")
    assert symptom["session"]["index_use_share"] is not None
    assert 0.0 < float(symptom["session"]["index_use_share"]) < 1.0
    assert int(symptom["session"]["files_read"]) > 0
    agg = _h.aggregate(rows)
    assert agg["atlas_correct"] == fixture_count
    assert agg["ratio"] > 0.0
    # Same floors ci.yml gates on, so the proving path fails with the gate, not after it.
    _h.assert_benchmark(rows, min_ratio=0.29, min_recall=1.0)

# --- Task 045: the local tier (a repo already on disk, its index reused) --------------------


def test_grep_scan_holds_at_most_max_read_files_bodies(tmp_path: Path) -> None:
    """The bound is applied while collecting: a broad pattern must not buffer the whole tree."""
    for n in range(12):
        (tmp_path / f"f{n:02d}.php").write_text(f"<?php\nclass Hit{n} {{}}\n", encoding="utf-8")
    matches, bodies = _h.grep_scan(tmp_path, re.compile("class Hit"), ["*.php"], 3)

    assert len(bodies) == 3, f"kept {len(bodies)} bodies for a cap of 3"
    assert len(matches) == 12, "every match line is still reported; only bodies are capped"
    assert list(bodies) == ["f00.php", "f01.php", "f02.php"]  # first matches win, deterministically


def test_grep_scan_keeps_nothing_when_nothing_matches(tmp_path: Path) -> None:
    (tmp_path / "a.php").write_text("<?php\n// quiet\n", encoding="utf-8")
    matches, bodies = _h.grep_scan(tmp_path, re.compile("class Repo"), ["*.php"], 20)
    assert matches == [] and bodies == {}


def test_bind_existing_index_fails_loud_and_names_the_missing_path(tmp_path: Path) -> None:
    """A missing index must never read as a zero-token answer (R5.3)."""
    with pytest.raises(FileNotFoundError) as err:
        _h.bind_existing_index(tmp_path)
    assert str(tmp_path) in str(err.value)


def test_bind_existing_index_honours_an_explicit_db_path(tmp_path: Path) -> None:
    db = tmp_path / "elsewhere" / "graph.db"
    db.parent.mkdir(parents=True)
    db.write_bytes(b"")  # presence is what is checked here; the store is not opened
    config = _h.bind_existing_index(tmp_path, db)
    assert config.db_path == db and config.root == tmp_path


def test_run_local_questions_uses_the_tree_in_place(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No copy, no clone, no rebuild — the whole point of the local tier."""
    repo = tmp_path / "on-disk-repo"
    repo.mkdir()
    questions = [
        {"id": "skip-me", "source": "fixture", "root": "tests/fixtures/whatever"},
        {"id": "local-1", "source": "local", "root": str(repo)},
        {"id": "local-2", "source": "local", "root": str(repo)},
    ]
    bound: list[Path] = []

    def fake_bind(root: Path, db_path: Path | None = None) -> object:
        bound.append(root)
        return object()  # sentinel config; evaluate_question is faked too

    monkeypatch.setattr(_h, "bind_existing_index", fake_bind)
    monkeypatch.setattr(
        _h, "build_index", lambda *a, **k: pytest.fail("local tier must not build by default")
    )
    monkeypatch.setattr(
        _h, "prepare_fixture_root", lambda *a, **k: pytest.fail("local tier must not copy the tree")
    )
    monkeypatch.setattr(
        _h, "evaluate_question", lambda cfg, q: {"id": q["id"], "atlas_correct": True}
    )

    rows = _h.run_local_questions(questions, php_cmd="php")

    assert [r["id"] for r in rows] == ["local-1", "local-2"]  # the fixture row is not ours
    assert bound == [repo.resolve()], "one bind per distinct root, and the root is used as given"
    assert not (repo / ".git").exists(), "the local tier must not git-init somebody's repo"
    # Nothing was copied next to it, so the tree really was read where it lies.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["on-disk-repo"]


def test_run_local_questions_builds_only_when_asked(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    built: list[Path] = []
    monkeypatch.setattr(
        _h, "build_index", lambda root, db, cmd: built.append(root) or object()
    )
    monkeypatch.setattr(
        _h, "evaluate_question", lambda cfg, q: {"id": q["id"], "atlas_correct": True}
    )
    questions = [{"id": "l", "source": "local", "root": str(repo)}]

    _h.run_local_questions(questions, php_cmd="php", build=True, workdir=tmp_path / "wd")

    assert built == [repo.resolve()]


def test_run_local_questions_rejects_a_root_that_is_not_a_directory(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    questions = [{"id": "l", "source": "local", "root": str(missing)}]
    with pytest.raises(NotADirectoryError) as err:
        _h.run_local_questions(questions, php_cmd="php")
    assert str(missing) in str(err.value)


def test_local_and_samples_cannot_both_be_selected(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as err:
        _h.main(["--local", "--samples", "--report-out", str(tmp_path / "r.json")])
    assert err.value.code == 2  # argparse usage error, not a silent precedence rule


def test_tier_note_states_which_tier_produced_the_numbers() -> None:
    assert "Local tier" in _h._tier_note(local=True, samples=False)
    assert "outside this repository" in _h._tier_note(local=True, samples=False)
    assert "Sample tier" in _h._tier_note(local=False, samples=True)
    assert "sample_questions_skipped" in _h._tier_note(local=False, samples=False)


def test_local_verdict_markdown_marks_the_numbers_as_not_ours() -> None:
    agg = _h.aggregate([_row("a", atlas=10, grep=100)])
    markdown = _h.verdict_markdown(
        agg, min_ratio=None, failure=None, samples_skipped=0, mode="local"
    )
    assert "local tier" in markdown
    assert "not to this one" in markdown


def test_local_run_does_not_write_the_report_ci_uploads() -> None:
    """CI uploads artifacts/tokens-to-answer-report.json; a local run may name a private repo."""
    assert _h._DEFAULT_LOCAL_REPORT != _h._DEFAULT_REPORT


@needs_php
def test_local_tier_reuses_a_prebuilt_index_and_is_deterministic(tmp_path: Path) -> None:
    """Proving path: build an index once, then measure against it twice with identical results."""
    php_cmd = shlex.join([PHP or "php", str(PHP_ENTRY), "--server"])
    repo = tmp_path / "standin"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "Billing.php").write_text(
        "<?php\nclass Billing {\n    public function charge() { return 1; }\n}\n", encoding="utf-8"
    )
    (repo / "src" / "Caller.php").write_text(
        "<?php\nclass Caller {\n    public function go(Billing $b) { return $b->charge(); }\n}\n",
        encoding="utf-8",
    )
    _h.build_index(repo, repo / ".code-atlas" / "graph.db", php_cmd)

    question = {
        "id": "local-billing",
        "source": "local",
        "root": str(repo),
        "atlas_path": [{"tool": "search_symbol", "args": {"query": "Billing"}}],
        "expected": ["Billing"],
        "grep": {"pattern": "class Billing", "globs": ["*.php"]},
    }
    first = _h.run_local_questions([question], php_cmd=php_cmd)
    second = _h.run_local_questions([question], php_cmd=php_cmd)

    assert len(first) == 1 and first[0]["atlas_correct"]
    assert first[0]["atlas_tokens"] > 0 and first[0]["grep_tokens"] > 0
    assert first == second, "same index + same question must give the same token counts (R4)"
    assert not (repo / ".git").exists()
