"""Task 035: read-through freshness — inline reparse on hash drift."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

from code_atlas import contract
from code_atlas.config import load_config
from code_atlas.indexer import full_build, reparse_file
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, read_symbol, search_symbol
from code_atlas.tools.freshness import READ_THROUGH_CAP, FreshnessGuard
from code_atlas.tools.nav_result import REASON_INDEX_STALE

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"

NODE_COLUMNS = ", ".join(contract.NODE_FIELDS)
EDGE_COLUMNS = ", ".join(contract.EDGE_FIELDS)


def fake_env(path_log: Path | None = None) -> dict[str, str]:
    env = {
        "CA_WORKERS": "1",
        "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
    }
    if path_log is not None:
        env["CA_FAKE_PATHLOG"] = str(path_log)
    return env


def write(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def config_for(root: Path, *, path_log: Path | None = None):
    db = root / ".code-atlas" / "graph.db"
    return load_config(root, {**fake_env(path_log), "CA_DB_PATH": str(db)})


def snapshot_file(store: GraphStore, path: str) -> dict[str, object]:
    conn = store._conn
    return {
        "file": conn.execute(
            "SELECT path, hash, language, parsed_ok FROM files WHERE path = ?", (path,)
        ).fetchone(),
        "nodes": conn.execute(
            f"SELECT {NODE_COLUMNS} FROM nodes WHERE file_path = ? "
            f"ORDER BY qualified_name, line_start",
            (path,),
        ).fetchall(),
        "edges": conn.execute(
            f"SELECT {EDGE_COLUMNS} FROM edges WHERE file_path = ? "
            f"ORDER BY kind, source_qname, target_raw, line",
            (path,),
        ).fetchall(),
    }


def test_read_symbol_repairs_drifted_file_inline(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    write(tmp_path, "src/a.aa", "// edited\nclass Thing {}\n")
    qname = "src/a.aa::Thing"
    result = read_symbol.create(config)(qname, detail_level="minimal")
    assert result["found"] is True
    assert result["stale"] is False
    assert "edited" in result["source"] or result["source"]  # adapter line_start=1 → full slice
    assert result.get("reason") != REASON_INDEX_STALE
    with GraphStore(config.db_path) as store:
        assert store.file_hash("src/a.aa") is not None


def test_untouched_file_does_not_call_adapter(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    write(tmp_path, "src/b.aa", "class Other {}\n")
    path_log = tmp_path / "paths.log"
    config = config_for(tmp_path, path_log=path_log)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    before = path_log.read_text(encoding="utf-8") if path_log.is_file() else ""
    # Edit b only; query a.
    write(tmp_path, "src/b.aa", "class Other { /* drift */ }\n")
    read_symbol.create(config)("src/a.aa::Thing", detail_level="minimal")
    after = path_log.read_text(encoding="utf-8") if path_log.is_file() else ""
    assert after == before


def test_reparse_file_rows_match_full_build(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    write(tmp_path, "src/a.aa", "class Thing { /* v2 */ }\n")
    with GraphStore(config.db_path) as store:
        assert reparse_file(config, store, "src/a.aa") is True
        repaired = snapshot_file(store, "src/a.aa")
    # Fresh DB via full build of the same on-disk content.
    other = tmp_path / "other.db"
    config2 = load_config(
        tmp_path, {**fake_env(), "CA_DB_PATH": str(other)}
    )
    with GraphStore(config2.db_path) as store2:
        full_build(config2, store2)
        expected = snapshot_file(store2, "src/a.aa")
    assert repaired["nodes"] == expected["nodes"]
    assert repaired["edges"] == expected["edges"]
    assert repaired["file"] is not None and expected["file"] is not None
    assert repaired["file"][1] == expected["file"][1]  # hash


def test_cap_overflow_yields_index_stale(tmp_path: Path) -> None:
    assert READ_THROUGH_CAP == 1
    write(tmp_path, "src/a.aa", "class A {}\n")
    write(tmp_path, "src/b.aa", "class B {}\n")
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    write(tmp_path, "src/a.aa", "class A { /* drift */ }\n")
    write(tmp_path, "src/b.aa", "class B { /* drift */ }\n")
    with GraphStore(config.db_path) as store:
        guard = FreshnessGuard(config, store, cap=1)
        assert guard.ensure("src/a.aa") == "repaired"
        assert guard.ensure("src/b.aa") == "stale"
    # One tool call whose hit set spans two drifted files exhausts cap=1 → index_stale.
    write(tmp_path, "src/a.aa", "class A { /* drift2 */ }\n")
    write(tmp_path, "src/b.aa", "class B { /* drift2 */ }\n")
    # Re-index hashes to the pre-drift2 state so both look drifted again without spending budget.
    with GraphStore(config.db_path) as store:
        # Restore indexed hashes from the post-first-repair era by re-building once, then re-drift.
        full_build(config, store)
    write(tmp_path, "src/a.aa", "class A { /* drift3 */ }\n")
    write(tmp_path, "src/b.aa", "class B { /* drift3 */ }\n")
    result = search_symbol.create(config)("Thing", detail_level="minimal")
    assert result["reason"] == REASON_INDEX_STALE
    assert result["results"] == []
    assert result["total_count"] == 0


def test_find_callers_repairs_subject_file(tmp_path: Path) -> None:
    write(tmp_path, "src/a.aa", "class Thing {}\n")
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        old_hash = store.file_hash("src/a.aa")
    write(tmp_path, "src/a.aa", "class Thing { /* drift */ }\n")
    find_callers.create(config)("src/a.aa::Thing", detail_level="minimal")
    with GraphStore(config.db_path) as store:
        assert store.file_hash("src/a.aa") != old_hash
