"""Task 201: a forced full rebuild is answered before it is started, and it names its route.

Field run, 2026-08-31: `build_or_update_index(full=false)` on an index four commits behind ran for
73 minutes, the client gave up at its 3600 s ceiling, and the session lost all 24 tools. The index
was written correctly — the defect is what the tool *says* and *when*. `indexer.py` knows the
escalation is coming before it has parsed a file (030 AC1) and used to say nothing.

The refusal is the 050 shape for the other version key. 172 set the other half: an escalation is
recorded, so `wrote.files: 0` can never mean both "nothing to do" and "could not act".
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

import pytest

from code_atlas import cli, contract
from code_atlas.config import load_config
from code_atlas.indexer import CONTRACT_REBUILD_REQUIRED, FULL_REBUILD_ROUTE
from code_atlas.store import CONTRACT_VERSION_KEY, GraphStore
from code_atlas.tools import build_or_update_index as build_module
from code_atlas.tools.build_or_update_index import create as build_tool
from code_atlas.tools.get_index_status import FULL_REBUILD_REQUIRED
from code_atlas.tools.get_index_status import NAME as STATUS_NAME
from code_atlas.tools.get_index_status import create as status_tool

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"

# The ticket's own bar: the refusal must return in under a second where the build died at 3600 s.
REFUSAL_BUDGET_SECONDS = 1.0


def fake_cmd(mode: str = "ok") -> str:
    return shlex.join([sys.executable, str(FAKE), mode])


ONE_ADAPTER = {"CA_WORKERS": "1", "CA_FAKE_CMD": fake_cmd()}
TWO_ADAPTERS = {**ONE_ADAPTER, "CA_SECOND_CMD": fake_cmd("second")}


def config_for(root: Path, env: dict[str, str] | None = None):
    return load_config(
        root, {**(env or ONE_ADAPTER), "CA_DB_PATH": str(root / ".code-atlas" / "graph.db")}
    )


def seeded(root: Path, env: dict[str, str] | None = None) -> None:
    """A committed repo with an index built by the fake adapter."""
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "a.aa").write_text("class Thing {}\n", encoding="utf-8")
    (root / "src" / "c.cc").write_text("class Third {}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"],
        cwd=root, check=True, capture_output=True,
    )
    build_tool(config_for(root, env))(full=True)


def lag_the_stored_era(root: Path) -> str:
    """Put the index one vocabulary era behind, exactly as an 8 -> 9 bump does."""
    behind = str(contract.CONTRACT_VERSION - 1)
    with GraphStore(config_for(root).db_path) as store:
        store.set_meta(CONTRACT_VERSION_KEY, behind)
    return behind


def refuse_to_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC1 is about work NOT done, so the builders are made to fail loudly if entered."""
    def never(*args: object, **kwargs: object) -> None:
        raise AssertionError("a build was started; the refusal was supposed to precede it")

    monkeypatch.setattr(build_module, "full_build", never)
    monkeypatch.setattr(build_module, "incremental_update", never)


