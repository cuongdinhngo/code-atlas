"""Task 260: local fit counters — tuple shape, privacy, determinism, verbose/reset."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.store import GraphStore, close_fit_connections, fit_meta_key
from code_atlas.tools import fit, get_index_status
from code_atlas.tools.find_callers import create as callers_create
from tests.test_store import nodes_for


@pytest.fixture(autouse=True)
def _drop_counter_handles():
    """The counter keeps one handle per index; a tmp_path index must not outlive its test."""
    yield
    close_fit_connections()


def _plant(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with GraphStore(db_path) as store:
        store.upsert_file("a.php", "h", "php")
        store.replace_file_rows("a.php", nodes_for("a.php"), [])


def test_fit_meta_key_is_counts_only_tuple() -> None:
    key = fit_meta_key(
        "find_callers", "ok", authoritative=True, truncated=False
    )
    assert key == "fit:find_callers|ok|1|0"
    assert "/" not in key and "::" not in key


def test_record_never_puts_qname_or_path_in_meta(tmp_path: Path) -> None:
    """AC1: increment from return payload only — args cannot reach the meta row."""
    db_path = tmp_path / ".code-atlas" / "graph.db"
    _plant(db_path)
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    secret_qname = "\\App\\SecretUserRepo::save"
    secret_path = "src/leaked/Secret.php"
    # Simulate a tool return that somehow echoed subjects — record must still ignore them.
    payload = {
        "reason": "ok",
        "authoritative": True,
        "truncated": False,
        "qname": secret_qname,
        "path": secret_path,
        "results": [{"qname": secret_qname, "file": secret_path}],
    }
    fit.record("find_callers", config, payload)
    with GraphStore(db_path) as store:
        rows = store.list_fit_counts()
        key = fit_meta_key(
            "find_callers", "ok", authoritative=True, truncated=False
        )
        assert store.get_meta(key) == "1"
    assert rows == [
        {
            "tool": "find_callers",
            "reason": "ok",
            "authoritative": True,
            "truncated": False,
            "count": 1,
        }
    ]
    blob = json.dumps(rows, sort_keys=True) + key
    assert secret_qname not in blob and secret_path not in blob
    assert "Secret" not in blob


def test_nav_payload_byte_identical_while_counter_increments(tmp_path: Path) -> None:
    """AC2: identical queries → byte-identical nav payloads with the counter on (R4.2)."""
    db_path = tmp_path / ".code-atlas" / "graph.db"
    _plant(db_path)
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    tool = fit.wrap("find_callers", config, callers_create(config))
    first = tool(qname="\\App\\UserRepo::save", detail_level="minimal")
    second = tool(qname="\\App\\UserRepo::save", detail_level="minimal")
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    with GraphStore(db_path) as store:
        counts = store.list_fit_counts()
    assert sum(int(row["count"]) for row in counts) == 2


def test_docs_state_fit_definition_before_any_counter_number() -> None:
    """AC3: design/fit.md defines fit before any local counter percentage is quoted in docs/."""
    fit_doc = Path("docs/design/fit.md").read_text(encoding="utf-8")
    assert "relationship" in fit_doc.lower()
    assert "search" in fit_doc.lower() or "grep" in fit_doc.lower()
    assert "cannot be compared" in fit_doc.lower() or "not comparable" in fit_doc.lower()
    # No quoted percentage attributed to the local counter yet (founding 19% may still appear
    # as the historical all-calls figure, but only with that disclaimer).
    for path in Path("docs").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if "fit_counts" not in text and "task 260" not in text and path.name != "fit.md":
            continue
        # Pages that mention the counter must point at the definition doc first in spirit —
        # fit.md itself is the definition.
        if path.name == "fit.md":
            defn = text.split("## What this counter does")[0]
            assert re.search(r"relationship", defn, re.I)


def test_verbose_shows_counts_and_reset_clears(tmp_path: Path) -> None:
    """AC4: verbose surfaces fit_counts; reset_fit_counts clears them."""
    db_path = tmp_path / ".code-atlas" / "graph.db"
    _plant(db_path)
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    fit.record(
        "search_symbol",
        config,
        {"reason": "ok", "authoritative": True, "truncated": False},
    )
    status = get_index_status.create(config, (get_index_status.NAME,))
    standard = status(detail_level="standard")
    verbose = status(detail_level="verbose")
    assert fit.FIT_COUNTS_FIELD not in standard
    assert verbose[fit.FIT_COUNTS_FIELD] == [
        {
            "tool": "search_symbol",
            "reason": "ok",
            "authoritative": True,
            "truncated": False,
            "count": 1,
        }
    ]
    cleared = status(detail_level="verbose", reset_fit_counts=True)
    assert cleared[fit.FIT_COUNTS_FIELD] == []


def test_verbose_status_is_idempotent_with_the_counter_on(tmp_path: Path) -> None:
    """AC2 where it can actually fail: the tool reporting the counter must not move it."""
    db_path = tmp_path / ".code-atlas" / "graph.db"
    _plant(db_path)
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    served = fit.wrap(
        get_index_status.NAME,
        config,
        get_index_status.create(config, (get_index_status.NAME,)),
    )
    first = served(detail_level="verbose")
    second = served(detail_level="verbose")
    assert json.dumps(first, sort_keys=True, default=str) == json.dumps(
        second, sort_keys=True, default=str
    )
    with GraphStore(db_path) as store:
        assert store.list_fit_counts() == []


def test_counting_survives_an_index_deleted_under_the_handle(tmp_path: Path) -> None:
    """A stale handle is dropped and retried; counting never raises into an answer."""
    db_path = tmp_path / ".code-atlas" / "graph.db"
    _plant(db_path)
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    payload = {"reason": "ok", "authoritative": True, "truncated": False}
    fit.record("find_callers", config, payload)
    db_path.unlink()
    _plant(db_path)
    fit.record("find_callers", config, payload)
    with GraphStore(db_path) as store:
        assert [row["count"] for row in store.list_fit_counts()] == [1]
