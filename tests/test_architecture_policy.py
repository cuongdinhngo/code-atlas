"""Task 307: human-authored architecture budgets over 138/139 evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from code_atlas import check
from code_atlas.architecture_policy import (
    KIND_CONFIRMED_DEPENDENCY,
    KIND_MATRIX_ADDED,
    KIND_MODULES_ADDED,
    KIND_REACHABILITY,
    NOT_MEASURED_INCOMPATIBLE,
    NOT_MEASURED_MISSING_SNAPSHOT,
    NOT_MEASURED_MISSING_SOURCE,
    NOT_MEASURED_SCHEMA,
    NOT_MEASURED_TRUNCATED,
    OUTCOME_CANDIDATE_ONLY,
    OUTCOME_CONFIRMED_BREACH,
    OUTCOME_INVALID_POLICY,
    OUTCOME_NOT_MEASURED,
    OUTCOME_PASSED,
    PolicyRule,
    evaluate_architecture_policy,
    load_policy_from_path,
)
from code_atlas.config import ConfigError
from tests.test_check_cli import _prepare


def test_red_first_blocking_budget_fails_policy_gate_only(tmp_path: Path) -> None:
    """AC — confirmed forbidden dep + budget 0: report green, --policy-gate fails."""
    _prepare(
        tmp_path,
        policies=[
            {
                "id": "deps",
                "kind": KIND_CONFIRMED_DEPENDENCY,
                "budget": 0,
                "blocking": True,
            }
        ],
    )
    code_ok, result_ok = check.run_check(
        tmp_path, base_override="main", skip_build=True
    )
    assert code_ok == check.OK
    outcomes = result_ok["architecture_policy"]["outcomes"]
    assert outcomes[0]["outcome"] == OUTCOME_CONFIRMED_BREACH
    assert "POLICY deps: confirmed_breach" in check.render_text(result_ok)

    code_fail, result_fail = check.run_check(
        tmp_path, base_override="main", policy_gate=True, skip_build=True
    )
    assert code_fail == check.CONFIRMED_VIOLATIONS
    assert result_fail["reason"] == check.REASON_POLICY_BREACH
    assert result_fail["policy_blocking_breaches"] == ["deps"]


def test_heuristic_is_candidate_only_never_fails_gate(tmp_path: Path) -> None:
    _prepare(
        tmp_path,
        heuristic_last=True,
        policies=[
            {
                "id": "deps",
                "kind": KIND_CONFIRMED_DEPENDENCY,
                "budget": 0,
                "blocking": True,
            }
        ],
    )
    code, result = check.run_check(
        tmp_path, base_override="main", policy_gate=True, skip_build=True
    )
    assert code == check.OK
    assert result["architecture_policy"]["outcomes"][0]["outcome"] == OUTCOME_CANDIDATE_ONLY


def test_non_authoritative_reasons_are_distinct() -> None:
    policy = PolicyRule("p", KIND_CONFIRMED_DEPENDENCY, 0, True)
    missing = evaluate_architecture_policy(
        [policy],
        rules_payload={"reason": "rule_matched_no_files", "results": [], "candidates": []},
        diff_payload={"reason": "ok", "diff": {}},
    )[0]
    assert missing.outcome == OUTCOME_NOT_MEASURED
    assert missing.detail == NOT_MEASURED_MISSING_SOURCE

    truncated = evaluate_architecture_policy(
        [policy],
        rules_payload={
            "reason": "ok",
            "truncated": True,
            "results": [],
            "total_count": 0,
            "candidates": [],
        },
        diff_payload={"reason": "ok", "diff": {}},
    )[0]
    assert truncated.detail == NOT_MEASURED_TRUNCATED

    snap = evaluate_architecture_policy(
        [PolicyRule("d", KIND_MODULES_ADDED, 0, True)],
        rules_payload={"reason": "ok", "results": [], "total_count": 0},
        diff_payload={"reason": "snapshot_not_found"},
    )[0]
    assert snap.detail == NOT_MEASURED_MISSING_SNAPSHOT

    schema = evaluate_architecture_policy(
        [PolicyRule("d", KIND_MATRIX_ADDED, 0, True)],
        rules_payload={"reason": "ok", "results": [], "total_count": 0},
        diff_payload={"reason": "dataset_schema_mismatch"},
    )[0]
    assert schema.detail == NOT_MEASURED_SCHEMA


def test_zero_numeric_and_observation_policies_validate(tmp_path: Path) -> None:
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "policies": [
                    {
                        "id": "zero",
                        "kind": KIND_CONFIRMED_DEPENDENCY,
                        "budget": 0,
                        "blocking": True,
                    },
                    {
                        "id": "numeric",
                        "kind": KIND_MODULES_ADDED,
                        "budget": 3,
                        "blocking": True,
                    },
                    {
                        "id": "observe",
                        "kind": KIND_REACHABILITY,
                        "budget": 0,
                        "blocking": False,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    rules = load_policy_from_path(path)
    assert [row.id for row in rules] == ["zero", "numeric", "observe"]
    assert rules[0].budget == 0 and rules[0].blocking is True
    assert rules[1].budget == 3
    assert rules[2].blocking is False


def test_invalid_policy_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"version": 1, "policies": [{"id": "x", "kind": "nope"}]}\n')
    with pytest.raises(ConfigError):
        load_policy_from_path(path)


def test_evaluator_evidence_refs_agree_with_payload_rows() -> None:
    rules_payload = {
        "reason": "ok",
        "truncated": False,
        "total_count": 1,
        "candidate_count": 0,
        "results": [
            {
                "rule_id": "no-http-domain",
                "source_file": "Http/A.aa",
                "forbidden_file": "Domain/B.aa",
                "confidence_tier": "RESOLVED",
            }
        ],
        "candidates": [],
    }
    outcomes = evaluate_architecture_policy(
        [PolicyRule("deps", KIND_CONFIRMED_DEPENDENCY, 0, True)],
        rules_payload=rules_payload,
        diff_payload={"reason": "ok", "unchanged": True, "diff": {}},
    )
    assert outcomes[0].outcome == OUTCOME_CONFIRMED_BREACH
    assert outcomes[0].evidence_refs == ("architecture_rules.results[0]",)
    assert outcomes[0].measured == 1


def test_deterministic_ordering() -> None:
    policies = (
        PolicyRule("a", KIND_MODULES_ADDED, 0, False),
        PolicyRule("b", KIND_MATRIX_ADDED, 1, True),
    )
    diff = {
        "reason": "ok",
        "diff": {"modules_added": ["m1", "m2"], "matrix_added": [("L", "D", 1)]},
    }
    first = evaluate_architecture_policy(
        policies, rules_payload={"reason": "ok", "results": [], "total_count": 0}, diff_payload=diff
    )
    second = evaluate_architecture_policy(
        policies, rules_payload={"reason": "ok", "results": [], "total_count": 0}, diff_payload=diff
    )
    assert first == second
    assert first[0].outcome == OUTCOME_CONFIRMED_BREACH
    assert first[1].outcome == OUTCOME_PASSED


def test_no_repo_or_framework_names_in_module() -> None:
    text = Path(__file__).resolve().parents[1].joinpath(
        "code_atlas/architecture_policy.py"
    ).read_text(encoding="utf-8")
    for banned in ("laravel", "symfony", "django", "flask", "nestjs", "spring"):
        assert banned not in text.lower()


def test_non_blocking_breach_does_not_fail_gate(tmp_path: Path) -> None:
    _prepare(
        tmp_path,
        policies=[
            {
                "id": "observe-deps",
                "kind": KIND_CONFIRMED_DEPENDENCY,
                "budget": 0,
                "blocking": False,
            }
        ],
    )
    code, result = check.run_check(
        tmp_path, base_override="main", policy_gate=True, skip_build=True
    )
    assert code == check.OK
    assert result["architecture_policy"]["outcomes"][0]["outcome"] == OUTCOME_CONFIRMED_BREACH
    assert result["policy_blocking_breaches"] == []


def test_invalid_policy_file_is_operational_never_a_green_gate(tmp_path: Path) -> None:
    """A configured policy that will not parse must stop the run, like 303's malformed_rules."""
    _prepare(
        tmp_path,
        policies=[
            {
                "id": "deps",
                "kind": KIND_CONFIRMED_DEPENDENCY,
                "budget": 0,
                "blocking": True,
            }
        ],
    )
    (tmp_path / "policy.json").write_text(
        json.dumps(
            {"version": 1, "policies": [{"id": "deps", "kind": "typo", "budget": 0,
                                         "blocking": True}]}
        ),
        encoding="utf-8",
    )
    for gate in (False, True):
        code, result = check.run_check(
            tmp_path, base_override="main", policy_gate=gate, skip_build=True
        )
        assert code == check.OPERATIONAL
        assert result["reason"] == OUTCOME_INVALID_POLICY
        assert result["policy_blocking_breaches"] == []
        assert "POLICY invalid:" in check.render_text(result)


def test_unreadable_drift_shape_is_not_measured(tmp_path: Path) -> None:
    """AC5 — evidence whose shape carries neither section cannot read as a measured zero."""
    outcome = evaluate_architecture_policy(
        [PolicyRule("drift", KIND_MODULES_ADDED, 0, True)],
        rules_payload={"reason": "ok", "results": [], "total_count": 0},
        diff_payload={"unrecognised": "shape"},
    )[0]
    assert outcome.outcome == OUTCOME_NOT_MEASURED
    assert outcome.measured is None
    assert outcome.detail == NOT_MEASURED_INCOMPATIBLE


def test_minimal_diff_shape_counts_absent_section_as_zero(tmp_path: Path) -> None:
    """139 at ``minimal`` lists only non-empty sections, so an absent one is a real zero."""
    outcome = evaluate_architecture_policy(
        [PolicyRule("drift", KIND_MODULES_ADDED, 0, True)],
        rules_payload={"reason": "ok", "results": [], "total_count": 0},
        diff_payload={"reason": "ok", "results": [{"section": "matrix_added", "count": 2}]},
    )[0]
    assert outcome.outcome == OUTCOME_PASSED
    assert outcome.measured == 0
