"""Human-authored architecture budgets over 138/139 evidence (task 307).

A pure evaluator: identical policy + evidence → identical ordered outcomes (R4.2). The core ships
vocabulary and validation only — never project thresholds or framework names (R2). Candidate,
truncated, stale or incompatible evidence never satisfies a policy or fails as a confirmed breach.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from code_atlas.config import Config, ConfigError
from code_atlas.tools.nav_result import (
    REASON_CAPABILITY_NOT_CONFIGURED,
    REASON_OK,
    REASON_RULE_MATCHED_NO_FILES,
    REASON_SNAPSHOT_NOT_FOUND,
)

POLICY_VERSION = 1

OUTCOME_PASSED = "passed"
OUTCOME_CONFIRMED_BREACH = "confirmed_breach"
OUTCOME_CANDIDATE_ONLY = "candidate_only"
OUTCOME_NOT_MEASURED = "not_measured"
OUTCOME_INVALID_POLICY = "invalid_policy"

KIND_CONFIRMED_DEPENDENCY = "confirmed_dependency_violations"
KIND_MODULES_ADDED = "modules_added"
KIND_MATRIX_ADDED = "matrix_added"
KIND_REACHABILITY = "reachability_deltas"

KINDS: frozenset[str] = frozenset(
    {
        KIND_CONFIRMED_DEPENDENCY,
        KIND_MODULES_ADDED,
        KIND_MATRIX_ADDED,
        KIND_REACHABILITY,
    }
)

NOT_MEASURED_MISSING_SOURCE = "missing_source_matches"
NOT_MEASURED_MISSING_SNAPSHOT = "missing_snapshot"
NOT_MEASURED_TRUNCATED = "truncated_walk"
NOT_MEASURED_SCHEMA = "schema_mismatch"
NOT_MEASURED_STALE = "stale_evidence"
NOT_MEASURED_INCOMPATIBLE = "incompatible_evidence"
NOT_MEASURED_UNCONFIGURED = "capability_not_configured"

__all__ = [
    "KINDS",
    "KIND_CONFIRMED_DEPENDENCY",
    "KIND_MATRIX_ADDED",
    "KIND_MODULES_ADDED",
    "KIND_REACHABILITY",
    "NOT_MEASURED_INCOMPATIBLE",
    "NOT_MEASURED_MISSING_SNAPSHOT",
    "NOT_MEASURED_MISSING_SOURCE",
    "NOT_MEASURED_SCHEMA",
    "NOT_MEASURED_STALE",
    "NOT_MEASURED_TRUNCATED",
    "NOT_MEASURED_UNCONFIGURED",
    "OUTCOME_CANDIDATE_ONLY",
    "OUTCOME_CONFIRMED_BREACH",
    "OUTCOME_INVALID_POLICY",
    "OUTCOME_NOT_MEASURED",
    "OUTCOME_PASSED",
    "POLICY_VERSION",
    "PolicyOutcome",
    "PolicyRule",
    "evaluate_architecture_policy",
    "load_architecture_policy",
]


@dataclass(frozen=True, slots=True)
class PolicyRule:
    """One budget: a measured category, a numeric ceiling, and whether breach blocks a gate."""

    id: str
    kind: str
    budget: int
    blocking: bool
    rule_ids: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class PolicyOutcome:
    """One policy's verdict over cited evidence — never a second graph walk."""

    policy_id: str
    kind: str
    outcome: str
    measured: int | None
    budget: int | None
    blocking: bool
    evidence_refs: tuple[str, ...]
    detail: str = ""


def load_architecture_policy(config: Config) -> tuple[PolicyRule, ...] | None:
    """Load the configured policy file; ``None`` when the knob is off."""
    relative = config.architecture_policy
    if relative is None:
        return None
    path = config.root / relative
    if not path.is_file():
        raise ConfigError(
            f"architecture_policy: {relative!r} is not a file under {config.root}"
        )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(
            f"architecture_policy: {relative!r} could not be read ({error})"
        ) from error
    return _parse_policy(relative, text)


def evaluate_architecture_policy(
    policies: Sequence[PolicyRule],
    *,
    rules_payload: Mapping[str, Any] | None,
    diff_payload: Mapping[str, Any] | None,
) -> tuple[PolicyOutcome, ...]:
    """Evaluate every policy against 138/139 result objects. Pure — no store, no network."""
    outcomes: list[PolicyOutcome] = []
    for policy in policies:
        outcomes.append(
            _evaluate_one(policy, rules_payload=rules_payload, diff_payload=diff_payload)
        )
    return tuple(outcomes)


def outcomes_as_dicts(outcomes: Sequence[PolicyOutcome]) -> list[dict[str, object]]:
    """Deterministic JSON-ready rows (sorted keys via ``asdict`` field order + caller dump)."""
    return [asdict(row) for row in outcomes]


def blocking_breaches(outcomes: Sequence[PolicyOutcome]) -> tuple[PolicyOutcome, ...]:
    """Confirmed breaches marked blocking — the only population ``--policy-gate`` fails."""
    return tuple(
        row
        for row in outcomes
        if row.outcome == OUTCOME_CONFIRMED_BREACH and row.blocking
    )


