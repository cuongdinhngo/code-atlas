"""Task 009: ``full_build`` against real subprocesses and a real database (§8.1).

Every acceptance criterion here can only fail at the integration or runtime layer — a fan-out that
writes from the wrong thread, a hash that is not the file's bytes, a child that never answers — so
nothing is mocked. The hang proofs park a genuinely sleeping process; a mock of one would only prove
the mock.

Three exclusions other tasks recorded are closed here: task 002's `contract.validate()` integration
half, task 005's hung adapter at both call sites, and task 004's `busy_timeout` contention (that one
lands in ``test_store.py``, beside the pragma it proves).
"""

import ast
import hashlib
import shlex
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.adapter import AdapterError, ParseResult
from code_atlas.config import Config, load_config
from code_atlas.indexer import BuildReport, _write, collect, full_build
from code_atlas.store import (
    BUILT_AT_KEY,
    CONTRACT_VERSION_KEY,
    INDEXED_SUFFIXES_KEY,
    LAST_COMMIT_KEY,
    GraphStore,
)

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP_FIXTURE = REPO / "tests" / "fixtures" / "php" / "namespaced.php"

# Short enough that a hang proof finishes, long enough that a healthy boot never trips it.
SHORT_TIMEOUT = 1
# A hang proof must return in far less than the 600 s the fixture would otherwise sleep.
BOUND = 30.0

NODE_COLUMNS = ", ".join(contract.NODE_FIELDS)
EDGE_COLUMNS = ", ".join(contract.EDGE_FIELDS)

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)


# --- fixtures and helpers -------------------------------------------------------------------


def indexed_config(
    root: Path, *, workers: int, command: Sequence[str], timeout: int = 30
) -> Config:
    """A build config with the worker count **pinned**.

    ``workers`` has no default on purpose: R4.2 forbids a fan-out assertion that silently inherits
    a hosted runner's core count, and a required argument enforces that better than a review note.
    """
    return load_config(
        root,
        {
            "CA_WORKERS": str(workers),
            "CA_ADAPTER_TIMEOUT": str(timeout),
            "CA_FAKE_CMD": shlex.join(command),
        },
    )


def fake_command(mode: str = "ok") -> tuple[str, ...]:
    return (sys.executable, str(FAKE), mode)


def php_config(root: Path, *, workers: int) -> Config:
    return load_config(
        root,
        {
            "CA_WORKERS": str(workers),
            "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        },
    )


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / ".code-atlas" / "graph.db") as opened:
        yield opened


class RecordingStore(GraphStore):
    """A store that remembers which threads mutated it — R4.3's single writer, made observable."""

    def __init__(self, db_path: Path) -> None:
        # Set first: creating the schema already writes, and the recorder must survive that.
        self.writers: set[int] = set()
        super().__init__(db_path)
        self.writers.clear()

    def upsert_file(self, *args: object, **kwargs: object) -> None:
        self.writers.add(threading.get_ident())
        super().upsert_file(*args, **kwargs)

    def replace_file_rows(self, *args: object, **kwargs: object) -> int:
        self.writers.add(threading.get_ident())
        return super().replace_file_rows(*args, **kwargs)

    def remove_file(self, *args: object, **kwargs: object) -> None:
        self.writers.add(threading.get_ident())
        super().remove_file(*args, **kwargs)

    def set_meta(self, *args: object, **kwargs: object) -> None:
        self.writers.add(threading.get_ident())
        super().set_meta(*args, **kwargs)


def tree(root: Path, *paths: str) -> tuple[str, ...]:
    """Create each path with distinct content, so no two files can share a hash by accident."""
    for index, path in enumerate(paths):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"content {index} of {path}\n", encoding="utf-8")
    return tuple(sorted(paths))


def git_repo(root: Path) -> None:
    for arguments in (["init", "-q"], ["add", "-A"]):
        subprocess.run(["git", *arguments], cwd=root, check=True, capture_output=True)


def files_table(store: GraphStore) -> dict[str, tuple[object, ...]]:
    rows = store._conn.execute("SELECT path, hash, language, parsed_ok FROM files").fetchall()
    return {str(row[0]): tuple(row[1:]) for row in rows}


