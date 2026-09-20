"""Task 309: the recall measurement is honest about its bar, its labels and its misses.

The numbers themselves come from `scripts/test_impact_recall.py` over real upstream commits and
cannot be re-derived here without a network and four adapters. What IS guarded here is everything
that would let a reader misread them: a verdict that does not follow the pre-registered bar, a
cause split that does not reconcile, a precision claim the labels cannot support, a committed
benchmark that drifted from the bar, and any wording that reads as permission to skip a test.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from code_atlas.candidate_tests import assert_no_selective_language
from scripts.test_impact_recall import (
    BAR,
    CAUSES,
    VERDICT_ELIGIBLE,
    VERDICT_INSUFFICIENT,
    VERDICT_RETAINED,
    CorpusDriftError,
    aggregate,
    load_corpus,
    render_text,
    verdict_for,
)

REPO = Path(__file__).resolve().parent.parent
BENCHMARK = REPO / "docs" / "benchmarks" / "309_test-impact-recall.md"
REPORTER = REPO / "scripts" / "test_impact_recall.py"
CORPUS_PATH = REPO / "scripts" / "test_impact_corpus.json"


def _row(
    sample: str, language: str, labelled: int, matched: int, causes: dict[str, str] | None = None
):
    expected = [f"tests/{sample}_{i}.py" for i in range(labelled)]
    return {
        "sample_id": sample,
        "language": language,
        "expected_test_files": expected,
        "matched": expected[:matched],
        "miss_causes": causes if causes is not None else {p: CAUSES[0] for p in expected[matched:]},
        "recall": (matched / labelled) if labelled else None,
    }


def _head(root: Path) -> str:
    done = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def _rows(total: int, matched: int):
    """``total`` one-label scenarios spread over the registered minimum repos and languages."""
    assert total >= BAR["min_scenarios"]
    names = [("a", "python"), ("b", "php"), ("c", "typescript")]
    out = []
    for index in range(total):
        sample, language = names[index % len(names)]
        out.append(_row(f"{sample}{index}", language, 1, 1 if index < matched else 0))
    return out


# --------------------------------------------------------------------- the bar


def test_the_verdict_is_read_off_the_pre_registered_bar_at_its_boundaries() -> None:
    """AC5 — the thresholds decide, not the reader; each boundary value lands on its own side."""
    # 20 scenarios make both thresholds land on a whole scenario, so each side is exact.
    total = 20
    promote = int(BAR["promote_recall"] * total)
    retain = int(BAR["retain_recall"] * total)
    assert verdict_for(_rows(total, promote), BAR)[0] == VERDICT_ELIGIBLE
    assert verdict_for(_rows(total, promote - 1), BAR)[0] == VERDICT_RETAINED
    assert verdict_for(_rows(total, retain), BAR)[0] == VERDICT_RETAINED
    assert verdict_for(_rows(total, retain - 1), BAR)[0] == VERDICT_INSUFFICIENT


def test_a_corpus_below_the_floor_is_insufficient_however_perfect_the_recall() -> None:
    """AC5's failure mode (R6.8): a flawless run on too little evidence must not promote."""
    tiny = [_row("a", "python", 3, 3)]
    name, recall, reason = verdict_for(tiny, BAR)
    assert recall == 1.0
    assert name == VERDICT_INSUFFICIENT
    assert "corpus floor not met" in reason


def test_one_language_short_of_the_floor_cannot_promote() -> None:
    """The floor is three numbers, not one — a 12-scenario single-language run is still short."""
    rows = [_row(f"a{i}", "python", 1, 1) for i in range(BAR["min_scenarios"])]
    assert verdict_for(rows, BAR)[0] == VERDICT_INSUFFICIENT


# --------------------------------------------------------------- the cause split


def test_cause_totals_that_do_not_reconcile_are_a_failure_not_a_footnote() -> None:
    """AC4 — an unexplained miss must stop the report (observed failing, R6.5)."""
    rows = _rows(12, 11)
    for row in rows:
        row["miss_causes"] = {}
    with pytest.raises(AssertionError, match="do not reconcile"):
        aggregate(rows, BAR)


def test_every_cause_the_reporter_can_emit_is_documented_in_the_benchmark() -> None:
    """R6.7 — the cause set is derived from the module, never re-typed in the doc's table."""
    text = BENCHMARK.read_text(encoding="utf-8")
    missing = [cause for cause in CAUSES if f"`{cause}`" not in text]
    assert not missing, f"benchmark does not document {missing}"


def test_the_aggregate_reconciles_and_refuses_to_claim_precision() -> None:
    """Scope item 3 — non-exhaustive labels can carry recall and must not carry precision."""
    summary = aggregate(_rows(12, 9), BAR)
    assert summary["matched"] + summary["missed"] == summary["labelled_test_files"]
    assert sum(summary["miss_causes"].values()) == summary["missed"]
    assert summary["precision"] is None
    assert "exhaustive" in summary["precision_not_computed_because"]


# ------------------------------------------------------------------- the corpus


def test_the_committed_corpus_clears_the_floor_it_pre_registered() -> None:
    corpus = load_corpus(CORPUS_PATH)
    scenarios = corpus["scenarios"]
    assert len(scenarios) >= BAR["min_scenarios"]
    assert len({s["sample_id"] for s in scenarios}) >= BAR["min_repos"]
    assert len({s["language"] for s in scenarios}) >= BAR["min_languages"]


