"""Task 400: an incremental build publishes its writes in one step, as 356's full rebuild does.

Before 400 an incremental wrote the live index one file at a time, so a reader between a
dependent's re-parse and the resolve saw its calls unlinked and got ``reason: ok`` without them.
The builds here are real ``incremental_update`` runs over a real file database through the fake
adapter; the reads are the tools' own entry points, called from the build's progress callback.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from code_atlas.config import Config
from code_atlas.index_lock import try_index_write_lock
from code_atlas.indexer import incremental_update
from code_atlas.store import BUILD_COMPLETE, WRITE_ERRORS, GraphStore, close_fit_connections
from code_atlas.tools import fit
from code_atlas.tools.build_or_update_index import create as build_tool
from code_atlas.tools.find_callers import create as find_callers_tool
from tests.test_rebuild_behind_a_shadow_index import (
    CALLERS,
    CORE,
    Died,
    git,
    live_state,
    repo,
)


def committed_repo(root: Path) -> Config:
    """The shared fixture under git, built once, so a later commit leaves the index ``behind``."""
    config = repo(root)
    git(root, "init", "-q", ".")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "one")
    build_tool(config)(full=True)
    return config


def changed_core(config: Config) -> None:
    """A committed token change to the subject's file, so its callers re-parse as dependents."""
    (config.root / "lib/core.aa").write_text("class Thing {} // changed\n", encoding="utf-8")
    git(config.root, "commit", "-qam", "two")


def incremental(config: Config, probe) -> None:  # type: ignore[no-untyped-def]
    """One incremental over the live index, holding ``write.lock`` as every real build does."""
    with try_index_write_lock(config.db_path) as held, GraphStore(config.db_path) as store:
        assert held
        incremental_update(
            config, store, ["lib/core.aa"], progress=lambda phase, done, total: probe(phase)
        )


def test_callers_stay_listed_at_every_phase_of_an_incremental(tmp_path: Path) -> None:
    """AC1 (proving test): the subject's file changes and its callers are dependents. At every
    progress tick the callers are still listed. Fails before 400 — a re-parsed dependent's calls
    were unlinked until the resolve phase."""
    config = committed_repo(tmp_path)
    callers = find_callers_tool(config)
    assert callers(qname=CORE)["total_count"] == len(CALLERS)
    changed_core(config)
    phases: list[str] = []

    def probe(phase: str) -> None:
        phases.append(phase)
        answer = callers(qname=CORE)
        lost = f"callers lost during {phase}: {answer['reason']}"
        assert answer["total_count"] == len(CALLERS), lost

    incremental(config, probe)

    assert {"parse", "resolve", "meta"} <= set(phases)
    assert callers(qname=CORE)["total_count"] == len(CALLERS)


def test_a_served_call_during_an_incremental_does_not_wait_on_it(tmp_path: Path) -> None:
    """C1: the fit and cost bumps every served call makes skip while a build holds the live
    index, so a call neither waits out the 5 s busy timeout nor bumps a count."""
    config = committed_repo(tmp_path)
    served = fit.wrap("find_callers", config, find_callers_tool(config))
    changed_core(config)
    timings: list[float] = []

    def probe(phase: str) -> None:
        if phase == "resolve":
            started = time.monotonic()
            served(qname=CORE)
            timings.append(time.monotonic() - started)

    incremental(config, probe)

    assert timings and max(timings) < 1.0, f"a served call waited {timings}"
    close_fit_connections()
    with GraphStore(config.db_path) as store:
        assert not [k for k in store.list_fit_counts() if k["tool"] == "find_callers"]


def test_a_killed_incremental_leaves_the_graph_it_found(tmp_path: Path) -> None:
    """H2: whichever phase an incremental dies in, the rows and the completion stamp are what
    the previous build left, so the next build needs no escalation to ``--full``."""
    config = committed_repo(tmp_path)
    _, rows, stamp = live_state(config.db_path)
    assert stamp == BUILD_COMPLETE
    changed_core(config)

    for dying in ("parse", "resolve", "meta"):

        def die(phase: str, dying: str = dying) -> None:
            if phase == dying:
                raise Died(dying)

        with pytest.raises(Died):
            incremental(config, die)
        _, after, after_stamp = live_state(config.db_path)
        assert (after, after_stamp) == (rows, stamp), f"the live index moved when {dying} died"


def test_a_failing_file_in_a_batch_rolls_back_only_itself(tmp_path: Path) -> None:
    """C2 (R5.1): inside the batch one file's write error restores that file's rows, and every
    other write in the batch still commits."""
    node = {"kind": "Class", "name": "A", "line_start": 1}
    with GraphStore(tmp_path / "graph.db") as store:
        for path in ("a.aa", "b.aa"):
            store.upsert_file(path, "h", "fake", parsed_ok=True)
        store.replace_file_rows(
            "a.aa", [{**node, "qualified_name": "a::A", "file_path": "a.aa"}], []
        )
        original = store._insert

        def insert(table: str, groups: object) -> None:
            if failing:
                raise sqlite3.IntegrityError("planted")
            original(table, groups)

        failing = False
        store._insert = insert  # type: ignore[method-assign]
        with store.batched():
            store.begin_batch()
            store.replace_file_rows(
                "b.aa", [{**node, "qualified_name": "b::A", "file_path": "b.aa"}], []
            )
            failing = True
            with pytest.raises(WRITE_ERRORS):
                store.replace_file_rows("a.aa", [], [])
            failing = False
        store._insert = original  # type: ignore[method-assign]
        names = set(store.qnames_in_files(["a.aa", "b.aa"]))

    assert names == {"a::A", "b::A"}
