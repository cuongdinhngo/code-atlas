"""SQLite schema and GraphStore — the only module that touches SQLite (§10, R1.4).

One instance owns one connection, so the graph has a single writer while parsing fans out (R4.3).
Column lists are derived from :mod:`code_atlas.contract`, never re-typed here (R3.2); the DDL below
carries the §10 text and ``tests/test_store.py`` cross-checks the two representations.

Three stored columns are deliberately **not** reproducible: ``nodes.id``/``edges.id`` follow insert
order, and ``files.updated_at`` is wall-clock. The clock is injectable so a caller can pin it, and
determinism (R4.2) is asserted over row content ordered by a stable key, with the ids excluded.
"""

import json
import sqlite3
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from code_atlas import contract

SCHEMA_VERSION = "1"
SCHEMA_VERSION_KEY = "schema_version"
CONTRACT_VERSION_KEY = "contract_version"
LAST_COMMIT_KEY = "last_commit"
BUILT_AT_KEY = "built_at"
META_KEYS: tuple[str, ...] = (
    SCHEMA_VERSION_KEY,
    CONTRACT_VERSION_KEY,
    LAST_COMMIT_KEY,
    BUILT_AT_KEY,
)

MEMORY_DB = ":memory:"

# Set outside any transaction: foreign_keys is silently ignored inside one.
PRAGMAS: tuple[str, ...] = ("journal_mode=WAL", "foreign_keys=ON", "busy_timeout=5000")

DDL = """
CREATE TABLE IF NOT EXISTS files (
  path TEXT PRIMARY KEY, hash TEXT, language TEXT, parsed_ok INT DEFAULT 1, updated_at TEXT);

CREATE TABLE IF NOT EXISTS nodes (
  id INTEGER PRIMARY KEY, kind TEXT, name TEXT, qualified_name TEXT,
  file_path TEXT REFERENCES files(path), line_start INT, line_end INT,
  modifiers TEXT, params TEXT, is_test INT DEFAULT 0, extra TEXT,
  UNIQUE(qualified_name, file_path));
CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);
CREATE INDEX IF NOT EXISTS idx_nodes_file ON nodes(file_path);

CREATE TABLE IF NOT EXISTS edges (
  id INTEGER PRIMARY KEY, kind TEXT, source_qname TEXT, target_qname TEXT, target_raw TEXT,
  file_path TEXT, line INT, confidence_tier TEXT DEFAULT 'RESOLVED');
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(source_qname, kind);
CREATE INDEX IF NOT EXISTS idx_edges_tgt ON edges(target_qname, kind);

CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
  name, qualified_name, file_path, params, content='nodes', content_rowid='id');

CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
  INSERT INTO nodes_fts(rowid, name, qualified_name, file_path, params)
  VALUES (new.id, new.name, new.qualified_name, new.file_path, new.params);
END;
CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, name, qualified_name, file_path, params)
  VALUES ('delete', old.id, old.name, old.qualified_name, old.file_path, old.params);
END;
CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, name, qualified_name, file_path, params)
  VALUES ('delete', old.id, old.name, old.qualified_name, old.file_path, old.params);
  INSERT INTO nodes_fts(rowid, name, qualified_name, file_path, params)
  VALUES (new.id, new.name, new.qualified_name, new.file_path, new.params);
END;

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""

_NODE_COLUMNS = ", ".join(contract.NODE_FIELDS)
_EDGE_COLUMNS = ", ".join(contract.EDGE_FIELDS)
_NODE_COLUMNS_JOINED = ", ".join(f"nodes.{field}" for field in contract.NODE_FIELDS)

NODE_ROW_KEYS: tuple[str, ...] = ("id", *contract.NODE_FIELDS)
EDGE_ROW_KEYS: tuple[str, ...] = ("id", *contract.EDGE_FIELDS)

NODES = "nodes"
EDGES = "edges"

# Full orderings, so equal-ranking rows cannot reorder between runs (R4.2).
_NODE_ORDER = "qualified_name, file_path, line_start, id"
_EDGE_ORDER = "source_qname, kind, target_raw, file_path, line, id"
_SEARCH_ORDER = "nodes_fts.rank, nodes.qualified_name, nodes.file_path, nodes.id"

Row = dict[str, object]


class SchemaVersionError(Exception):
    """Written by another schema version — a programmer error, so it raises loud (R5.3)."""


def utc_now() -> str:
    """The default clock: a second-precision UTC timestamp."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def fts_term(query: str) -> str:
    """Quote a query as one literal fts5 prefix term, so punctuation and operators never raise."""
    return '"' + query.replace('"', '""') + '"*'


