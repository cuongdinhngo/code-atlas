"""GraphStore against a real SQLite file: schema, per-file idempotency, FTS, and determinism.

No mocks — every acceptance criterion of task 004 can only fail at the integration layer, so each
test drives an actual database. Row ids are excluded from the determinism assertions on purpose:
they follow insert order, which follows worker completion order (PLAN §8.1).
"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.store import (
    META_KEYS,
    SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    GraphStore,
    SchemaVersionError,
    fts_term,
    stored,
)

FIXED_CLOCK = "2026-07-29T00:00:00+00:00"

TABLES = ("files", "nodes", "edges", "nodes_fts", "meta")
INDEXES = (
    "idx_nodes_name",
    "idx_nodes_kind",
    "idx_nodes_file",
    "idx_edges_src",
    "idx_edges_tgt",
)
TRIGGERS = ("nodes_ai", "nodes_ad", "nodes_au")
SCHEMA_OBJECTS = TABLES + INDEXES + TRIGGERS

FILE_COLUMNS = ("path", "hash", "language", "parsed_ok", "updated_at")
META_COLUMNS = ("key", "value")


def a_node(kind: str, name: str, qname: str, path: str, **rest: object) -> dict[str, object]:
    """One contract-shaped node; only the required fields are mandatory (contract.py)."""
    row: dict[str, object] = {
        "kind": kind,
        "name": name,
        "qualified_name": qname,
        "file_path": path,
        "line_start": 1,
    }
    row.update(rest)
    return row


def an_edge(
    kind: str, source: str, target_raw: str, path: str, **rest: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "kind": kind,
        "source_qname": source,
        "target_raw": target_raw,
        "file_path": path,
        "line": 7,
    }
    row.update(rest)
    return row


def nodes_for(path: str) -> list[dict[str, object]]:
    """A class and one of its methods, both owned by ``path``."""
    return [
        a_node("Class", "UserRepo", "\\App\\UserRepo", path),
        a_node(
            "Method", "save", "\\App\\UserRepo::save", path, line_end=12, modifiers=["public"]
        ),
    ]


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / ".code-atlas" / "graph.db"


@pytest.fixture
def store(db_path: Path) -> Iterator[GraphStore]:
    with GraphStore(db_path, now=lambda: FIXED_CLOCK) as opened:
        yield opened


def seeded(store: GraphStore, path: str = "a.php") -> GraphStore:
    """One file with two nodes and one edge — the smallest graph the read helpers need."""
    store.upsert_file(path, "hash-1", "php")
    store.replace_file_rows(
        path,
        nodes_for(path),
        [an_edge("CALLS", "\\App\\UserRepo::save", "\\App\\Db::write", path)],
    )
    return store


def columns(db_path: Path, table: str) -> tuple[str, ...]:
    with sqlite3.connect(db_path) as conn:
        return tuple(row[1] for row in conn.execute(f"PRAGMA table_info({table})"))


def content(db_path: Path) -> tuple[list[tuple[object, ...]], ...]:
    """Every stored row except the two id columns, in a stable order (the R4.2 carve-out).

    Each ORDER BY spans **every** selected column: a partial ordering falls back to rowid, which is
    insert order, which is exactly what these assertions must not depend on.
    """
    with sqlite3.connect(db_path) as conn:
        return tuple(
            conn.execute(
                f"SELECT {', '.join(fields)} FROM {table} ORDER BY {', '.join(fields)}"
            ).fetchall()
            for table, fields in (
                ("nodes", contract.NODE_FIELDS),
                ("edges", contract.EDGE_FIELDS),
                ("files", FILE_COLUMNS),
            )
        )


# --- AC1a: the schema is the one PLAN §10 specifies -----------------------------------------------


def test_plan_10_specifies_fourteen_schema_objects() -> None:
    # Guards the denominator: a shrunken list would pass every per-object check while covering less.
    assert len(SCHEMA_OBJECTS) + 1 == 14


@pytest.mark.parametrize("name", SCHEMA_OBJECTS)
def test_schema_object_is_created(store: GraphStore, db_path: Path, name: str) -> None:
    with sqlite3.connect(db_path) as conn:
        found = conn.execute("SELECT name FROM sqlite_master WHERE name = ?", (name,)).fetchone()
    assert found == (name,)


def test_the_journal_mode_is_wal_on_a_real_file(store: GraphStore, db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone() == ("wal",)


def test_foreign_keys_are_enforced(store: GraphStore) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        store.replace_file_rows("ghost.php", [a_node("Class", "G", "\\G", "ghost.php")], [])


def test_node_columns_are_the_contract_node_fields(store: GraphStore, db_path: Path) -> None:
    assert columns(db_path, "nodes") == ("id", *contract.NODE_FIELDS)


def test_edge_columns_are_the_contract_edge_fields(store: GraphStore, db_path: Path) -> None:
    assert columns(db_path, "edges") == ("id", *contract.EDGE_FIELDS)


@pytest.mark.parametrize(
    ("table", "expected"), [("files", FILE_COLUMNS), ("meta", META_COLUMNS)]
)
def test_supporting_table_columns_are_as_specified(
    store: GraphStore, db_path: Path, table: str, expected: tuple[str, ...]
) -> None:
    assert columns(db_path, table) == expected


def test_reopening_an_existing_database_is_idempotent(db_path: Path) -> None:
    seeded(GraphStore(db_path, now=lambda: FIXED_CLOCK)).close()
    with GraphStore(db_path, now=lambda: FIXED_CLOCK) as reopened:
        assert len(reopened.nodes_by_file("a.php", limit=10)) == 2


# --- AC1b: per-file replacement is idempotent -----------------------------------------------------


def test_re_indexing_identical_content_changes_nothing(store: GraphStore, db_path: Path) -> None:
    seeded(store)
    before = content(db_path)
    seeded(store)
    assert content(db_path) == before


def test_re_indexing_drops_a_symbol_that_disappeared(store: GraphStore) -> None:
    seeded(store)
    store.replace_file_rows("a.php", nodes_for("a.php")[:1], [])
    assert [row["qualified_name"] for row in store.nodes_by_file("a.php", limit=10)] == [
        "\\App\\UserRepo"
    ]
    assert store.edges_by_source("\\App\\UserRepo::save", limit=10) == []


def test_ids_follow_insert_order_while_content_does_not(tmp_path: Path) -> None:
    """Why the determinism assertions exclude ids: the same graph built in either file order.

    Content is byte-identical, ids are not — and PLAN §8.1 fans files across N workers, so the
    order is not ours to fix.
    """
    databases, ids = [], []
    for name, order in (("one", ("a.php", "b.php")), ("two", ("b.php", "a.php"))):
        path = tmp_path / name / "graph.db"
        with GraphStore(path, now=lambda: FIXED_CLOCK) as built:
            for file_path in order:
                seeded(built, file_path)
            ids.append([row["id"] for row in built.nodes_by_file("a.php", limit=10)])
        databases.append(path)

    assert content(databases[0]) == content(databases[1])
    assert ids[0] != ids[1]


def test_two_files_may_declare_the_same_qualified_name(store: GraphStore) -> None:
    for path in ("a.php", "b.php"):
        store.upsert_file(path, "h", "php")
        store.replace_file_rows(path, [a_node("Namespace", "App", "\\App", path)], [])
    assert len(store.nodes_by_name("App", limit=10)) == 2


def test_remove_file_drops_its_rows_and_its_file_row(store: GraphStore, db_path: Path) -> None:
    seeded(store)
    store.remove_file("a.php")
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT count(*) FROM files").fetchone() == (0,)
    assert store.nodes_by_file("a.php", limit=10) == []


def test_a_failed_parse_keeps_a_file_row_with_no_graph_rows(
    store: GraphStore, db_path: Path
) -> None:
    store.upsert_file("bad.php", "h", "php", parsed_ok=False)
    store.replace_file_rows("bad.php", [], [])
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT parsed_ok FROM files WHERE path = 'bad.php'").fetchone() == (0,)
    assert store.nodes_by_file("bad.php", limit=10) == []


# --- AC2a: FTS returns the expected rows ----------------------------------------------------------


def test_the_search_index_follows_a_per_file_replace(store: GraphStore, db_path: Path) -> None:
    """The proving test: the FTS index gains, loses, and regains a symbol with its file's rows."""
    seeded(store)
    assert [row["qualified_name"] for row in store.search_nodes("UserRepo", limit=10)] == [
        "\\App\\UserRepo",
        "\\App\\UserRepo::save",
    ]

    store.replace_file_rows("a.php", nodes_for("a.php")[:1], [])
    assert [row["qualified_name"] for row in store.search_nodes("save", limit=10)] == []

    seeded(store)
    assert [row["qualified_name"] for row in store.search_nodes("save", limit=10)] == [
        "\\App\\UserRepo::save"
    ]
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES ('integrity-check')")


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("UserRepo", 2),
        ("save", 1),
        ("App", 2),
        ("UserRep", 2),
        ("a.php", 2),
        ("Nonexistent", 0),
    ],
)
def test_search_finds_the_expected_row_count(
    store: GraphStore, query: str, expected: int
) -> None:
    seeded(store)
    assert len(store.search_nodes(query, limit=10)) == expected


