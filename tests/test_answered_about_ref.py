"""Task 317: answered_about_ref on every nav envelope from the shared attach site."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.store import LAST_REF_KEY, GraphStore
from code_atlas.tools import (
    file_outline,
    find_callers,
    find_implementations,
    find_references,
    get_index_status,
    read_symbol,
    search_symbol,
)
from code_atlas.tools.nav_result import (
    ANSWERED_ABOUT_REF_FIELD,
    REASON_OK,
    attach_answered_about_ref,
    empty_nav,
    list_result,
)
from tests.test_nav_tools import db_config, edge, node, seed_file
from tests.test_store import nodes_for


def test_shared_attach_site_is_the_only_writer() -> None:
    """AC2 — one attach site; envelope builders call it (R6.7 anti-drift)."""
    root = Path(__file__).resolve().parent.parent
    writers = subprocess.run(
        ["grep", "-rn", "ANSWERED_ABOUT_REF_FIELD]", "code_atlas/"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert len(writers) == 1, writers
    assert writers[0].startswith("code_atlas/tools/nav_result.py:")
    assert "attach_answered_about_ref" in (root / "code_atlas/tools/nav_result.py").read_text()
    src = (root / "code_atlas/tools/nav_result.py").read_text()
    for name in (
        "def empty_nav",
        "def nav_result",
        "def list_result",
        "def batch_result",
        "def batch_not_indexed",
    ):
        assert name in src
    assert src.count("attach_answered_about_ref(") >= 5


def test_nav_tools_carry_answered_about_ref(tmp_path: Path) -> None:
    """AC1 — find_callers / find_references / search_symbol / read_symbol name the index ref."""
    with GraphStore(tmp_path / "graph.db") as store:
        seed_file(
            store,
            "a.x",
            [
                node("Function", "target", "\\App\\target", "a.x"),
                node("Function", "caller", "\\App\\caller", "a.x"),
            ],
            [
                edge(
                    "CALLS",
                    "\\App\\caller",
                    "\\App\\target",
                    "a.x",
                    target_qname="\\App\\target",
                )
            ],
            root=tmp_path,
        )
        store.set_meta(LAST_REF_KEY, "feat/demo")
        store.set_meta("last_commit", "abcdef0123456789")
    config = replace(db_config(tmp_path), root=tmp_path)
    callers = find_callers.create(config)("\\App\\target", detail_level="minimal")
    refs = find_references.create(config)("\\App\\target", detail_level="minimal")
    search = search_symbol.create(config)("target", detail_level="minimal")
    read = read_symbol.create(config)("\\App\\target", detail_level="minimal")
    for payload, name in (
        (callers, "find_callers"),
        (refs, "find_references"),
        (search, "search_symbol"),
        (read, "read_symbol"),
    ):
        assert ANSWERED_ABOUT_REF_FIELD in payload, name
        assert payload[ANSWERED_ABOUT_REF_FIELD] == "feat/demo", (name, payload)


def test_answered_about_ref_agrees_with_status(tmp_path: Path) -> None:
    """AC3 — same index state → same last_ref as get_index_status."""
    db = tmp_path / ".code-atlas" / "graph.db"
    db.parent.mkdir(parents=True)
    with GraphStore(db) as store:
        store.upsert_file("a.php", "h", "php")
        store.replace_file_rows("a.php", nodes_for("a.php"), [])
        store.set_meta(LAST_REF_KEY, "main")
        store.set_meta("last_commit", "deadbeefdeadbeef")
    config = load_config(tmp_path)
    status = get_index_status.create(config, (get_index_status.NAME,))(detail_level="minimal")
    search = search_symbol.create(config)("User", detail_level="minimal")
    assert search[ANSWERED_ABOUT_REF_FIELD] == status.get("last_ref")


def test_helpers_stamp_null_when_unknown() -> None:
    """Unbuilt / unknown → field present and null (061)."""
    payload = empty_nav("x", detail_level="minimal", index_root="/tmp")
    assert payload[ANSWERED_ABOUT_REF_FIELD] is None
    payload = list_result(
        [],
        detail_level="minimal",
        index_root="/tmp",
        truncated=False,
        reason=REASON_OK,
        total_count=0,
    )
    assert payload[ANSWERED_ABOUT_REF_FIELD] is None
    stamped = attach_answered_about_ref({"indexed": True}, "main")
    assert stamped[ANSWERED_ABOUT_REF_FIELD] == "main"


def test_serve_behind_does_not_duplicate_revision_label(tmp_path: Path) -> None:
    """AC4 — answered_about_ref fills the current-answer gap; no second behind-revision field."""
    with GraphStore(tmp_path / "graph.db") as store:
        seed_file(
            store,
            "a.x",
            [node("Function", "target", "\\App\\target", "a.x")],
            [],
            root=tmp_path,
        )
        store.set_meta(LAST_REF_KEY, "main")
        store.set_meta("last_commit", "abcdef0123456789")
    config = replace(db_config(tmp_path), root=tmp_path)
    payload = find_callers.create(config)(
        "\\App\\target", detail_level="minimal", serve_behind=True
    )
    assert ANSWERED_ABOUT_REF_FIELD in payload
    # Behind labelling uses existing serve_behind / claim plumbing — not a twin of this field.
    twin = [k for k in payload if "behind" in k.lower() and "ref" in k.lower()]
    assert twin == [], twin


def test_other_nav_tools_inherit_answered_about_ref(tmp_path: Path) -> None:
    """Scope D1 — other nav tools that use shared envelopes name the index ref too."""
    with GraphStore(tmp_path / "graph.db") as store:
        seed_file(
            store,
            "a.x",
            [
                node("Interface", "IFace", "\\App\\IFace", "a.x"),
                node("Class", "Impl", "\\App\\Impl", "a.x"),
            ],
            [
                edge(
                    "IMPLEMENTS",
                    "\\App\\Impl",
                    "\\App\\IFace",
                    "a.x",
                    target_qname="\\App\\IFace",
                )
            ],
            root=tmp_path,
        )
        store.set_meta(LAST_REF_KEY, "feat/demo")
        store.set_meta("last_commit", "abcdef0123456789")
    config = replace(db_config(tmp_path), root=tmp_path)
    impl = find_implementations.create(config)("\\App\\IFace", detail_level="minimal")
    outline = file_outline.create(config)("a.x", detail_level="minimal")
    assert impl[ANSWERED_ABOUT_REF_FIELD] == "feat/demo"
    assert outline[ANSWERED_ABOUT_REF_FIELD] == "feat/demo"