def stored(value: object) -> object:
    """Structured values become canonical JSON, so identical input stores identical bytes (R4.2)."""
    if value is None or isinstance(value, str | int | float):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class GraphStore:
    """The graph in SQLite: schema creation, per-file writes, and every bounded read."""

    def __init__(self, db_path: Path, *, now: Callable[[], str] | None = None) -> None:
        self._now = utc_now if now is None else now
        if str(db_path) != MEMORY_DB:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        for pragma in PRAGMAS:
            self._conn.execute(f"PRAGMA {pragma}")
        self._create_schema()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "GraphStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def now(self) -> str:
        """The store's clock, exposed so a caller stamping ``meta`` shares its injection point."""
        return self._now()

    def _create_schema(self) -> None:
        """Create the §10 objects, then refuse a database another schema version wrote (R5.3)."""
        self._conn.executescript(DDL)
        self._conn.commit()
        found = self.get_meta(SCHEMA_VERSION_KEY)
        if found is None:
            self.set_meta(SCHEMA_VERSION_KEY, SCHEMA_VERSION)
        elif found != SCHEMA_VERSION:
            self._conn.close()
            raise SchemaVersionError(
                f"database schema version {found!r} is not {SCHEMA_VERSION!r} — "
                "delete the index file and rebuild"
            )

    # --- writes ---------------------------------------------------------------------------------

    def upsert_file(
        self, path: str, file_hash: str, language: str, *, parsed_ok: bool = True
    ) -> None:
        """Insert or update one file row; a failed parse keeps its row with parsed_ok=0 (R5.1)."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO files (path, hash, language, parsed_ok, updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(path) DO UPDATE SET "
                "hash = excluded.hash, language = excluded.language, "
                "parsed_ok = excluded.parsed_ok, updated_at = excluded.updated_at",
                (path, file_hash, language, int(parsed_ok), self._now()),
            )

    def replace_file_rows(
        self,
        path: str,
        nodes: Iterable[Mapping[str, object]],
        edges: Iterable[Mapping[str, object]],
    ) -> None:
        """Delete this path's rows then insert the given ones, so re-indexing is idempotent."""
        node_groups = _grouped(contract.NODE_FIELDS, nodes)
        edge_groups = _grouped(contract.EDGE_FIELDS, edges)
        with self._conn:
            self._delete_rows(path)
            self._insert(NODES, node_groups)
            self._insert(EDGES, edge_groups)

    def _insert(self, table: str, groups: dict[tuple[str, ...], list[tuple[object, ...]]]) -> None:
        """One statement per distinct field set, so a column §10 gives a DEFAULT keeps it."""
        for present, values in groups.items():
            columns = ", ".join(present)
            placeholders = ", ".join("?" * len(present))
            self._conn.executemany(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values
            )

    def remove_file(self, path: str) -> None:
        """Drop a vanished path (§8.1); nodes go before the files row, because FKs are on."""
        with self._conn:
            self._delete_rows(path)
            self._conn.execute("DELETE FROM files WHERE path = ?", (path,))

    def _delete_rows(self, path: str) -> None:
        self._conn.execute("DELETE FROM edges WHERE file_path = ?", (path,))
        self._conn.execute("DELETE FROM nodes WHERE file_path = ?", (path,))

    def get_meta(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row[0])

    def set_meta(self, key: str, value: str) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def rebuild_search_index(self) -> None:
        """Repair only: the triggers keep nodes_fts current, so this just recovers a stale index."""
        with self._conn:
            self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES ('rebuild')")

    # --- reads ----------------------------------------------------------------------------------

    def file_paths(self) -> tuple[str, ...]:
        """Every indexed path, sorted — what a build reconciles its collection against (§8.1)."""
        cursor = self._conn.execute("SELECT path FROM files ORDER BY path")
        return tuple(str(row[0]) for row in cursor)

    def counts(self) -> dict[str, int]:
        """Row totals for the status tool: counted in SQL, never by loading the graph (R4.3)."""
        row = self._conn.execute(
            "SELECT (SELECT COUNT(*) FROM files), (SELECT COUNT(*) FROM files WHERE parsed_ok = 1),"
            " (SELECT COUNT(*) FROM nodes), (SELECT COUNT(*) FROM edges)"
        ).fetchone()
        files, parsed, nodes, edges = (int(value) for value in row)
        return {
            "files": files,
            "parsed": parsed,
            "failed": files - parsed,
            "nodes": nodes,
            "edges": edges,
        }

    def nodes_by_name(self, name: str, *, kind: str | None = None, limit: int) -> list[Row]:
        return self._nodes("name = ?", name, kind, limit)

    def nodes_by_qualified_name(
        self, qname: str, *, kind: str | None = None, limit: int
    ) -> list[Row]:
        return self._nodes("qualified_name = ?", qname, kind, limit)

    def nodes_by_kind(self, kind: str, *, limit: int) -> list[Row]:
        return self._nodes("kind = ?", kind, None, limit)

    def nodes_by_file(self, path: str, *, limit: int) -> list[Row]:
        return self._nodes("file_path = ?", path, None, limit)

    def edges_by_source(
        self, qname: str, *, kinds: Sequence[str] | None = None, limit: int
    ) -> list[Row]:
        return self._edges("source_qname = ?", qname, kinds, limit)

    def edges_by_target(
        self, qname: str, *, kinds: Sequence[str] | None = None, limit: int
    ) -> list[Row]:
        """Edges whose resolved ``target_qname`` is ``qname``.

        Optional ``kinds`` narrows the set (e.g. CALLER_KINDS).
        """
        return self._edges("target_qname = ?", qname, kinds, limit)

    def unresolved_edges(self) -> list[Row]:
        """Every edge the resolver may still link — ``target_qname`` is still NULL (§8.2)."""
        sql = (
            f"SELECT id, {_EDGE_COLUMNS} FROM edges WHERE target_qname IS NULL "
            f"ORDER BY {_EDGE_ORDER}"
        )
        return self._rows(EDGE_ROW_KEYS, sql, ())

    def link_edge(self, edge_id: int, target_qname: str, confidence_tier: str) -> None:
        """Set one edge's resolved target and tier (resolver only — R1.4)."""
        with self._conn:
            self._conn.execute(
                "UPDATE edges SET target_qname = ?, confidence_tier = ? WHERE id = ?",
                (target_qname, confidence_tier, edge_id),
            )

    def insert_edge(self, edge: Mapping[str, object]) -> None:
        """Insert one edge row — used when a multi-candidate resolve expands into siblings."""
        with self._conn:
            self._insert(EDGES, _grouped(contract.EDGE_FIELDS, [edge]))

    def search_nodes(self, query: str, *, kind: str | None = None, limit: int) -> list[Row]:
        """Search the FTS index by one literal prefix term; punctuation is quoted, never raised."""
        where, params = _narrow("nodes_fts MATCH ?", fts_term(query), kind, "nodes.kind = ?")
        sql = (
            f"SELECT nodes.id, {_NODE_COLUMNS_JOINED} FROM nodes "
            f"JOIN nodes_fts ON nodes_fts.rowid = nodes.id "
            f"WHERE {where} ORDER BY {_SEARCH_ORDER} LIMIT ?"
        )
        return self._rows(NODE_ROW_KEYS, sql, (*params, limit))

    def _nodes(self, where: str, value: str, kind: str | None, limit: int) -> list[Row]:
        clause, params = _narrow(where, value, kind, "kind = ?")
        sql = f"SELECT id, {_NODE_COLUMNS} FROM nodes WHERE {clause} ORDER BY {_NODE_ORDER} LIMIT ?"
        return self._rows(NODE_ROW_KEYS, sql, (*params, limit))

    def _edges(
        self, where: str, value: str, kinds: Sequence[str] | None, limit: int
    ) -> list[Row]:
        if kinds is None:
            sql = (
                f"SELECT id, {_EDGE_COLUMNS} FROM edges WHERE {where} "
                f"ORDER BY {_EDGE_ORDER} LIMIT ?"
            )
            return self._rows(EDGE_ROW_KEYS, sql, (value, limit))
        if not kinds:
            raise ValueError("kinds must be non-empty")
        placeholders = ", ".join("?" for _ in kinds)
        sql = (
            f"SELECT id, {_EDGE_COLUMNS} FROM edges "
            f"WHERE {where} AND kind IN ({placeholders}) "
            f"ORDER BY {_EDGE_ORDER} LIMIT ?"
        )
        return self._rows(EDGE_ROW_KEYS, sql, (value, *kinds, limit))

    def _rows(self, keys: tuple[str, ...], sql: str, params: Sequence[object]) -> list[Row]:
        cursor = self._conn.execute(sql, params)
        return [dict(zip(keys, row, strict=True)) for row in cursor]


def _grouped(
    fields: tuple[str, ...], rows: Iterable[Mapping[str, object]]
) -> dict[tuple[str, ...], list[tuple[object, ...]]]:
    """Insert tuples keyed by the contract fields a row actually carries, in contract order.

    An **absent** optional field is left out of the statement so the column's §10 DEFAULT applies
    (``confidence_tier``, ``is_test``); a field present as ``None`` is stored as an explicit NULL.
    """
    groups: dict[tuple[str, ...], list[tuple[object, ...]]] = {}
    for row in rows:
        present = tuple(field for field in fields if field in row)
        groups.setdefault(present, []).append(tuple(stored(row[field]) for field in present))
    return groups


def _narrow(
    where: str, value: str, kind: str | None, kind_clause: str
) -> tuple[str, tuple[object, ...]]:
    """Add the optional kind filter to a predicate, keeping placeholders and values in step."""
    if kind is None:
        return where, (value,)
    return f"{where} AND {kind_clause}", (value, kind)