@pytest.mark.parametrize("query", ["user.ts", 'he"llo', "", "   ", "*", "-x", "NOT App", "a:b"])
def test_a_punctuated_query_never_raises(store: GraphStore, query: str) -> None:
    seeded(store)
    assert isinstance(store.search_nodes(query, limit=10), list)


def test_a_search_operator_is_treated_as_a_literal(store: GraphStore) -> None:
    seeded(store)
    assert store.search_nodes("NOT App", limit=10) == []


def test_search_narrows_by_kind(store: GraphStore) -> None:
    seeded(store)
    found = store.search_nodes("UserRepo", kind="Method", limit=10)
    assert [row["qualified_name"] for row in found] == ["\\App\\UserRepo::save"]


def test_search_honours_its_limit(store: GraphStore) -> None:
    seeded(store)
    assert len(store.search_nodes("UserRepo", limit=1)) == 1


def test_rebuilding_the_search_index_keeps_the_same_hits(store: GraphStore) -> None:
    seeded(store)
    before = store.search_nodes("UserRepo", limit=10)
    store.rebuild_search_index()
    assert store.search_nodes("UserRepo", limit=10) == before


def test_the_tokenizer_splits_underscores_but_not_camel_case(store: GraphStore) -> None:
    # Documents unicode61's actual behaviour; camelCase splitting is deferred to task 014.
    store.upsert_file("c.php", "h", "php")
    store.replace_file_rows(
        "c.php",
        [
            a_node("Function", "find_by_email", "\\App\\find_by_email", "c.php"),
            a_node("Function", "findByEmail", "\\App\\findByEmail", "c.php"),
        ],
        [],
    )
    assert [row["name"] for row in store.search_nodes("email", limit=10)] == ["find_by_email"]


