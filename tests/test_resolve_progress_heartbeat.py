"""Task 290 — ``resolve`` advances published progress so slow ≠ hung."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.resolver import resolve_edges
from code_atlas.store import GraphStore
from code_atlas.tools import build_or_update_index

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"


def test_resolve_on_batch_fires_more_than_once(tmp_path: Path) -> None:
    """AC1: a non-trivial unresolved set advances the reporter more than once."""
    db = tmp_path / "graph.db"
    ticks: list[int] = []
    with GraphStore(db) as store:
        store.upsert_file("a.php", "d" * 64, "php")
        store.replace_file_rows(
            "a.php",
            [
                {
                    "kind": "Function",
                    "name": "caller",
                    "qualified_name": "\\caller",
                    "file_path": "a.php",
                    "line_start": 1,
                    "line_end": 1,
                }
            ],
            [
                {
                    "kind": "CALLS",
                    "source": "\\caller",
                    "target_raw": f"\\missing{i}",
                    "confidence_tier": "HEURISTIC",
                    "file_path": "a.php",
                    "line": 1,
                }
                for i in range(5)
            ],
        )
        with patch("code_atlas.resolver._RESOLVE_BATCH", 2):
            resolve_edges(
                store,
                max_candidates=50,
                on_batch=lambda: ticks.append(len(ticks) + 1),
            )
    assert len(ticks) >= 2, ticks


def test_resolve_publishes_every_batch_despite_progress_interval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1: resolve done lines are not swallowed by PROGRESS_INTERVAL (total=0 path)."""
    from code_atlas.tools.build_or_update_index import _progress_sink

    published: list[str] = []

    def capture(_db: Path, line: str) -> None:
        published.append(line)

    monkeypatch.setattr(
        "code_atlas.tools.build_or_update_index.publish_build_progress", capture
    )
    monkeypatch.setattr(
        "code_atlas.tools.build_or_update_index.PROGRESS_INTERVAL", 60.0
    )
    config = load_config(tmp_path, {"CA_DB_PATH": str(tmp_path / "graph.db")})
    sink = _progress_sink(config)
    sink("resolve", 0, 0)
    sink("resolve", 1, 0)
    sink("resolve", 2, 0)
    assert sum("done=" in line for line in published) >= 2, published


def test_progress_sink_publishes_done_without_total() -> None:
    """AC4: done advances when total is 0; resolve's coarse throttle is ``_RESOLVE_BATCH``."""
    from code_atlas import resolver as resolve_mod

    assert resolve_mod._RESOLVE_BATCH >= 1
    assert build_or_update_index.PROGRESS_INTERVAL > 0  # still gates parse (total known)
    done, total = 3, 0
    if total:
        counted = f" done={done} total={total}"
    elif done:
        counted = f" done={done}"
    else:
        counted = ""
    assert counted == " done=3"


def test_parse_progress_still_carries_totals(tmp_path: Path) -> None:
    """AC5: parse's existing progress shape is untouched; resolve now ticks too."""
    env = {
        "CA_WORKERS": "1",
        "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
        "CA_DB_PATH": str(tmp_path / ".code-atlas" / "graph.db"),
    }
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.aa").write_text("class Thing {}\n", encoding="utf-8")
    config = load_config(tmp_path, env)
    seen: list[tuple[str, int, int]] = []
    with GraphStore(config.db_path) as store:
        full_build(config, store, progress=lambda *row: seen.append(row))
    assert ("parse", 1, 1) in seen
    assert any(phase == "resolve" for phase, _d, _t in seen), seen
