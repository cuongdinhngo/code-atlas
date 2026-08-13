"""Task 080: a true no-op incremental writes nothing and reports a zero delta.

Round 4 timed a no-op incremental at ~56 s on the anchor index and saw it report
``wrote:{files:0,parsed:0,nodes:0,edges:6071}`` — 6,071 edges written having parsed no file. Both
came from ``_count_late_writes`` (enrichment + resolver) running full-graph on every build. When the
delta is empty those passes only re-derive rows already present, so they are skipped: the floor
drops to collect+diff+hash and ``wrote.*`` becomes an honest zero. The fixture uses ``twin/*`` (two
``run`` definitions) + ``dep/name_*`` (a call to the short name) so the resolver *does* insert
siblings on a full build — the exact work a no-op re-derived before this fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from code_atlas import gitutil, indexer
from code_atlas.indexer import full_build, incremental_update
from code_atlas.store import LAST_COMMIT_KEY, GraphStore
from tests.test_incremental import committed, config_for


def _fixture_with_siblings(tmp_path: Path):
    """A tree whose full build inserts resolver siblings (ambiguous ``run`` call)."""
    committed(
        tmp_path,
        {
            "twin/a.aa": "one\n",
            "twin/b.aa": "two\n",
            "dep/name_x.aa": "calls run\n",
        },
    )
    return config_for(tmp_path)


def test_a_noop_incremental_does_not_rerun_the_late_writers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proving test: a true no-op skips enrichment+resolver and reports a zero delta (080).

    Fails pre-080 — both writers run and ``report.edges`` counts the re-derived siblings (> 0).
    """
    config = _fixture_with_siblings(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        last = store.get_meta(LAST_COMMIT_KEY)
    changed = gitutil.changed_paths(tmp_path, last)
    assert changed == ()  # nothing committed since the build → a true no-op

    calls = {"resolve": 0, "enrich": 0}
    real_resolve, real_enrich = indexer.resolve_edges, indexer.apply_indirection_rules

    def spy_resolve(*a: object, **k: object) -> object:
        calls["resolve"] += 1
        return real_resolve(*a, **k)

    def spy_enrich(*a: object, **k: object) -> object:
        calls["enrich"] += 1
        return real_enrich(*a, **k)

    monkeypatch.setattr(indexer, "resolve_edges", spy_resolve)
    monkeypatch.setattr(indexer, "apply_indirection_rules", spy_enrich)

    with GraphStore(config.db_path) as store:
        report = incremental_update(config, store, changed)

    assert calls == {"resolve": 0, "enrich": 0}  # late writers skipped on an empty delta
    assert (report.files, report.parsed, report.nodes, report.edges) == (0, 0, 0, 0)


def test_two_consecutive_noops_are_identical_and_zero(tmp_path: Path) -> None:
    """R4 / C1: two no-ops produce identical zero-delta payloads (080)."""
    config = _fixture_with_siblings(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        last = store.get_meta(LAST_COMMIT_KEY)
    changed = gitutil.changed_paths(tmp_path, last)

    with GraphStore(config.db_path) as store:
        first = incremental_update(config, store, changed)
    with GraphStore(config.db_path) as store:
        second = incremental_update(config, store, changed)

    assert first == second
    assert (first.files, first.parsed, first.nodes, first.edges) == (0, 0, 0, 0)


def test_a_real_delta_still_runs_the_late_writers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C3 / 068: a non-empty delta must still run enrichment+resolver — no over-skip (080)."""
    config = _fixture_with_siblings(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        last = store.get_meta(LAST_COMMIT_KEY)
    committed(tmp_path, {"dep/name_x.aa": "calls run, edited\n"}, message="edit")
    changed = gitutil.changed_paths(tmp_path, last)
    assert changed  # non-empty delta

    calls = {"resolve": 0}
    real_resolve = indexer.resolve_edges

    def spy_resolve(*a: object, **k: object) -> object:
        calls["resolve"] += 1
        return real_resolve(*a, **k)

    monkeypatch.setattr(indexer, "resolve_edges", spy_resolve)
    with GraphStore(config.db_path) as store:
        incremental_update(config, store, changed)

    assert calls["resolve"] == 1  # the writers still run when there is a real delta