@pytest.mark.parametrize(
    ("query", "expected"), [("plain", '"plain"*'), ('a"b', '"a""b"*'), ("", '""*')]
)
def test_a_query_becomes_one_quoted_prefix_term(query: str, expected: str) -> None:
    assert fts_term(query) == expected


# --- AC2b: identical input, identical rows --------------------------------------------------------


def test_identical_input_produces_identical_rows(tmp_path: Path) -> None:
    paths = []
    for name in ("one", "two"):
        path = tmp_path / name / "graph.db"
        with GraphStore(path, now=lambda: FIXED_CLOCK) as built:
            seeded(built)
        paths.append(path)
    assert content(paths[0]) == content(paths[1])


def test_a_structured_value_is_stored_as_canonical_json(store: GraphStore) -> None:
    store.upsert_file("d.php", "h", "php")
    unordered = a_node("Class", "C", "\\C", "d.php", extra={"b": 1, "a": 2})
    store.replace_file_rows("d.php", [unordered], [])
    assert store.nodes_by_file("d.php", limit=10)[0]["extra"] == '{"a":2,"b":1}'


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("text", "text"),
        (3, 3),
        (["public", "static"], '["public","static"]'),
        ({"b": 1, "a": 2}, '{"a":2,"b":1}'),
    ],
)
def test_stored_canonicalises_a_value(value: object, expected: object) -> None:
    assert stored(value) == expected


