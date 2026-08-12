"""SQLite schema and GraphStore — the only module that touches SQLite (§10, R1.4).

One instance owns one connection, so the graph has a single writer while parsing fans out (R4.3).
Column lists are derived from :mod:`code_atlas.contract`, never re-typed here (R3.2); the DDL below
carries the §10 text and ``tests/test_store.py`` cross-checks the two representations.
Requires SQLite ≥ 3.25 (``ROW_NUMBER`` window functions); ``IN (...)`` lists are chunked at
``_IN_CHUNK`` so hosts below 3.32's higher max-vars still work.

Three stored columns are deliberately **not** reproducible: ``nodes.id``/``edges.id`` follow insert
order, and ``files.updated_at`` is wall-clock. The clock is injectable so a caller can pin it, and
determinism (R4.2) is asserted over row content ordered by a stable key, with the ids excluded.
"""

import json
import sqlite3
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

from code_atlas import contract
from code_atlas.contract import CONFIDENCE_TIERS

SCHEMA_VERSION = "4"
SCHEMA_VERSION_KEY = "schema_version"
CONTRACT_VERSION_KEY = "contract_version"
LAST_COMMIT_KEY = "last_commit"
# Human ref the index was built on (branch name or ``HEAD`` when detached) — beside the SHA (077).
LAST_REF_KEY = "last_ref"
BUILT_AT_KEY = "built_at"
# Which suffixes the build claimed. Only the adapter handshake knows them, and a status read must
# not start an adapter to find out — so the build leaves them here (047).
INDEXED_SUFFIXES_KEY = "indexed_suffixes"
META_KEYS: tuple[str, ...] = (
    SCHEMA_VERSION_KEY,
    CONTRACT_VERSION_KEY,
    LAST_COMMIT_KEY,
    LAST_REF_KEY,
    BUILT_AT_KEY,
    INDEXED_SUFFIXES_KEY,
)

# Bound SQLite variable lists so a large incremental unlink cannot trip the host's max-vars.
_IN_CHUNK = 400

# Impact engine (§12 / task 017) — hop decay and inclusive floor (A1/A6).
# Kind weights live in contract.IMPACT_KIND_WEIGHTS (R3.2).
IMPACT_DECAY = 0.7
IMPACT_FLOOR = 0.05
IMPACT_WEIGHTS = contract.IMPACT_KIND_WEIGHTS
_RESOLVED = CONFIDENCE_TIERS[0]

MEMORY_DB = ":memory:"

# The errors a per-file store write may raise. Callers (the indexer) catch this rather than name
# sqlite3, so SQLite stays confined to this module (R1.4 / tests/test_sql_confinement.py).
WRITE_ERRORS: tuple[type[Exception], ...] = (sqlite3.Error,)

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
  file_path TEXT, line INT, confidence_tier TEXT DEFAULT 'RESOLVED', args TEXT, arg_keys TEXT);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(source_qname, kind);
CREATE INDEX IF NOT EXISTS idx_edges_tgt ON edges(target_qname, kind);
CREATE INDEX IF NOT EXISTS idx_edges_tier ON edges(confidence_tier);
CREATE INDEX IF NOT EXISTS idx_edges_raw ON edges(target_raw, kind);

CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
  name, qualified_name, file_path, params,
  content='nodes', content_rowid='id', tokenize='trigram');

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


class ImpactResult(NamedTuple):
    """Rows plus counters for omitted seeds / non-RESOLVED frontier edges."""

    rows: list[Row]
    frontier_skipped_non_resolved: int
    seeds_dropped: int


class ReachabilityResult(NamedTuple):
    """Forward reachable set plus unproven (HEURISTIC/DYNAMIC-only) neighbors (task 031)."""

    reachable: list[Row]
    unproven: list[Row]
    frontier_skipped_non_resolved: int
    truncated: bool
    depth_exhausted: bool


class OrphanResult(NamedTuple):
    """Complement of reachability: orphans with why, plus unproven (task 031)."""

    orphans: list[Row]
    unproven: list[Row]
    truncated: bool
    depth_exhausted: bool


# explain_path statuses (task 038) — distinct outcomes, never empty-as-proof.
PATH_STATUS_PATH = "path"
PATH_STATUS_UNPROVEN = "unproven"
PATH_STATUS_NO_PATH = "no_path"
PATH_STATUS_UNKNOWN = "unknown"
PATH_STATUS_INCOMPLETE = "incomplete"


class ExplainPathResult(NamedTuple):
    """Shortest A→B path over IMPACT_KINDS, or a distinct non-path status (task 038)."""

    status: str
    hops: list[Row]
    truncated: bool
    depth_exhausted: bool


# Which way a schema mismatch points. Only OLDER is safe to fix by deleting the index; the other two
# would destroy a database this server cannot read but also did not write (050).
SCHEMA_OLDER = "index_older_than_server"
SCHEMA_NEWER = "index_newer_than_server"
SCHEMA_UNRECOGNISED = "index_version_unrecognised"

SCHEMA_RELATIONS: dict[str, str] = {
    SCHEMA_OLDER: "predates",
    SCHEMA_NEWER: "is newer than",
    SCHEMA_UNRECOGNISED: "is not comparable with",
}
SCHEMA_ACTIONS: dict[str, str] = {
    SCHEMA_OLDER: "rebuild the index — build_or_update_index rebuilds it in-band",
    SCHEMA_NEWER: (
        "restart or upgrade this server: the index is current and this process is stale — "
        "do not delete the index"
    ),
    SCHEMA_UNRECOGNISED: "inspect the database by hand; delete it only if it is disposable",
}


def schema_direction(found: str, expected: str) -> str:
    """Which side is behind. A version that will not parse is never reported as older (050)."""
    try:
        return SCHEMA_OLDER if int(found) < int(expected) else SCHEMA_NEWER
    except ValueError:
        return SCHEMA_UNRECOGNISED


class SchemaVersionError(Exception):
    """Written by another schema version, so it raises loud (R5.3).

    Carries the direction because the two directions need opposite fixes: an older index is
    rebuilt, a newer one means *this process* is stale and the index must be left alone (050).
    """

    def __init__(self, found: str, expected: str, db_path: Path) -> None:
        self.found = found
        self.expected = expected
        self.direction = schema_direction(found, expected)
        self.action = SCHEMA_ACTIONS[self.direction]
        super().__init__(
            f"database schema version {found!r} {SCHEMA_RELATIONS[self.direction]} "
            f"this server's {expected!r} ({db_path}) — {self.action}"
        )