def test_every_scenario_names_its_revisions_labels_and_how_they_were_verified() -> None:
    """AC2 — base/head, changed paths, expected tests, collection method and ground truth."""
    corpus = load_corpus(CORPUS_PATH)
    assert "co-change" in corpus["ground_truth"]["collection_method"]
    assert corpus["ground_truth"]["labels_exhaustive"] is False
    for scenario in corpus["scenarios"]:
        for field in ("base", "head", "url", "hand_verification"):
            assert scenario[field], f"{scenario['id']} is missing {field}"
        assert len(scenario["base"]) == 40 and len(scenario["head"]) == 40
        assert scenario["changed_production_paths"], scenario["id"]
        assert scenario["expected_test_files"], scenario["id"]
        assert scenario["labels_exhaustive"] is False


def test_the_selection_rule_and_its_rejections_are_recorded() -> None:
    """A reverse-chronological pick is only honest if what it threw out is written down."""
    corpus = load_corpus(CORPUS_PATH)
    assert "reverse-chronological" in corpus["selection_rule"]
    for rejected in corpus["rejected"]:
        assert rejected["reason"]


def test_a_label_that_no_longer_matches_its_commit_is_refused(tmp_path: Path) -> None:
    """The corpus is data about someone else's repo, so drift is a refusal, not a warning."""
    from scripts.test_impact_recall import verify_labels

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "thing.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_thing.py").write_text("y = 1\n", encoding="utf-8")
    git("init", "-q", ".")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    git("add", "-A")
    git("commit", "-qm", "base")
    base = _head(tmp_path)
    (tmp_path / "src" / "thing.py").write_text("x = 2\n", encoding="utf-8")
    (tmp_path / "tests" / "test_thing.py").write_text("y = 2\n", encoding="utf-8")
    git("commit", "-qam", "change")
    head = _head(tmp_path)

    honest = {
        "id": "fixture", "language": "python", "base": base, "head": head,
        "changed_production_paths": ["src/thing.py"],
        "expected_test_files": ["tests/test_thing.py"],
    }
    verify_labels(honest, tmp_path)
    drifted = {**honest, "expected_test_files": ["tests/test_other.py"]}
    with pytest.raises(CorpusDriftError, match="expected_test_files"):
        verify_labels(drifted, tmp_path)


# ----------------------------------------------------- nothing reads as a skip


def test_no_309_artifact_suggests_skipping_an_unlisted_test() -> None:
    """AC6 — the guard 308 ships, pointed at everything 309 adds."""
    for path in (REPORTER, CORPUS_PATH, BENCHMARK):
        assert_no_selective_language(path.read_text(encoding="utf-8"))


def test_the_rendered_report_carries_the_full_suite_statement() -> None:
    """R6.9 — assert what the reader is handed, not the constant it was built from."""
    payload = {
        "bar": BAR,
        "provenance": {"code_atlas_commit": "0" * 40, "contract_version": 10,
                       "python": "3.13.14", "host": "fixture"},
        "scenarios": _rows(12, 9),
        "aggregate": aggregate(_rows(12, 9), BAR),
    }
    for row in payload["scenarios"]:
        row.setdefault("id", row["sample_id"])
    text = render_text(payload)
    assert "full suite remains authoritative" in text
    assert "VERDICT:" in text


# ------------------------------------------------------- the committed verdict


def _recorded_aggregate() -> dict:
    """The one machine-readable block in the benchmark — the numbers a reader is quoting."""
    blocks = re.findall(r"```json\n(.*?)\n```", BENCHMARK.read_text(encoding="utf-8"), re.S)
    assert len(blocks) == 1, "the benchmark must carry exactly one recorded-measurement block"
    return json.loads(blocks[0])


def test_the_benchmark_records_the_verdict_its_own_numbers_dictate() -> None:
    """AC5 at the consumer: recompute the verdict from the committed counts, not from the label."""
    recorded = _recorded_aggregate()
    assert recorded["matched"] + recorded["missed"] == recorded["labelled_test_files"]
    assert sum(recorded["miss_causes"].values()) == recorded["missed"]
    assert set(recorded["miss_causes"]) == set(CAUSES)

    floor_met = (
        recorded["scenarios"] >= BAR["min_scenarios"]
        and len(recorded["repos"]) >= BAR["min_repos"]
        and len(recorded["languages"]) >= BAR["min_languages"]
    )
    recall = recorded["recall_micro"]
    if not floor_met:
        expected = VERDICT_INSUFFICIENT
    elif recall >= BAR["promote_recall"]:
        expected = VERDICT_ELIGIBLE
    elif recall >= BAR["retain_recall"]:
        expected = VERDICT_RETAINED
    else:
        expected = VERDICT_INSUFFICIENT
    assert recorded["verdict"] == expected
    assert recorded["matched"] / recorded["labelled_test_files"] == pytest.approx(recall, abs=5e-5)


def test_the_benchmark_table_agrees_with_the_block_it_sits_beside() -> None:
    """Two renderings of one measurement drift; the test is what stops the table lying."""
    recorded = _recorded_aggregate()
    text = BENCHMARK.read_text(encoding="utf-8")
    rows = re.findall(r"^\| `([^`]+)` \| \w+ \| (\d+) / (\d+) \|", text, re.M)
    assert len(rows) == recorded["scenarios"]
    assert sum(int(m) for _, m, _ in rows) == recorded["matched"]
    assert sum(int(t) for _, _, t in rows) == recorded["labelled_test_files"]
