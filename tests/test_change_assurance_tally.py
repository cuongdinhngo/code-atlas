"""Task 310: the frozen adoption protocol's counter — rules, not results.

The four-week window has not run. These tests exercise the *instrument* on fixtures, which is
the only thing that can be proven before a cohort exists; the ticket's ACs that need field data
stay unmet and say so in the ticket.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.change_assurance_tally import (  # noqa: E402
    EVIDENCE_RATE_BAR,
    EXCLUSION_CODES,
    FAILURE_CLASSES,
    REQUIRED_WEEKS,
    RUN_RATE_BAR,
    VERDICT_ADOPTION_FAILURE,
    VERDICT_INVALID,
    VERDICT_MUST_HAVE,
    VERDICT_USEFUL_OPTIONAL,
    evaluate,
    load_record,
    render_json,
    render_text,
)

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "docs" / "runbooks" / "change-assurance-tally.template.json"
PROTOCOL = REPO / "docs" / "runbooks" / "change-assurance-field-protocol.md"

_PROVENANCE = {
    "host_build": "host-1",
    "client_build": "client-1",
    "server_build": "server-1",
    "config_build": "config-1",
    "repository_revision": "0123456789ab",
}


def _week(number: int, *, ok: int = 18, failed: int = 3, reviews: int = 12, cited: int = 7):
    return {
        "week": number,
        "code_changing_prs": 25,
        "assurance_runs": {"ok": ok, "failed": failed, "invalid": 0},
        "failure_classifications": ["operational"] * failed,
        "reviews": reviews,
        "reviews_citing_evidence": cited,
        "exclusions": [],
        "provenance": dict(_PROVENANCE),
    }


def _record(**over: Any) -> dict[str, Any]:
    """A record that passes every validity rule — 0.84 run, 0.5833 evidence."""
    weeks = [_week(n) for n in range(1, REQUIRED_WEEKS + 1)]
    base = {
        "protocol_version": 1,
        "weeks": weeks,
        "removal_cost_probe": {"kind": "removal_comparison", "recorded": True},
        "aggregate_declared": {
            "code_changing_prs": 100,
            "assurance_runs_attempted": 84,
            "reviews": 48,
            "reviews_citing_evidence": 28,
        },
    }
    base.update(over)
    return base


def test_the_committed_template_reports_no_result() -> None:
    """The shipped template is an observed failing case, not a green one (R6.5)."""
    result = evaluate(load_record(TEMPLATE))
    assert result["verdict"] == VERDICT_INVALID
    assert result["run_rate"] is None and result["evidence_rate"] is None
    assert any(failure.startswith("V1 weeks") for failure in result["validity_failures"])


def test_a_passing_record_reaches_must_have() -> None:
    """The fixture the other tests perturb clears both bars, so each failure is attributable."""
    result = evaluate(_record())
    assert result["run_rate"] == 0.84
    assert result["evidence_rate"] == 0.5833
    assert result["verdict"] == VERDICT_MUST_HAVE
    assert result["validity_failures"] == []


def test_weekly_records_must_reconcile_exactly_to_the_aggregate() -> None:
    """AC2 mechanism — one PR of drift invalidates; there is no rounding tolerance."""
    record = _record()
    record["aggregate_declared"]["code_changing_prs"] = 101
    result = evaluate(record)
    assert result["verdict"] == VERDICT_INVALID
    assert "V2 reconciliation" in result["validity_failures"][0]
    assert "declared 101 vs weeks 100" in result["validity_failures"][0]


def test_the_two_rates_use_separate_denominators() -> None:
    """AC3 — evidence is per review; dividing it by PRs would flip this record's verdict."""
    result = evaluate(_record())
    aggregate = result["aggregate"]
    assert aggregate["code_changing_prs"] != aggregate["reviews"]
    shared = round(aggregate["reviews_citing_evidence"] / aggregate["code_changing_prs"], 4)
    assert shared < EVIDENCE_RATE_BAR <= result["evidence_rate"]


