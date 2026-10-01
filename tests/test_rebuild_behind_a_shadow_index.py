"""Task 356: a full rebuild keeps serving the last good index until the new one is published.

The build fills ``graph.db.shadow`` and copies it over the live index in one SQLite backup, so a
reader sees the previous graph or the new one, never a half-built one. The builds here are real
``full_build`` runs over a real file database through the fake adapter; the reads are the tools'
own entry points, called from the build's progress callback so every phase is visited.
"""

from __future__ import annotations

import hashlib
import os
import shlex
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import Config, load_config
from code_atlas.index_lock import publish_build_progress, read_build_progress, try_index_write_lock
from code_atlas.indexer import full_build, incremental_update
from code_atlas.store import (
    BUILD_COMPLETE,
    BUILD_COMPLETE_KEY,
    MEMORY_DB,
    GraphStore,
    bump_fit_count,
    close_fit_connections,
    shadow_db_path,
)
from code_atlas.tools.build_or_update_index import create as build_tool
from code_atlas.tools.find_callers import create as find_callers_tool
from code_atlas.tools.get_index_status import create as status_tool
from code_atlas.tools.read_symbol import create as read_symbol_tool
from code_atlas.tools.schema_guard import BUILD_IN_PROGRESS, BUILD_PHASE, guard

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
CORE = "lib/core.aa::Thing"
CALLERS = ("dep/a.aa", "dep/b.aa")
NODE_COLUMNS = ", ".join(contract.NODE_FIELDS)
EDGE_COLUMNS = ", ".join(contract.EDGE_FIELDS)


def env_for(root: Path) -> dict[str, str]:
    return {
        "CA_WORKERS": "1",
        "CA_ADAPTER_TIMEOUT": "30",
        "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
        "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
    }


def config_for(root: Path) -> Config:
    return load_config(root, env_for(root))


def inherited_env() -> dict[str, str]:
    """This process's environment minus `CA_*`, so a child build sees only the fake adapter."""
    return {key: value for key, value in os.environ.items() if not key.startswith("CA_")}


def write(root: Path, *paths: str) -> None:
    for path in paths:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"class Thing {{}} // {path}\n", encoding="utf-8")


def repo(root: Path) -> Config:
    write(root, "lib/core.aa", *CALLERS, "src/x.aa")
    return config_for(root)


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root, check=True, capture_output=True,
    )


def snapshot(store: GraphStore) -> dict[str, list[tuple[object, ...]]]:
    """Row content under the R4.2 carve-out: no ids, no ``updated_at`` (as 219's test)."""
    conn = store._conn
    return {
        "files": conn.execute(
            "SELECT path, hash, language, parsed_ok FROM files ORDER BY path"
        ).fetchall(),
        "nodes": conn.execute(
            f"SELECT {NODE_COLUMNS} FROM nodes ORDER BY qualified_name, file_path, line_start"
        ).fetchall(),
        "edges": conn.execute(
            f"SELECT {EDGE_COLUMNS} FROM edges "
            "ORDER BY source_qname, kind, target_raw, file_path, line"
        ).fetchall(),
    }


def live_state(db: Path) -> tuple[str, dict[str, list[tuple[object, ...]]], str | None]:
    """The main file's bytes, its rows, and its completion stamp — what a kill must not move."""
    digest = hashlib.sha256(db.read_bytes()).hexdigest()
    with GraphStore(db) as store:
        return digest, snapshot(store), store.get_meta(BUILD_COMPLETE_KEY)


def node_count(db: Path) -> int:
    with GraphStore(db) as store:
        return store.counts()["nodes"]


def rebuild(config: Config, probe: Callable[[str], None]) -> None:
    """One more full build over the live index, calling ``probe`` at every progress tick."""
    with GraphStore(config.db_path) as store:
        full_build(config, store, progress=lambda phase, done, total: probe(phase))


class Died(RuntimeError):
    """Stands in for a kill at one phase: the build stops there and nothing after it runs."""


def test_reads_answer_from_the_last_good_index_at_every_build_phase(tmp_path: Path) -> None:
    """AC1 (proving test): at every phase of a rebuild, the reads see everything the previous
    build held. Fails before 356 — the rebuild truncated the live index first."""
    config = repo(tmp_path)
    build_tool(config)(full=True)
    before = node_count(config.db_path)
    read = read_symbol_tool(config)
    callers = find_callers_tool(config)
    phases: list[str] = []

    def probe(phase: str) -> None:
        phases.append(phase)
        assert node_count(config.db_path) >= before, f"fewer nodes during {phase}"
        hit = read(qname=CORE)
        assert hit["found"] is True, f"{CORE} not found during {phase}: {hit['reason']}"
        called = callers(qname=CORE)
        assert called["total_count"] == len(CALLERS), f"callers lost during {phase}"

    rebuild(config, probe)

    assert {"announce", "parse", "meta", "publish"} <= set(phases)