def snapshot(store: GraphStore) -> dict[str, list[tuple[object, ...]]]:
    """Row **content** under task 004's ratified carve-out: no ids, no ``updated_at``."""
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


# --- the guard on the guards ------------------------------------------------------------------


def test_the_proof_has_something_to_run() -> None:
    # Runs without PHP: a skipped proof must not also hide a missing fixture or entry point.
    assert FAKE.is_file() and PHP_ENTRY.is_file() and PHP_FIXTURE.is_file()
    source = FAKE.read_text(encoding="utf-8")
    for mode in ("silent-boot", "silent-after-first-boot", "hang/"):
        assert mode in source, f"the fixture cannot stay silent as {mode}"


def test_no_build_here_can_inherit_the_runner_core_count() -> None:
    """R4.2: a hosted runner has fewer cores than a laptop, so an unpinned default is theirs."""
    tree_ = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree_)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "load_config"
    ]
    assert len(calls) == 3, "a new resolution site must be counted, not silently uncovered"
    for call in calls:
        keys = [element.value for element in call.args[1].keys if element is not None]
        assert "CA_WORKERS" in keys, "every build here pins the worker count explicitly"


# --- collection (§8.1 step 1) -------------------------------------------------------------------


def test_collection_takes_claimed_suffixes_minus_the_ignore_rules(tmp_path: Path) -> None:
    tree(
        tmp_path,
        "src/b.aa",
        "src/a.bb",
        "src/notes.md",
        "vendor/skipped.aa",
        "build/generated.aa",
        "keep/deep/nested.aa",
    )
    (tmp_path / ".codeatlasignore").write_text("build/\n", encoding="utf-8")
    git_repo(tmp_path)

    found = collect(tmp_path, (".aa", ".bb"))

    assert found == ("keep/deep/nested.aa", "src/a.bb", "src/b.aa")
    assert found == tuple(sorted(found)), "collection order must not depend on git's own ordering"


def test_collection_falls_back_to_a_walk_when_there_is_no_git_index(tmp_path: Path) -> None:
    """Same answer without a repo: `git ls-files` is the fast path, never the only one.

    The tree is shaped so the walk *reaches* the paths out of order — a root-level file is seen
    before a deeply nested one — so R4.2's ordering is proven, not merely inherited from git.
    """
    tree(tmp_path, "zz.aa", "aaa/deep/x.aa", "src/notes.md", "vendor/skipped.aa")
    expected = ("aaa/deep/x.aa", "zz.aa")

    walked = collect(tmp_path, (".aa", ".bb"))

    git_repo(tmp_path)
    assert walked == collect(tmp_path, (".aa", ".bb")) == expected


# --- the proving test ---------------------------------------------------------------------------


@needs_php
def test_the_core_builds_a_repo_into_a_queryable_index(tmp_path: Path, store: GraphStore) -> None:
    """G1/AC1a: a real adapter, a real database, and an index that answers real queries.

    A build that wrote no row would raise nothing at all, so every assertion here is about rows
    coming back out — the non-vacuity bar tasks 004/006/007 each set.
    """
    (tmp_path / "src").mkdir()
    shutil.copy(PHP_FIXTURE, tmp_path / "src" / "User.php")

    report = full_build(php_config(tmp_path, workers=2), store)

    assert report.files == 1 and report.parsed == 1 and report.failed == 0
    assert report.nodes > 1 and report.edges > 1

    found = store.nodes_by_name("User", kind="Class", limit=10)
    assert [row["qualified_name"] for row in found] == ["\\App\\Models\\User"]
    assert found[0]["file_path"] == "src/User.php"

    # The FTS index is consistent with `nodes`, not merely present.
    searched = store.search_nodes("User", kind="Class", limit=10)
    assert [row["qualified_name"] for row in searched] == ["\\App\\Models\\User"]

    extends = store.edges_by_source("\\App\\Models\\User", kinds=("EXTENDS",), limit=10)
    assert [row["target_raw"] for row in extends] == ["\\App\\Models\\Base"]
    assert extends[0]["target_qname"] is None, "external Base is absent — stays unlinked"

    assert store.get_meta(CONTRACT_VERSION_KEY) == str(contract.CONTRACT_VERSION)
    assert store.get_meta(BUILT_AT_KEY)
    assert files_table(store) == {
        "src/User.php": (sha256_of(tmp_path / "src" / "User.php"), "php", 1)
    }


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- idempotency, reconciliation, hashing, metadata ---------------------------------------------