def utc_now() -> str:
    """The default clock: a second-precision UTC timestamp."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def fts_term(query: str) -> str:
    """Quote a query as one literal fts5 prefix term, so punctuation and operators never raise."""
    return '"' + query.replace('"', '""') + '"*'


def _like_literal(value: str) -> str:
    """Escape ``!``, ``%``, and ``_`` for a ``LIKE … ESCAPE '!'`` pattern (``\\`` stays literal)."""
    return value.replace("!", "!!").replace("%", "!%").replace("_", "!_")


def _chunks(values: Sequence[str], size: int) -> Iterator[Sequence[str]]:
    """Yield successive slices of ``values`` so ``IN (...)`` lists stay under the host max."""
    for start in range(0, len(values), size):
        yield values[start : start + size]


# A ready-made SQL fragment plus its parameters, appended to an edge WHERE clause.
_Predicate = tuple[str, tuple[object, ...]] | None


def _args_predicate(args_at: tuple[int, str] | None) -> _Predicate:
    """Turn ``(1-based position, selector)`` into SQL over the JSON ``args`` column (task 049).

    An edge with no recorded ``args`` never matches: unknown is not absent, and a filter that
    quietly counted it as such would be the untrustworthy measurement this replaces.
    """
    if args_at is None:
        return None
    position, selector = args_at
    if position < 1:
        raise ValueError(f"argument position is 1-based, got {position}")
    if selector not in contract.ARG_SELECTORS:
        raise ValueError(f"unknown argument selector {selector!r}: {contract.ARG_SELECTORS}")
    if selector == contract.ARG_ABSENT:
        return "args IS NOT NULL AND json_array_length(args) < ?", (position,)
    at = f"$[{position - 1}]"
    if selector == contract.ARG_DYNAMIC:
        return (
            "args IS NOT NULL AND json_array_length(args) >= ? AND json_extract(args, ?) IS NULL",
            (position, at),
        )
    return "args IS NOT NULL AND json_extract(args, ?) = ?", (at, selector)


def stored(value: object) -> object:
    """Structured values become canonical JSON, so identical input stores identical bytes (R4.2)."""
    if value is None or isinstance(value, str | int | float):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class GraphStore:
    """The graph in SQLite: schema creation, per-file writes, and every bounded read."""

    def __init__(self, db_path: Path, *, now: Callable[[], str] | None = None) -> None:
        self._now = utc_now if now is None else now
        self._db_path = db_path
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
        """Refuse a database another schema version wrote (R5.3), then create the §10 objects."""
        found = self._schema_version_on_disk()
        if found is not None and found != SCHEMA_VERSION:
            self._conn.close()
            raise SchemaVersionError(found, SCHEMA_VERSION, self._db_path)
        self._conn.executescript(DDL)
        self._conn.commit()
        if found is None:
            self.set_meta(SCHEMA_VERSION_KEY, SCHEMA_VERSION)

    def _schema_version_on_disk(self) -> str | None:
        """Read the stamp before the DDL runs, so a foreign-schema database is never written to.

        ``meta(key, value)`` is the one shape that must survive every bump — it is how a version
        this build has never heard of still manages to say what it is.
        """
        present = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'"
        ).fetchone()
        return self.get_meta(SCHEMA_VERSION_KEY) if present else None

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
    ) -> int:
        """Delete this path's rows then insert the given ones, so re-indexing is idempotent.

        A file may legally declare one qname twice (conditional/guarded definitions); keep-first
        dedupe drops the repeats so the file soft-succeeds instead of tripping UNIQUE (R5.1).
        Returns the number of duplicate nodes dropped.
        """
        kept_nodes, deduped = _dedupe_nodes(nodes)
        node_groups = _grouped(contract.NODE_FIELDS, kept_nodes)
        edge_groups = _grouped(contract.EDGE_FIELDS, edges)
        with self._conn:
            self._delete_rows(path)
            self._insert(NODES, node_groups)
            self._insert(EDGES, edge_groups)
        return deduped

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
            "stubs": self.stub_file_count(),
        }

    def failed_paths(self, limit: int, offset: int = 0) -> tuple[str, ...]:
        """Paths with ``parsed_ok = 0``, ordered — the list behind ``parse_failures`` (task 058)."""
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cursor = self._conn.execute(
            "SELECT path FROM files WHERE parsed_ok = 0 ORDER BY path LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return tuple(str(row[0]) for row in cursor)

    def stub_file_count(self) -> int:
        """Distinct files whose nodes carry ``extra.stub`` (task 039)."""
        (count,) = self._conn.execute(
            "SELECT COUNT(DISTINCT file_path) FROM nodes "
            f"WHERE json_extract(extra, '$.{contract.STUB_FLAG}') = 1"
        ).fetchone()
        return int(count)

    def edge_health(self) -> dict[str, object]:
        """Tier mix and link-resolution split for ``get_index_status`` (R4; SQL only).

        ``by_tier`` always includes every ``CONFIDENCE_TIERS`` key (missing tiers are 0).
        NULL or unknown tiers fold into RESOLVED (same as other §8.2 readers), so
        ``sum(by_tier.values()) == counts()["edges"]``. ``linked`` / ``unlinked`` count
        ``target_qname`` presence: an edge that found *a* name, at any tier. Only
        ``by_tier.RESOLVED`` says the name is trusted — the two differ by ~2x on a real repo (048).
        """
        by_tier = dict.fromkeys(CONFIDENCE_TIERS, 0)
        for tier, count in self._conn.execute(
            "SELECT confidence_tier, COUNT(*) FROM edges GROUP BY confidence_tier"
        ):
            # NULL / unknown reads as RESOLVED, as §8.2 readers already do; keeps the sum == edges.
            by_tier[str(tier) if tier in by_tier else _RESOLVED] += int(count)
        (linked,) = self._conn.execute(
            "SELECT COUNT(*) FROM edges WHERE target_qname IS NOT NULL"
        ).fetchone()
        total = sum(by_tier.values())
        return {
            "by_tier": by_tier,
            "linked": int(linked),
            "unlinked": total - int(linked),
        }

    def nodes_by_name(self, name: str, *, kind: str | None = None, limit: int) -> list[Row]:
        """Single-key lookup via the batch path; prefer ``nodes_by_names`` in a loop."""
        return self.nodes_by_names([name], kind=kind, limit=limit).get(name, [])

    def nodes_by_qualified_name(
        self, qname: str, *, kind: str | None = None, limit: int
    ) -> list[Row]:
        """Single-key lookup via the batch path; prefer ``nodes_by_qualified_names`` in a loop."""
        return self.nodes_by_qualified_names([qname], kind=kind, limit=limit).get(qname, [])

    def nodes_by_names(
        self, names: Sequence[str], *, kind: str | None = None, limit: int
    ) -> dict[str, list[Row]]:
        """Per-name top-``limit`` nodes (``_NODE_ORDER`` within each name)."""
        return self._nodes_batched(key_column="name", keys=names, kind=kind, limit=limit)

    def nodes_by_qualified_names(
        self, qnames: Sequence[str], *, kind: str | None = None, limit: int
    ) -> dict[str, list[Row]]:
        """Per-qname top-``limit`` nodes (``_NODE_ORDER`` within each qname)."""
        return self._nodes_batched(
            key_column="qualified_name", keys=qnames, kind=kind, limit=limit
        )

    def nodes_by_qname_endswith(self, name: str, suffix: str, *, limit: int) -> list[Row]:
        """Nodes whose short ``name`` matches and whose ``qualified_name`` ends with ``suffix``.

        ``name`` seeks ``idx_nodes_name``; the suffix ``LIKE`` runs only over that small set.
        Component-boundary correctness is the caller's job (task 075/076).
        """
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        pattern = "%" + _like_literal(suffix)
        sql = (
            f"SELECT id, {_NODE_COLUMNS} FROM nodes "
            "WHERE name = ? AND qualified_name LIKE ? ESCAPE '!' "
            f"ORDER BY {_NODE_ORDER} LIMIT ?"
        )
        return self._rows(NODE_ROW_KEYS, sql, (name, pattern, limit))

    def nodes_by_kind(self, kind: str, *, limit: int) -> list[Row]:
        return self._nodes("kind = ?", kind, None, limit)

    def nodes_by_file(self, path: str, *, limit: int) -> list[Row]:
        return self._nodes("file_path = ?", path, None, limit)

    def edges_by_source(
        self,
        qname: str,
        *,
        kinds: Sequence[str] | None = None,
        limit: int,
        offset: int = 0,
    ) -> list[Row]:
        return self._edges("source_qname = ?", qname, kinds, limit, offset=offset)

    def count_edges_by_source(
        self, qname: str, *, kinds: Sequence[str] | None = None
    ) -> int:
        """How many edges leave ``qname`` (same kind filter as ``edges_by_source``)."""
        return self._count_edges("source_qname = ?", qname, kinds)

    def edges_matching_kind(self, kind: str, *, limit: int) -> list[Row]:
        """Up to ``limit`` edges of ``kind`` in store order (enrichment scans — task 062)."""
        return self._edges("kind = ?", kind, None, limit)

    def calls_by_target_raw(self, target_raw: str) -> list[Row]:
        """Every CALLS edge with exact ``target_raw`` (``idx_edges_raw``; no scan cap)."""
        sql = (
            f"SELECT id, {_EDGE_COLUMNS} FROM edges "
            "WHERE kind = 'CALLS' AND target_raw = ? "
            f"ORDER BY {_EDGE_ORDER}"
        )
        return self._rows(EDGE_ROW_KEYS, sql, (target_raw,))

    def calls_ending_with_target_raw(self, suffix: str) -> list[Row]:
        """CALLS whose ``target_raw`` ends with ``suffix`` (bare-setter ``::method`` arm)."""
        if not suffix:
            raise ValueError("suffix must be non-empty")
        sql = (
            f"SELECT id, {_EDGE_COLUMNS} FROM edges "
            "WHERE kind = 'CALLS' AND substr(target_raw, -?) = ? "
            f"ORDER BY {_EDGE_ORDER}"
        )
        return self._rows(EDGE_ROW_KEYS, sql, (len(suffix), suffix))

    def edges_by_target(
        self,
        qname: str,
        *,
        kinds: Sequence[str] | None = None,
        limit: int,
        offset: int = 0,
        args_at: tuple[int, str] | None = None,
    ) -> list[Row]:
        """Edges whose resolved ``target_qname`` is ``qname``.

        Optional ``kinds`` narrows the set (e.g. CALLER_KINDS); ``args_at`` narrows to call sites
        whose argument at a 1-based position has a given shape (task 049).
        ``offset`` skips leading rows in ``_EDGE_ORDER`` (task 057).
        """
        return self._edges(
            "target_qname = ?",
            qname,
            kinds,
            limit,
            offset=offset,
            extra=_args_predicate(args_at),
        )

    def count_edges_by_target(
        self,
        qname: str,
        *,
        kinds: Sequence[str] | None = None,
        args_at: tuple[int, str] | None = None,
    ) -> int:
        """How many edges target ``qname`` (same filters as ``edges_by_target``)."""
        return self._count_edges(
            "target_qname = ?", qname, kinds, extra=_args_predicate(args_at)
        )

    def edge_subtrees_by_target(
        self,
        qname: str,
        *,
        kinds: Sequence[str] | None = None,
        args_at: tuple[int, str] | None = None,
    ) -> dict[str, int]:
        """Top-level path segment → count over the full set targeting ``qname`` (task 067).

        Same filters as ``count_edges_by_target``, so the numbers reconcile. ``JOIN files``
        drops the synthetic rule bookmark (no ``files`` row since 068), leaving only real
        source subtrees. The segment is the path text before the first ``/`` — structural,
        never a repo name (R2); ``GROUP BY``/``ORDER BY`` keep the dict deterministic (R4.2).
        """
        clause, params = self._edge_where(
            "target_qname = ?", kinds, _args_predicate(args_at)
        )
        segment = (
            "CASE WHEN instr(files.path, '/') > 0 "
            "THEN substr(files.path, 1, instr(files.path, '/') - 1) ELSE files.path END"
        )
        sql = (
            f"SELECT {segment} AS seg, COUNT(*) FROM edges "
            "JOIN files ON files.path = edges.file_path "
            f"WHERE {clause} GROUP BY seg ORDER BY seg"
        )
        return {
            str(seg): int(count)
            for seg, count in self._conn.execute(sql, (qname, *params))
        }

    def count_edges_without_args(
        self, qname: str, *, kinds: Sequence[str] | None = None
    ) -> int:
        """Edges targeting ``qname`` whose arguments were never recorded — the filter's blind spot.

        Unknown is not absent: an ``args_at`` filter can say nothing about these, so a caller that
        reports a filtered count must report this one beside it (§19: no silent narrowing).
        """
        return self._count_edges("target_qname = ?", qname, kinds, extra=("args IS NULL", ()))

    def count_bare_calls_not_targeting(self, qname: str, *, bare_name: str) -> int:
        """Distinct HEURISTIC CALLS sites named ``bare_name`` that never resolve to ``qname``.

        After a truncated bare-name resolve (top-N Method candidates), call sites link only to
        the alphabetical winners — so a subject outside the cap has zero inbound CALLS but this
        count is still positive (task 054 Part B).

        CALLS-only (not ``NEW``): the resolver's bare-name fallback is HEURISTIC ``CALLS``
        (``resolver.py``). ``GROUP BY source_qname, file_path, line`` collapses sibling rows and
        two same-name calls on one line into one site.
        """
        sql = (
            "SELECT COUNT(*) FROM ("
            "  SELECT source_qname, file_path, line FROM edges"
            "  WHERE kind = 'CALLS' AND target_raw = ?"
            "    AND confidence_tier = 'HEURISTIC'"
            "  GROUP BY source_qname, file_path, line"
            "  HAVING SUM(CASE WHEN target_qname = ? THEN 1 ELSE 0 END) = 0"
            ")"
        )
        return int(self._conn.execute(sql, (bare_name, qname)).fetchone()[0])

    def count_unlinked_by_target_raw(
        self, raws: Sequence[str], *, kinds: Sequence[str]
    ) -> int:
        """Edges whose ``target_raw`` matches and ``target_qname`` is still empty (task 065).

        Evidence that a relationship exists in the table but the resolver never links that kind.
        """
        cleaned = tuple(raw for raw in raws if raw)
        if not cleaned or not kinds:
            return 0
        kind_marks = ",".join("?" * len(kinds))
        raw_marks = ",".join("?" * len(cleaned))
        sql = (
            f"SELECT COUNT(*) FROM edges WHERE kind IN ({kind_marks}) "
            f"AND target_raw IN ({raw_marks}) "
            "AND (target_qname IS NULL OR target_qname = '')"
        )
        return int(self._conn.execute(sql, (*kinds, *cleaned)).fetchone()[0])

    def count_unlinked_includes_mentioning(self, needle: str) -> int:
        """Unlinked ``INCLUDES`` whose ``target_raw`` contains ``needle`` (task 065).

        Cheap inbound approximation: dynamic/computed paths never get ``target_qname``, so
        per-path inbound unresolved cannot be exact — basename/path fragment is the proxy.
        """
        if not needle:
            return 0
        sql = (
            "SELECT COUNT(*) FROM edges WHERE kind = 'INCLUDES' "
            "AND (target_qname IS NULL OR target_qname = '') "
            "AND instr(target_raw, ?) > 0"
        )
        return int(self._conn.execute(sql, (needle,)).fetchone()[0])

    def count_nodes_by_name(self, name: str, *, kind: str | None = None) -> int:
        """How many nodes share ``name`` (optional ``kind``), via ``idx_nodes_name``."""
        if kind is None:
            sql = "SELECT COUNT(*) FROM nodes WHERE name = ?"
            params: tuple[object, ...] = (name,)
        else:
            sql = "SELECT COUNT(*) FROM nodes WHERE name = ? AND kind = ?"
            params = (name, kind)
        return int(self._conn.execute(sql, params).fetchone()[0])

    def alias_targets(self) -> dict[str, str]:
        """Map alias FQN → real FQN from ``ALIASES`` edges (``source_qname`` → ``target_raw``)."""
        rows = self._conn.execute(
            "SELECT source_qname, target_raw FROM edges WHERE kind = 'ALIASES'"
        ).fetchall()
        return {str(source): str(target) for source, target in rows}

    def unresolved_edges(self) -> list[Row]:
        """Every unresolved edge (``target_qname`` NULL), in ``id`` order (§8.2).

        Materializes via ``iter_unresolved_edges`` (was a single ``_EDGE_ORDER`` query).
        """
        return [row for batch in self.iter_unresolved_edges() for row in batch]

    def iter_unresolved_edges(
        self,
        *,
        batch_size: int = 1000,
        skip_dynamic: bool = False,
        file_path: str | None = None,
    ) -> Iterator[list[Row]]:
        """Stream unresolved edges in ``id`` order so a large graph need not load at once (§8.2 M4).

        ``batch_size`` is validated immediately (not deferred to first ``next()``).
        ``skip_dynamic`` omits ``DYNAMIC`` rows so resolve batches stay full of linkable work.
        ``file_path`` scopes to edges emitted by one file (read-through reparse).
        """
        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {batch_size}")
        return self._iter_unresolved_edges(
            batch_size, skip_dynamic=skip_dynamic, file_path=file_path
        )

    def _iter_unresolved_edges(
        self, batch_size: int, *, skip_dynamic: bool, file_path: str | None = None
    ) -> Iterator[list[Row]]:
        last_id = 0
        dynamic_clause = " AND confidence_tier != 'DYNAMIC'" if skip_dynamic else ""
        path_clause = " AND file_path = ?" if file_path is not None else ""
        sql = (
            f"SELECT id, {_EDGE_COLUMNS} FROM edges "
            f"WHERE target_qname IS NULL{dynamic_clause}{path_clause} AND id > ? "
            f"ORDER BY id LIMIT ?"
        )
        while True:
            params: tuple[object, ...] = (
                (file_path, last_id, batch_size)
                if file_path is not None
                else (last_id, batch_size)
            )
            batch = self._rows(EDGE_ROW_KEYS, sql, params)
            if not batch:
                return
            last_id = int(str(batch[-1]["id"]))
            yield batch

    def link_edge(self, edge_id: int, target_qname: str, confidence_tier: str) -> None:
        """Set one edge's resolved target and tier (resolver only — R1.4)."""
        self.link_edges([(edge_id, target_qname, confidence_tier)])

    def link_edges(self, links: Sequence[tuple[int, str, str]]) -> None:
        """Batch-set resolved targets — one transaction for the whole list (§8.2 M4)."""
        self.apply_resolution(links, ())

    def insert_edge(self, edge: Mapping[str, object]) -> None:
        """Insert one edge row — used when a multi-candidate resolve expands into siblings."""
        self.insert_edges([edge])

    def insert_edges(self, edges: Sequence[Mapping[str, object]]) -> None:
        """Insert many edge rows in one transaction (multi-candidate expand / M4)."""
        self.apply_resolution((), edges)

    def apply_resolution(
        self,
        links: Sequence[tuple[int, str, str]],
        siblings: Sequence[Mapping[str, object]],
    ) -> None:
        """Link parents and insert HEURISTIC siblings in one transaction (crash-safe)."""
        if not links and not siblings:
            return
        with self._conn:
            if links:
                self._conn.executemany(
                    "UPDATE edges SET target_qname = ?, confidence_tier = ? WHERE id = ?",
                    [(qname, tier, edge_id) for edge_id, qname, tier in links],
                )
            if siblings:
                self._insert(EDGES, _grouped(contract.EDGE_FIELDS, siblings))

    def file_hash(self, path: str) -> str | None:
        """Content hash stored for ``path``, or ``None`` when the file is not indexed."""
        row = self._conn.execute("SELECT hash FROM files WHERE path = ?", (path,)).fetchone()
        return None if row is None else str(row[0])

    def qnames_in_files(self, paths: Sequence[str]) -> tuple[str, ...]:
        """Every ``qualified_name`` living under ``paths``, sorted and de-duplicated (§8.3)."""
        if not paths:
            return ()
        found: set[str] = set()
        for chunk in _chunks(paths, _IN_CHUNK):
            placeholders = ", ".join("?" * len(chunk))
            rows = self._conn.execute(
                f"SELECT DISTINCT qualified_name FROM nodes WHERE file_path IN ({placeholders})",
                tuple(chunk),
            )
            found.update(str(row[0]) for row in rows)
        return tuple(sorted(found))

    def file_paths_targeting(self, qnames: Sequence[str]) -> tuple[str, ...]:
        """Distinct edge ``file_path`` values whose resolved target is in ``qnames`` (§8.3)."""
        if not qnames:
            return ()
        found: set[str] = set()
        for chunk in _chunks(qnames, _IN_CHUNK):
            placeholders = ", ".join("?" * len(chunk))
            rows = self._conn.execute(
                f"SELECT DISTINCT file_path FROM edges WHERE target_qname IN ({placeholders})",
                tuple(chunk),
            )
            found.update(str(row[0]) for row in rows)
        return tuple(sorted(found))

    def search_nodes(
        self,
        query: str,
        *,
        kind: str | None = None,
        namespace: str | None = None,
        limit: int,
        offset: int = 0,
    ) -> list[Row]:
        """Search symbols by FTS (trigram) or, for queries shorter than 3 chars, name prefix.

        Trigram FTS cannot match terms under three characters, so short queries use a
        ``name``/``qualified_name`` prefix ``LIKE`` instead (restores ``DB`` / ``Us`` / ``Go``).

        Optional ``namespace`` is matched case-insensitively: exact or continues
        with ``\\``, ``.``, or ``::``. ``offset`` pages in search order (task 057).
        """
        if len(query) < 3:
            return self._search_short(
                query, kind=kind, namespace=namespace, limit=limit, offset=offset
            )
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        where, params = self._fts_search_clause(query, kind=kind, namespace=namespace)
        sql = (
            f"SELECT nodes.id, {_NODE_COLUMNS_JOINED} FROM nodes "
            f"JOIN nodes_fts ON nodes_fts.rowid = nodes.id "
            f"WHERE {where} ORDER BY {_SEARCH_ORDER} LIMIT ? OFFSET ?"
        )
        return self._rows(NODE_ROW_KEYS, sql, (*params, limit, offset))

    def count_search_nodes(
        self,
        query: str,
        *,
        kind: str | None = None,
        namespace: str | None = None,
    ) -> int:
        """Exact hit count for ``search_nodes`` filters (no LIMIT)."""
        if len(query) < 3:
            return self._count_search_short(query, kind=kind, namespace=namespace)
        where, params = self._fts_search_clause(query, kind=kind, namespace=namespace)
        sql = (
            f"SELECT COUNT(*) FROM nodes "
            f"JOIN nodes_fts ON nodes_fts.rowid = nodes.id "
            f"WHERE {where}"
        )
        return int(self._conn.execute(sql, params).fetchone()[0])

    def _fts_search_clause(
        self,
        query: str,
        *,
        kind: str | None,
        namespace: str | None,
    ) -> tuple[str, tuple[object, ...]]:
        where, params = _narrow("nodes_fts MATCH ?", fts_term(query), kind, "nodes.kind = ?")
        return _with_namespace(where, params, namespace, qname_column="nodes.qualified_name")

    def impact_radius(
        self, seeds: Sequence[str], *, depth: int, max_nodes: int
    ) -> ImpactResult:
        """Bounded best-score blast radius via iterative SQL waves (§12).

        Walks **incoming** edges of impact kinds (callers / subtypes / includers). All
        tiers appear in the result; only ``RESOLVED`` expands the frontier (A2 / nav-013).
        Seeds outrank discovered nodes under the ``max_nodes`` prune. Temp tables live
        in a ``try/finally`` so a mid-wave error cannot leak them onto a long-lived store.
        """
        if depth < 0:
            raise ValueError(f"depth must be >= 0, got {depth}")
        if max_nodes < 1:
            raise ValueError(f"max_nodes must be >= 1, got {max_nodes}")
        ordered_seeds = list(dict.fromkeys(q for q in seeds if q))
        if not ordered_seeds:
            return ImpactResult([], 0, 0)

        conn = self._conn
        skipped = 0
        seeds_dropped = 0
        self._impact_drop_temps()
        try:
            conn.execute(
                "CREATE TEMP TABLE impact_best ("
                "qname TEXT PRIMARY KEY, score REAL NOT NULL, depth INT NOT NULL, "
                "file TEXT NOT NULL, line INT NOT NULL, "
                "confidence_tier TEXT NOT NULL, is_seed INT NOT NULL)"
            )
            conn.execute(
                "CREATE TEMP TABLE impact_frontier ("
                "qname TEXT PRIMARY KEY, score REAL NOT NULL, depth INT NOT NULL)"
            )
            conn.execute(
                "CREATE TEMP TABLE impact_weights ("
                "kind TEXT PRIMARY KEY, weight REAL NOT NULL)"
            )
            conn.executemany(
                "INSERT INTO temp.impact_weights (kind, weight) VALUES (?, ?)",
                [(kind, IMPACT_WEIGHTS[kind]) for kind in contract.IMPACT_KINDS],
            )

            seed_rows = [
                (q, 1.0, 0, *self._impact_node_loc(q), _RESOLVED, 1) for q in ordered_seeds
            ]
            conn.executemany(
                "INSERT INTO temp.impact_best "
                "(qname, score, depth, file, line, confidence_tier, is_seed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                seed_rows,
            )
            conn.executemany(
                "INSERT INTO temp.impact_frontier (qname, score, depth) VALUES (?, ?, ?)",
                [(q, 1.0, 0) for q in ordered_seeds],
            )
            if len(ordered_seeds) > max_nodes:
                seeds_dropped = len(ordered_seeds) - max_nodes
                self._impact_prune_best(max_nodes)
                conn.execute(
                    "DELETE FROM temp.impact_frontier WHERE qname NOT IN "
                    "(SELECT qname FROM temp.impact_best)"
                )

            expand_sql = (
                "INSERT INTO temp.impact_next (qname, score, depth, confidence_tier) "
                "SELECT e.source_qname, f.score * w.weight * ?, f.depth + 1, "
                "COALESCE(e.confidence_tier, ?) "
                "FROM temp.impact_frontier f "
                "JOIN edges e ON e.target_qname = f.qname "
                "JOIN temp.impact_weights w ON w.kind = e.kind "
                "WHERE e.target_qname IS NOT NULL "
                "AND f.score * w.weight * ? >= ?"
            )
            # Depth must come from a max-score row — never MIN(depth) across all paths (R4.2).
            merge_sql = (
                "INSERT INTO temp.impact_best "
                "(qname, score, depth, file, line, confidence_tier, is_seed) "
                "SELECT n.qname, n.score, n.depth, "
                "COALESCE(("
                "  SELECT nodes.file_path FROM nodes WHERE nodes.qualified_name = n.qname "
                "  ORDER BY nodes.file_path, nodes.line_start, nodes.id LIMIT 1"
                "), ''), "
                "COALESCE(("
                "  SELECT nodes.line_start FROM nodes WHERE nodes.qualified_name = n.qname "
                "  ORDER BY nodes.file_path, nodes.line_start, nodes.id LIMIT 1"
                "), 0), "
                "n.confidence_tier, 0 "
                "FROM ("
                "  SELECT nxt.qname AS qname, nxt.score AS score, "
                "  MIN(nxt.depth) AS depth, "
                "  MAX(nxt.confidence_tier) AS confidence_tier "
                "  FROM temp.impact_next AS nxt "
                "  JOIN ("
                "    SELECT qname, MAX(score) AS score FROM temp.impact_next GROUP BY qname"
                "  ) AS top ON top.qname = nxt.qname AND top.score = nxt.score "
                "  GROUP BY nxt.qname"
                ") AS n "
                "WHERE n.score >= ? "
                "ON CONFLICT(qname) DO UPDATE SET "
                "score = excluded.score, depth = excluded.depth, "
                "file = excluded.file, line = excluded.line, "
                "confidence_tier = excluded.confidence_tier "
                "WHERE excluded.score > impact_best.score"
            )
            # Only RESOLVED neighbors whose score matches the retained best join the frontier.
            refill_frontier_sql = (
                "INSERT INTO temp.impact_frontier (qname, score, depth) "
                "SELECT b.qname, b.score, b.depth FROM temp.impact_best b "
                "JOIN ("
                "  SELECT qname, MAX(score) AS score FROM temp.impact_next "
                "  WHERE confidence_tier = ? GROUP BY qname"
                ") AS n ON n.qname = b.qname AND n.score = b.score"
            )

            for _hop in range(depth):
                empty = conn.execute(
                    "SELECT 1 FROM temp.impact_frontier LIMIT 1"
                ).fetchone()
                if empty is None:
                    break
                conn.execute("DROP TABLE IF EXISTS temp.impact_next")
                conn.execute(
                    "CREATE TEMP TABLE impact_next ("
                    "qname TEXT NOT NULL, score REAL NOT NULL, depth INT NOT NULL, "
                    "confidence_tier TEXT NOT NULL)"
                )
                conn.execute(
                    expand_sql, (IMPACT_DECAY, _RESOLVED, IMPACT_DECAY, IMPACT_FLOOR)
                )
                skipped += int(
                    conn.execute(
                        "SELECT COUNT(*) FROM ("
                        "  SELECT DISTINCT qname FROM temp.impact_next "
                        "  WHERE confidence_tier != ?"
                        ")",
                        (_RESOLVED,),
                    ).fetchone()[0]
                )
                conn.execute(merge_sql, (IMPACT_FLOOR,))
                self._impact_prune_best(max_nodes)
                conn.execute("DELETE FROM temp.impact_frontier")
                conn.execute(refill_frontier_sql, (_RESOLVED,))
                conn.execute(
                    "DELETE FROM temp.impact_frontier WHERE qname NOT IN "
                    "(SELECT qname FROM temp.impact_best)"
                )

            keys = ("qname", "score", "depth", "file") + contract.EDGE_FIELDS[5:7]
            rows = self._rows(
                keys,
                "SELECT qname, score, depth, file, line, confidence_tier "
                "FROM temp.impact_best "
                "ORDER BY is_seed DESC, score DESC, qname ASC LIMIT ?",
                (max_nodes,),
            )
            return ImpactResult(rows, skipped, seeds_dropped)
        finally:
            self._impact_drop_temps()

    def reachable_from(
        self,
        seeds: Sequence[str],
        *,
        depth: int | None,
        max_nodes: int,
        retain_temps: bool = False,
    ) -> ReachabilityResult:
        """Bounded forward reachability over outgoing IMPACT_KINDS (task 031).

        ``depth=None`` walks until the frontier empties or ``max_nodes`` binds (closure).
        Only ``RESOLVED`` edges expand the frontier. HEURISTIC/DYNAMIC neighbors are
        recorded as unproven and never expand. A reached member keeps its container
        qnames alive via :func:`contract.split_qname` (no CONTAINS expand).
        """
        if depth is not None and depth < 0:
            raise ValueError(f"depth must be >= 0, got {depth}")
        if max_nodes < 1:
            raise ValueError(f"max_nodes must be >= 1, got {max_nodes}")
        ordered_seeds = list(dict.fromkeys(q for q in seeds if q))
        if not ordered_seeds:
            return ReachabilityResult([], [], 0, False, False)

        conn = self._conn
        self._reach_drop_temps()
        try:
            conn.execute(
                "CREATE TEMP TABLE reach_seen ("
                "qname TEXT PRIMARY KEY, depth INT NOT NULL, is_seed INT NOT NULL)"
            )
            conn.execute(
                "CREATE TEMP TABLE reach_frontier (qname TEXT PRIMARY KEY, depth INT NOT NULL)"
            )
            conn.execute("CREATE TEMP TABLE reach_kinds (kind TEXT PRIMARY KEY)")
            conn.execute(
                "CREATE TEMP TABLE reach_unproven ("
                "qname TEXT PRIMARY KEY, confidence_tier TEXT NOT NULL)"
            )
            conn.executemany(
                "INSERT INTO temp.reach_kinds (kind) VALUES (?)",
                [(kind,) for kind in contract.IMPACT_KINDS],
            )
            conn.executemany(
                "INSERT INTO temp.reach_seen (qname, depth, is_seed) VALUES (?, 0, 1)",
                [(q,) for q in ordered_seeds],
            )
            conn.executemany(
                "INSERT INTO temp.reach_frontier (qname, depth) VALUES (?, 0)",
                [(q,) for q in ordered_seeds],
            )
            if len(ordered_seeds) > max_nodes:
                self._reach_prune_seen(max_nodes)
                conn.execute(
                    "DELETE FROM temp.reach_frontier WHERE qname NOT IN "
                    "(SELECT qname FROM temp.reach_seen)"
                )

            expand_sql = (
                "INSERT INTO temp.reach_next (qname, depth, confidence_tier) "
                "SELECT e.target_qname, f.depth + 1, COALESCE(e.confidence_tier, ?) "
                "FROM temp.reach_frontier f "
                "JOIN edges e ON e.source_qname = f.qname "
                "JOIN temp.reach_kinds k ON k.kind = e.kind "
                "WHERE e.target_qname IS NOT NULL"
            )

            hop = 0
            while True:
                if depth is not None and hop >= depth:
                    break
                empty = conn.execute(
                    "SELECT 1 FROM temp.reach_frontier LIMIT 1"
                ).fetchone()
                if empty is None:
                    break
                conn.execute("DROP TABLE IF EXISTS temp.reach_next")
                conn.execute(
                    "CREATE TEMP TABLE reach_next ("
                    "qname TEXT NOT NULL, depth INT NOT NULL, confidence_tier TEXT NOT NULL)"
                )
                conn.execute(expand_sql, (_RESOLVED,))
                conn.execute(
                    "INSERT OR IGNORE INTO temp.reach_unproven (qname, confidence_tier) "
                    "SELECT n.qname, n.confidence_tier FROM temp.reach_next n "
                    "WHERE n.confidence_tier != ? "
                    "AND n.qname NOT IN (SELECT qname FROM temp.reach_seen)",
                    (_RESOLVED,),
                )
                # Only newly admitted nodes expand next hop (cycles must not re-queue forever).
                conn.execute("DROP TABLE IF EXISTS temp.reach_before")
                conn.execute(
                    "CREATE TEMP TABLE reach_before AS SELECT qname FROM temp.reach_seen"
                )
                conn.execute(
                    "INSERT OR IGNORE INTO temp.reach_seen (qname, depth, is_seed) "
                    "SELECT n.qname, MIN(n.depth), 0 FROM temp.reach_next n "
                    "WHERE n.confidence_tier = ? "
                    "GROUP BY n.qname",
                    (_RESOLVED,),
                )
                self._reach_prune_seen(max_nodes)
                conn.execute("DELETE FROM temp.reach_frontier")
                conn.execute(
                    "INSERT INTO temp.reach_frontier (qname, depth) "
                    "SELECT s.qname, s.depth FROM temp.reach_seen s "
                    "WHERE s.qname NOT IN (SELECT qname FROM temp.reach_before)"
                )
                conn.execute(
                    "DELETE FROM temp.reach_frontier WHERE qname NOT IN "
                    "(SELECT qname FROM temp.reach_seen)"
                )
                conn.execute(
                    "DELETE FROM temp.reach_unproven WHERE qname IN "
                    "(SELECT qname FROM temp.reach_seen)"
                )
                hop += 1

            # Live member → keep its containers (class/interface) out of the orphan set.
            for qname, member_depth in conn.execute(
                "SELECT qname, depth FROM temp.reach_seen"
            ).fetchall():
                container, _ = contract.split_qname(str(qname))
                while container is not None:
                    conn.execute(
                        "INSERT OR IGNORE INTO temp.reach_seen "
                        "(qname, depth, is_seed) VALUES (?, ?, 0)",
                        (container, member_depth),
                    )
                    container, _ = contract.split_qname(container)

            depth_exhausted = (
                depth is not None
                and conn.execute(
                    "SELECT 1 FROM temp.reach_frontier LIMIT 1"
                ).fetchone()
                is not None
            )
            seen_count = int(
                conn.execute("SELECT COUNT(*) FROM temp.reach_seen").fetchone()[0]
            )
            unproven_total = int(
                conn.execute("SELECT COUNT(*) FROM temp.reach_unproven").fetchone()[0]
            )
            truncated = (
                depth_exhausted or seen_count >= max_nodes or unproven_total > max_nodes
            )
            # Distinct non-RESOLVED nodes (matches reach_unproven), not per-hop encounters.
            skipped = unproven_total

            # Key tuples keep ≤1 contract vocab string per literal (R3.2 sole-source gate).
            reachable = self._rows(
                ("qname", "depth", "file") + ("kind",) + ("line",),
                "SELECT s.qname, s.depth, "
                "COALESCE(("
                "  SELECT nodes.file_path FROM nodes WHERE nodes.qualified_name = s.qname "
                "  ORDER BY nodes.file_path, nodes.line_start, nodes.id LIMIT 1"
                "), ''), "
                "COALESCE(("
                "  SELECT nodes.kind FROM nodes WHERE nodes.qualified_name = s.qname "
                "  ORDER BY nodes.file_path, nodes.line_start, nodes.id LIMIT 1"
                "), ''), "
                "COALESCE(("
                "  SELECT nodes.line_start FROM nodes WHERE nodes.qualified_name = s.qname "
                "  ORDER BY nodes.file_path, nodes.line_start, nodes.id LIMIT 1"
                "), 0) "
                "FROM temp.reach_seen s "
                "ORDER BY s.is_seed DESC, s.depth ASC, s.qname ASC LIMIT ?",
                (max_nodes,),
            )
            unproven = self._rows(
                ("qname",) + ("confidence_tier",) + ("file",) + ("kind",) + ("line",),
                "SELECT u.qname, u.confidence_tier, "
                "COALESCE(("
                "  SELECT nodes.file_path FROM nodes WHERE nodes.qualified_name = u.qname "
                "  ORDER BY nodes.file_path, nodes.line_start, nodes.id LIMIT 1"
                "), ''), "
                "COALESCE(("
                "  SELECT nodes.kind FROM nodes WHERE nodes.qualified_name = u.qname "
                "  ORDER BY nodes.file_path, nodes.line_start, nodes.id LIMIT 1"
                "), ''), "
                "COALESCE(("
                "  SELECT nodes.line_start FROM nodes WHERE nodes.qualified_name = u.qname "
                "  ORDER BY nodes.file_path, nodes.line_start, nodes.id LIMIT 1"
                "), 0) "
                "FROM temp.reach_unproven u "
                "ORDER BY u.qname ASC LIMIT ?",
                (max_nodes,),
            )
            return ReachabilityResult(
                reachable, unproven, skipped, truncated, depth_exhausted
            )
        finally:
            if not retain_temps:
                self._reach_drop_temps()

    def find_orphans(
        self, seeds: Sequence[str], *, depth: int | None, max_nodes: int
    ) -> OrphanResult:
        """Orphans = indexed nodes outside reachable∪unproven∪seeds, with why (task 031)."""
        reach = self.reachable_from(
            seeds, depth=depth, max_nodes=max_nodes, retain_temps=True
        )
        conn = self._conn
        conn.execute("DROP TABLE IF EXISTS temp.reach_excluded")
        try:
            conn.execute("CREATE TEMP TABLE reach_excluded (qname TEXT PRIMARY KEY)")
            # Full temp sets — not the LIMITed row lists — so overflow unproven stay excluded.
            conn.execute(
                "INSERT OR IGNORE INTO temp.reach_excluded (qname) "
                "SELECT qname FROM temp.reach_seen"
            )
            conn.execute(
                "INSERT OR IGNORE INTO temp.reach_excluded (qname) "
                "SELECT qname FROM temp.reach_unproven"
            )
            for qname in seeds:
                if qname:
                    conn.execute(
                        "INSERT OR IGNORE INTO temp.reach_excluded (qname) VALUES (?)",
                        (qname,),
                    )
            kind_placeholders = ", ".join("?" for _ in contract.IMPACT_KINDS)
            sql = (
                "SELECT n.qualified_name AS qname, n.kind, n.file_path AS file, "
                "n.line_start, "
                "CASE WHEN NOT EXISTS ("
                "  SELECT 1 FROM edges e "
                f"  WHERE e.target_qname = n.qualified_name AND e.kind IN ({kind_placeholders}) "
                "  AND e.target_qname IS NOT NULL"
                ") THEN 'no_inbound' ELSE 'unreachable_from_roots' END AS why "
                "FROM nodes n "
                "WHERE n.qualified_name NOT IN (SELECT qname FROM temp.reach_excluded) "
                "ORDER BY n.qualified_name ASC, n.file_path ASC, n.line_start ASC, n.id ASC "
                "LIMIT ?"
            )
            rows = self._rows(
                ("qname", "kind") + ("file", "line_start", "why"),
                sql,
                (*contract.IMPACT_KINDS, max_nodes),
            )
            orphan_total = int(
                conn.execute(
                    "SELECT COUNT(*) FROM nodes n "
                    "WHERE n.qualified_name NOT IN (SELECT qname FROM temp.reach_excluded)"
                ).fetchone()[0]
            )
            orphans: list[Row] = []
            for row in rows:
                item: Row = {
                    "qname": row["qname"],
                    "file": row["file"],
                    "why": row["why"],
                }
                item["kind"] = row["kind"]
                item["line"] = row["line_start"]
                orphans.append(item)
            truncated = reach.truncated or orphan_total > max_nodes
            return OrphanResult(
                orphans, reach.unproven, truncated, reach.depth_exhausted
            )
        finally:
            conn.execute("DROP TABLE IF EXISTS temp.reach_excluded")
            self._reach_drop_temps()

    def explain_path(
        self,
        from_qname: str,
        to_qname: str,
        *,
        depth: int | None,
        max_nodes: int,
    ) -> ExplainPathResult:
        """Bounded shortest path A→B over outgoing IMPACT_KINDS (task 038).

        RESOLVED-first: a proven path is preferred. If none exists within the bound but
        a HEURISTIC/DYNAMIC path does, status is ``unproven``. Bound exhaustion before
        finding ``to`` is ``incomplete``, never ``no_path``. Missing endpoints →
        ``unknown``. Traversal is iterative SQL waves joined from the frontier — never
        a whole-table edge load (R4.3).
        """
        if depth is not None and depth < 0:
            raise ValueError(f"depth must be >= 0, got {depth}")
        if max_nodes < 1:
            raise ValueError(f"max_nodes must be >= 1, got {max_nodes}")
        if not from_qname or not to_qname:
            return ExplainPathResult(PATH_STATUS_UNKNOWN, [], False, False)
        if not self.nodes_by_qualified_name(from_qname, limit=1):
            return ExplainPathResult(PATH_STATUS_UNKNOWN, [], False, False)
        if not self.nodes_by_qualified_name(to_qname, limit=1):
            return ExplainPathResult(PATH_STATUS_UNKNOWN, [], False, False)
        if from_qname == to_qname:
            return ExplainPathResult(PATH_STATUS_PATH, [], False, False)

        proven = self._explain_path_search(
            from_qname, to_qname, depth=depth, max_nodes=max_nodes, resolved_only=True
        )
        if proven.status == PATH_STATUS_PATH:
            return proven
        # Node-budget overflow generalises (proven ⊆ mixed); depth exhaustion does not —
        # a HEURISTIC hop may still reach ``to`` inside the same depth.
        if proven.status == PATH_STATUS_INCOMPLETE and not proven.depth_exhausted:
            return proven
        unproven = self._explain_path_search(
            from_qname, to_qname, depth=depth, max_nodes=max_nodes, resolved_only=False
        )
        if unproven.status == PATH_STATUS_PATH:
            return ExplainPathResult(
                PATH_STATUS_UNPROVEN,
                unproven.hops,
                unproven.truncated,
                unproven.depth_exhausted,
            )
        # Prefer honest incomplete over a false no_path when the proven pass was budget-bound.
        if unproven.status == PATH_STATUS_NO_PATH and proven.status == PATH_STATUS_INCOMPLETE:
            return proven
        return unproven

    def _explain_path_search(
        self,
        from_qname: str,
        to_qname: str,
        *,
        depth: int | None,
        max_nodes: int,
        resolved_only: bool,
    ) -> ExplainPathResult:
        """One BFS pass; ``resolved_only`` gates which tiers expand the frontier."""
        conn = self._conn
        self._path_drop_temps()
        try:
            conn.execute(
                "CREATE TEMP TABLE path_seen ("
                "qname TEXT PRIMARY KEY, depth INT NOT NULL, "
                "prev_qname TEXT, edge_kind TEXT, edge_tier TEXT, "
                "edge_file TEXT, edge_line INT)"
            )
            conn.execute(
                "CREATE TEMP TABLE path_frontier (qname TEXT PRIMARY KEY, depth INT NOT NULL)"
            )
            conn.execute("CREATE TEMP TABLE path_kinds (kind TEXT PRIMARY KEY)")
            conn.executemany(
                "INSERT INTO temp.path_kinds (kind) VALUES (?)",
                [(kind,) for kind in contract.IMPACT_KINDS],
            )
            conn.execute(
                "INSERT INTO temp.path_seen "
                "(qname, depth, prev_qname, edge_kind, edge_tier, edge_file, edge_line) "
                "VALUES (?, 0, NULL, NULL, NULL, NULL, NULL)",
                (from_qname,),
            )
            conn.execute(
                "INSERT INTO temp.path_frontier (qname, depth) VALUES (?, 0)",
                (from_qname,),
            )

            expand_sql = (
                "INSERT OR IGNORE INTO temp.path_seen "
                "(qname, depth, prev_qname, edge_kind, edge_tier, edge_file, edge_line) "
                "SELECT qname, depth, prev_qname, edge_kind, edge_tier, edge_file, edge_line "
                "FROM ("
                "  SELECT e.target_qname AS qname, f.depth + 1 AS depth, "
                "  f.qname AS prev_qname, e.kind AS edge_kind, "
                "  COALESCE(e.confidence_tier, ?) AS edge_tier, "
                "  e.file_path AS edge_file, e.line AS edge_line, "
                "  ROW_NUMBER() OVER ("
                "    PARTITION BY e.target_qname "
                "    ORDER BY e.kind ASC, e.source_qname ASC, e.file_path ASC, "
                "    e.line ASC, e.id ASC"
                "  ) AS rn "
                "  FROM temp.path_frontier f "
                "  JOIN edges e ON e.source_qname = f.qname "
                "  JOIN temp.path_kinds k ON k.kind = e.kind "
                "  WHERE e.target_qname IS NOT NULL"
                f"{' AND COALESCE(e.confidence_tier, ?) = ?' if resolved_only else ''}"
                ") WHERE rn = 1"
            )

            hop = 0
            depth_exhausted = False
            truncated = False
            while True:
                if depth is not None and hop >= depth:
                    depth_exhausted = (
                        conn.execute(
                            "SELECT 1 FROM temp.path_frontier LIMIT 1"
                        ).fetchone()
                        is not None
                    )
                    break
                empty = conn.execute(
                    "SELECT 1 FROM temp.path_frontier LIMIT 1"
                ).fetchone()
                if empty is None:
                    break
                if (
                    conn.execute(
                        "SELECT 1 FROM temp.path_seen WHERE qname = ? LIMIT 1",
                        (to_qname,),
                    ).fetchone()
                    is not None
                ):
                    break

                conn.execute("DROP TABLE IF EXISTS temp.path_before")
                conn.execute(
                    "CREATE TEMP TABLE path_before AS SELECT qname FROM temp.path_seen"
                )
                params: tuple[object, ...] = (_RESOLVED,)
                if resolved_only:
                    params = (_RESOLVED, _RESOLVED, _RESOLVED)
                conn.execute(expand_sql, params)

                seen_count = int(
                    conn.execute("SELECT COUNT(*) FROM temp.path_seen").fetchone()[0]
                )
                if seen_count > max_nodes:
                    self._path_prune_seen(max_nodes)
                    if (
                        conn.execute(
                            "SELECT 1 FROM temp.path_seen WHERE qname = ? LIMIT 1",
                            (to_qname,),
                        ).fetchone()
                        is None
                    ):
                        truncated = True
                        break

                conn.execute("DELETE FROM temp.path_frontier")
                conn.execute(
                    "INSERT INTO temp.path_frontier (qname, depth) "
                    "SELECT s.qname, s.depth FROM temp.path_seen s "
                    "WHERE s.qname NOT IN (SELECT qname FROM temp.path_before)"
                )
                hop += 1

            if truncated or (
                depth_exhausted
                and conn.execute(
                    "SELECT 1 FROM temp.path_seen WHERE qname = ? LIMIT 1",
                    (to_qname,),
                ).fetchone()
                is None
            ):
                return ExplainPathResult(
                    PATH_STATUS_INCOMPLETE, [], truncated or depth_exhausted, depth_exhausted
                )

            if (
                conn.execute(
                    "SELECT 1 FROM temp.path_seen WHERE qname = ? LIMIT 1",
                    (to_qname,),
                ).fetchone()
                is None
            ):
                return ExplainPathResult(PATH_STATUS_NO_PATH, [], False, False)

            hops = self._path_reconstruct(from_qname, to_qname)
            return ExplainPathResult(PATH_STATUS_PATH, hops, False, False)
        finally:
            self._path_drop_temps()

    def _path_reconstruct(self, from_qname: str, to_qname: str) -> list[Row]:
        """Walk ``prev_qname`` from ``to`` back to ``from``; reverse into forward hops."""
        hops_rev: list[Row] = []
        current = to_qname
        while current != from_qname:
            row = self._conn.execute(
                "SELECT prev_qname, edge_kind, edge_tier, edge_file, edge_line "
                "FROM temp.path_seen WHERE qname = ?",
                (current,),
            ).fetchone()
            if row is None or row[0] is None:
                break
            prev, kind, tier, file_path, line = row
            # One EDGE_FIELDS key per statement — R3.2 sole-source gate.
            hop: Row = {}
            hop["source_qname"] = prev
            hop["target_qname"] = current
            hop["kind"] = kind
            hop["confidence_tier"] = tier or _RESOLVED
            hop["file"] = file_path or ""
            hop["line"] = line or 0
            hops_rev.append(hop)
            current = str(prev)
        hops_rev.reverse()
        return hops_rev

    def _path_drop_temps(self) -> None:
        for name in (
            "path_seen",
            "path_frontier",
            "path_kinds",
            "path_before",
        ):
            self._conn.execute(f"DROP TABLE IF EXISTS temp.{name}")

    def _path_prune_seen(self, max_nodes: int) -> None:
        """Keep shallowest nodes (tie: qname ASC) when the visit budget binds."""
        self._conn.execute(
            "DELETE FROM temp.path_seen WHERE qname NOT IN ("
            "  SELECT qname FROM ("
            "    SELECT qname FROM temp.path_seen "
            "    ORDER BY depth ASC, qname ASC LIMIT ?"
            "  )"
            ")",
            (max_nodes,),
        )

    def _reach_drop_temps(self) -> None:
        for name in (
            "reach_seen",
            "reach_frontier",
            "reach_kinds",
            "reach_unproven",
            "reach_next",
            "reach_before",
        ):
            self._conn.execute(f"DROP TABLE IF EXISTS temp.{name}")

    def _reach_prune_seen(self, max_nodes: int) -> None:
        """Keep seeds preferentially, then shallowest depth (tie: qname ASC)."""
        self._conn.execute(
            "DELETE FROM temp.reach_seen WHERE qname NOT IN ("
            "  SELECT qname FROM ("
            "    SELECT qname FROM temp.reach_seen "
            "    ORDER BY is_seed DESC, depth ASC, qname ASC LIMIT ?"
            "  )"
            ")",
            (max_nodes,),
        )

    def _impact_drop_temps(self) -> None:
        for name in (
            "impact_best",
            "impact_frontier",
            "impact_weights",
            "impact_next",
        ):
            self._conn.execute(f"DROP TABLE IF EXISTS temp.{name}")

    def _impact_prune_best(self, max_nodes: int) -> None:
        """Keep seeds preferentially, then highest score (tie: qname ASC)."""
        self._conn.execute(
            "DELETE FROM temp.impact_best WHERE qname NOT IN ("
            "  SELECT qname FROM ("
            "    SELECT qname FROM temp.impact_best "
            "    ORDER BY is_seed DESC, score DESC, qname ASC LIMIT ?"
            "  )"
            ")",
            (max_nodes,),
        )

    def nodes_by_file_all(self, path: str) -> list[Row]:
        """Every node on ``path`` (impact path seeds — no silent row cap)."""
        sql = (
            f"SELECT id, {_NODE_COLUMNS} FROM nodes WHERE file_path = ? "
            f"ORDER BY {_NODE_ORDER}"
        )
        return self._rows(NODE_ROW_KEYS, sql, (path,))

    def _impact_node_loc(self, qname: str) -> tuple[str, int]:
        """Pick one node's file/line for ``qname`` (same order as merge_sql subqueries)."""
        rows = self.nodes_by_qualified_name(qname, limit=1)
        if not rows:
            return ("", 0)
        line = rows[0]["line_start"]
        return (str(rows[0]["file_path"]), line if isinstance(line, int) else 0)

    def _search_short(
        self,
        query: str,
        *,
        kind: str | None,
        namespace: str | None,
        limit: int,
        offset: int = 0,
    ) -> list[Row]:
        """Prefix match on ``name`` / ``qualified_name`` when trigram FTS cannot help."""
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        pattern = f"{_like_literal(query.lower())}%"
        where = "(LOWER(name) LIKE ? ESCAPE '!' OR LOWER(qualified_name) LIKE ? ESCAPE '!')"
        params: tuple[object, ...] = (pattern, pattern)
        if kind is not None:
            where = f"{where} AND kind = ?"
            params = (*params, kind)
        where, params = _with_namespace(where, params, namespace, qname_column="qualified_name")
        sql = (
            f"SELECT id, {_NODE_COLUMNS} FROM nodes WHERE {where} "
            f"ORDER BY {_NODE_ORDER} LIMIT ? OFFSET ?"
        )
        return self._rows(NODE_ROW_KEYS, sql, (*params, limit, offset))

    def _nodes(self, where: str, value: str, kind: str | None, limit: int) -> list[Row]:
        clause, params = _narrow(where, value, kind, "kind = ?")
        sql = f"SELECT id, {_NODE_COLUMNS} FROM nodes WHERE {clause} ORDER BY {_NODE_ORDER} LIMIT ?"
        return self._rows(NODE_ROW_KEYS, sql, (*params, limit))

    def _nodes_batched(
        self,
        *,
        key_column: str,
        keys: Sequence[str],
        kind: str | None,
        limit: int,
    ) -> dict[str, list[Row]]:
        """Per-key top-N via ``ROW_NUMBER``; keys chunked under ``_IN_CHUNK`` (host max-vars)."""
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        # Keep checks as separate comparisons — a 2-string Literal/tuple trips R3.2.
        if key_column != "name" and key_column != "qualified_name":
            raise ValueError(f"unsupported batch column: {key_column}")
        # Dedupe while preserving first-seen order so empty IN () never runs.
        ordered_keys: list[str] = list(dict.fromkeys(keys))
        if not ordered_keys:
            return {}
        kind_sql = " AND kind = ?" if kind is not None else ""
        grouped: dict[str, list[Row]] = {key: [] for key in ordered_keys}
        # Full `_NODE_ORDER` inside the partition — required for `name` keys where
        # `qualified_name` still varies within the partition (R4.2 / AC1).
        for chunk in _chunks(ordered_keys, _IN_CHUNK):
            placeholders = ", ".join("?" for _ in chunk)
            sql = (
                f"SELECT id, {_NODE_COLUMNS} FROM ("
                f"  SELECT id, {_NODE_COLUMNS}, "
                f"    ROW_NUMBER() OVER ("
                f"      PARTITION BY {key_column} ORDER BY {_NODE_ORDER}"
                f"    ) AS rn "
                f"  FROM nodes WHERE {key_column} IN ({placeholders}){kind_sql}"
                f") WHERE rn <= ? "
                f"ORDER BY {_NODE_ORDER}"
            )
            params: list[object] = [*chunk]
            if kind is not None:
                params.append(kind)
            params.append(limit)
            for row in self._rows(NODE_ROW_KEYS, sql, params):
                grouped[str(row[key_column])].append(row)
        return grouped

    def _edges(
        self,
        where: str,
        value: str,
        kinds: Sequence[str] | None,
        limit: int,
        *,
        offset: int = 0,
        extra: _Predicate = None,
    ) -> list[Row]:
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        clause, params = self._edge_where(where, kinds, extra)
        sql = (
            f"SELECT id, {_EDGE_COLUMNS} FROM edges WHERE {clause} "
            f"ORDER BY {_EDGE_ORDER} LIMIT ? OFFSET ?"
        )
        return self._rows(EDGE_ROW_KEYS, sql, (value, *params, limit, offset))

    def _count_edges(
        self,
        where: str,
        value: str,
        kinds: Sequence[str] | None,
        *,
        extra: _Predicate = None,
    ) -> int:
        clause, params = self._edge_where(where, kinds, extra)
        sql = f"SELECT COUNT(*) FROM edges WHERE {clause}"
        return int(self._conn.execute(sql, (value, *params)).fetchone()[0])

    @staticmethod
    def _edge_where(
        where: str, kinds: Sequence[str] | None, extra: _Predicate
    ) -> tuple[str, tuple[object, ...]]:
        """One WHERE builder for both the row read and its count, so they cannot diverge."""
        clauses: list[str] = [where]
        params: list[object] = []
        if kinds is not None:
            if not kinds:
                raise ValueError("kinds must be non-empty")
            clauses.append(f"kind IN ({', '.join('?' for _ in kinds)})")
            params.extend(kinds)
        if extra is not None:
            clauses.append(extra[0])
            params.extend(extra[1])
        return " AND ".join(clauses), tuple(params)

    def _count_search_short(
        self,
        query: str,
        *,
        kind: str | None,
        namespace: str | None,
    ) -> int:
        pattern = f"{_like_literal(query.lower())}%"
        where = "(LOWER(name) LIKE ? ESCAPE '!' OR LOWER(qualified_name) LIKE ? ESCAPE '!')"
        params: tuple[object, ...] = (pattern, pattern)
        if kind is not None:
            where = f"{where} AND kind = ?"
            params = (*params, kind)
        where, params = _with_namespace(where, params, namespace, qname_column="qualified_name")
        sql = f"SELECT COUNT(*) FROM nodes WHERE {where}"
        return int(self._conn.execute(sql, params).fetchone()[0])

    def _rows(self, keys: tuple[str, ...], sql: str, params: Sequence[object]) -> list[Row]:
        cursor = self._conn.execute(sql, params)
        return [dict(zip(keys, row, strict=True)) for row in cursor]