# --- R2: meta get/set ----------------------------------------------------------------------------


def test_the_schema_version_is_written_on_creation(store: GraphStore) -> None:
    assert store.get_meta(SCHEMA_VERSION_KEY) == SCHEMA_VERSION


@pytest.mark.parametrize("key", META_KEYS)
def test_a_meta_key_round_trips(store: GraphStore, key: str) -> None:
    store.set_meta(key, "value-1")
    assert store.get_meta(key) == "value-1"
    store.set_meta(key, "value-2")
    assert store.get_meta(key) == "value-2"


def test_an_absent_meta_key_is_none(store: GraphStore) -> None:
    assert store.get_meta("never-set") is None


def test_a_foreign_schema_version_fails_loud(db_path: Path) -> None:
    with GraphStore(db_path, now=lambda: FIXED_CLOCK) as created:
        created.set_meta(SCHEMA_VERSION_KEY, "2")
    with pytest.raises(SchemaVersionError):
        GraphStore(db_path)


# --- R3: the six query helpers --------------------------------------------------------------------


def test_nodes_by_name(store: GraphStore) -> None:
    seeded(store)
    assert [row["qualified_name"] for row in store.nodes_by_name("save", limit=10)] == [
        "\\App\\UserRepo::save"
    ]


def test_nodes_by_name_narrows_by_kind(store: GraphStore) -> None:
    seeded(store)
    assert store.nodes_by_name("save", kind="Class", limit=10) == []


def test_nodes_by_kind(store: GraphStore) -> None:
    seeded(store)
    assert [row["name"] for row in store.nodes_by_kind("Class", limit=10)] == ["UserRepo"]


def test_nodes_by_file(store: GraphStore) -> None:
    seeded(store)
    assert len(store.nodes_by_file("a.php", limit=10)) == 2
    assert store.nodes_by_file("other.php", limit=10) == []


def test_edges_by_source(store: GraphStore) -> None:
    seeded(store)
    found = store.edges_by_source("\\App\\UserRepo::save", limit=10)
    assert [row["target_raw"] for row in found] == ["\\App\\Db::write"]
    assert found[0]["target_qname"] is None
    assert found[0]["confidence_tier"] == "RESOLVED"


def test_edges_by_source_narrows_by_kind(store: GraphStore) -> None:
    seeded(store)
    assert store.edges_by_source("\\App\\UserRepo::save", kind="NEW", limit=10) == []


def test_edges_by_target(store: GraphStore) -> None:
    seeded(store)
    store.replace_file_rows(
        "a.php",
        nodes_for("a.php"),
        [
            an_edge(
                "CALLS",
                "\\App\\UserRepo::save",
                "\\App\\Db::write",
                "a.php",
                target_qname="\\App\\Db::write",
            )
        ],
    )
    found = store.edges_by_target("\\App\\Db::write", limit=10)
    assert [row["source_qname"] for row in found] == ["\\App\\UserRepo::save"]


@pytest.mark.parametrize("limit", [1, 2])
def test_a_read_helper_honours_its_limit(store: GraphStore, limit: int) -> None:
    seeded(store)
    assert len(store.nodes_by_file("a.php", limit=limit)) == limit


def test_a_read_helper_orders_ties_deterministically(store: GraphStore) -> None:
    # Same name in three files: only the full ORDER BY makes the sequence reproducible.
    for path in ("c.php", "a.php", "b.php"):
        store.upsert_file(path, "h", "php")
        store.replace_file_rows(path, [a_node("Namespace", "App", "\\App", path)], [])
    ordered = [row["file_path"] for row in store.nodes_by_name("App", limit=10)]
    assert ordered == ["a.php", "b.php", "c.php"]
