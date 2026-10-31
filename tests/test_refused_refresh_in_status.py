"""Task 401: a hook refresh refused for an unusable adapter is named by ``get_index_status``.

On ``main`` the refusal reached only stderr and ``refresh.log``; the status read ``current`` and
the session start said nothing. The hook now records it beside the index, dated, and the next
build that succeeds removes it.
"""

from __future__ import annotations

import os
import re
import shlex
import sys
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.hooks import state
from code_atlas.hooks.refresh import refresh
from code_atlas.index_lock import read_refresh_refused, refresh_refused_path_for
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status
from code_atlas.tools.build_or_update_index import NO_USABLE_ADAPTER
from code_atlas.tools.get_index_status import (
    COVERAGE_LOSS_PENDING,
    REFRESH_REFUSED,
    REFRESH_REFUSED_LEAD,
)
from tests.test_incremental import FAKE, committed

UTC_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _adapter(monkeypatch: pytest.MonkeyPatch, root: Path, mode: str) -> None:
    """Point the hook's own config read at the fake adapter in ``mode``; no host CA_* leaks in."""
    for key in [key for key in os.environ if key.startswith("CA_")]:
        monkeypatch.delenv(key)
    monkeypatch.setenv("CA_WORKERS", "1")
    monkeypatch.setenv("CA_FAKE_CMD", shlex.join([sys.executable, str(FAKE), mode]))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))


@pytest.fixture
def built(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    committed(tmp_path, {"src/Widget.aa": "class Widget {}\n"})
    _adapter(monkeypatch, tmp_path, "ok")
    config = load_config(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    return tmp_path


def _status(root: Path) -> dict[str, object]:
    return get_index_status.create(load_config(root), ())()


def test_a_refused_refresh_is_named_with_its_time(
    built: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1: an adapter that fails its handshake, a hook refresh, then the status names both."""
    committed(built, {"src/Widget.aa": "class Widget { }\n"}, message="edit")
    _adapter(monkeypatch, built, "not-json-handshake")

    assert refresh(built) == 0

    block = _status(built)[REFRESH_REFUSED]
    assert isinstance(block, dict)
    assert block["reason"] == NO_USABLE_ADAPTER
    assert UTC_STAMP.match(str(block["at"])), block
    assert block.get("hint") and "route" not in block, "no tool repairs an adapter (R5.4c)"
    summary = str(_status(built)["summary"])
    assert f"{REFRESH_REFUSED_LEAD} at {block['at']}: {NO_USABLE_ADAPTER}" in summary
    minimal = get_index_status.create(load_config(built), ())(detail_level="minimal")
    assert REFRESH_REFUSED in minimal, "the summary is on every level, so the field is too"


def test_the_session_start_line_puts_it_on_screen(
    built: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The consumer, not the field (R6.9): the state hook speaks and the person sees it (381)."""
    committed(built, {"src/Widget.aa": "class Widget { }\n"}, message="edit")
    _adapter(monkeypatch, built, "not-json-handshake")
    refresh(built)

    line = state.state_line(built)
    assert line is not None and REFRESH_REFUSED_LEAD in line
    assert state.screen_lines(None, line) == [line]


def test_the_next_successful_refresh_clears_it(
    built: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2: the adapter fixed, the next refresh runs and the record and the clause are gone."""
    committed(built, {"src/Widget.aa": "class Widget { }\n"}, message="edit")
    _adapter(monkeypatch, built, "not-json-handshake")
    refresh(built)
    db = load_config(built).db_path
    assert read_refresh_refused(db) is not None

    _adapter(monkeypatch, built, "ok")
    assert refresh(built) == 0

    assert not refresh_refused_path_for(db).exists()
    status = _status(built)
    assert REFRESH_REFUSED not in status
    assert REFRESH_REFUSED_LEAD not in str(status["summary"])
    assert state.state_line(built) is None, "a current index with nothing refused is silent"


def test_a_refused_reason_already_on_the_summary_is_not_said_twice(
    built: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A coverage_loss refusal is named by 355's field; the record stays, the clause does not."""
    db = load_config(built).db_path
    refresh_refused_path_for(db).write_text(
        '{"reason": "coverage_loss", "at": "2026-10-19T00:00:00Z"}', encoding="utf-8"
    )
    monkeypatch.delenv("CA_FAKE_CMD")

    status = _status(built)
    assert COVERAGE_LOSS_PENDING in status and REFRESH_REFUSED in status
    assert REFRESH_REFUSED_LEAD not in str(status["summary"])


def test_an_unreadable_record_is_silence(built: Path) -> None:
    """A torn or foreign file never raises out of a status call."""
    refresh_refused_path_for(load_config(built).db_path).write_text("{not json", encoding="utf-8")

    assert REFRESH_REFUSED not in _status(built)
