"""GraphStore against a real SQLite file: schema, per-file idempotency, FTS, and determinism.

No mocks — every acceptance criterion of task 004 can only fail at the integration layer, so each
test drives an actual database. Row ids are excluded from the determinism assertions on purpose:
they follow insert order, which follows worker completion order (PLAN §8.1).
"""

import sqlite3
import threading
import time
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
    "idx_edges_tier",
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


def test_plan_10_specifies_fifteen_schema_objects() -> None:
    # Guards the denominator: a shrunken list would pass every per-object check while covering less.
    # +1 is the WAL pragma; idx_edges_tier (task 028) brought the count from 14 to 15.
    assert len(SCHEMA_OBJECTS) + 1 == 15


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


# --- task 043: a file may legally declare one qname twice — keep-first, never abort ---------------


def test_replace_file_rows_keeps_first_of_a_duplicate_qname(store: GraphStore) -> None:
    """Two same-qname nodes for one file persist exactly one — the first emitted (R5.1, AC2)."""
    store.upsert_file("dup.php", "hash", "php")
    dropped = store.replace_file_rows(
        "dup.php",
        [
            a_node("Function", "f", "\\f", "dup.php", line_start=1),
            a_node("Function", "f", "\\f", "dup.php", line_start=9),
            a_node("Interface", "X", "\\X", "dup.php", line_start=20),
            a_node("Class", "X", "\\X", "dup.php", line_start=30),
        ],
        [],
    )
    assert dropped == 2
    survivors = store.nodes_by_file("dup.php", limit=10)
    assert sorted(row["qualified_name"] for row in survivors) == ["\\X", "\\f"]
    by_qname = {row["qualified_name"]: row for row in survivors}
    # Keep-first: the first emit of each qname is the survivor (its line_start, its kind).
    assert by_qname["\\f"]["line_start"] == 1
    assert by_qname["\\X"]["kind"] == "Interface"


def test_replace_file_rows_leaves_null_qnames_distinct(store: GraphStore) -> None:
    """NULL/anonymous qnames never collide, so keep-first must not collapse them (AC2)."""
    store.upsert_file("anon.php", "hash", "php")
    dropped = store.replace_file_rows(
        "anon.php",
        [
            a_node("Function", "{closure}", None, "anon.php", line_start=1),
            a_node("Function", "{closure}", None, "anon.php", line_start=2),
        ],
        [],
    )
    assert dropped == 0
    assert len(store.nodes_by_file("anon.php", limit=10)) == 2


def test_deduping_a_duplicate_declaration_is_deterministic(
    store: GraphStore, db_path: Path
) -> None:
    """Re-indexing the same duplicate-declaration file yields identical rows (R4.2, AC3)."""
    nodes = [
        a_node("Function", "f", "\\f", "dup.php", line_start=1),
        a_node("Function", "f", "\\f", "dup.php", line_start=9),
    ]
    store.upsert_file("dup.php", "hash", "php")
    store.replace_file_rows("dup.php", nodes, [])
    before = content(db_path)
    store.replace_file_rows("dup.php", nodes, [])
    assert content(db_path) == before


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


def test_the_update_trigger_keeps_the_search_index_in_step(
    store: GraphStore, db_path: Path
) -> None:
    """Fires `nodes_au` directly: no store method updates a node, so nothing else exercises it.

    The trigger closes the mirror invariant for a write path the store does not currently take;
    without this test a broken trigger body would ship green.
    """
    seeded(store)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE nodes SET name = 'Renamed', qualified_name = '\\App\\Renamed' "
            "WHERE name = 'UserRepo'"
        )

    assert [row["name"] for row in store.search_nodes("Renamed", limit=10)] == ["Renamed"]
    # The method still carries the old token in its own qname, so only the class moved.
    assert [row["name"] for row in store.search_nodes("UserRepo", limit=10)] == ["save"]
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES ('integrity-check')")


def test_rebuilding_the_search_index_keeps_the_same_hits(store: GraphStore) -> None:
    seeded(store)
    before = store.search_nodes("UserRepo", limit=10)
    store.rebuild_search_index()
    assert store.search_nodes("UserRepo", limit=10) == before