def _dedupe_nodes(
    nodes: Iterable[Mapping[str, object]],
) -> tuple[list[Mapping[str, object]], int]:
    """Keep the first node per UNIQUE key ``(qualified_name, file_path)``; return survivors + drops.

    A caller may pass same-qname nodes for different files in one call (multi-candidate siblings),
    so the key must be the full UNIQUE key, not ``qualified_name`` alone. NULL/anonymous qnames are
    never collapsed — SQLite treats NULLs as distinct. Emit order is preserved (R4.2).
    """
    seen: set[tuple[object, object]] = set()
    kept: list[Mapping[str, object]] = []
    dropped = 0
    for node in nodes:
        qname = node.get("qualified_name")
        if qname is not None:
            key = (qname, node.get("file_path"))
            if key in seen:
                dropped += 1
                continue
            seen.add(key)
        kept.append(node)
    return kept, dropped


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


def _with_namespace(
    where: str,
    params: tuple[object, ...],
    namespace: str | None,
    *,
    qname_column: str,
) -> tuple[str, tuple[object, ...]]:
    """Case-insensitive namespace prefix (exact or segment boundary via ``\\`` / ``.`` / ``::``)."""
    if namespace is None:
        return where, params
    lowered = namespace.lower()
    escaped = _like_literal(lowered)
    clause = (
        f"(LOWER({qname_column}) = ? OR "
        f"LOWER({qname_column}) LIKE ? ESCAPE '!' OR "
        f"LOWER({qname_column}) LIKE ? ESCAPE '!' OR "
        f"LOWER({qname_column}) LIKE ? ESCAPE '!')"
    )
    return f"({where}) AND {clause}", (
        *params,
        lowered,
        f"{escaped}\\%",
        f"{escaped}.%",
        f"{escaped}::%",
    )