def test_a_reader_thread_never_misses_across_the_swap(tmp_path: Path) -> None:
    """AC1 under real concurrency: a reader on its own thread and connection, looping through a
    whole rebuild including the backup, never gets a not-found for a symbol both builds hold."""
    config = repo(tmp_path)
    build_tool(config)(full=True)
    read = read_symbol_tool(config)
    answers: list[bool] = []
    done = threading.Event()

    def reader() -> None:
        while not done.is_set():
            answers.append(read(qname=CORE)["found"] is True)

    thread = threading.Thread(target=reader)
    thread.start()
    try:
        for _ in range(3):
            assert build_tool(config)(full=True)["mode"] == "full"
    finally:
        done.set()
        thread.join()
    assert answers and all(answers), f"{answers.count(False)} of {len(answers)} reads missed"


def test_an_incomplete_shadow_is_never_published(tmp_path: Path) -> None:
    """Scope 1: publish only a shadow its build stamped complete."""
    live = tmp_path / "graph.db"
    shadow = GraphStore.open_shadow(live)
    with pytest.raises(ValueError, match="never stamped complete"):
        shadow.publish()
    shadow.discard()
    assert not live.exists()


def test_a_build_that_dies_at_any_phase_leaves_the_live_index_untouched(tmp_path: Path) -> None:
    """AC2: whichever phase a build dies in, the live file's bytes, rows and completion stamp are
    what the previous build left, and no shadow stays behind."""
    config = repo(tmp_path)
    build_tool(config)(full=True)
    phases: list[str] = []
    rebuild(config, lambda phase: phases.append(phase) if phase not in phases else None)
    before = live_state(config.db_path)
    assert before[2] == BUILD_COMPLETE

    for dying in phases:

        def die(phase: str, dying: str = dying) -> None:
            if phase == dying:
                raise Died(dying)

        with pytest.raises(Died):
            rebuild(config, die)
        assert live_state(config.db_path) == before, f"the live index moved when {dying} died"
        assert not shadow_db_path(config.db_path).exists(), f"a shadow survived {dying}"


def test_a_killed_build_process_leaves_the_live_index_untouched(tmp_path: Path) -> None:
    """AC2 by a real SIGKILL mid-parse: nothing in-process gets to clean up, and the live index
    is still the previous build's."""
    src = tmp_path / "src"
    src.mkdir()
    for n in range(1500):
        (src / f"m{n}.aa").write_text(f"class Thing{n} {{}}\n", encoding="utf-8")
    config = config_for(tmp_path)
    build_tool(config)(full=True)
    before = live_state(config.db_path)
    script = (
        "import os, pathlib;"
        "from code_atlas.config import load_config;"
        "from code_atlas.tools.build_or_update_index import create;"
        "create(load_config(pathlib.Path(os.environ['CA_ROOT'])))(full=True, "
        "allow_full_rebuild=True)"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", script],
        env={**inherited_env(), **env_for(tmp_path), "CA_ROOT": str(tmp_path)},
        cwd=tmp_path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 60
    try:
        while True:
            line = read_build_progress(config.db_path)
            if line and "phase=parse" in line and "done=" in line:
                break
            assert child.poll() is None, "the build finished before it could be killed (R6.5)"
            assert time.monotonic() < deadline, "no build reached phase=parse within 60s"
            time.sleep(0.02)
        assert node_count(config.db_path) == len(before[1]["nodes"])
    finally:
        child.send_signal(signal.SIGKILL)
        child.wait(timeout=30)

    assert live_state(config.db_path) == before
    # The next build drops what the killed one left behind, then publishes as usual.
    assert build_tool(config)(full=True)["mode"] == "full"
    assert not shadow_db_path(config.db_path).exists()


def test_a_published_rebuild_equals_an_in_place_build_row_for_row(tmp_path: Path) -> None:
    """AC3: the call after the publish answers from the new graph, and that graph is the one an
    in-place build writes (R4.2)."""
    config = repo(tmp_path)
    build_tool(config)(full=True)
    write(tmp_path, "src/new.aa")
    missing = read_symbol_tool(config)(qname="src/new.aa::Thing")
    assert missing["found"] is False

    with GraphStore(config.db_path) as live:
        full_build(config, live)
        published = snapshot(live)
    with GraphStore(Path(MEMORY_DB)) as in_place:
        full_build(config, in_place)
        expected = snapshot(in_place)

    assert published == expected
    found = read_symbol_tool(config)(qname="src/new.aa::Thing")
    assert found["found"] is True


def test_reads_during_a_build_name_it_and_its_phase(tmp_path: Path) -> None:
    """AC4: while a writer holds the lock, every guarded answer says a build is running and in
    which phase; with none, the answer is byte-identical to before (061)."""
    config = repo(tmp_path)
    build_tool(config)(full=True)
    read = guard(read_symbol_tool(config), config)

    quiet = read(qname=CORE)
    assert BUILD_IN_PROGRESS not in quiet and BUILD_PHASE not in quiet

    with try_index_write_lock(config.db_path) as held:
        assert held
        publish_build_progress(config.db_path, "phase=parse done=1 total=4 pid=1 at=0")
        during = read(qname=CORE)

    assert during[BUILD_IN_PROGRESS] is True and during[BUILD_PHASE] == "parse"
    assert {k: v for k, v in during.items() if k not in (BUILD_IN_PROGRESS, BUILD_PHASE)} == quiet


def test_a_build_in_flight_never_makes_a_behind_index_read_current(tmp_path: Path) -> None:
    """AC4: the live index is the last good one, so with HEAD moved past it a mid-build status
    says ``behind`` and names the build — never ``current``."""
    config = repo(tmp_path)
    git(tmp_path, "init", "-q", ".")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "one")
    build_tool(config)(full=True)
    write(tmp_path, "src/later.aa")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "two")
    status = guard(status_tool(config, ("get_index_status", "build_or_update_index")), config)

    with try_index_write_lock(config.db_path) as held:
        assert held
        publish_build_progress(config.db_path, "phase=resolve pid=1 at=0")
        during = status()

    assert during["staleness"] == "behind"
    assert during[BUILD_IN_PROGRESS] is True and during[BUILD_PHASE] == "resolve"