def test_a_re_run_over_an_unchanged_tree_is_idempotent(tmp_path: Path, store: GraphStore) -> None:
    """AC1b, under the carve-out task 004 ratified: ids follow insert order, content does not."""
    paths = tree(tmp_path, "src/a.aa", "src/b.aa", "src/c.bb")
    config = indexed_config(tmp_path, workers=3, command=fake_command())

    first = full_build(config, store)
    before = snapshot(store)
    second = full_build(config, store)

    assert snapshot(store) == before
    assert first == second == BuildReport(
        files=len(paths), parsed=3, failed=0, removed=0, nodes=3, edges=0, stubs=0
    )


def test_a_vanished_path_loses_its_rows_on_the_next_build(
    tmp_path: Path, store: GraphStore
) -> None:
    tree(tmp_path, "src/a.aa", "src/b.aa")
    config = indexed_config(tmp_path, workers=1, command=fake_command())
    full_build(config, store)
    assert store.file_paths() == ("src/a.aa", "src/b.aa")

    (tmp_path / "src" / "b.aa").unlink()
    report = full_build(config, store)

    assert report.removed == 1
    assert store.file_paths() == ("src/a.aa",)
    assert store.nodes_by_file("src/b.aa", limit=10) == []
    assert store.search_nodes("src/b.aa::Thing", limit=10) == []


def test_the_stored_hash_is_the_sha256_of_the_file_bytes(tmp_path: Path, store: GraphStore) -> None:
    tree(tmp_path, "src/a.aa", "src/b.aa")
    full_build(indexed_config(tmp_path, workers=2, command=fake_command()), store)

    rows = files_table(store)
    assert rows["src/a.aa"][0] == sha256_of(tmp_path / "src" / "a.aa")
    assert rows["src/a.aa"][0] != rows["src/b.aa"][0], "two files must not share one hash"


def test_the_build_stamps_the_index_with_its_provenance(tmp_path: Path, store: GraphStore) -> None:
    tree(tmp_path, "src/a.aa")
    config = indexed_config(tmp_path, workers=1, command=fake_command())

    full_build(config, store)
    assert store.get_meta(CONTRACT_VERSION_KEY) == str(contract.CONTRACT_VERSION)
    assert store.get_meta(BUILT_AT_KEY)
    # No repo, so there is honestly no commit to name — an absent key, never a fabricated one.
    assert store.get_meta(LAST_COMMIT_KEY) is None

    git_repo(tmp_path)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "seed"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    full_build(config, store)
    assert store.get_meta(LAST_COMMIT_KEY) == head_of(tmp_path)


def head_of(root: Path) -> str:
    found = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    return found.stdout.strip()


# --- AC2: one writer, N workers ------------------------------------------------------------------


def test_every_write_happens_on_the_single_writer_thread(tmp_path: Path) -> None:
    """AC2a/R4.3. Also structurally true: the database driver binds a connection to its maker."""
    tree(tmp_path, *[f"src/f{index}.aa" for index in range(12)])
    with RecordingStore(tmp_path / ".code-atlas" / "graph.db") as recording:
        report = full_build(indexed_config(tmp_path, workers=4, command=fake_command()), recording)

        assert report.parsed == 12, "a build that wrote nothing would satisfy any writer claim"
        assert recording.writers == {threading.get_ident()}


