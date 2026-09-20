#!/usr/bin/env python3
"""Task 310: apply the frozen Change Assurance field protocol to one committed record.

Local-only and deterministic: reads one JSON record, writes stdout. The thresholds and the
validity rules are the protocol's, frozen before any window ran — this file applies them and
never chooses them. See ``docs/runbooks/change-assurance-field-protocol.md``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Ticket 310's pre-registered bar. Both must pass; neither is re-derived here.
RUN_RATE_BAR = 0.80
EVIDENCE_RATE_BAR = 0.50
REQUIRED_WEEKS = 4

VERDICT_MUST_HAVE = "must_have_observed"
VERDICT_USEFUL_OPTIONAL = "useful_but_optional"
VERDICT_ADOPTION_FAILURE = "adoption_failure"
VERDICT_INVALID = "measurement_invalid"

PROVENANCE_FIELDS: tuple[str, ...] = (
    "host_build",
    "client_build",
    "server_build",
    "config_build",
    "repository_revision",
)

# Provenance names what answered, not whose code it was — §5 exempts it, nothing else.
_PRIVACY_EXEMPT_KEYS = frozenset({"provenance"})

# §5 admits no free text. A sniffer cannot tell a repo name from an English word, so the
# record carries only closed vocabularies and the guard checks membership, not shape.
TEAM_ID = re.compile(r"^team-\d+$")
FAILURE_CLASSES: frozenset[str] = frozenset(
    {"operational", "timeout", "index_unavailable", "config", "crash", "other"}
)
EXCLUSION_CODES: frozenset[str] = frozenset(
    {"reverted_within_24h", "bot_authored_no_human_review", "index_unavailable_over_one_day"}
)
REMOVAL_PROBE_KINDS: frozenset[str] = frozenset({"removal_comparison", "interview"})

# §5 — the only places a string may appear at all. Anything else, including a free-text note,
# is rejected: a repository name typed into an unpoliced field is the defect this guard exists for.
_INDEX = re.compile(r"\[\d+\]")
ADMISSIBLE_STRING_SLOTS: frozenset[str] = frozenset(
    {
        "frozen_at",
        "cohort.teams[]",
        "weeks[].failure_classifications[]",
        "weeks[].exclusions[].reason",
        "removal_cost_probe.kind",
    }
)

# Second net only: anything that still reaches a string field must not look like an identifier.
_IDENTIFIER_LIKE = re.compile(
    r"[\w.-]+/[\w./-]+"  # a path
    r"|\.(?:py|php|ts|js|sql|tsx|jsx|go|rb|java|cs)\b"  # a source suffix
    r"|\w+::\w+|\\\\?\w+"  # a :: or backslash qname
    r"|\b\w+(?:\.\w+){2,}\b"  # a dotted qname: two or more dots
    r"|\b[a-z0-9_]+\.[A-Z]\w*\b"  # a dotted qname ending in a type name
    r"|\b[a-z]+[A-Z]\w*\b"  # camelCase or PascalCase identifier
)

__all__ = [
    "EVIDENCE_RATE_BAR",
    "REQUIRED_WEEKS",
    "RUN_RATE_BAR",
    "VERDICT_ADOPTION_FAILURE",
    "VERDICT_INVALID",
    "VERDICT_MUST_HAVE",
    "VERDICT_USEFUL_OPTIONAL",
    "evaluate",
    "load_record",
    "render_json",
    "render_text",
]


def load_record(path: Path) -> dict[str, Any]:
    """Read one committed record; a malformed file is a read error, never a silent empty count."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("record must be a JSON object")
    return data


