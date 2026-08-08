"""Task 052: profile incremental_update phases (measure-only; no optimisation)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from code_atlas.indexer import INCREMENTAL_PHASES, full_build, incremental_update
from code_atlas.store import GraphStore
from tests.test_incremental import committed, config_for

REPO = Path(__file__).resolve().parent.parent
_SCRIPT = REPO / "scripts" / "profile_incremental.py"


def _load_profiler():
    spec = importlib.util.spec_from_file_location("profile_incremental", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_phase_times_cover_named_phases_and_sum_near_wall(tmp_path: Path) -> None:
    """Proving: every named phase is timed; resolve is explicit; sum ≈ wall (AC1, AC2)."""
    profiler = _load_profiler()
    committed(tmp_path, {"src/a.aa": "one\n", "src/b.aa": "two\n"})
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)

    report = profiler.profile(tmp_path, db_path=config.db_path, pull_files=2)
    assert {s["scenario"] for s in report["scenarios"]} == {
        "noop",
        "one_edit",
        "pull_shaped",
    }
    for scenario in report["scenarios"]:
        phases = scenario["phases"]
        assert list(phases) == list(INCREMENTAL_PHASES)
        assert "resolve" in phases
        assert scenario["phase_sum_vs_wall"]["within_tolerance"] is True
        assert abs(scenario["phase_sum_seconds"] - scenario["wall_seconds"]) <= max(
            profiler.WALL_TOLERANCE * float(scenario["wall_seconds"]), 0.05
        )


def test_two_noops_leave_identical_counts(tmp_path: Path) -> None:
    """R4.2 / AC6: timings vary; counts must not."""
    committed(tmp_path, {"src/a.aa": "one\n", "src/b.aa": "two\n"})
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        first: dict[str, float] = {}
        r1 = incremental_update(config, store, [], phase_times=first)
        c1 = store.counts()
        second: dict[str, float] = {}
        r2 = incremental_update(config, store, [], phase_times=second)
        c2 = store.counts()

    assert r1 == r2
    assert c1 == c2
    assert set(first) >= set(INCREMENTAL_PHASES)
    assert set(second) >= set(INCREMENTAL_PHASES)


def test_profile_report_json_round_trip(tmp_path: Path) -> None:
    profiler = _load_profiler()
    committed(tmp_path, {"src/a.aa": "one\n"})
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    payload = profiler.profile(tmp_path, db_path=config.db_path, pull_files=1)
    blob = json.dumps(payload)
    assert json.loads(blob)["scenarios"][2]["scenario"] == "pull_shaped"
    assert payload["scenarios"][2]["changed_files"] == 1