def test_a_lagging_contract_version_refuses_without_building(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1 — the proving test. Red before the fix: line 239 started a full build instead."""
    seeded(tmp_path)
    behind = lag_the_stored_era(tmp_path)
    refuse_to_build(monkeypatch)

    started = time.perf_counter()
    payload = build_tool(config_for(tmp_path))(full=False)
    elapsed = time.perf_counter() - started

    assert payload["mode"] == "refused"
    assert payload["reason"] == CONTRACT_REBUILD_REQUIRED
    assert payload["performed"] is False
    assert payload["stored_contract_version"] == behind
    assert payload["contract_version"] == contract.CONTRACT_VERSION
    assert payload["route"] == FULL_REBUILD_ROUTE
    assert payload["in_band_option"] == "allow_full_rebuild=true"
    assert "wrote" not in payload, "nothing was built, so a count would say the repo is empty (060)"
    assert elapsed < REFUSAL_BUDGET_SECONDS, f"{elapsed:.3f}s — the ticket's bar is under a second"


def test_a_matching_contract_version_keeps_todays_payload(tmp_path: Path) -> None:
    """AC2/061 — the untouched path gains no field, so the refusal cannot leak into it."""
    seeded(tmp_path)

    payload = build_tool(config_for(tmp_path))(full=False)

    assert payload["mode"] == "incremental"
    leaked = ("reason", "route", "in_band_option", "contract_change", "stored_contract_version")
    for added in leaked:
        assert added not in payload, f"{added} leaked onto the normal incremental path"


def test_the_opt_in_builds_in_band_and_says_which_escalation_it_was(tmp_path: Path) -> None:
    """AC3 — a knowing caller is not blocked, and the run reports 176's `mode: full`."""
    seeded(tmp_path)
    lag_the_stored_era(tmp_path)

    payload = build_tool(config_for(tmp_path))(full=False, allow_full_rebuild=True)

    assert payload["mode"] == "full"
    change = payload["contract_change"]
    assert isinstance(change, dict) and change["escalated_to"] == "full"
    assert change["current"] == str(contract.CONTRACT_VERSION)
    wrote = payload["wrote"]
    # One file: the fake adapter owns `.aa`; `.cc` belongs to the second adapter.
    assert isinstance(wrote, dict) and wrote["files"] == 1, "the rebuild actually ran"


def test_the_three_escalation_states_are_disjoint(tmp_path: Path) -> None:
    """AC4 — a caller can tell which escalation it hit; checked per state, never as a total."""
    refused_root, opted_root, scoped_root = (tmp_path / n for n in ("a", "b", "c"))
    for root in (refused_root, opted_root, scoped_root):
        root.mkdir()

    seeded(refused_root)
    lag_the_stored_era(refused_root)
    refused = build_tool(config_for(refused_root))(full=False)

    seeded(opted_root)
    lag_the_stored_era(opted_root)
    opted = build_tool(config_for(opted_root))(full=False, allow_full_rebuild=True)

    seeded(scoped_root, ONE_ADAPTER)
    scoped = build_tool(config_for(scoped_root, TWO_ADAPTERS))(full=False)

    assert (refused["mode"], refused["reason"]) == ("refused", CONTRACT_REBUILD_REQUIRED)
    assert "contract_change" not in refused and "scope_change" not in refused

    assert opted["mode"] == "full"
    assert "contract_change" in opted and "scope_change" not in opted

    assert scoped["mode"] == "full"
    assert "scope_change" in scoped and "contract_change" not in scoped


def test_get_index_status_names_the_pending_rebuild(tmp_path: Path) -> None:
    """AC5 — call-this-first learns about the 73 minutes before spending them."""
    seeded(tmp_path)
    lag_the_stored_era(tmp_path)

    status = status_tool(config_for(tmp_path), (STATUS_NAME,))()

    pending = status[FULL_REBUILD_REQUIRED]
    assert isinstance(pending, dict)
    assert pending["reason"] == CONTRACT_REBUILD_REQUIRED
    assert pending["route"] == FULL_REBUILD_ROUTE


@pytest.mark.parametrize("detail_level", ["minimal", "standard"])
def test_the_summary_names_the_pending_rebuild_at_an_unmoved_head(
    tmp_path: Path, detail_level: str
) -> None:
    """347 AC1: HEAD has not moved, so staleness reads current — the summary must still say it."""
    seeded(tmp_path)
    stored = lag_the_stored_era(tmp_path)

    status = status_tool(config_for(tmp_path), (STATUS_NAME,))(detail_level=detail_level)

    assert status["staleness"] == "current"
    summary = str(status["summary"])
    assert summary.startswith("rebuild required")
    assert f"index contract v{stored}, server v{contract.CONTRACT_VERSION}" in summary
    assert f"`{FULL_REBUILD_ROUTE}`" in summary and "allow_full_rebuild=true" in summary
    assert "healthy" not in summary


def test_minimal_says_nothing_when_no_rebuild_is_pending(tmp_path: Path) -> None:
    """347 AC4: omit-when-empty at every level, so a same-era payload is unchanged."""
    seeded(tmp_path)
    status = status_tool(config_for(tmp_path), (STATUS_NAME,))(detail_level="minimal")
    assert FULL_REBUILD_REQUIRED not in status
    assert str(status["summary"]).startswith("current")


def test_get_index_status_says_nothing_when_no_rebuild_is_pending(tmp_path: Path) -> None:
    """AC5's other half, and R6.5: the field is observed absent, not assumed to omit itself."""
    seeded(tmp_path)

    status = status_tool(config_for(tmp_path), (STATUS_NAME,))()

    assert FULL_REBUILD_REQUIRED not in status


def test_the_shell_route_is_never_refused_and_maps_to_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC7/H1 — the refusal names `code-atlas-build`, so that command must not itself refuse."""
    seeded(tmp_path)
    lag_the_stored_era(tmp_path)
    env = {**ONE_ADAPTER, "CA_DB_PATH": str(tmp_path / ".code-atlas" / "graph.db")}
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    assert cli.build(tmp_path) == cli.OK

    with GraphStore(config_for(tmp_path).db_path) as store:
        assert store.get_meta(CONTRACT_VERSION_KEY) == str(contract.CONTRACT_VERSION)


def test_the_status_flag_reports_no_running_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC7 — 176's exit map in the same flow: no build running is `3`, never a failure."""
    seeded(tmp_path)
    monkeypatch.setenv("CA_DB_PATH", str(tmp_path / ".code-atlas" / "graph.db"))

    assert cli.status(tmp_path) == cli.NOTHING_TO_DO


def test_the_refusal_reason_is_not_the_only_thing_that_can_refuse(tmp_path: Path) -> None:
    """R5.4/R6.5 — `reason` holds one register, so the pre-201 refusals keep their own values."""
    env = {**os.environ}
    env.pop("CA_FAKE_CMD", None)
    config = load_config(tmp_path, {"CA_DB_PATH": str(tmp_path / ".code-atlas" / "graph.db")})

    payload = build_tool(config)(full=True)

    assert payload["reason"] == "no_usable_adapter" != CONTRACT_REBUILD_REQUIRED


def test_the_exit_map_covers_the_contract_refusal_it_will_never_see() -> None:
    """AC7 — 176's map must *cover* the new payload, which "the CLI never sends it" does not prove.

    Raised by the ticket-blind challenger: the shell route opts in, so this branch is unreachable
    from `code-atlas-build`. Unreachable is not the same as unhandled, and only one of those is
    checkable.
    """
    refusal = {
        "mode": "refused",
        "reason": CONTRACT_REBUILD_REQUIRED,
        "route": FULL_REBUILD_ROUTE,
        "performed": False,
    }

    assert cli.exit_code(refusal) == cli.FAILED