def _parse_policy(label: str, text: str) -> tuple[PolicyRule, ...]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise ConfigError(f"architecture_policy ({label}): invalid JSON ({error})") from error
    if not isinstance(raw, dict):
        raise ConfigError(f"architecture_policy ({label}): root must be an object")
    version = raw.get("version")
    if version != POLICY_VERSION:
        raise ConfigError(
            f"architecture_policy ({label}): version must be {POLICY_VERSION}, got {version!r}"
        )
    rows = raw.get("policies")
    if not isinstance(rows, list) or not rows:
        raise ConfigError(f"architecture_policy ({label}): policies must be a non-empty list")
    parsed: list[PolicyRule] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        parsed.append(_parse_rule(f"{label}[{index}]", row, seen))
    return tuple(parsed)


def _parse_rule(label: str, raw: object, seen: set[str]) -> PolicyRule:
    if not isinstance(raw, dict):
        raise ConfigError(f"architecture_policy ({label}): each policy must be an object")
    policy_id = raw.get("id")
    if not isinstance(policy_id, str) or not policy_id.strip():
        raise ConfigError(f"architecture_policy ({label}): id must be a non-empty string")
    if policy_id in seen:
        raise ConfigError(f"architecture_policy ({label}): duplicate id {policy_id!r}")
    seen.add(policy_id)
    kind = raw.get("kind")
    if kind not in KINDS:
        raise ConfigError(
            f"architecture_policy ({label}): kind must be one of {sorted(KINDS)}, got {kind!r}"
        )
    budget = raw.get("budget")
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 0:
        raise ConfigError(
            f"architecture_policy ({label}): budget must be an int >= 0, got {budget!r}"
        )
    blocking = raw.get("blocking")
    if not isinstance(blocking, bool):
        raise ConfigError(
            f"architecture_policy ({label}): blocking must be a bool, got {blocking!r}"
        )
    rule_ids: tuple[str, ...] | None = None
    if "rule_ids" in raw:
        raw_ids = raw.get("rule_ids")
        if not isinstance(raw_ids, list) or not all(
            isinstance(item, str) and item.strip() for item in raw_ids
        ):
            raise ConfigError(
                f"architecture_policy ({label}): rule_ids must be a list of non-empty strings"
            )
        rule_ids = tuple(raw_ids)
    if kind != KIND_CONFIRMED_DEPENDENCY and rule_ids is not None:
        raise ConfigError(
            f"architecture_policy ({label}): rule_ids only applies to {KIND_CONFIRMED_DEPENDENCY}"
        )
    return PolicyRule(policy_id, str(kind), budget, blocking, rule_ids)


def _evaluate_one(
    policy: PolicyRule,
    *,
    rules_payload: Mapping[str, Any] | None,
    diff_payload: Mapping[str, Any] | None,
) -> PolicyOutcome:
    if policy.kind == KIND_CONFIRMED_DEPENDENCY:
        return _eval_dependency(policy, rules_payload)
    return _eval_drift(policy, diff_payload)


def _eval_dependency(
    policy: PolicyRule, rules_payload: Mapping[str, Any] | None
) -> PolicyOutcome:
    if rules_payload is None:
        return _not_measured(policy, NOT_MEASURED_UNCONFIGURED, ())
    reason = str(rules_payload.get("reason") or "")
    if reason == REASON_CAPABILITY_NOT_CONFIGURED:
        return _not_measured(policy, NOT_MEASURED_UNCONFIGURED, ("architecture_rules.reason",))
    if reason == REASON_RULE_MATCHED_NO_FILES:
        return _not_measured(
            policy, NOT_MEASURED_MISSING_SOURCE, ("architecture_rules.reason",)
        )
    if rules_payload.get("truncated") or rules_payload.get("candidates_truncated"):
        return _not_measured(
            policy,
            NOT_MEASURED_TRUNCATED,
            ("architecture_rules.truncated",),
        )
    staleness = rules_payload.get("staleness")
    if staleness and staleness != "current":
        return _not_measured(
            policy, NOT_MEASURED_STALE, (f"architecture_rules.staleness={staleness}",)
        )
    if reason and reason not in {REASON_OK, "no_matches"}:
        return _not_measured(
            policy, NOT_MEASURED_INCOMPATIBLE, (f"architecture_rules.reason={reason}",)
        )

    confirmed = _violation_rows(rules_payload.get("results"), policy.rule_ids)
    candidates = _violation_rows(rules_payload.get("candidates"), policy.rule_ids)
    # Prefer total_count when unfiltered — paging may truncate ``results``.
    if policy.rule_ids is None:
        total_raw = rules_payload.get("total_count")
        measured = int(total_raw) if isinstance(total_raw, int) else len(confirmed)
        candidate_raw = rules_payload.get("candidate_count")
        candidate_n = (
            int(candidate_raw) if isinstance(candidate_raw, int) else len(candidates)
        )
    else:
        measured = len(confirmed)
        candidate_n = len(candidates)

    refs = tuple(
        f"architecture_rules.results[{index}]"
        for index, _ in enumerate(confirmed)
    ) or (("architecture_rules.total_count",) if measured else ())

    if measured == 0 and candidate_n > 0:
        return PolicyOutcome(
            policy.id,
            policy.kind,
            OUTCOME_CANDIDATE_ONLY,
            candidate_n,
            policy.budget,
            policy.blocking,
            ("architecture_rules.candidates",),
            detail="HEURISTIC-only evidence never fails a gate",
        )
    if measured > policy.budget:
        return PolicyOutcome(
            policy.id,
            policy.kind,
            OUTCOME_CONFIRMED_BREACH,
            measured,
            policy.budget,
            policy.blocking,
            refs,
            detail=f"confirmed={measured} budget={policy.budget}",
        )
    return PolicyOutcome(
        policy.id,
        policy.kind,
        OUTCOME_PASSED,
        measured,
        policy.budget,
        policy.blocking,
        refs if refs else ("architecture_rules.total_count",),
        detail=f"confirmed={measured} budget={policy.budget}",
    )