def test_the_worker_count_honours_the_configured_value(
    tmp_path: Path, store: GraphStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2b: exactly k processes for a repo with more files than workers — the probe is worker 0."""
    boot_log = tmp_path / "boots.log"
    monkeypatch.setenv("CA_FAKE_BOOTLOG", str(boot_log))
    tree(tmp_path, *[f"src/f{index}.aa" for index in range(12)])

    full_build(indexed_config(tmp_path, workers=3, command=fake_command()), store)

    assert len(boot_log.read_text(encoding="utf-8").splitlines()) == 3


# --- AC3 / B1 / B6: soft failures never break the stream -----------------------------------------


def test_a_result_the_contract_rejects_is_recorded_unparsed_and_the_stream_survives(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC3 — task 002's excluded integration half: `validate()` driven through a real build."""
    tree(tmp_path, "invalid/bad.aa", "zafter/good.aa")

    report = full_build(indexed_config(tmp_path, workers=1, command=fake_command()), store)

    rows = files_table(store)
    assert rows["invalid/bad.aa"][2] == 0
    assert rows["zafter/good.aa"][2] == 1, "one rejected result must not end the boot"
    assert report.parsed == 1 and report.failed == 1
    assert store.nodes_by_file("invalid/bad.aa", limit=10) == []


def test_a_soft_parse_failure_is_recorded_and_the_stream_survives(
    tmp_path: Path, store: GraphStore
) -> None:
    """B1/R5.1: an `ok:false` reply is one bad file, never a dead build."""
    tree(tmp_path, "soft-error/bad.aa", "zafter/good.aa")

    full_build(indexed_config(tmp_path, workers=1, command=fake_command()), store)

    rows = files_table(store)
    assert rows["soft-error/bad.aa"][2] == 0 and rows["zafter/good.aa"][2] == 1


def test_an_adapter_that_exits_mid_stream_does_not_wedge_the_build(
    tmp_path: Path, store: GraphStore
) -> None:
    """B6: a dead process is loud to the driver and soft to the build — and the worker restarts."""
    tree(tmp_path, "die/gone.aa", "zafter/good.aa")

    full_build(indexed_config(tmp_path, workers=1, command=fake_command()), store)

    rows = files_table(store)
    assert rows["die/gone.aa"][2] == 0
    assert rows["zafter/good.aa"][2] == 1, "the worker must replace the dead adapter and carry on"


# --- AC4: the hung adapter, at both call sites ---------------------------------------------------


def test_an_adapter_that_never_answers_is_killed_and_that_file_recorded_unparsed(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC4 (silent reply) — closes task 005's exclusion at `parse()`.

    The fixture sleeps for ten minutes; without the deadline this test would never return, which is
    exactly the wedge the ticket describes.
    """
    tree(tmp_path, "hang/silent.aa", "zafter/good.aa")
    config = indexed_config(tmp_path, workers=1, command=fake_command(), timeout=SHORT_TIMEOUT)

    started = time.monotonic()
    report = full_build(config, store)
    elapsed = time.monotonic() - started

    assert elapsed < BOUND, "the build waited on a silent adapter instead of killing it"
    rows = files_table(store)
    assert rows["hang/silent.aa"][2] == 0
    assert rows["zafter/good.aa"][2] == 1, "a killed adapter must be replaced, not end the build"
    assert report.files == 2 and report.failed == 1


def test_a_worker_whose_adapter_never_announces_does_not_wedge_the_build(
    tmp_path: Path, store: GraphStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC4 (silent boot) — closes task 005's exclusion at `start()`.

    The first boot is the probe and answers; every later boot goes silent, so the extra workers hang
    on the handshake. The build must still return, with a `files` row for every collected path.
    """
    monkeypatch.setenv("CA_FAKE_BOOTLOG", str(tmp_path / "boots.log"))
    paths = tree(tmp_path, *[f"src/f{index}.aa" for index in range(6)])
    config = indexed_config(
        tmp_path,
        workers=3,
        command=fake_command("silent-after-first-boot"),
        timeout=SHORT_TIMEOUT,
    )

    started = time.monotonic()
    report = full_build(config, store)
    elapsed = time.monotonic() - started

    assert elapsed < BOUND, "a silent worker boot wedged the build"
    assert report.files == len(paths)
    assert set(files_table(store)) == set(paths), "every collected path must leave a files row"
    assert report.parsed >= 1, "the worker that did boot must still have done its share"


def test_an_adapter_that_never_announces_at_all_fails_loud_rather_than_hanging(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC4 (silent probe): no file is known yet, so there is nothing to record — R5.3 applies."""
    tree(tmp_path, "src/a.aa")
    config = indexed_config(
        tmp_path, workers=1, command=fake_command("silent-boot"), timeout=SHORT_TIMEOUT
    )

    started = time.monotonic()
    with pytest.raises(AdapterError, match="did not announce itself"):
        full_build(config, store)

    assert time.monotonic() - started < BOUND, "the build hung on the handshake"


# --- the whole build, one language at a time -----------------------------------------------------


def test_a_file_no_adapter_claims_is_never_indexed(tmp_path: Path, store: GraphStore) -> None:
    tree(tmp_path, "src/a.aa", "src/README.md", "src/script.zz")

    report = full_build(indexed_config(tmp_path, workers=1, command=fake_command()), store)

    assert report.files == 1
    assert store.file_paths() == ("src/a.aa",)


def test_the_language_stored_is_the_one_the_adapter_announced(
    tmp_path: Path, store: GraphStore
) -> None:
    # R1.1: the core never names a language; it repeats what the handshake said.
    tree(tmp_path, "src/a.aa")

    full_build(indexed_config(tmp_path, workers=1, command=fake_command()), store)

    assert files_table(store)["src/a.aa"][1] == "fake"


def test_a_build_with_no_configured_adapter_fails_loud(
    tmp_path: Path, store: GraphStore
) -> None:
    """Task 064: empty adapter_cmds is config error, not a successful empty index."""
    tree(tmp_path, "src/a.aa")

    with pytest.raises(AdapterError, match="no adapters configured"):
        full_build(load_config(tmp_path, {"CA_WORKERS": "1"}), store)

    assert store.get_meta(LAST_COMMIT_KEY) is None
    assert store.get_meta(INDEXED_SUFFIXES_KEY) is None


# --- task 043: the per-file write soft-fails a bad file; it never aborts the build (R5.1) ---------


def _node(kind: str, name: str, qname: str, path: str, line: int) -> dict[str, object]:
    return {
        "kind": kind,
        "name": name,
        "qualified_name": qname,
        "file_path": path,
        "line_start": line,
    }


def test_write_survives_duplicate_declarations(store: GraphStore) -> None:
    """A file emitting two same-qname nodes soft-succeeds; each dup name resolves to one node (AC1).

    Pre-fix this raised sqlite3.IntegrityError out of `_write`, which aborted the whole build.
    """
    result = ParseResult(
        path="dup.php",
        ok=True,
        nodes=(
            _node("Function", "f", "\\f", "dup.php", 1),
            _node("Function", "f", "\\f", "dup.php", 9),
            _node("Interface", "X", "\\X", "dup.php", 20),
            _node("Class", "X", "\\X", "dup.php", 30),
        ),
        edges=(),
    )
    tally = {"parsed": 0, "failed": 0, "nodes": 0, "edges": 0}

    _write(store, "dup.php", "digest", "php", result, tally)

    assert tally == {"parsed": 1, "failed": 0, "nodes": 2, "edges": 0}
    assert store.counts()["parsed"] == 1
    # INVENTORY N=2: each duplicated name resolves to exactly one node.
    assert len(store.nodes_by_qualified_name("\\f", limit=10)) == 1
    assert len(store.nodes_by_qualified_name("\\X", limit=10)) == 1


def test_write_soft_fails_a_per_file_store_error(
    store: GraphStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A per-file store error marks that file parsed_ok=0 and the build carries on (AC4)."""

    def boom(*_args: object, **_kwargs: object) -> int:
        raise sqlite3.IntegrityError("simulated per-file store error")

    monkeypatch.setattr(store, "replace_file_rows", boom)
    tally = {"parsed": 0, "failed": 0, "nodes": 0, "edges": 0}
    bad = ParseResult(
        path="bad.php", ok=True, nodes=(_node("Class", "B", "\\B", "bad.php", 1),), edges=()
    )

    _write(store, "bad.php", "digest", "php", bad, tally)  # must not raise

    assert tally["failed"] == 1
    assert store.counts()["parsed"] == 0

    # The build carries on: the next file writes normally.
    monkeypatch.undo()
    good = ParseResult(
        path="ok.php", ok=True, nodes=(_node("Class", "G", "\\G", "ok.php", 1),), edges=()
    )
    _write(store, "ok.php", "digest", "php", good, tally)
    assert tally["parsed"] == 1
    assert store.counts()["parsed"] == 1