def test_failed_runs_stay_in_the_run_rate_numerator() -> None:
    """Constraint 3 — dropping failures would push this record below the bar, rewarding breakage."""
    with_failures = evaluate(_record())
    assert with_failures["run_rate"] >= RUN_RATE_BAR

    clean = _record(weeks=[_week(n, failed=0) for n in range(1, REQUIRED_WEEKS + 1)])
    clean["aggregate_declared"]["assurance_runs_attempted"] = 72
    without = evaluate(clean)
    assert without["validity_failures"] == []
    assert without["run_rate"] < RUN_RATE_BAR
    assert without["verdict"] == VERDICT_ADOPTION_FAILURE


def test_an_unclassified_failure_is_invalid() -> None:
    """V4 — a failed run with no cause recorded is not a countable week."""
    record = _record()
    record["weeks"][0]["failure_classifications"] = []
    result = evaluate(record)
    assert result["verdict"] == VERDICT_INVALID
    assert any("V4 classification" in failure for failure in result["validity_failures"])


def test_no_removal_cost_probe_is_invalid_rather_than_must_have() -> None:
    """AC4 / V5 — approving in principle is not missing it; the absent probe voids the verdict."""
    record = _record(removal_cost_probe={"kind": "", "recorded": False})
    result = evaluate(record)
    assert result["verdict"] == VERDICT_INVALID
    assert result["verdict"] != VERDICT_MUST_HAVE
    assert any("V5 removal cost" in failure for failure in result["validity_failures"])


def test_missing_provenance_is_invalid() -> None:
    """V6 — a week that cannot name what answered is not evidence."""
    record = _record()
    record["weeks"][2]["provenance"]["server_build"] = ""
    result = evaluate(record)
    assert result["verdict"] == VERDICT_INVALID
    assert any("V6 provenance" in failure for failure in result["validity_failures"])


@pytest.mark.parametrize(
    "value",
    [
        "src/Service.php",
        "App\\Service",
        "Service::run",
        "tests/test_basic.py",
        # The five a shape-sniffer let through, which is why the guard is a closed vocabulary.
        "code_atlas.core.store.Store",
        "com.example.service.UserService",
        "acme-webapp",
        "acme_internal_repo",
        "UserController",
    ],
)
def test_identifying_content_is_rejected(value: str) -> None:
    """Constraint 1 / V7 — no free text is admitted, so no name can ride in on one."""
    record = _record()
    record["weeks"][0]["exclusions"] = [value]
    result = evaluate(record)
    assert result["verdict"] == VERDICT_INVALID
    assert any("V7 privacy" in failure for failure in result["validity_failures"])


@pytest.mark.parametrize("value", ["acme-webapp", "billing-service", "alice", "team1"])
def test_a_team_must_be_an_opaque_id(value: str) -> None:
    """§1 — the cohort names teams team-1, team-2; anything else is a name we did not want."""
    record = _record(cohort={"teams": [value], "repository_size_floor_files": 2000})
    result = evaluate(record)
    assert result["verdict"] == VERDICT_INVALID
    assert any("opaque team-N id" in failure for failure in result["validity_failures"])


def test_the_declared_vocabularies_are_what_the_record_may_carry() -> None:
    """A value inside the closed set passes; the sets are small and stated in the protocol."""
    record = _record(cohort={"teams": ["team-1", "team-2"], "repository_size_floor_files": 2000})
    record["weeks"][0]["exclusions"] = [{"count": 1, "reason": sorted(EXCLUSION_CODES)[0]}]
    record["weeks"][1]["failure_classifications"] = ["operational", "timeout", "config"]
    assert {"operational", "timeout", "config"} <= FAILURE_CLASSES
    result = evaluate(record)
    assert result["validity_failures"] == []
    assert result["verdict"] == VERDICT_MUST_HAVE


def test_free_text_notes_are_not_admitted() -> None:
    """§5 — a notes field is exactly where a repository name would arrive."""
    record = _record(
        removal_cost_probe={"kind": "interview", "recorded": True, "notes": "they liked it"}
    )
    result = evaluate(record)
    assert result["verdict"] == VERDICT_INVALID
    assert any("free text" in failure for failure in result["validity_failures"])


