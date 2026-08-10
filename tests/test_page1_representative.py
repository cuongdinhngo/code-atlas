"""Task 067: a skewed first page must advertise the subtrees it hides (``result_subtrees``).

Proving path is integration: seed the store, then call the real nav tools — the layer where a
one-page reader would otherwise conclude "no ``src`` callers" from a page that is all ``legacy``.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from code_atlas.config import Config, load_config
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references

TARGET = "\\getActiveStatus"
# getActiveStatus-shaped: 15 legacy/ callers + 8 src/ callers of one target (ticket Evidence).
LEGACY = [f"legacy/alpha/mod{i:02d}.php" for i in range(9)] + [
    f"legacy/beta/mod{i:02d}.php" for i in range(6)
]
SRC = [f"src/App/Service/S{i:02d}.php" for i in range(8)]
EXPECTED_SPREAD = {"legacy": 15, "src": 8}


def _edge(path: str, line: int) -> dict[str, object]:
    # File-scope call site: source_qname IS the file path, as in the ticket evidence.
    return {
        "kind": "CALLS",
        "source_qname": path,
        "target_qname": TARGET,
        "target_raw": "getActiveStatus",
        "file_path": path,
        "line": line,
    }


def _seed(db_path: Path, paths: list[str]) -> None:
    with GraphStore(db_path) as store:
        for path in paths:
            store.upsert_file(path, "hash", "php")
        store.insert_edges([_edge(path, 100 + i) for i, path in enumerate(paths)])


def _config(tmp_path: Path) -> Config:
    return replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")


def test_truncated_multi_subtree_callers_advertise_subtrees(tmp_path: Path) -> None:
    """Proving test: page 1 is all ``legacy`` yet the payload reveals ``src`` exists too."""
    _seed(tmp_path / "graph.db", LEGACY + SRC)
    result = find_callers.create(_config(tmp_path))(TARGET, limit=10, detail_level="minimal")

    assert result["truncated"] is True
    assert result["total_count"] == 23
    # Page 1 under the storage order is 100% one subtree — the regression the signal repairs.
    assert {str(hit["file"]).split("/", 1)[0] for hit in result["results"]} == {"legacy"}
    assert result["result_subtrees"] == EXPECTED_SPREAD


def test_find_references_advertises_subtrees(tmp_path: Path) -> None:
    """find_references carries the same signal on a truncated multi-subtree page."""
    _seed(tmp_path / "graph.db", LEGACY + SRC)
    result = find_references.create(_config(tmp_path))(TARGET, limit=10, detail_level="minimal")

    assert result["truncated"] is True
    assert result["result_subtrees"] == EXPECTED_SPREAD


def test_no_signal_when_page_shows_everything(tmp_path: Path) -> None:
    """Not truncated → the reader sees the whole spread; the field is omitted (token-frugal)."""
    _seed(tmp_path / "graph.db", LEGACY + SRC)
    result = find_callers.create(_config(tmp_path))(TARGET, limit=50, detail_level="minimal")

    assert result["truncated"] is False
    assert "result_subtrees" not in result


def test_no_signal_for_single_subtree(tmp_path: Path) -> None:
    """One subtree → nothing is hidden by subtree; the field is omitted even when truncated."""
    _seed(tmp_path / "graph.db", LEGACY)
    result = find_callers.create(_config(tmp_path))(TARGET, limit=5, detail_level="minimal")

    assert result["truncated"] is True
    assert "result_subtrees" not in result


def test_no_signal_at_depth_above_one(tmp_path: Path) -> None:
    """Deeper walks report a floor total_count, so the exact spread is depth-1 only."""
    _seed(tmp_path / "graph.db", LEGACY + SRC)
    result = find_callers.create(_config(tmp_path))(
        TARGET, depth=2, limit=10, detail_level="minimal"
    )

    assert "result_subtrees" not in result


def test_signal_is_deterministic_across_runs_and_rebuild(tmp_path: Path) -> None:
    """AC5: identical spread + row order across repeated runs and a rebuild of the same tree."""
    _seed(tmp_path / "graph.db", LEGACY + SRC)
    call = find_callers.create(_config(tmp_path))
    first = call(TARGET, limit=10, detail_level="minimal")
    second = call(TARGET, limit=10, detail_level="minimal")
    assert first == second

    # Rebuild in a fresh tree, inserting in a different order — output must not change.
    rebuilt = tmp_path / "rebuilt"
    rebuilt.mkdir()
    _seed(rebuilt / "graph.db", SRC + LEGACY)
    third = find_callers.create(replace(_config(tmp_path), db_path=rebuilt / "graph.db"))(
        TARGET, limit=10, detail_level="minimal"
    )
    assert third["result_subtrees"] == first["result_subtrees"]
    assert [hit["file"] for hit in third["results"]] == [hit["file"] for hit in first["results"]]


def test_paging_still_returns_every_row_exactly_once(tmp_path: Path) -> None:
    """C3 / 057: additive signal — paging still partitions the full set (no dup, none lost)."""
    _seed(tmp_path / "graph.db", LEGACY + SRC)
    call = find_callers.create(_config(tmp_path))
    total = call(TARGET, limit=1, detail_level="minimal")["total_count"]

    seen: list[object] = []
    for offset in range(0, total, 10):
        page = call(TARGET, limit=10, offset=offset, detail_level="minimal")
        seen.extend(f"{hit['file']}:{hit['line']}" for hit in page["results"])
    assert len(seen) == total == 23
    assert len(set(seen)) == total
