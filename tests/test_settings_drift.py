"""424 — the settings the standard records are read back and compared (SEC-SC-10, SEC-GV-04, …).

`scripts/settings_drift.py` takes its expected values from the standard's `set:` items and its live
values from an injected `fetch`. These tests feed it the API JSON a read of this repo returned on
2026-10-31, so nothing here touches the network; the workflow `Settings drift` runs the same code
against the live repo (its first scheduled run is the one thing not proven before merge).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from scripts import settings_drift as sd

REPO = "owner/name"
CHECKS = [
    "adapter manifests · syntax · static analysis",
    "lint · type · test (py3.12)",
    "lint · type · test (py3.13)",
    "rulebook grep-gates",
    "test image builds (docker/Dockerfile)",
]
MAIN = {
    "id": 1,
    "target": "branch",
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
    "bypass_actors": [
        {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}
    ],
    "rules": [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {"type": "pull_request"},
        {
            "type": "required_status_checks",
            "parameters": {"required_status_checks": [{"context": c} for c in CHECKS]},
        },
    ],
}
TAGS = {
    "id": 2,
    "target": "tag",
    "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
    "bypass_actors": [],
    "rules": [{"type": "deletion"}, {"type": "update"}, {"type": "non_fast_forward"}],
}
LIVE: dict[str, Any] = {
    f"repos/{REPO}/rulesets": [{"id": 1}, {"id": 2}],
    f"repos/{REPO}/rulesets/1": MAIN,
    f"repos/{REPO}/rulesets/2": TAGS,
    f"repos/{REPO}/private-vulnerability-reporting": {"enabled": True},
    f"repos/{REPO}": {
        "security_and_analysis": {
            "secret_scanning": {"status": "enabled"},
            "secret_scanning_push_protection": {"status": "enabled"},
            "dependabot_security_updates": {"status": "enabled"},
        }
    },
    f"repos/{REPO}/actions/permissions": {"sha_pinning_required": True},
    f"repos/{REPO}/collaborators?affiliation=direct&per_page=100": [
        {"login": "cuongdinhngo", "role_name": "admin"}
    ],
}
ADMINS = f"repos/{REPO}/collaborators?affiliation=direct&per_page=100"


def _fetch(live: dict[str, Any]) -> Any:
    return lambda path: copy.deepcopy(live[path])


def _expected() -> dict[str, tuple[str, str]]:
    return sd.expected_settings(sd.STANDARD.read_text(encoding="utf-8"))


def _drift(live: dict[str, Any]) -> list[str]:
    return sd.drift(_expected(), _fetch(live), REPO)


def test_the_standard_holds_a_set_item_for_every_setting_the_ticket_names() -> None:
    expected = _expected()
    assert set(expected) == set(sd.READERS), "a reader nobody cites, or a set: nobody can read"
    assert expected["admins"][0] == "cuongdinhngo"
    assert expected["secret_scanning_push_protection"][0] == "enabled"


def test_a_repo_matching_the_standard_reports_no_drift() -> None:
    assert _drift(LIVE) == []


def _with(path: str, change: Any) -> dict[str, Any]:
    live = copy.deepcopy(LIVE)
    change(live[path])
    return live


PLANTED = {
    "rulesets.main.non_fast_forward": _with(
        f"repos/{REPO}/rulesets/1", lambda r: r["rules"].remove({"type": "non_fast_forward"})
    ),
    "rulesets.main.required_checks": _with(
        f"repos/{REPO}/rulesets/1",
        lambda r: r["rules"][3]["parameters"].update(
            required_status_checks=[{"context": CHECKS[0]}]
        ),
    ),
    "rulesets.main.bypass": _with(
        f"repos/{REPO}/rulesets/1",
        lambda r: r["bypass_actors"].append(
            {"actor_id": 9, "actor_type": "Team", "bypass_mode": "always"}
        ),
    ),
    "rulesets.tags.update": _with(
        f"repos/{REPO}/rulesets/2", lambda r: r["rules"].remove({"type": "update"})
    ),
    "private_vulnerability_reporting": _with(
        f"repos/{REPO}/private-vulnerability-reporting", lambda r: r.update(enabled=False)
    ),
    "secret_scanning_push_protection": _with(
        f"repos/{REPO}",
        lambda r: r["security_and_analysis"]["secret_scanning_push_protection"].update(
            status="disabled"
        ),
    ),
    "dependabot_security_updates": _with(
        f"repos/{REPO}", lambda r: r["security_and_analysis"].pop("dependabot_security_updates")
    ),
    "actions.sha_pinning_required": _with(
        f"repos/{REPO}/actions/permissions", lambda r: r.update(sha_pinning_required=False)
    ),
    "admins": _with(ADMINS, lambda r: r.append({"login": "intruder", "role_name": "admin"})),
}


@pytest.mark.parametrize("name", sorted(PLANTED))
def test_each_planted_drift_is_named(name: str) -> None:
    lines = _drift(PLANTED[name])
    assert [line.split()[1] for line in lines] == [name], lines


def test_a_ruleset_that_vanished_reads_as_every_rule_missing() -> None:
    live = copy.deepcopy(LIVE)
    live[f"repos/{REPO}/rulesets"] = [{"id": 2}]
    named = {line.split()[1] for line in _drift(live)}
    assert {"rulesets.main.deletion", "rulesets.main.pull_request"} <= named


def test_an_unknown_set_name_is_an_error_not_a_pass() -> None:
    with pytest.raises(sd.SettingsError, match="no reader"):
        sd.drift({"rulesets.main.invented": ("true", "SEC-XX-01")}, _fetch(LIVE), REPO)


def test_a_malformed_or_conflicting_set_item_is_an_error() -> None:
    row = "| SEC-GV-99 | c | MUST | s | {} |"
    with pytest.raises(sd.SettingsError, match="not `<name> = <value>`"):
        sd.expected_settings(row.format("set: secret_scanning"))
    with pytest.raises(sd.SettingsError, match="two values"):
        sd.expected_settings(row.format("set: admins = a") + "\n" + row.format("set: admins = b"))


def _standard(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "standard.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_main_exits_zero_on_no_drift_and_one_naming_each_drift(
    capsys: pytest.CaptureFixture[str],
) -> None:
    env = {"GH_TOKEN": "t", "GITHUB_REPOSITORY": REPO}
    assert sd.main([], _fetch(LIVE), env) == 0
    assert "none" in capsys.readouterr().out
    assert sd.main([], _fetch(PLANTED["admins"]), env) == 1
    out = capsys.readouterr().out
    assert "DRIFT admins (SEC-GV-04)" in out and "intruder" in out


def test_a_missing_token_names_the_secret_and_the_scope(capsys: pytest.CaptureFixture[str]) -> None:
    assert sd.main([], None, {"GITHUB_REPOSITORY": REPO}) == 2
    out = capsys.readouterr().out
    assert "SETTINGS_READ_TOKEN" in out and "Administration: read" in out


def test_a_standard_with_no_set_item_fails_rather_than_passing(tmp_path: Path) -> None:
    path = _standard(tmp_path, "| SEC-GV-99 | c | MUST | s | doc: SECURITY.md#Trust model |\n")
    env = {"GH_TOKEN": "t", "GITHUB_REPOSITORY": REPO}
    assert sd.main([], _fetch(LIVE), env, standard=path) == 2


def test_an_unreadable_setting_is_a_failure_to_run() -> None:
    def broken(path: str) -> Any:
        raise sd.SettingsError(f"cannot read {path}: HTTP 403")

    env = {"GH_TOKEN": "t", "GITHUB_REPOSITORY": REPO}
    assert sd.main([], broken, env) == 2