def _as_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _walk_strings(node: object, trail: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for key in sorted(node):
            if key in _PRIVACY_EXEMPT_KEYS:
                continue
            found.extend(_walk_strings(node[key], f"{trail}.{key}" if trail else str(key)))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(_walk_strings(item, f"{trail}[{index}]"))
    elif isinstance(node, str):
        found.append((trail, node))
    return found


def _vocabulary_violations(record: dict[str, Any]) -> list[str]:
    """§5 — every admissible string is drawn from a closed set, so none can carry a name."""
    hits: list[str] = []
    teams = (record.get("cohort") or {}).get("teams")
    for team in teams if isinstance(teams, list) else []:
        if not (isinstance(team, str) and TEAM_ID.match(team)):
            hits.append(f"cohort.teams carries {team!r}, not an opaque team-N id")

    weeks = record.get("weeks")
    for index, week in enumerate(weeks if isinstance(weeks, list) else []):
        if not isinstance(week, dict):
            continue
        for label in week.get("failure_classifications") or []:
            if label not in FAILURE_CLASSES:
                hits.append(f"weeks[{index}].failure_classifications carries {label!r}")
        for exclusion in week.get("exclusions") or []:
            code = exclusion.get("reason") if isinstance(exclusion, dict) else exclusion
            if code not in EXCLUSION_CODES:
                hits.append(f"weeks[{index}].exclusions carries {code!r}")

    probe = record.get("removal_cost_probe")
    kind = probe.get("kind") if isinstance(probe, dict) else None
    if kind and kind not in REMOVAL_PROBE_KINDS:
        hits.append(f"removal_cost_probe.kind carries {kind!r}")
    if isinstance(probe, dict) and probe.get("notes"):
        # §5 keeps narrative outside the tree; a notes field is where a repo name would arrive.
        hits.append("removal_cost_probe.notes carries free text, which §5 does not admit")

    for trail, text in _walk_strings(record):
        slot = _INDEX.sub("[]", trail)
        if slot not in ADMISSIBLE_STRING_SLOTS:
            hits.append(f"{trail} is a string the protocol admits nowhere")
        elif _IDENTIFIER_LIKE.search(text):
            hits.append(f"{trail} carries identifier-shaped content")
    return hits


def _week_totals(weeks: list[dict[str, Any]]) -> dict[str, int]:
    runs = [week.get("assurance_runs") or {} for week in weeks]
    return {
        "code_changing_prs": sum(_as_int(week.get("code_changing_prs")) for week in weeks),
        # A failed or invalid run still ran (§3) — the attempt is the numerator, not the success.
        "assurance_runs_attempted": sum(
            _as_int(run.get("ok")) + _as_int(run.get("failed")) + _as_int(run.get("invalid"))
            for run in runs
        ),
        "reviews": sum(_as_int(week.get("reviews")) for week in weeks),
        "reviews_citing_evidence": sum(
            _as_int(week.get("reviews_citing_evidence")) for week in weeks
        ),
    }


def _validity_failures(
    record: dict[str, Any], totals: dict[str, int], weeks: list[dict[str, Any]]
) -> list[str]:
    """The seven rules of §9, each naming itself. Order is fixed so output is deterministic."""
    raw = record.get("weeks")
    raw = raw if isinstance(raw, list) else []
    failures: list[str] = []

    if len(raw) != REQUIRED_WEEKS:
        failures.append(
            f"V1 weeks: {len(raw)} weekly record(s), protocol requires {REQUIRED_WEEKS}"
        )
    if len(weeks) != len(raw):
        failures.append(
            f"V1 weeks: {len(raw) - len(weeks)} entry/entries are not weekly records"
        )

    declared = record.get("aggregate_declared")
    if not isinstance(declared, dict):
        failures.append("V2 reconciliation: no declared aggregate to reconcile against")
    else:
        mismatched = sorted(
            key for key, value in totals.items() if _as_int(declared.get(key)) != value
        )
        if mismatched:
            detail = ", ".join(
                f"{key} declared {_as_int(declared.get(key))} vs weeks {totals[key]}"
                for key in mismatched
            )
            failures.append(f"V2 reconciliation: {detail}")

    if totals["code_changing_prs"] <= 0 or totals["reviews"] <= 0:
        failures.append("V3 denominators: run-rate or evidence-rate denominator is zero")

    for week in weeks:
        runs = week.get("assurance_runs") or {}
        unhealthy = _as_int(runs.get("failed")) + _as_int(runs.get("invalid"))
        classifications = week.get("failure_classifications")
        counted = len(classifications) if isinstance(classifications, list) else 0
        if counted != unhealthy:
            failures.append(
                f"V4 classification: week {week.get('week')} has {unhealthy} failed/invalid run(s) "
                f"and {counted} classification(s)"
            )

    probe = record.get("removal_cost_probe")
    if not isinstance(probe, dict) or not probe.get("kind"):
        failures.append("V5 removal cost: no removal comparison or interview recorded")

    for week in weeks:
        provenance = week.get("provenance") or {}
        missing = [field for field in PROVENANCE_FIELDS if not provenance.get(field)]
        if missing:
            failures.append(
                f"V6 provenance: week {week.get('week')} is missing {', '.join(missing)}"
            )

    failures.extend(f"V7 privacy: {hit}" for hit in _vocabulary_violations(record))
    return failures


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def evaluate(record: dict[str, Any]) -> dict[str, Any]:
    """Apply §§8–9 to one record. Validity is decided before any rate is read."""
    weeks = record.get("weeks")
    weeks = [week for week in weeks if isinstance(week, dict)] if isinstance(weeks, list) else []
    totals = _week_totals(weeks)
    failures = _validity_failures(record, totals, weeks)

    run_rate = _rate(totals["assurance_runs_attempted"], totals["code_changing_prs"])
    evidence_rate = _rate(totals["reviews_citing_evidence"], totals["reviews"])

    if failures:
        verdict = VERDICT_INVALID
        reason = failures[0]
    elif run_rate is not None and evidence_rate is not None and run_rate >= RUN_RATE_BAR:
        if evidence_rate >= EVIDENCE_RATE_BAR:
            verdict = VERDICT_MUST_HAVE
            reason = (
                f"run {run_rate} >= {RUN_RATE_BAR} and "
                f"evidence {evidence_rate} >= {EVIDENCE_RATE_BAR}"
            )
        else:
            verdict = VERDICT_USEFUL_OPTIONAL
            reason = (
                f"run {run_rate} >= {RUN_RATE_BAR} but "
                f"evidence {evidence_rate} < {EVIDENCE_RATE_BAR}"
            )
    else:
        verdict = VERDICT_ADOPTION_FAILURE
        reason = f"run {run_rate} < {RUN_RATE_BAR}"

    return {
        "aggregate": totals,
        "bar": {
            "evidence_rate": EVIDENCE_RATE_BAR,
            "required_weeks": REQUIRED_WEEKS,
            "run_rate": RUN_RATE_BAR,
        },
        "evidence_rate": evidence_rate,
        "run_rate": run_rate,
        "validity_failures": failures,
        "verdict": verdict,
        "verdict_reason": reason,
        "weeks": [
            {
                "week": _as_int(week.get("week")),
                "code_changing_prs": _as_int(week.get("code_changing_prs")),
                "assurance_runs_attempted": (
                    _as_int((week.get("assurance_runs") or {}).get("ok"))
                    + _as_int((week.get("assurance_runs") or {}).get("failed"))
                    + _as_int((week.get("assurance_runs") or {}).get("invalid"))
                ),
                "reviews": _as_int(week.get("reviews")),
                "reviews_citing_evidence": _as_int(week.get("reviews_citing_evidence")),
            }
            for week in weeks
        ],
    }


def render_text(result: dict[str, Any]) -> str:
    """Human text derived only from ``result`` — never a second evaluation."""
    lines = [
        "change_assurance_adoption:",
        f"weeks: {len(result['weeks'])} of {REQUIRED_WEEKS}",
        f"run_rate: {result['run_rate']} (bar {RUN_RATE_BAR})",
        f"evidence_rate: {result['evidence_rate']} (bar {EVIDENCE_RATE_BAR})",
    ]
    for week in result["weeks"]:
        lines.append(
            f"WEEK {week['week']} prs={week['code_changing_prs']} "
            f"runs={week['assurance_runs_attempted']} reviews={week['reviews']} "
            f"cited={week['reviews_citing_evidence']}"
        )
    for failure in result["validity_failures"]:
        lines.append(f"INVALID: {failure}")
    lines.append(f"VERDICT: {result['verdict']} ({result['verdict_reason']})")
    return "\n".join(lines) + "\n"


def render_json(result: dict[str, Any]) -> str:
    """Deterministic JSON — sorted keys (R4.2)."""
    return json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path, help="the committed weekly-record JSON")
    parser.add_argument("--json", action="store_true", help="emit the result object")
    args = parser.parse_args(argv)

    result = evaluate(load_record(args.record))
    sys.stdout.write(render_json(result) if args.json else render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
