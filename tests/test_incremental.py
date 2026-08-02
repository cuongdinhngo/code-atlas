"""Task 016: incremental update via git diff (§8.3).

Hermetic throwaway repos only — CI stays shallow; every proof builds its own history.
"""

from __future__ import annotations

import hashlib
import shlex
import subprocess
import sys
from pathlib import Path

from code_atlas import contract, gitutil
from code_atlas.config import load_config
from code_atlas.indexer import full_build, incremental_update
from code_atlas.main import build_server
from code_atlas.store import LAST_COMMIT_KEY, GraphStore
from code_atlas.tools.build_or_update_index import NAME as BUILD
from code_atlas.tools.get_index_status import NAME as STATUS
from tests.test_mcp_server import call

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"

NODE_COLUMNS = ", ".join(contract.NODE_FIELDS)
EDGE_COLUMNS = ", ".join(contract.EDGE_FIELDS)


def fake_env(workers: int = 2) -> dict[str, str]:
    return {
        "CA_WORKERS": str(workers),
        "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
    }


def git(root: Path, *arguments: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=test", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def write(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def committed(root: Path, files: dict[str, str], message: str = "commit") -> str:
    for path, body in files.items():
        write(root, path, body)
    if not (root / ".git").exists():
        git(root, "init", "-q")
        # Keep the index out of the diff so incremental proofs see source edits only.
        write(root, ".gitignore", ".code-atlas/\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", message)
    return git(root, "rev-parse", "HEAD")


def config_for(root: Path, db_name: str = "graph.db"):
    db = root / ".code-atlas" / db_name
    return load_config(root, {**fake_env(), "CA_DB_PATH": str(db)})


def snapshot(store: GraphStore) -> dict[str, list[tuple[object, ...]]]:
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


def node_id(store: GraphStore, path: str) -> int:
    row = store._conn.execute(
        "SELECT id FROM nodes WHERE file_path = ? ORDER BY id LIMIT 1", (path,)
    ).fetchone()
    assert row is not None
    return int(row[0])


def test_changed_paths_lists_edits_and_none_on_bad_since(tmp_path: Path) -> None:
    committed(tmp_path, {"a.aa": "one\n"})
    first = git(tmp_path, "rev-parse", "HEAD")
    committed(tmp_path, {"a.aa": "two\n", "b.aa": "new\n"}, message="second")

    assert gitutil.changed_paths(tmp_path, first) == ("a.aa", "b.aa")
    assert gitutil.changed_paths(tmp_path, "0" * 40) is None


def test_one_file_edit_matches_full_rebuild_and_leaves_unrelated_ids(tmp_path: Path) -> None:
    """AC1: incremental content equals a fresh full build; unrelated row ids stay put."""
    committed(
        tmp_path,
        {
            "lib/core.aa": "core v1\n",
            "dep/user.aa": "calls core\n",
            "other/stay.aa": "untouched\n",
        },
    )
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        stay_id = node_id(store, "other/stay.aa")
        dep_before = store.edges_by_source("dep/user.aa::Thing", kinds=("CALLS",), limit=5)
        assert [row["target_qname"] for row in dep_before] == ["lib/core.aa::Thing"]
        last = store.get_meta(LAST_COMMIT_KEY)
        assert last is not None

    committed(tmp_path, {"lib/core.aa": "core v2\n"}, message="edit core")
    changed = gitutil.changed_paths(tmp_path, last)
    assert changed == ("lib/core.aa",)

    with GraphStore(config.db_path) as store:
        report = incremental_update(config, store, changed)
        assert report.files >= 1
        assert node_id(store, "other/stay.aa") == stay_id
        # Dependent was hash-skipped but re-linked after unlink.
        dep_after = store.edges_by_source("dep/user.aa::Thing", kinds=("CALLS",), limit=5)
        assert [row["target_qname"] for row in dep_after] == ["lib/core.aa::Thing"]
        digest = hashlib.sha256(b"core v2\n").hexdigest()
        assert store.file_hash("lib/core.aa") == digest
        incremental = snapshot(store)

    fresh = config_for(tmp_path, "fresh.db")
    with GraphStore(fresh.db_path) as store:
        full_build(fresh, store)
        assert snapshot(store) == incremental


def test_build_tool_runs_incremental_then_clears_staleness(tmp_path: Path) -> None:
    """AC2: behind after a new commit; incremental brings status back to current."""
    committed(tmp_path, {"src/a.aa": "one\n", "src/b.aa": "two\n"})
    config = config_for(tmp_path)
    server = build_server(config)

    first = call(server, BUILD, {"full": True})
    assert first["mode"] == "full"
    assert call(server, STATUS, {})["staleness"] == "current"

    committed(tmp_path, {"src/a.aa": "edited\n"}, message="edit")
    assert call(server, STATUS, {})["staleness"] == "behind"

    second = call(server, BUILD, {"full": False})
    assert second["mode"] == "incremental"
    assert second["requested_full"] is False
    status = call(server, STATUS, {})
    assert status["staleness"] == "current"
    assert status["last_commit"] == git(tmp_path, "rev-parse", "HEAD")


def test_bad_last_commit_falls_back_to_full(tmp_path: Path) -> None:
    committed(tmp_path, {"src/a.aa": "one\n"})
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        store.set_meta(LAST_COMMIT_KEY, "0" * 40)

    result = call(build_server(config), BUILD, {"full": False})
    assert result["mode"] == "full"


def test_heuristic_siblings_still_match_a_full_rebuild(tmp_path: Path) -> None:
    """R4.2: unlink must collapse top-N siblings or hash-skipped dependents diverge."""
    committed(
        tmp_path,
        {
            "twin/a.aa": "run a v1\n",
            "twin/b.aa": "run b\n",
            "dep/name_caller.aa": "calls run\n",
        },
    )
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        linked = store.edges_by_source("dep/name_caller.aa::Thing", kinds=("CALLS",), limit=10)
        assert len(linked) == 2
        last = store.get_meta(LAST_COMMIT_KEY)
        assert last is not None

    committed(tmp_path, {"twin/a.aa": "run a v2\n"}, message="edit twin a")
    changed = gitutil.changed_paths(tmp_path, last)
    assert changed == ("twin/a.aa",)

    with GraphStore(config.db_path) as store:
        incremental_update(config, store, changed)
        incremental = snapshot(store)
        linked = store.edges_by_source("dep/name_caller.aa::Thing", kinds=("CALLS",), limit=10)
        assert len(linked) == 2

    fresh = config_for(tmp_path, "fresh.db")
    with GraphStore(fresh.db_path) as store:
        full_build(fresh, store)
        assert snapshot(store) == incremental


def test_delete_is_reconciled_like_a_full_rebuild(tmp_path: Path) -> None:
    committed(tmp_path, {"keep.aa": "k\n", "gone.aa": "g\n"})
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        last = store.get_meta(LAST_COMMIT_KEY)
        assert last is not None
        assert "gone.aa" in store.file_paths()

    (tmp_path / "gone.aa").unlink()
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "delete")
    changed = gitutil.changed_paths(tmp_path, last)
    assert changed == ("gone.aa",)

    with GraphStore(config.db_path) as store:
        report = incremental_update(config, store, changed)
        assert report.removed == 1
        assert "gone.aa" not in store.file_paths()
        incremental = snapshot(store)

    fresh = config_for(tmp_path, "fresh.db")
    with GraphStore(fresh.db_path) as store:
        full_build(fresh, store)
        assert snapshot(store) == incremental
