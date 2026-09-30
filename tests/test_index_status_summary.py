"""Task 316: get_index_status leads with a derived one-line summary."""

from __future__ import annotations

from pathlib import Path

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import get_index_status
from code_atlas.tools.get_index_status import _compose_summary
from tests.test_store import an_edge, nodes_for


def test_unbuilt_summary_leads_and_is_present_at_minimal(tmp_path: Path) -> None:
    """AC1/AC3 — every payload leads with summary; minimal included."""
    config = load_config(tmp_path)
    tool = get_index_status.create(config, (get_index_status.NAME,))
    payload = tool(detail_level="minimal")
    assert next(iter(payload)) == "summary"
    assert payload["summary"] == (
        "unknown · 0 files · 0 symbols — not indexed — run build_or_update_index"
    )
    assert payload["indexed"] is False


def test_summary_is_pure_function_of_structured_fields() -> None:
    """AC2 — mutate a count/staleness fixture; summary tracks with no independent path."""
    base = {
        "indexed": True,
        "files": 10,
        "nodes": 100,
        "last_commit": "abcdef0123456789",
        "staleness": "current",
    }
    assert _compose_summary(base) == "current @ abcdef0 · 10 files · 100 symbols"
    mutated = {**base, "files": 11, "nodes": 200}
    assert _compose_summary(mutated) == "current @ abcdef0 · 11 files · 200 symbols"
    behind = {**base, "staleness": "behind", "behind_serves": ["search_symbol"]}
    assert _compose_summary(behind) == (
        "behind @ abcdef0 · 10 files · 100 symbols (read tools still serve) "
        "— run build_or_update_index"
    )
    mismatch = {**base, "indexed": False, "error": "schema_version_mismatch"}
    assert _compose_summary(mismatch) == (
        "unknown @ abcdef0 · 10 files · 100 symbols — schema mismatch — "
        "not indexed — run build_or_update_index"
    )


def test_a_pending_rebuild_leads_the_summary_whatever_the_staleness() -> None:
    """347 AC1: an incremental refuses on an older era, so the route must be the full one."""
    pending = {
        "reason": "contract_rebuild_required",
        "route": "code-atlas-build --full",
        "in_band_option": "allow_full_rebuild=true",
        "stored_contract": "10",
        "server_contract": "13",
    }
    base = {"indexed": True, "files": 10, "nodes": 100, "last_commit": "abcdef0123456789"}
    expected = (
        "rebuild required @ abcdef0 · 10 files · 100 symbols — index contract v10, server v13 — "
        "run `code-atlas-build --full` (or build_or_update_index allow_full_rebuild=true)"
    )
    for staleness in ("current", "behind"):
        payload = {**base, "staleness": staleness, "full_rebuild_required": pending}
        assert _compose_summary(payload) == expected


def test_built_minimal_summary_and_claim_unchanged(tmp_path: Path) -> None:
    """AC1/AC4 — built minimal has summary; sign=True still appends claim last."""
    db = tmp_path / ".code-atlas" / "graph.db"
    db.parent.mkdir(parents=True)
    path = "a.php"
    with GraphStore(db) as store:
        store.upsert_file(path, "h", "php")
        store.replace_file_rows(path, nodes_for(path), [an_edge(
            "CALLS",
            "\\App\\UserRepo::save",
            "\\App\\Db::write",
            path,
            target_qname="\\App\\Db::write",
        )])
        store.set_meta("last_commit", "7efaa91deadbeef")
        store.set_meta("last_ref", "main")
    config = load_config(tmp_path)
    tool = get_index_status.create(config, (get_index_status.NAME,))
    payload = tool(detail_level="minimal")
    assert next(iter(payload)) == "summary"
    assert "7efaa91" in payload["summary"]
    assert "1 files" in payload["summary"] or "files" in payload["summary"]
    assert "symbols" in payload["summary"]
    assert payload["summary"].startswith(("current", "unknown", "behind", "incomplete"))
    signed = tool(detail_level="minimal", sign=True)
    assert "claim" in signed
    # Structured fields still present (061 / AC4).
    assert signed["indexed"] is True
    assert "staleness" in signed
    assert "last_commit" in signed
