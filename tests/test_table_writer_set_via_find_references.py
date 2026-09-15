"""Task 278 — find_references on Table/Column returns the WRITES writer set."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from code_atlas.store import COVERED_LANGUAGES_KEY, EMITTED_KINDS_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import find_references
from code_atlas.tools.nav_result import (
    CAVEAT_WRITES_EMITTERS_ONLY,
    REASON_OK,
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
    REASON_RELATIONSHIP_NOT_MODELLED,
)
from tests.test_nav_tools import db_config, edge, node
from tests.test_nav_tools import store as store  # noqa: F401

TABLE = "dbo.UserNotes"
COLUMN = "dbo.UserNotes::Note"
WRITER = "dbo.usp_UpdateUserNotes"
OTHER_WRITER = "dbo.usp_InsertUserNotes"


def _seed(
    graph: GraphStore,
    root: Path,
    path: str,
    nodes: list,
    edges: list,
    *,
    language: str,
) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    body = b"# planted\n"
    target.write_bytes(body)
    graph.upsert_file(path, hashlib.sha256(body).hexdigest(), language)
    graph.replace_file_rows(path, nodes, edges)


def _stamp_langs(
    graph: GraphStore,
    *languages: str,
    writers: frozenset[str] | None = None,
) -> None:
    graph.set_meta(COVERED_LANGUAGES_KEY, ",".join(languages))
    emit = writers if writers is not None else frozenset({"sql"})
    kinds = {name: (["WRITES"] if name in emit else []) for name in languages}
    graph.set_meta(EMITTED_KINDS_BY_LANGUAGE_KEY, json.dumps(kinds, sort_keys=True))


def test_table_returns_writer_routines(tmp_path: Path, store: GraphStore) -> None:
    """AC1 — Table subject lists linked WRITES sources with tier (table ∪ columns)."""
    _seed(
        store,
        tmp_path,
        "schema.sql",
        [
            node("Table", "UserNotes", TABLE, "schema.sql"),
            node("Column", "Note", COLUMN, "schema.sql"),
            node("Function", "usp_UpdateUserNotes", WRITER, "schema.sql"),
            node("Function", "usp_InsertUserNotes", OTHER_WRITER, "schema.sql"),
        ],
        [
            edge("CONTAINS", TABLE, COLUMN, "schema.sql", target_qname=COLUMN),
            edge("WRITES", WRITER, TABLE, "schema.sql", target_qname=TABLE, tier="RESOLVED"),
            edge(
                "WRITES",
                OTHER_WRITER,
                COLUMN,
                "schema.sql",
                target_qname=COLUMN,
                tier="HEURISTIC",
            ),
        ],
        language="sql",
    )
    _stamp_langs(store, "sql")
    payload = find_references.create(db_config(tmp_path))(TABLE)
    assert payload["reason"] == REASON_OK
    assert payload["total_count"] == 2
    by_qname = {hit["qname"]: hit for hit in payload["results"]}  # type: ignore[misc]
    assert by_qname[WRITER]["confidence_tier"] == "RESOLVED"
    assert by_qname[OTHER_WRITER]["confidence_tier"] == "HEURISTIC"
    assert payload["production_count"] == 2
    assert payload.get("test_count", 0) == 0
    col = find_references.create(db_config(tmp_path))(COLUMN)
    assert col["total_count"] == 1
    assert col["results"][0]["qname"] == OTHER_WRITER  # type: ignore[index]


def test_multi_lang_index_marks_sql_half(tmp_path: Path, store: GraphStore) -> None:
    """AC2 — other languages emit no WRITES ⇒ caveat names the SQL half."""
    _seed(
        store,
        tmp_path,
        "schema.sql",
        [
            node("Table", "UserNotes", TABLE, "schema.sql"),
            node("Function", "usp_UpdateUserNotes", WRITER, "schema.sql"),
        ],
        [
            edge("WRITES", WRITER, TABLE, "schema.sql", target_qname=TABLE, tier="RESOLVED"),
        ],
        language="sql",
    )
    _seed(
        store,
        tmp_path,
        "app.php",
        [node("Function", "save", "App\\save", "app.php")],
        [],
        language="php",
    )
    _stamp_langs(store, "sql", "php")
    payload = find_references.create(db_config(tmp_path))(TABLE)
    assert payload["reason"] == REASON_OK
    assert payload["authoritative"] is False
    assert CAVEAT_WRITES_EMITTERS_ONLY in payload["authoritative_caveats"]


def test_unstamped_index_keeps_the_caveat(tmp_path: Path, store: GraphStore) -> None:
    """281 — no EMITTED_KINDS stamp is not evidence every covered language writes (R5.6)."""
    _seed(
        store,
        tmp_path,
        "schema.sql",
        [
            node("Table", "UserNotes", TABLE, "schema.sql"),
            node("Function", "usp_UpdateUserNotes", WRITER, "schema.sql"),
        ],
        [
            edge("WRITES", WRITER, TABLE, "schema.sql", target_qname=TABLE, tier="RESOLVED"),
        ],
        language="sql",
    )
    _seed(
        store,
        tmp_path,
        "app.php",
        [node("Function", "save", "App\\save", "app.php")],
        [],
        language="php",
    )
    store.set_meta(COVERED_LANGUAGES_KEY, "sql,php")
    payload = find_references.create(db_config(tmp_path))(TABLE)
    assert payload["reason"] == REASON_OK
    assert CAVEAT_WRITES_EMITTERS_ONLY in payload["authoritative_caveats"]


def test_all_covered_writers_emit_no_partial_caveat(
    tmp_path: Path, store: GraphStore
) -> None:
    """281 — second WRITES-emitting language already in the answer ⇒ no caveat."""
    other = "dbo.usp_FromHost"
    _seed(
        store,
        tmp_path,
        "schema.sql",
        [
            node("Table", "UserNotes", TABLE, "schema.sql"),
            node("Function", "usp_UpdateUserNotes", WRITER, "schema.sql"),
        ],
        [
            edge("WRITES", WRITER, TABLE, "schema.sql", target_qname=TABLE, tier="RESOLVED"),
        ],
        language="sql",
    )
    _seed(
        store,
        tmp_path,
        "writer.php",
        [node("Function", "save", other, "writer.php")],
        [
            edge("WRITES", other, TABLE, "writer.php", target_qname=TABLE, tier="HEURISTIC"),
        ],
        language="php",
    )
    _stamp_langs(store, "sql", "php", writers=frozenset({"sql", "php"}))
    payload = find_references.create(db_config(tmp_path))(TABLE)
    assert payload["reason"] == REASON_OK
    assert payload["total_count"] == 2
    assert CAVEAT_WRITES_EMITTERS_ONLY not in (payload.get("authoritative_caveats") or [])


def test_unlinked_writes_count_on_answer(tmp_path: Path, store: GraphStore) -> None:
    """AC3 — unlinked writers naming the table are a count on the answer."""
    _seed(
        store,
        tmp_path,
        "schema.sql",
        [
            node("Table", "UserNotes", TABLE, "schema.sql"),
            node("Function", "usp_UpdateUserNotes", WRITER, "schema.sql"),
        ],
        [
            edge("WRITES", WRITER, TABLE, "schema.sql", target_qname=TABLE, tier="RESOLVED"),
            edge("WRITES", "writer.site", TABLE, "schema.sql", target_qname="", tier="DYNAMIC"),
        ],
        language="sql",
    )
    _stamp_langs(store, "sql")
    payload = find_references.create(db_config(tmp_path))(TABLE)
    assert payload["unlinked_writes_count"] == 1
    assert payload["total_count"] == 1


def test_empty_table_with_unlinked_still_not_bare_no_matches(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2 empty arm — unlinked WRITES still upgrade bare no_matches (255 keeps)."""
    _seed(
        store,
        tmp_path,
        "schema.sql",
        [node("Table", "UserNotes", TABLE, "schema.sql")],
        [
            edge("WRITES", "writer.site", TABLE, "schema.sql", target_qname="", tier="DYNAMIC"),
        ],
        language="sql",
    )
    _stamp_langs(store, "sql")
    payload = find_references.create(db_config(tmp_path))(TABLE)
    assert payload["reason"] in (
        REASON_RELATIONSHIP_NOT_MODELLED,
        REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
    )
    assert payload["reason"] != "no_matches"
    assert payload.get("unlinked_writes_count", 0) >= 1 or "WRITES" in (
        payload.get("unlinked_edge_kinds") or []
    )