def test_a_malformed_week_entry_is_invalid_not_a_crash() -> None:
    """A null inside a four-length weeks list must degrade to a verdict, never an exception."""
    record = _record()
    record["weeks"][1] = None
    result = evaluate(record)
    assert result["verdict"] == VERDICT_INVALID
    assert any("not weekly records" in failure for failure in result["validity_failures"])


def test_provenance_shas_are_not_read_as_identifying() -> None:
    """§5 exempts provenance — a build string naming what answered is required, not banned."""
    record = _record()
    record["weeks"][0]["provenance"]["server_build"] = "code-atlas/0.9.1+abc123"
    result = evaluate(record)
    assert not any("V7 privacy" in failure for failure in result["validity_failures"])


@pytest.mark.parametrize(
    ("ok", "cited", "expected"),
    [
        (18, 7, VERDICT_MUST_HAVE),
        (18, 2, VERDICT_USEFUL_OPTIONAL),
        (14, 2, VERDICT_ADOPTION_FAILURE),
        # Declared on purpose: heavy use by a minority is still an adoption failure.
        (14, 7, VERDICT_ADOPTION_FAILURE),
    ],
)
def test_the_verdict_follows_the_thresholds_mechanically(
    ok: int, cited: int, expected: str
) -> None:
    """AC5 — the verdict is a function of the two rates, with no room to read it afterwards."""
    weeks = [_week(n, ok=ok, cited=cited) for n in range(1, REQUIRED_WEEKS + 1)]
    attempted = (ok + 3) * REQUIRED_WEEKS
    record = _record(
        weeks=weeks,
        aggregate_declared={
            "code_changing_prs": 100,
            "assurance_runs_attempted": attempted,
            "reviews": 48,
            "reviews_citing_evidence": cited * REQUIRED_WEEKS,
        },
    )
    result = evaluate(record)
    assert result["validity_failures"] == []
    assert result["verdict"] == expected


def test_two_evaluations_are_byte_identical() -> None:
    """R4.2 — identical input, identical rows."""
    record = _record()
    first = render_json(evaluate(copy.deepcopy(record)))
    second = render_json(evaluate(copy.deepcopy(record)))
    assert first == second
    assert json.loads(first)["verdict"] == VERDICT_MUST_HAVE


def test_text_and_json_render_the_same_object() -> None:
    """One evaluation, two surfaces — the text never recomputes a rate."""
    result = evaluate(_record())
    text = render_text(result)
    assert f"run_rate: {result['run_rate']}" in text
    assert result["verdict"] in text
    assert json.loads(render_json(result))["run_rate"] == result["run_rate"]


def test_cli_runs_on_the_committed_template() -> None:
    """The protocol's section 10 command works as written and writes nothing."""
    done = subprocess.run(
        [sys.executable, "scripts/change_assurance_tally.py", str(TEMPLATE), "--json"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(done.stdout)["verdict"] == VERDICT_INVALID


def test_the_protocol_states_the_bar_it_was_frozen_with() -> None:
    """The thresholds are the ticket's; the doc and the code must not drift apart."""
    text = PROTOCOL.read_text(encoding="utf-8")
    assert str(RUN_RATE_BAR) in text and str(EVIDENCE_RATE_BAR) in text
    assert "blocked" in text


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("note", "acme-webapp rollout, billing-service excluded"),
        ("comment", "the team at acme liked it"),
        ("cohort_description", "two squads on the monorepo"),
    ],
)
def test_a_string_in_an_unpoliced_field_is_rejected(key: str, value: str) -> None:
    """§5 — a closed vocabulary is worthless if any new key may carry free text beside it.

    The first cut of this guard admitted a top-level ``note``, and a repository name typed there
    passed every check. A string is now admissible in five named slots and nowhere else.
    """
    record = _record(**{key: value})
    result = evaluate(record)
    assert result["verdict"] == VERDICT_INVALID
    assert any("admits nowhere" in failure for failure in result["validity_failures"])


def test_the_committed_template_passes_its_own_privacy_rule() -> None:
    """The template is invalid for having no data — never for carrying content it bans."""
    result = evaluate(load_record(TEMPLATE))
    assert not any("V7 privacy" in failure for failure in result["validity_failures"])