def test_an_escalated_incremental_leaves_the_live_index_untouched_until_publish(
    tmp_path: Path,
) -> None:
    """Scope 1: the escalations inside ``incremental_update`` reach the shadowed full build before
    their first write, so the live index is the previous one right up to the publish."""
    config = repo(tmp_path)
    build_tool(config)(full=True)
    with GraphStore(config.db_path) as store:
        store.set_meta("indexed_suffixes", ".aa")  # the adapter now also claims .bb: scope moved
    before = live_state(config.db_path)

    seen: list[tuple[str, str]] = []
    original = GraphStore.publish

    def publish(shadow: GraphStore) -> None:
        seen.append(live_state(config.db_path)[:1] + (shadow.db_path.name,))
        original(shadow)

    scope: dict[str, object] = {}
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(GraphStore, "publish", publish)
        with GraphStore(config.db_path) as store:
            incremental_update(config, store, ["src/x.aa"], scope=scope)

    assert "scope_change" in scope
    assert seen == [(before[0], shadow_db_path(config.db_path).name)]


def test_an_outgrown_index_is_replaced_only_by_the_publish(tmp_path: Path) -> None:
    """Scope 1: an older-schema index is not unlinked first — readers keep its mismatch answer
    until the rebuilt graph is published over it."""
    config = repo(tmp_path)
    build_tool(config)(full=True)
    conn = sqlite3.connect(config.db_path)
    conn.execute("UPDATE meta SET value = '1' WHERE key = 'schema_version'")
    conn.commit()
    conn.close()

    at_publish: list[str] = []
    original = GraphStore.publish

    def publish(shadow: GraphStore) -> None:
        live = sqlite3.connect(config.db_path)
        at_publish.append(
            live.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()[0]
        )
        live.close()
        original(shadow)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(GraphStore, "publish", publish)
        result = build_tool(config)(full=True)

    assert result["schema_rebuilt"] is True
    assert at_publish == ["1"]
    assert read_symbol_tool(config)(qname=CORE)["found"] is True


def test_the_shadow_takes_the_live_page_size(tmp_path: Path) -> None:
    """Risk 4: a backup into a WAL database refuses a different page size, so the shadow copies
    the live one before its first write."""
    live = tmp_path / "graph.db"
    conn = sqlite3.connect(live)
    conn.execute("PRAGMA page_size=1024")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE t (a)")
    conn.commit()
    conn.close()

    shadow = GraphStore.open_shadow(live)
    assert shadow._conn.execute("PRAGMA page_size").fetchone()[0] == 1024
    shadow.set_meta(BUILD_COMPLETE_KEY, BUILD_COMPLETE)
    shadow.publish()
    with GraphStore(live) as published:
        assert published.get_meta("schema_version") is not None
    assert not shadow_db_path(live).exists()


def test_the_publish_carries_the_fit_counts_readers_wrote(tmp_path: Path) -> None:
    """Risk 2: fit counters bumped on the live index during a build survive its publish (260)."""
    config = repo(tmp_path)
    build_tool(config)(full=True)
    bump_fit_count(config.db_path, "read_symbol", "ok", authoritative=True, truncated=False)

    def bump(phase: str) -> None:
        if phase == "meta":
            bump_fit_count(
                config.db_path, "read_symbol", "ok", authoritative=True, truncated=False
            )

    rebuild(config, bump)
    close_fit_connections()
    with GraphStore(config.db_path) as store:
        assert store.get_meta("fit:read_symbol|ok|1|0") == "2"