def test_the_tokenizer_matches_camel_case_substrings(store: GraphStore) -> None:
    # schema_version 2: trigram FTS — ``email`` hits ``findByEmail`` (004 Q8 / task 014).
    store.upsert_file("c.php", "h", "php")
    store.replace_file_rows(
        "c.php",
        [
            a_node("Function", "find_by_email", "\\App\\find_by_email", "c.php"),
            a_node("Function", "findByEmail", "\\App\\findByEmail", "c.php"),
        ],
        [],
    )
    assert {row["name"] for row in store.search_nodes("email", limit=10)} == {
        "find_by_email",
        "findByEmail",
    }

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
        created.set_meta(SCHEMA_VERSION_KEY, "1")
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
    assert store.edges_by_source("\\App\\UserRepo::save", kinds=("NEW",), limit=10) == []


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


def test_nodes_by_qualified_name(store: GraphStore) -> None:
    seeded(store)
    found = store.nodes_by_qualified_name("\\App\\UserRepo::save", limit=10)
    assert [row["name"] for row in found] == ["save"]


def test_nodes_by_qualified_names_chunks_large_key_lists(
    store: GraphStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Batch IN lists stay under host max-vars via ``_IN_CHUNK`` (PR #30 review)."""
    import code_atlas.store as store_mod

    monkeypatch.setattr(store_mod, "_IN_CHUNK", 2)
    nodes = [
        a_node("Class", f"C{i}", f"\\Ns\\C{i}", f"f{i}.x") for i in range(5)
    ]
    for path in sorted({str(n["file_path"]) for n in nodes}):
        store.upsert_file(path, "h", "lang")
    store.replace_file_rows("f0.x", nodes, [])

    calls = {"n": 0}
    original = GraphStore._rows

    def counting(
        self: GraphStore, keys: tuple[str, ...], sql: str, params: object
    ) -> list[dict[str, object]]:
        calls["n"] += 1
        return original(self, keys, sql, params)  # type: ignore[arg-type]

    monkeypatch.setattr(GraphStore, "_rows", counting)
    qnames = [f"\\Ns\\C{i}" for i in range(5)]
    found = store.nodes_by_qualified_names(qnames, limit=1)
    assert calls["n"] == 3  # ceil(5 / 2)
    assert [found[q][0]["qualified_name"] for q in qnames] == qnames


def test_unresolved_edges_skips_already_linked_rows(store: GraphStore) -> None:
    seeded(store)
    assert len(store.unresolved_edges()) == 1
    store.link_edge(store.unresolved_edges()[0]["id"], "\\App\\Db::write", "RESOLVED")
    assert store.unresolved_edges() == []


def test_link_edge_and_insert_edge(store: GraphStore) -> None:
    seeded(store)
    edge_id = store.unresolved_edges()[0]["id"]
    store.link_edge(int(edge_id), "\\App\\Db::write", "HEURISTIC")
    store.insert_edge(
        an_edge(
            "CALLS",
            "\\App\\UserRepo::save",
            "\\App\\Db::write",
            "a.php",
            target_qname="\\App\\Other::write",
            confidence_tier="HEURISTIC",
        )
    )
    targets = [
        row["target_qname"]
        for row in store.edges_by_source("\\App\\UserRepo::save", kinds=("CALLS",), limit=10)
    ]
    assert targets == ["\\App\\Db::write", "\\App\\Other::write"]


# --- task 009: the two reads a build needs, and the busy_timeout proof deferred from task 004 -----


def test_the_indexed_paths_come_back_sorted(store: GraphStore) -> None:
    # What a build reconciles its collection against, so the order must not follow insert order.
    assert store.file_paths() == ()
    for path in ("c.php", "a.php", "b.php"):
        store.upsert_file(path, "h", "php")
    assert store.file_paths() == ("a.php", "b.php", "c.php")

    store.remove_file("b.php")
    assert store.file_paths() == ("a.php", "c.php")


def test_the_store_exposes_the_clock_it_stamps_rows_with(db_path: Path) -> None:
    """`meta.built_at` must share the one injection point, or two clocks disagree in one build."""
    with GraphStore(db_path, now=lambda: FIXED_CLOCK) as opened:
        assert opened.now() == FIXED_CLOCK
        opened.upsert_file("a.php", "h", "php")
        row = opened._conn.execute("SELECT updated_at FROM files").fetchone()
    assert row[0] == FIXED_CLOCK


def hold_a_write_lock(db_path: Path) -> sqlite3.Connection:
    """A competing writer holding a real reserved lock — not a simulation of one."""
    blocker = sqlite3.connect(db_path)
    blocker.execute("BEGIN IMMEDIATE")
    blocker.execute("INSERT INTO meta (key, value) VALUES ('blocker', '1')")
    return blocker


def test_a_second_writer_waits_out_a_held_lock_instead_of_failing(db_path: Path) -> None:
    """R4.3's companion: one writer is the design, but a stray second one must not lose data.

    Deferred from task 004, which had no fan-out to contend with. `busy_timeout` is per connection,
    so the contending store is built inside that thread — sqlite3 objects are bound to their maker.
    """
    GraphStore(db_path).close()
    blocker = hold_a_write_lock(db_path)
    outcome: dict[str, object] = {}

    def contend() -> None:
        with GraphStore(db_path) as second:
            started = time.monotonic()
            try:
                second.upsert_file("a.php", "h", "php")
                outcome["result"] = "succeeded"
            except sqlite3.OperationalError as error:
                outcome["result"] = f"raised {error}"
            outcome["waited"] = time.monotonic() - started

    thread = threading.Thread(target=contend)
    thread.start()
    time.sleep(0.75)
    blocker.commit()
    blocker.close()
    thread.join(timeout=30)

    assert not thread.is_alive(), "the contending writer never returned"
    assert outcome["result"] == "succeeded"
    assert isinstance(outcome["waited"], float) and outcome["waited"] >= 0.5, (
        "it returned too fast to have waited on the lock at all"
    )
    with GraphStore(db_path) as reopened:
        assert reopened.file_paths() == ("a.php",)


def test_without_busy_timeout_the_same_contention_fails_at_once(db_path: Path) -> None:
    """The negative control: a pragma that is never exercised is not evidence (LESSONS 002)."""
    GraphStore(db_path).close()
    blocker = hold_a_write_lock(db_path)
    outcome: dict[str, object] = {}

    def contend_without_the_pragma() -> None:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA busy_timeout=0")
        try:
            conn.execute("INSERT INTO files (path) VALUES ('a.php')")
            conn.commit()
            outcome["result"] = "succeeded"
        except sqlite3.OperationalError as error:
            outcome["result"] = str(error)
        conn.close()

    thread = threading.Thread(target=contend_without_the_pragma)
    thread.start()
    thread.join(timeout=30)
    blocker.commit()
    blocker.close()

    assert outcome["result"] == "database is locked", (
        "the contention never happened, so the test above proved nothing"
    )


# --- task 010: the aggregate the status tool reports ----------------------------------------------


def test_the_counts_come_from_the_rows_not_from_the_file_total(store: GraphStore) -> None:
    """`parsed` follows `parsed_ok`: reporting the file total would hide every failed parse."""
    assert store.counts() == {
        "files": 0,
        "parsed": 0,
        "failed": 0,
        "nodes": 0,
        "edges": 0,
        "stubs": 0,
    }

    seeded(store)
    store.upsert_file("b.php", "h", "php", parsed_ok=False)

    assert store.counts() == {
        "files": 2,
        "parsed": 1,
        "failed": 1,
        "nodes": 2,
        "edges": 1,
        "stubs": 0,
    }


def test_edge_health_counts_tiers_and_link_resolution(store: GraphStore) -> None:
    """Hand-counted plant: every CONFIDENCE_TIERS key present; unresolved ≠ DYNAMIC."""
    path = "a.php"
    store.upsert_file(path, "h", "php")
    store.replace_file_rows(
        path,
        nodes_for(path),
        [
            an_edge(
                "CALLS",
                "\\App\\UserRepo::save",
                "\\App\\Db::write",
                path,
                target_qname="\\App\\Db::write",
                confidence_tier="RESOLVED",
            ),
            an_edge(
                "CALLS",
                "\\App\\UserRepo::save",
                "save",
                path,
                target_qname="\\App\\Other::save",
                confidence_tier="HEURISTIC",
            ),
            an_edge(
                "CALLS",
                "\\App\\UserRepo::save",
                "$m",
                path,
                confidence_tier="DYNAMIC",
            ),
            an_edge(
                "EXTENDS",
                "\\App\\UserRepo",
                "\\Vendor\\Base",
                path,
                confidence_tier="RESOLVED",
            ),
        ],
    )

    assert store.edge_health() == {
        "by_tier": {"RESOLVED": 2, "HEURISTIC": 1, "DYNAMIC": 1},
        "resolved": 2,
        "unresolved": 2,
    }
    assert sum(store.edge_health()["by_tier"].values()) == store.counts()["edges"]  # type: ignore[arg-type]


def test_edge_health_folds_null_and_unknown_tiers_into_resolved(store: GraphStore) -> None:
    """NULL / unknown tiers must not vanish — sum(by_tier) stays equal to edges."""
    path = "a.php"
    store.upsert_file(path, "h", "php")
    store.replace_file_rows(
        path,
        nodes_for(path),
        [
            an_edge(
                "CALLS",
                "\\App\\UserRepo::save",
                "\\App\\Db::write",
                path,
                target_qname="\\App\\Db::write",
                confidence_tier="RESOLVED",
            ),
            an_edge(
                "CALLS",
                "\\App\\UserRepo::save",
                "gone",
                path,
                confidence_tier=None,
            ),
            an_edge(
                "CALLS",
                "\\App\\UserRepo::save",
                "weird",
                path,
                confidence_tier="FUTURE_TIER",
            ),
        ],
    )

    health = store.edge_health()
    assert health == {
        "by_tier": {"RESOLVED": 3, "HEURISTIC": 0, "DYNAMIC": 0},
        "resolved": 1,
        "unresolved": 2,
    }
    assert sum(health["by_tier"].values()) == store.counts()["edges"]  # type: ignore[arg-type]


def test_count_edges_by_target_matches_listed_rows(store: GraphStore) -> None:
    path = "a.php"
    store.upsert_file(path, "h", "php")
    store.replace_file_rows(
        path,
        nodes_for(path),
        [
            an_edge(
                "CALLS",
                "\\App\\UserRepo::save",
                "\\App\\Db::write",
                path,
                target_qname="\\App\\Db::write",
            ),
            an_edge(
                "CALLS",
                "\\App\\UserRepo::find",
                "\\App\\Db::write",
                path,
                target_qname="\\App\\Db::write",
            ),
            an_edge(
                "EXTENDS",
                "\\App\\UserRepo",
                "\\Base",
                path,
                target_qname="\\Base",
            ),
        ],
    )
    assert store.count_edges_by_target("\\App\\Db::write") == 2
    assert store.count_edges_by_target("\\App\\Db::write", kinds=("CALLS",)) == 2
    assert store.count_edges_by_target("\\Base", kinds=("EXTENDS",)) == 1
    assert store.count_edges_by_target("\\missing") == 0


def test_count_search_nodes_matches_search_hits(store: GraphStore) -> None:
    path = "a.php"
    store.upsert_file(path, "h", "php")
    store.replace_file_rows(
        path,
        [
            a_node("Function", "Alpha0", "\\Alpha0", path),
            a_node("Function", "Alpha1", "\\Alpha1", path),
            a_node("Function", "Other", "\\Other", path),
            a_node("Class", "Db", "\\App\\Db", path),
        ],
        [],
    )
    assert store.count_search_nodes("Alpha") == len(store.search_nodes("Alpha", limit=50))
    assert store.count_search_nodes("Alpha") == 2
    assert store.count_search_nodes("ZzNope") == 0
    assert store.count_search_nodes("Db") == len(store.search_nodes("Db", limit=50))
    assert store.count_search_nodes("Alpha", kind="Function") == 2
    assert store.count_search_nodes("Alpha", kind="Class") == 0
    assert store.count_search_nodes("Db", namespace="\\App") == 1


def test_count_edges_by_target_rejects_empty_kinds(store: GraphStore) -> None:
    with pytest.raises(ValueError, match="kinds must be non-empty"):
        store.count_edges_by_target("\\x", kinds=())
