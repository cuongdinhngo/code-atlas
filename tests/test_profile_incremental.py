"""Task 052: profile incremental_update phases (measure-only; no optimisation)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from code_atlas.indexer import INCREMENTAL_PHASES, full_build, incremental_update
from code_atlas.store import GraphStore
from tests.test_incremental import committed, config_for, fake_env

REPO = Path(__file__).resolve().parent.parent
_SCRIPT = REPO / "scripts" / "profile_incremental.py"


def _load_profiler():
    spec = importlib.util.spec_from_file_location("profile_incremental", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_phase_times_cover_named_phases_and_sum_near_wall(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proving: phases timed; resolve verdict present; index survives the profiler (AC1, AC2)."""
    profiler = _load_profiler()
    for key, value in fake_env().items():
        monkeypatch.setenv(key, value)

    files = {f"src/f{i:03d}.aa": f"body {i}\n" for i in range(100)}
    committed(tmp_path, files)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)

    report = profiler.profile(tmp_path, db_path=config.db_path, pull_files=100)
    assert {s["scenario"] for s in report["scenarios"]} == {
        "noop",
        "one_edit",
        "pull_shaped",
    }
    noop = next(s for s in report["scenarios"] if s["scenario"] == "noop")
    pull = next(s for s in report["scenarios"] if s["scenario"] == "pull_shaped")
    assert noop["counts_unchanged"] is True
    assert noop["counts_after"]["files"] >= 1
    assert noop["resolve_hypothesis"]["verdict"] in {
        "confirmed",
        "refuted",
        "inconclusive",
    }
    assert pull["changed_files"] == 100
    assert isinstance(pull["wall_seconds"], float)
    for scenario in report["scenarios"]:
        phases = scenario["phases"]
        assert list(phases) == list(INCREMENTAL_PHASES)
        gap = scenario["phase_sum_vs_wall"]
        assert gap["within_tolerance"] is True
        # Load-independent: phases are spans inside wall, so the glue is never negative (070).
        assert gap["unattributed_seconds"] >= 0.0

    profiler.assert_tree_matches_index(config)


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


def test_bind_index_fails_loud_without_adapters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profiler = _load_profiler()
    committed(tmp_path, {"src/a.aa": "one\n"})
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    monkeypatch.delenv("CA_FAKE_CMD", raising=False)
    for key in list(__import__("os").environ):
        if key.startswith("CA_") and key.endswith("_CMD"):
            monkeypatch.delenv(key, raising=False)
    with pytest.raises(Exception, match="no adapters configured"):
        profiler.bind_index(tmp_path, config.db_path)