def _eval_drift(
    policy: PolicyRule, diff_payload: Mapping[str, Any] | None
) -> PolicyOutcome:
    if diff_payload is None:
        return _not_measured(policy, NOT_MEASURED_MISSING_SNAPSHOT, ())
    reason = str(diff_payload.get("reason") or "")
    if reason == REASON_SNAPSHOT_NOT_FOUND:
        return _not_measured(
            policy, NOT_MEASURED_MISSING_SNAPSHOT, ("architecture_diff.reason",)
        )
    if reason in {"dataset_schema_mismatch", "schema_mismatch"}:
        return _not_measured(
            policy, NOT_MEASURED_SCHEMA, (f"architecture_diff.reason={reason}",)
        )
    if reason in {"incomplete_snapshot", "index_root_mismatch"}:
        return _not_measured(
            policy, NOT_MEASURED_INCOMPATIBLE, (f"architecture_diff.reason={reason}",)
        )
    if diff_payload.get("truncated"):
        return _not_measured(policy, NOT_MEASURED_TRUNCATED, ("architecture_diff.truncated",))
    staleness = diff_payload.get("staleness")
    if staleness and staleness != "current":
        return _not_measured(
            policy, NOT_MEASURED_STALE, (f"architecture_diff.staleness={staleness}",)
        )

    section = policy.kind
    measured = _drift_count(diff_payload, section)
    if measured is None:
        return _not_measured(
            policy, NOT_MEASURED_INCOMPATIBLE, ("architecture_diff.diff",)
        )
    refs = (f"architecture_diff.diff.{section}",)
    if measured > policy.budget:
        return PolicyOutcome(
            policy.id,
            policy.kind,
            OUTCOME_CONFIRMED_BREACH,
            measured,
            policy.budget,
            policy.blocking,
            refs,
            detail=f"{section}={measured} budget={policy.budget}",
        )
    return PolicyOutcome(
        policy.id,
        policy.kind,
        OUTCOME_PASSED,
        measured,
        policy.budget,
        policy.blocking,
        refs,
        detail=f"{section}={measured} budget={policy.budget}",
    )


def _drift_count(diff_payload: Mapping[str, Any], section: str) -> int | None:
    shaped = diff_payload.get("diff")
    if isinstance(shaped, Mapping) and section in shaped:
        value = shaped[section]
        if isinstance(value, list):
            return len(value)
        return None
    # ``minimal`` carries section rows instead of ``diff``; absent section = a measured zero,
    # because 139 only emits a row for a non-empty section.
    results = diff_payload.get("results")
    if isinstance(results, list):
        for row in results:
            if isinstance(row, Mapping) and row.get("section") == section:
                count = row.get("count")
                return int(count) if isinstance(count, int) else None
        return 0
    if diff_payload.get("unchanged") is True:
        return 0
    # Neither shape present: evidence we cannot read never satisfies a budget (AC5).
    return None


def _violation_rows(
    raw: object, rule_ids: tuple[str, ...] | None
) -> list[Mapping[str, Any]]:
    if not isinstance(raw, list):
        return []
    rows: list[Mapping[str, Any]] = []
    allowed = None if rule_ids is None else set(rule_ids)
    for row in raw:
        if not isinstance(row, Mapping):
            continue
        if allowed is not None and str(row.get("rule_id") or "") not in allowed:
            continue
        # HEURISTIC rows must never enter the confirmed population even if mis-filed.
        tier = str(row.get("confidence_tier") or "")
        if tier and tier != "RESOLVED":
            continue
        rows.append(row)
    return rows


def _not_measured(
    policy: PolicyRule, detail: str, refs: tuple[str, ...]
) -> PolicyOutcome:
    return PolicyOutcome(
        policy.id,
        policy.kind,
        OUTCOME_NOT_MEASURED,
        None,
        policy.budget,
        policy.blocking,
        refs,
        detail=detail,
    )


def load_policy_from_path(path: Path) -> tuple[PolicyRule, ...]:
    """Parse and validate one policy file by path, without a Config."""
    return _parse_policy(path.name, path.read_text(encoding="utf-8"))
