"""Task 219: a full rebuild bulk-clears the graph before the first file write.

The proving test drives a real ``full_build`` over a real database via the fake adapter (no PHP/node
needed), so the mechanism is exercised at the layer it lives — the write path — not mocked. On a
populated index the first per-file write must see an already-empty graph: the redundant per-path
delete (203's ~1.8x tax) is gone. The byte-identity test pins AC2 across the change.
"""

import shlex
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import Config, load_config
from code_atlas.indexer import build_incomplete, full_build
from code_atlas.store import BUILD_COMPLETE_KEY, BUILD_INCOMPLETE, GraphStore

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"

NODE_COLUMNS = ", ".join(contract.NODE_FIELDS)
EDGE_COLUMNS = ", ".join(contract.EDGE_FIELDS)


def fake_command() -> tuple[str, ...]:
    return (sys.executable, str(FAKE), "ok")


def indexed_config(root: Path) -> Config:
    return load_config(
        root,
        {
            "CA_WORKERS": "1",
            "CA_ADAPTER_TIMEOUT": "30",
            "CA_FAKE_CMD": shlex.join(fake_command()),
        },
    )


def tree(root: Path, *paths: str) -> tuple[str, ...]:
    for index, path in enumerate(paths):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"content {index} of {path}\n", encoding="utf-8")
    return tuple(sorted(paths))


def snapshot(store: GraphStore) -> dict[str, list[tuple[object, ...]]]:
    """Row content under the R4.2 carve-out: no ids, no ``updated_at`` (as ``test_indexer``)."""
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


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / ".code-atlas" / "graph.db") as opened:
        yield opened


def test_a_full_rebuild_clears_the_index_before_the_first_file_write(
    tmp_path: Path, store: GraphStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proving test: on a full rebuild over a POPULATED index the first per-file write sees an
    empty graph. Fails pre-change (the first write still sees the old rows); passes once truncate
    lands."""
    tree(tmp_path, "src/a.aa", "src/b.aa", "src/c.aa")
    config = indexed_config(tmp_path)
    full_build(config, store)
    assert store.counts()["nodes"] > 0

    original = store.replace_file_rows
    seen: list[int] = []

    def spy(path: str, nodes: object, edges: object) -> int:
        if not seen:
            seen.append(store.counts()["nodes"])
        return original(path, nodes, edges)  # type: ignore[arg-type]

    monkeypatch.setattr(store, "replace_file_rows", spy)
    full_build(config, store)

    assert seen == [0], "the first per-file write on a populated rebuild must see a truncated graph"


def test_a_populated_full_rebuild_is_byte_identical_to_a_fresh_build(tmp_path: Path) -> None:
    """AC2: a rebuild over a populated index writes the same graph as a fresh build, row for row."""
    tree(tmp_path, "src/a.aa", "src/b.aa", "src/c.bb")
    config = indexed_config(tmp_path)

    with GraphStore(tmp_path / ".code-atlas" / "fresh.db") as fresh:
        full_build(config, fresh)
        fresh_snapshot = snapshot(fresh)

    with GraphStore(tmp_path / ".code-atlas" / "populated.db") as populated:
        full_build(config, populated)
        full_build(config, populated)
        populated_snapshot = snapshot(populated)

    assert populated_snapshot == fresh_snapshot


def test_a_build_killed_after_truncate_reports_incomplete_not_current(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC3: the incomplete stamp is committed before the truncate and the truncate never touches it,
    so an index a build abandons mid-truncate reports incomplete — 202's escalation, not widened."""
    tree(tmp_path, "src/a.aa", "src/b.aa")
    config = indexed_config(tmp_path)
    full_build(config, store)
    assert not build_incomplete(store)

    # Reproduce the on-disk state a kill mid-truncate leaves: incomplete stamped, then the clear.
    store.set_meta(BUILD_COMPLETE_KEY, BUILD_INCOMPLETE)
    store.truncate_graph()

    assert build_incomplete(store)
    assert store.counts()["nodes"] == 0
