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

import atexit
import contextlib
import json
import sqlite3
import threading
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

from code_atlas import contract
from code_atlas.contract import CONFIDENCE_TIERS

# A quarter of the tour budget may go to roots, so the walk always has room to expand
# (task 106: 8,477 entry points against a 500 budget left zero room and zero edges).
_TOUR_SEED_BUDGET_DIVISOR = 4

SCHEMA_VERSION = "6"
SCHEMA_VERSION_KEY = "schema_version"
CONTRACT_VERSION_KEY = "contract_version"
LAST_COMMIT_KEY = "last_commit"
# Human ref the index was built on (branch name or ``HEAD`` when detached) — beside the SHA (077).
LAST_REF_KEY = "last_ref"
BUILT_AT_KEY = "built_at"
# Completeness, not liveness (task 178). Cleared to "0" when a build starts writing and set to "1"
# only after the late writes have linked the graph, so a build that dies mid-link leaves "0" —
# a surviving *negative* claim is honest, unlike a surviving "building: true".
BUILD_COMPLETE_KEY = "build_complete"
BUILD_COMPLETE = "1"
BUILD_INCOMPLETE = "0"
# Which suffixes the build claimed. Only the adapter handshake knows them, and a status read must
# not start an adapter to find out — so the build leaves them here (047).
INDEXED_SUFFIXES_KEY = "indexed_suffixes"
# What the graph actually HOLDS, as against the claimed scope above (task 173). Computed once per
# build and read from meta, so a zero answer never pays a scan of ``files`` to know its own gaps.
COVERED_SUFFIXES_KEY = "covered_suffixes"
COVERED_LANGUAGES_KEY = "covered_languages"
# The collect walk's by-cause tally (JSON), so verbose status can publish the denominator an
# outsider reconciles ``files`` against without a second traversal (task 082).
COLLECTION_CENSUS_KEY = "collection_census"
# Indexable-suffix, not-ignored untracked paths (JSON list) — separate from the int census (092).
UNTRACKED_INDEXABLE_KEY = "untracked_indexable"
# Per-source ignore counts (JSON object) — sibling of the int census; that reader int-casts (095).
IGNORE_SOURCES_KEY = "ignore_sources"
# What `skipped_suffix` is MADE OF, by extension (JSON object, task 174). Its own key, never inside
# the census structure: `collection_census()` int-casts every value, and widening that coercing
# reader would trade a total contract for a conditional one (R1.7).
SKIPPED_SUFFIX_COUNTS_KEY = "skipped_suffix_counts"
# Which CONFIG built this index (task 175) — a different claim from which config is running now.
# 164 stamped which code answered; the index could not say which config produced its contents.
CONFIG_IDENTITY_KEY = "config_identity"
# The tier mix split by the language of the edge's own file (JSON, task 183). Stamped once per
# build because a whole-graph blend cannot be attributed to any one adapter, and a GROUP BY over
# the edge table must never reach the per-answer path.
EDGE_HEALTH_BY_LANGUAGE_KEY = "edge_health_by_language"
# Which edge kinds each language has ever emitted (JSON, task 186). Same scan as the tier mix above,
# because "is this relation absent for this file's language?" is a data question the core may ask
# without knowing what any language is (R1.1) — and a language name in the core is forbidden.
EMITTED_KINDS_BY_LANGUAGE_KEY = "emitted_kinds_by_language"
# Resolution strategies File.extra named as unmodelled, unioned per language (JSON, task 279).
UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY = "unmodelled_resolution_by_language"
CAPABILITIES_BY_LANGUAGE_KEY = "capabilities_by_language"
# Each adapter's suffixes and grep shapes from the last build, for the grep-time nudge (345).
SYMBOL_SHAPES_BY_LANGUAGE_KEY = "symbol_shapes_by_language"
# Local fit counters (task 260): one meta row per (tool, reason, authoritative, truncated).
FIT_KEY_PREFIX = "fit:"
META_KEYS: tuple[str, ...] = (
    SCHEMA_VERSION_KEY,
    CONTRACT_VERSION_KEY,
    LAST_COMMIT_KEY,
    LAST_REF_KEY,
    BUILT_AT_KEY,
    INDEXED_SUFFIXES_KEY,
    COLLECTION_CENSUS_KEY,
    UNTRACKED_INDEXABLE_KEY,
    IGNORE_SOURCES_KEY,
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

# A full rebuild fills this file, then publishes it over the live index in one transaction (356).
SHADOW_SUFFIX = ".shadow"


def shadow_db_path(db_path: Path) -> Path:
    """Where a full rebuild writes before it publishes — the one definition site (356, R6.7)."""
    return db_path.with_name(db_path.name + SHADOW_SUFFIX)


def _remove_db_files(path: Path) -> None:
    """Delete a SQLite file and its WAL siblings."""
    for sibling in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        sibling.unlink(missing_ok=True)


def _page_size(db_path: Path) -> int | None:
    """The page size of the database at ``db_path``, or ``None`` when none is readable there."""
    if not db_path.is_file():
        return None
    try:
        conn = sqlite3.connect(db_path)
        try:
            return int(conn.execute("PRAGMA page_size").fetchone()[0])
        finally:
            conn.close()
    except sqlite3.Error:
        return None


DDL = """
CREATE TABLE IF NOT EXISTS files (
  path TEXT PRIMARY KEY, hash TEXT, language TEXT, parsed_ok INT DEFAULT 1, updated_at TEXT,
  fingerprint TEXT);

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
-- `replace_file_rows` deletes by file_path once per parsed file. Unindexed that is a full scan of
-- the edge table per file — 189 ms x 24,569 files = 77 min of a 76-minute rebuild (task 203).
CREATE INDEX IF NOT EXISTS idx_edges_file ON edges(file_path);

CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
  name, qualified_name, file_path, params,
  content='nodes', content_rowid='id', tokenize='trigram');
"""

# The nodes→nodes_fts triggers, single-sourced so `truncate_graph` recreates the exact same set the
# schema creates. Dropped around a bulk clear (they would otherwise fire once per deleted row) and
# recreated statement-by-statement — never via executescript, whose implicit commit breaks a txn.
_TRIGGER_NAMES: tuple[str, ...] = ("nodes_ai", "nodes_ad", "nodes_au")
_TRIGGER_DDL: tuple[str, ...] = (
    """CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
  INSERT INTO nodes_fts(rowid, name, qualified_name, file_path, params)
  VALUES (new.id, new.name, new.qualified_name, new.file_path, new.params);
END;""",
    """CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, name, qualified_name, file_path, params)
  VALUES ('delete', old.id, old.name, old.qualified_name, old.file_path, old.params);
END;""",
    """CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, name, qualified_name, file_path, params)
  VALUES ('delete', old.id, old.name, old.qualified_name, old.file_path, old.params);
  INSERT INTO nodes_fts(rowid, name, qualified_name, file_path, params)
  VALUES (new.id, new.name, new.qualified_name, new.file_path, new.params);
END;""",
)

DDL = DDL + "\n" + "\n".join(_TRIGGER_DDL) + """

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
# Inbound pages: RESOLVED before HEURISTIC before DYNAMIC, then today's stable keys (265).
_EDGE_TIER_RANK = (
    "CASE edges.confidence_tier "
    "WHEN 'RESOLVED' THEN 0 WHEN 'HEURISTIC' THEN 1 WHEN 'DYNAMIC' THEN 2 ELSE 3 END"
)
_EDGE_ORDER_TIER_FIRST = f"{_EDGE_TIER_RANK}, {_EDGE_ORDER}"
_SEARCH_ORDER = "nodes_fts.rank, nodes.qualified_name, nodes.file_path, nodes.id"
# Exactness outranks BM25 (task 180): a shorter document scores better, so a near-miss in a small
# file beat six exact matches. The band calls the ONE predicate `reason` is decided by (R6.7).
DIRECT_MATCH_SQL_FN = "ca_direct_match"
_SEARCH_BAND = f"{DIRECT_MATCH_SQL_FN}(?, nodes.name, nodes.qualified_name) DESC"
# Within a band: outside mirrors, then higher external-inbound side (277). No-op when stamp absent.
MIRROR_PREFER_SQL_FN = "ca_mirror_prefer"
_SEARCH_MIRROR = f"{MIRROR_PREFER_SQL_FN}(nodes.file_path) ASC"

Row = dict[str, object]


class LanguageEdgeCensus(NamedTuple):
    """Per-language edge facts from one scan: 183's tier mix, and 186's emitted-kind sets."""

    health: dict[str, object]
    kinds: dict[str, list[str]]


class ImpactResult(NamedTuple):
    """Rows plus counters for omitted seeds / non-RESOLVED frontier edges."""

    rows: list[Row]
    frontier_skipped_non_resolved: int
    seeds_dropped: int


# The temp tables a `retain_temps=True` walk promises its caller (task 187) — one definition site,
# so a guard derives the set instead of re-typing it (R6.7). `reach_next` / `reach_before` are
# per-hop scratch and an empty walk never creates them, so they are not part of that promise.
_REACH_RETAINED_TEMPS = ("reach_seen", "reach_frontier", "reach_kinds", "reach_unproven")
_REACH_TEMPS = _REACH_RETAINED_TEMPS + ("reach_next", "reach_before")


class ReachabilityResult(NamedTuple):
    """Forward reachable set plus unproven (HEURISTIC/DYNAMIC-only) neighbors (task 031)."""

    reachable: list[Row]
    unproven: list[Row]
    frontier_skipped_non_resolved: int
    truncated: bool
    depth_exhausted: bool
    # `truncated` conflates three causes and one of them — a caller's own `depth=` — is a deliberate
    # question, not a failure. This names the BUDGET half, which is the one that cannot be trusted
    # to say anything about reachability at all (task 182).
    budget_exhausted: bool = False


class OrphanResult(NamedTuple):
    """Complement of reachability: orphans with why, plus unproven (task 031)."""

    orphans: list[Row]
    unproven: list[Row]
    orphan_total: int
    truncated: bool
    depth_exhausted: bool
    walk_truncated: bool
    # How many nodes the roots actually reached, and how many exist (task 182). A 99.31% orphan
    # share is a correct algorithm with the wrong roots, and only these two numbers show which.
    reached: int = 0
    nodes_total: int = 0
    # The budget half of `walk_truncated`; a caller's own `depth=` is not this (task 182).
    budget_exhausted: bool = False


class SubtreeTierAttribution(NamedTuple):
    """Attributable vs duplicate-declaration counts for one confidence tier (task 120)."""

    attributable: int
    unattributable: int


class SubtreeCrossingReport(NamedTuple):
    """One direction of subtree crossing: tier split plus ranked file/path lists.

    A counts-only direction leaves both lists empty and both totals ``0`` — see
    ``GraphStore.subtree_dependency_report``, which asks for lists in one direction only.
    """

    by_tier: dict[str, SubtreeTierAttribution]
    ranked_files: list[Row]
    ranked_paths: list[Row]
    file_total: int
    path_total: int


class SubtreeDependencyResult(NamedTuple):
    """Tree-to-tree dependency with duplicate-declaration attribution (task 120)."""

    inbound: SubtreeCrossingReport
    outbound: SubtreeCrossingReport
    dynamic_bridges: list[Row]
    bridge_total: int
    lists_truncated: bool


class DeltaScope(NamedTuple):
    """What one incremental could have changed the resolve answer for (task 096).

    ``scoped_kinds`` are the kinds resolved by a lookup key; every other kind streams unscoped.
    The caller supplies them, so this module re-lists no edge kind (R6.7).
    """

    files: tuple[str, ...]
    keys: tuple[str, ...]
    scoped_kinds: tuple[str, ...]


# explain_path statuses (task 038) — distinct outcomes, never empty-as-proof.
PATH_STATUS_PATH = "path"
PATH_STATUS_UNPROVEN = "unproven"
PATH_STATUS_NO_PATH = "no_path"
PATH_STATUS_UNKNOWN = "unknown"
PATH_STATUS_INCOMPLETE = "incomplete"


class TourSubgraph(NamedTuple):
    """Node-budgeted module-grain dependency subgraph for the guided tour (task 087).

    ``entry_points`` is the subset of ``files`` with genuinely zero inbound, which a reader
    of ``edges`` alone cannot recover once the budget dropped a predecessor.
    """

    files: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    truncated: bool
    entry_points: tuple[str, ...] = ()


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


def is_exact_or_prefix_match(query: str, name: str, qualified_name: str) -> bool:
    """167's exact/prefix arm alone, without 287/293's separator-suffix arms.

    Its own definition site (R6.7) because ``search_symbol`` bands ``separator_normalised`` on
    exactly this half; a second copy there would drift the moment 167's arm changes.
    """
    q = query.casefold()
    for candidate in (name.casefold(), qualified_name.casefold()):
        if candidate == q or candidate.startswith(q):
            return True
    return False


def is_direct_match(query: str, name: str, qualified_name: str) -> bool:
    """True when ``query`` exactly matches or prefixes ``name`` or ``qualified_name`` (task 167).

    Case-insensitive and language-agnostic (R1.1) — a run of the query against the symbol, no SQL.
    A ``Class::method`` query that is a separator-boundary suffix of the qname is also direct
    (287), and so is the container-separator spelling ``Class.method`` via
    ``member_separator_variant`` (293). One definition site (R6.7): it decides both
    ``search_symbol``'s ``reason`` and the ordering's exactness band, so the two cannot drift.
    """
    if is_exact_or_prefix_match(query, name, qualified_name):
        return True
    folded = qualified_name.casefold()
    # Member-separator suffix on a component boundary — not any substring (287/293).
    for cand, allow_colon in _member_boundary_candidates(query):
        if not folded.endswith(cand):
            continue
        if len(folded) == len(cand):
            return True
        # Native ``::`` keeps 287's charset; variant arm also allows ``:`` (file::Class::method).
        seps = "\\/.:" if allow_colon else "\\/."
        if folded[-len(cand) - 1] in seps:
            return True
    return False


@lru_cache(maxsize=64)
def _member_boundary_candidates(query: str) -> tuple[tuple[str, bool], ...]:
    """Pairs of (:: form, allow_colon) — variant once per query; :: stays 287-shaped."""
    folded = query.casefold()
    sep = contract.MEMBER_SEPARATOR.casefold()
    if sep in folded:
        return ((folded, False),)
    variant = contract.member_separator_variant(query)
    if variant is None:
        return ()
    return ((variant.casefold(), True),)

def _direct_match_udf(query: object, name: object, qualified_name: object) -> int:
    """``is_direct_match`` as a SQLite scalar, so ORDER BY bands on the predicate, not a copy."""
    return int(is_direct_match(str(query), str(name or ""), str(qualified_name or "")))


def _search_contains_demote(
    query: str,
    *,
    kind: str | None,
    namespace: str | None,
    path_prefix: str | None = None,
) -> tuple[str, tuple[object, ...]]:
    """ORDER BY key: demote hits whose CONTAINS parent is also a hit for this query (292/297).

    Parent must satisfy the same FTS/kind/namespace/path filters as the outer search so a hit set
    with no container/member pair stays byte-identical (061).
    """
    parent_where, parent_params = _narrow(
        "nodes_fts MATCH ?", fts_term(query), kind, "p.kind = ?"
    )
    parent_where, parent_params = _with_namespace(
        parent_where, parent_params, namespace, qname_column="p.qualified_name"
    )
    parent_where, parent_params = _with_path_prefix(
        parent_where, parent_params, path_prefix, column="p.file_path"
    )
    # Uncorrelated on purpose: the member set is computed ONCE, not re-derived per outer row.
    # Correlating it made the subquery re-scan fts5 for every hit — 30x on SQLite 3.40 (297).
    members = (
        f"SELECT e.target_qname AS member FROM edges AS e "
        f"JOIN nodes AS p ON p.qualified_name = e.source_qname "
        f"JOIN nodes_fts ON nodes_fts.rowid = p.id "
        f"WHERE e.kind = '{contract.CONTAINS}' "
        f"AND {DIRECT_MATCH_SQL_FN}(?, p.name, p.qualified_name) "
        f"AND {parent_where} "
        f"UNION ALL "
        f"SELECT e.target_raw AS member FROM edges AS e "
        f"JOIN nodes AS p ON p.qualified_name = e.source_qname "
        f"JOIN nodes_fts ON nodes_fts.rowid = p.id "
        f"WHERE e.kind = '{contract.CONTAINS}' "
        f"AND {DIRECT_MATCH_SQL_FN}(?, p.name, p.qualified_name) "
        f"AND {parent_where}"
    )
    sql = f"(CASE WHEN nodes.qualified_name IN ({members}) THEN 1 ELSE 0 END)"
    return sql, (query, *parent_params, query, *parent_params)


def _like_literal(value: str) -> str:
    """Escape ``!``, ``%``, and ``_`` for a ``LIKE … ESCAPE '!'`` pattern (``\\`` stays literal)."""
    return value.replace("!", "!!").replace("%", "!%").replace("_", "!_")


# Cap on the unlinked-WRITES scan that backs ``has_unlinked_writes_relating_to`` (215).
_WALK_UNLINKED = 10_000


def _writes_raw_relates_to(raw: str, table_folded: str, bare: str) -> bool:
    """Does an unlinked WRITES ``target_raw`` name ``table`` under casefold (215)?"""
    folded = raw.casefold()
    if folded == table_folded or folded.startswith(table_folded + "::"):
        return True
    if folded == bare or folded.startswith(bare + "::"):
        return True
    if folded.endswith("." + bare) or ("." + bare + "::") in folded:
        return True
    return False


def _chunks(values: Sequence[str], size: int) -> Iterator[Sequence[str]]:
    """Yield successive slices of ``values`` so ``IN (...)`` lists stay under the host max."""
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _rank_window(partition: str, qname: str, distinct_qnames: bool) -> tuple[str, str]:
    """The per-key ``rn`` column and the extra WHERE prefix that keeps a row.

    Distinct mode ranks qnames, not rows: one row per qname (``dup = 1``), ``rn`` its qname's rank
    within the key — several files declaring one qname are one candidate (334).
    """
    if not distinct_qnames:
        return f"ROW_NUMBER() OVER (PARTITION BY {partition} ORDER BY {_NODE_ORDER}) AS rn", ""
    return (
        f"ROW_NUMBER() OVER (PARTITION BY {partition}, {qname} ORDER BY {_NODE_ORDER}) AS dup, "
        f"DENSE_RANK() OVER (PARTITION BY {partition} ORDER BY {qname}) AS rn",
        "dup = 1 AND ",
    )


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
        return "edges.args IS NOT NULL AND json_array_length(edges.args) < ?", (position,)
    at = f"$[{position - 1}]"
    if selector == contract.ARG_DYNAMIC:
        return (
            "edges.args IS NOT NULL AND json_array_length(edges.args) >= ? "
            "AND json_extract(edges.args, ?) IS NULL",
            (position, at),
        )
    return "edges.args IS NOT NULL AND json_extract(edges.args, ?) = ?", (at, selector)


def _tier_predicate(confidence_tier: str | None) -> _Predicate:
    """Narrow edges to one ``confidence_tier`` (task 251). Unknown spellings fail loud (R5.3)."""
    if confidence_tier is None:
        return None
    if confidence_tier not in contract.CONFIDENCE_TIERS:
        raise ValueError(
            f"unknown confidence_tier {confidence_tier!r}: "
            f"one of {', '.join(contract.CONFIDENCE_TIERS)}"
        )
    return "edges.confidence_tier = ?", (confidence_tier,)


def _exclude_test_sources_predicate(
    exclude_test_sources: bool, *, edges: str = "edges"
) -> _Predicate:
    """Drop inbound edges whose source is stored as test (262); ``edges`` names the alias."""
    if not exclude_test_sources:
        return None
    return (
        f"NOT EXISTS (SELECT 1 FROM nodes src WHERE src.qualified_name = {edges}.source_qname "
        "AND COALESCE(src.is_test, 0) = 1)",
        (),
    )


def _combine_predicates(*preds: _Predicate) -> _Predicate:
    """AND ready-made edge predicates so filters compose without a second WHERE builder."""
    active = [pred for pred in preds if pred is not None]
    if not active:
        return None
    if len(active) == 1:
        return active[0]
    return (
        " AND ".join(pred[0] for pred in active),
        tuple(value for pred in active for value in pred[1]),
    )


def stored(value: object) -> object:
    """Structured values become canonical JSON, so identical input stores identical bytes (R4.2)."""
    if value is None or isinstance(value, str | int | float):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def fit_meta_key(
    tool: str,
    reason: str,
    *,
    authoritative: bool,
    truncated: bool,
) -> str:
    """Encode the fit tuple as a meta key — counts only, never subject values (task 260)."""
    return (
        f"{FIT_KEY_PREFIX}{tool}|{reason}|{int(authoritative)}|{int(truncated)}"
    )


def parse_fit_meta_key(
    key: str,
) -> tuple[str, str, bool, bool] | None:
    """Decode a ``fit:`` meta key, or ``None`` when the shape is not ours."""
    if not key.startswith(FIT_KEY_PREFIX):
        return None
    parts = key[len(FIT_KEY_PREFIX) :].split("|")
    if len(parts) != 4:
        return None
    tool, reason, auth_s, trunc_s = parts
    if auth_s not in ("0", "1") or trunc_s not in ("0", "1"):
        return None
    return tool, reason, auth_s == "1", trunc_s == "1"


# One atomic read-free bump, shared by the open-store method and the per-call fast path (260).
_FIT_BUMP_SQL = (
    "INSERT INTO meta (key, value) VALUES (?, '1') "
    "ON CONFLICT(key) DO UPDATE SET value = CAST(CAST(meta.value AS INTEGER) + 1 AS TEXT)"
)

# The fit counter rides **every** served call, so it reuses one handle per index. Measured: the
# first write on a *fresh* connection costs 6.3 ms (WAL shared-memory setup), against 0.024 ms on
# a kept one — the difference between a 0.4 ms nav answer and a 7 ms one (260).
_FIT_CONNS: dict[Path, tuple[sqlite3.Connection, tuple[int, int]]] = {}
_FIT_LOCK = threading.Lock()


def _fit_conn(db_path: Path) -> sqlite3.Connection:
    """The kept counter handle for ``db_path``, opened on first use. Held under ``_FIT_LOCK``.

    Keyed on the file's identity, not its name: a rebuild that replaces the index leaves the old
    handle writing to an unlinked inode, where SQLite reports no error and the counts vanish.
    """
    stat = db_path.stat()
    ident = (stat.st_dev, stat.st_ino)
    cached = _FIT_CONNS.get(db_path)
    if cached is not None and cached[1] == ident:
        return cached[0]
    if cached is not None:
        with contextlib.suppress(sqlite3.Error):
            cached[0].close()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout=5000")
    # Durability the graph needs, a counter does not: no graph row is written here, and a
    # counter that loses its last few increments to a power cut is still a counter.
    conn.execute("PRAGMA synchronous=NORMAL")
    _FIT_CONNS[db_path] = (conn, ident)
    return conn


def close_fit_connections() -> None:
    """Drop every kept counter handle — server shutdown, and a test that replaces its index."""
    with _FIT_LOCK:
        while _FIT_CONNS:
            _, (conn, _ident) = _FIT_CONNS.popitem()
            with contextlib.suppress(sqlite3.Error):
                conn.close()


atexit.register(close_fit_connections)


def bump_fit_count(
    db_path: Path,
    tool: str,
    reason: str,
    *,
    authoritative: bool,
    truncated: bool,
) -> None:
    """Fit bump on an existing index (task 260), counts only — never a qname, path or argument.

    A file with no ``meta`` table, or one that vanished between the caller's check and this
    write, is not an answer this counter may spoil: the handle is dropped and the count abandoned.
    Counting must never raise into a caller's answer.
    """
    key = fit_meta_key(tool, reason, authoritative=authoritative, truncated=truncated)
    with _FIT_LOCK:
        try:
            conn = _fit_conn(db_path)
            with conn:
                conn.execute(_FIT_BUMP_SQL, (key,))
        except (sqlite3.Error, OSError):
            cached = _FIT_CONNS.pop(db_path, None)
            if cached is not None:
                with contextlib.suppress(sqlite3.Error):
                    cached[0].close()


class GraphStore:
    """The graph in SQLite: schema creation, per-file writes, and every bounded read."""

    def __init__(self, db_path: Path, *, now: Callable[[], str] | None = None) -> None:
        self._now = utc_now if now is None else now
        self._db_path = db_path
        self._publish_to: Path | None = None
        if str(db_path) != MEMORY_DB:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._mirror_stamp: dict[str, object] | None = None
        self._conn.create_function(
            DIRECT_MATCH_SQL_FN, 3, _direct_match_udf, deterministic=True
        )
        self._conn.create_function(
            MIRROR_PREFER_SQL_FN, 1, self._mirror_prefer_udf, deterministic=True
        )
        for pragma in PRAGMAS:
            self._conn.execute(f"PRAGMA {pragma}")
        self._create_schema()
        self.reload_mirror_search_stamp()

    def _mirror_prefer_udf(self, path: object) -> int:
        """SQLite ORDER BY helper — prefers non-mirror paths, then external-inbound (277)."""
        from code_atlas.mirror_search import mirror_prefer_key

        return mirror_prefer_key(str(path or ""), self._mirror_stamp)

    def reload_mirror_search_stamp(self) -> None:
        """Refresh the in-memory mirror-search stamp from meta (after build or open)."""
        from code_atlas.mirror_search import load_mirror_search_stamp

        self._mirror_stamp = load_mirror_search_stamp(self)

    def close(self) -> None:
        self._conn.close()

    @classmethod
    def open_shadow(cls, db_path: Path) -> "GraphStore":
        """A fresh store a full rebuild fills; :meth:`publish` copies it over ``db_path`` (356).

        A leftover from a killed build is dropped first. The page size is the live file's: a
        backup into a WAL database refuses a different one.
        """
        shadow = shadow_db_path(db_path)
        _remove_db_files(shadow)
        shadow.parent.mkdir(parents=True, exist_ok=True)
        size = _page_size(db_path)
        if size is not None:
            conn = sqlite3.connect(shadow)
            try:
                conn.execute(f"PRAGMA page_size={size}")
                conn.execute("PRAGMA journal_mode=WAL")
            finally:
                conn.close()
        store = cls(shadow)
        store._publish_to = db_path
        return store

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def in_memory(self) -> bool:
        return str(self._db_path) == MEMORY_DB

    @property
    def is_shadow(self) -> bool:
        return self._publish_to is not None

    def publish(self) -> None:
        """Copy this shadow over the live index in one destination transaction, then delete it.

        A reader is a WAL snapshot: one in flight finishes on the old graph, the next opens the new
        one, and the live path and inode never change (356). The live index's fit counters are
        carried in first, so only a bump inside the copy window itself can be lost.
        """
        if self._publish_to is None:
            raise ValueError("publish() needs a store from open_shadow()")
        live = sqlite3.connect(self._publish_to)
        try:
            live.execute("PRAGMA busy_timeout=5000")
            self._carry_fit_counts(live)
            self._conn.backup(live)
            # Best effort: a reader still on the old snapshot only delays the truncate.
            with contextlib.suppress(sqlite3.Error):
                live.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            live.close()
        self.discard()

    def discard(self) -> None:
        """Close this store and delete its file with the WAL siblings — a shadow never published."""
        self.close()
        _remove_db_files(self._db_path)

    def _carry_fit_counts(self, live: sqlite3.Connection) -> None:
        """Copy the live index's ``fit:`` rows into this shadow before it replaces them (260)."""
        try:
            rows = live.execute(
                "SELECT key, value FROM meta WHERE key LIKE ?", (f"{FIT_KEY_PREFIX}%",)
            ).fetchall()
        except sqlite3.Error:
            return  # no meta table: a first build writes over an empty file
        with self._conn:
            self._conn.executemany(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                rows,
            )

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
        self,
        path: str,
        file_hash: str,
        language: str,
        *,
        parsed_ok: bool = True,
        fingerprint: str | None = None,
    ) -> None:
        """Insert or update one file row; a failed parse keeps its row with parsed_ok=0 (R5.1).

        ``fingerprint`` is the whitespace-normalised digest (213). ``None`` leaves an existing
        value alone on conflict so test helpers that only plant a hash do not wipe it.
        """
        with self._conn:
            self._conn.execute(
                "INSERT INTO files (path, hash, language, parsed_ok, updated_at, fingerprint) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(path) DO UPDATE SET "
                "hash = excluded.hash, language = excluded.language, "
                "parsed_ok = excluded.parsed_ok, updated_at = excluded.updated_at, "
                "fingerprint = COALESCE(excluded.fingerprint, files.fingerprint)",
                (path, file_hash, language, int(parsed_ok), self._now(), fingerprint),
            )

    def touch_file_bytes(
        self, path: str, file_hash: str, fingerprint: str
    ) -> None:
        """Refresh hash + fingerprint without touching nodes/edges (213 fingerprint skip)."""
        with self._conn:
            self._conn.execute(
                "UPDATE files SET hash = ?, fingerprint = ?, updated_at = ? WHERE path = ?",
                (file_hash, fingerprint, self._now(), path),
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

    def fold_column_extras(self, qnames: Sequence[str] | None = None) -> int:
        """Merge sparse Column.extra enrichment onto the typed row of the same qname (247 AC3).

        An ``ALTER … PRIMARY KEY`` in another file cannot reach the CREATE Column under
        ``UNIQUE(qualified_name, file_path)``. Rows with no ``data_type``/``type`` that carry
        ``nullable`` / ``identity`` / ``primary_key`` contribute those keys onto every typed
        Column of that qname, then the sparse rows are deleted. True duplicate typed decls are
        left alone. Returns the number of sparse rows removed.

        Matching is case-insensitive: SQL identifiers are, so ``PRIMARY KEY (id)`` names the
        column declared ``Id`` — folding by exact spelling would leave a typeless phantom column
        behind and drop the key. ``qnames`` restricts the fold to those columns; the delta path
        passes what it touched rather than rescanning every Column in the graph.

        Each fold records its contributing files in ``extras_from`` on the typed row. That is the
        only trace left once the sparse rows are gone, and it is what lets an incremental re-parse
        of the CREATE file recover a key declared in another file (see
        ``file_paths_contributing_column_extras``).
        """
        enrich_keys = ("nullable", "identity", "primary_key")
        sql = "SELECT id, qualified_name, file_path, extra FROM nodes WHERE kind = ?"
        params: list[object] = ["Column"]
        wanted = {q.casefold() for q in qnames} if qnames is not None else None
        rows = self._conn.execute(sql, params).fetchall()
        by_qname: dict[str, list[tuple[int, str, str, dict[str, object], bool]]] = {}
        for node_id, qname, file_path, raw in rows:
            key = str(qname).casefold()
            if wanted is not None and key not in wanted:
                continue
            try:
                extra = json.loads(raw) if isinstance(raw, str) and raw else {}
            except json.JSONDecodeError:
                extra = {}
            if not isinstance(extra, dict):
                extra = {}
            has_type = bool(extra.get("data_type") or extra.get("type"))
            by_qname.setdefault(key, []).append(
                (int(node_id), str(qname), str(file_path), extra, has_type)
            )

        deleted = 0
        with self._conn:
            for group in by_qname.values():
                typed = [g for g in group if g[4]]
                sparse = [g for g in group if not g[4]]
                if not typed or not sparse:
                    continue
                enrich: dict[str, object] = {}
                sources: set[str] = set()
                for _, _, file_path, extra, _ in sparse:
                    contributed = False
                    for key in enrich_keys:
                        if key in extra:
                            enrich[key] = extra[key]
                            contributed = True
                    if contributed:
                        sources.add(file_path)
                if not enrich:
                    continue
                for node_id, _, file_path, extra, _ in typed:
                    merged = dict(extra)
                    merged.update(enrich)
                    merged["extras_from"] = sorted(sources - {file_path})
                    if not merged["extras_from"]:
                        del merged["extras_from"]
                    self._conn.execute(
                        "UPDATE nodes SET extra = ? WHERE id = ?",
                        (stored(merged), node_id),
                    )
                for node_id, qname, file_path, _, _ in sparse:
                    # Drop any CONTAINS the sparse ALTER file may have emitted for this qname.
                    self._conn.execute(
                        "DELETE FROM edges WHERE kind = 'CONTAINS' AND file_path = ? "
                        "AND (target_raw = ? OR target_qname = ?)",
                        (file_path, qname, qname),
                    )
                    self._conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
                    deleted += 1
        return deleted

    def file_paths_contributing_column_extras(self, qnames: Sequence[str]) -> tuple[str, ...]:
        """Files a previous fold consumed for these Column qnames (247).

        The fold deletes the sparse rows it merges, so nothing in the graph would otherwise say
        that an ``ALTER … PRIMARY KEY`` file contributes to a column declared elsewhere — and an
        incremental that re-parses only the CREATE file would drop the key for good. The delta
        re-parses these alongside it.
        """
        wanted = {q.casefold() for q in qnames}
        if not wanted:
            return ()
        out: set[str] = set()
        for (qname, raw) in self._conn.execute(
            "SELECT qualified_name, extra FROM nodes WHERE kind = 'Column' AND extra LIKE ?",
            ("%extras_from%",),
        ):
            if str(qname).casefold() not in wanted:
                continue
            try:
                extra = json.loads(raw) if isinstance(raw, str) and raw else {}
            except json.JSONDecodeError:
                continue
            if isinstance(extra, dict):
                out.update(str(p) for p in extra.get("extras_from", []) if isinstance(p, str))
        return tuple(sorted(out))

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

    def truncate_graph(self) -> None:
        """Clear all nodes/edges + the FTS index before a full rebuild, so each per-path
        _delete_rows is a no-op (203's ~1.8x tax). One explicit txn wraps the trigger drop/recreate
        (DDL commits eagerly otherwise) so a kill rolls back to a fully-triggered graph; the bulk
        clear then never fires nodes_ad per row."""
        self._conn.execute("BEGIN")
        try:
            for name in _TRIGGER_NAMES:
                self._conn.execute(f"DROP TRIGGER IF EXISTS {name}")
            self._conn.execute("DELETE FROM edges")
            self._conn.execute("DELETE FROM nodes")
            self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES ('delete-all')")
            for statement in _TRIGGER_DDL:
                self._conn.execute(statement)
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        self._conn.execute("COMMIT")

    def get_meta(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row[0])

    def has_meta(self, key: str) -> bool:
        """True when the key exists — distinguishes absent (pre-077) from a stamped null-clear."""
        row = self._conn.execute("SELECT 1 FROM meta WHERE key = ?", (key,)).fetchone()
        return row is not None

    def set_meta(self, key: str, value: str) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def delete_meta(self, key: str) -> None:
        """Drop a meta row so a rebuild cannot inherit a stale stamp (077)."""
        with self._conn:
            self._conn.execute("DELETE FROM meta WHERE key = ?", (key,))

    def increment_fit_count(
        self,
        tool: str,
        reason: str,
        *,
        authoritative: bool,
        truncated: bool,
    ) -> None:
        """Bump the local fit counter for one ``(tool, reason, authoritative, truncated)`` tuple.

        Counts only — the key never carries qname, path, or argument values (task 260 / R4).
        """
        key = fit_meta_key(tool, reason, authoritative=authoritative, truncated=truncated)
        with self._conn:
            self._conn.execute(_FIT_BUMP_SQL, (key,))

    def list_fit_counts(self) -> list[dict[str, object]]:
        """Every ``fit:`` meta row as a stable sorted list of count tuples (task 260)."""
        rows = self._conn.execute(
            "SELECT key, value FROM meta WHERE key LIKE ? ESCAPE '!' ORDER BY key",
            (FIT_KEY_PREFIX.replace("!", "!!") + "%",),
        ).fetchall()
        out: list[dict[str, object]] = []
        for key, value in rows:
            parsed = parse_fit_meta_key(str(key))
            if parsed is None:
                continue
            tool, reason, authoritative, truncated = parsed
            count = int(value) if str(value).isdigit() else 0
            out.append(
                {
                    "tool": tool,
                    "reason": reason,
                    "authoritative": authoritative,
                    "truncated": truncated,
                    "count": count,
                }
            )
        return out

    def clear_fit_counts(self) -> int:
        """Delete every ``fit:`` meta row; return how many were removed (task 260)."""
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM meta WHERE key LIKE ? ESCAPE '!'",
                (FIT_KEY_PREFIX.replace("!", "!!") + "%",),
            )
            return int(cursor.rowcount)

    def rebuild_search_index(self) -> None:
        """Repair only: the triggers keep nodes_fts current, so this just recovers a stale index."""
        with self._conn:
            self._conn.execute("INSERT INTO nodes_fts(nodes_fts) VALUES ('rebuild')")

    # --- reads ----------------------------------------------------------------------------------

    def file_paths(self) -> tuple[str, ...]:
        """Every indexed path, sorted — what a build reconciles its collection against (§8.1)."""
        cursor = self._conn.execute("SELECT path FROM files ORDER BY path")
        return tuple(str(row[0]) for row in cursor)

    def resolved_edge_file_pairs(self) -> list[tuple[str, str]]:
        """``(source_file, target_file)`` for resolved edges — mirror inbound stamp (277)."""
        cursor = self._conn.execute(
            "SELECT e.file_path, n.file_path FROM edges e "
            "JOIN nodes n ON n.qualified_name = e.target_qname "
            "WHERE e.target_qname IS NOT NULL "
            "ORDER BY e.file_path, n.file_path"
        )
        return [(str(src or ""), str(tgt or "")) for src, tgt in cursor]

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

    def indexed_languages(self) -> tuple[str, ...]:
        """Languages the graph actually holds files for. One DISTINCT over a small domain."""
        rows = self._conn.execute(
            "SELECT DISTINCT language FROM files WHERE language IS NOT NULL AND language != ''"
            " ORDER BY language"
        ).fetchall()
        return tuple(str(language) for (language,) in rows)

    def suffixes_with_files(self, candidates: Sequence[str]) -> tuple[str, ...]:
        """Which of ``candidates`` the graph has at least one file for.

        One ``LIMIT 1`` probe per candidate — bounded by the adapter count, never by the row count,
        and run once per build rather than per answer (task 173).
        """
        held = []
        for suffix in candidates:
            row = self._conn.execute(
                "SELECT 1 FROM files WHERE lower(path) LIKE ? LIMIT 1", ("%" + suffix.lower(),)
            ).fetchone()
            if row is not None:
                held.append(suffix)
        return tuple(held)

    def collection_census(self) -> dict[str, int] | None:
        """The stored collect-walk tally, or ``None`` for a pre-082 index (task 082).

        ``None`` (not a zeroed dict) so verbose status omits the block rather than publish a fake
        denominator for an index built before the census existed.
        """
        raw = self.get_meta(COLLECTION_CENSUS_KEY)
        if not raw:
            return None
        parsed = json.loads(raw)
        return {key: int(value) for key, value in parsed.items()}

    def untracked_indexable_paths(self) -> tuple[str, ...]:
        """Untracked indexable paths stamped at the last build, or empty when absent (092)."""
        raw = self.get_meta(UNTRACKED_INDEXABLE_KEY)
        if not raw:
            return ()
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            return ()
        return tuple(str(path) for path in parsed)

    def ignore_source_counts(self) -> dict[str, int]:
        """Per-source ignore tallies stamped at the last build, or empty when absent (095)."""
        raw = self.get_meta(IGNORE_SOURCES_KEY)
        if not raw:
            return {}
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return {}
        return {str(key): int(value) for key, value in parsed.items() if int(value) > 0}

    def skipped_suffix_counts(self) -> dict[str, int]:
        """Per-extension skip tallies stamped at the last build, or empty when absent (task 174)."""
        raw = self.get_meta(SKIPPED_SUFFIX_COUNTS_KEY)
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}
        return {str(key): int(value) for key, value in parsed.items() if int(value) > 0}

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

    @staticmethod
    def _tier_block(tiers: Mapping[str, int], linked: int) -> dict[str, object]:
        """One tier/link block. The single fold rule, so a split cannot sum unlike the whole (R1.8).

        NULL or unknown tiers fold into RESOLVED exactly as §8.2 readers do, which is what makes
        ``sum(by_tier.values())`` equal the row count for the whole graph and for every slice of it.
        """
        by_tier = dict.fromkeys(CONFIDENCE_TIERS, 0)
        for tier, count in tiers.items():
            by_tier[tier if tier in by_tier else _RESOLVED] += int(count)
        total = sum(by_tier.values())
        return {"by_tier": by_tier, "linked": int(linked), "unlinked": total - int(linked)}

    def edge_health(self) -> dict[str, object]:
        """Tier mix and link-resolution split for ``get_index_status`` (R4; SQL only).

        ``by_tier`` always includes every ``CONFIDENCE_TIERS`` key (missing tiers are 0).
        NULL or unknown tiers fold into RESOLVED (same as other §8.2 readers), so
        ``sum(by_tier.values()) == counts()["edges"]``. ``linked`` / ``unlinked`` count
        ``target_qname`` presence: an edge that found *a* name, at any tier. Only
        ``by_tier.RESOLVED`` says the name is trusted — the two differ by ~2x on a real repo (048).
        """
        tiers = {
            str(tier): int(count)
            for tier, count in self._conn.execute(
                "SELECT confidence_tier, COUNT(*) FROM edges GROUP BY confidence_tier"
            )
        }
        (linked,) = self._conn.execute(
            "SELECT COUNT(*) FROM edges WHERE target_qname IS NOT NULL"
        ).fetchone()
        return self._tier_block(tiers, int(linked))

    def edge_language_census(self) -> "LanguageEdgeCensus":
        """Both per-language edge facts from ONE statement (tasks 183 + 186).

        183 needs the tier mix per language; 186 needs which kinds each language has ever emitted.
        Grouping by ``(language, kind, confidence_tier)`` yields both, so the second fact costs no
        second scan of a table that is 2.1 M rows on the anchor repo.
        """
        tiers: dict[str, dict[str, int]] = {}
        linked: dict[str, int] = {}
        # Seeded with EVERY indexed language, so one that emitted no edges at all reads as
        # "emitted nothing" rather than as "never measured" — the two are different claims (R5.6).
        kinds: dict[str, set[str]] = {name: set() for name in self.indexed_languages()}
        for language, kind, tier, count, found in self._conn.execute(
            "SELECT files.language, edges.kind, edges.confidence_tier, COUNT(*), "
            "SUM(CASE WHEN edges.target_qname IS NOT NULL THEN 1 ELSE 0 END) "
            "FROM edges LEFT JOIN files ON files.path = edges.file_path "
            "GROUP BY files.language, edges.kind, edges.confidence_tier"
        ):
            key = str(language) if language else ""
            bucket = tiers.setdefault(key, {})
            bucket[str(tier)] = bucket.get(str(tier), 0) + int(count)
            linked[key] = linked.get(key, 0) + int(found or 0)
            if kind:
                kinds.setdefault(key, set()).add(str(kind))
        health: dict[str, object] = {
            "by_language": {
                name: self._tier_block(tiers[name], linked[name])
                for name in sorted(name for name in tiers if name)
            }
        }
        if "" in tiers:
            health["unattributed"] = self._tier_block(tiers[""], linked[""])
        health["cross_language"] = self._cross_language_edges()
        return LanguageEdgeCensus(
            health=health,
            kinds={name: sorted(kinds[name]) for name in sorted(kinds) if name},
        )


    def _cross_language_edges(self) -> dict[str, object]:
        """Linked edges whose target is declared in a file of ANOTHER language (task 204).

        183's per-language rows key on the DECLARING language alone, so a link to a callee that
        cannot be called counts as healthy. This is the row that can see it: on a graph the
        bare-name fallback no longer guesses across, it reads 0, and a non-zero value is the
        regression signal. ~3.2 s on the 2.19 M-edge anchor — one scan per build, never per answer.
        """
        tiers: dict[str, int] = {}
        pairs: dict[str, int] = {}
        for source, target, tier, count in self._conn.execute(
            "SELECT src.language, tgt.language, edges.confidence_tier, COUNT(DISTINCT edges.id) "
            "FROM edges "
            "JOIN files src ON src.path = edges.file_path "
            "JOIN nodes ON nodes.qualified_name = edges.target_qname "
            "JOIN files tgt ON tgt.path = nodes.file_path "
            "WHERE edges.target_qname IS NOT NULL AND src.language <> tgt.language "
            "GROUP BY src.language, tgt.language, edges.confidence_tier"
        ):
            tiers[str(tier)] = tiers.get(str(tier), 0) + int(count)
            key = f"{source}->{target}"
            pairs[key] = pairs.get(key, 0) + int(count)
        total = sum(tiers.values())
        # Every counted edge is linked by construction, so the shared fold's own `linked` argument
        # is the total — one fold rule for every block, never a second spelling of it (R1.8).
        block = self._tier_block(tiers, total)
        block["pairs"] = {key: pairs[key] for key in sorted(pairs)}
        return block

    def edge_health_by_language(self) -> dict[str, object]:
        """``edge_health`` split by the language of the edge's OWN file (task 183).

        An edge belongs to the file that declared it, so a cross-language edge is one row of the
        *source* language — the target's language is a different question and is not asked here.
        One statement; run once per build, never per answer.

        Returns ``{"by_language": {<lang>: block}, "unattributed": block}``, the second present only
        when some edge's file carries no language: ``edges.file_path`` has no foreign key, so the
        bucket is not structurally empty and dropping it would break the identity silently. Over
        every bucket, the tier counts sum to whole-graph ``edge_health`` (082's reconciliation).
        """
        return self.edge_language_census().health

    def stamped_edge_health_by_language(self) -> dict[str, object] | None:
        """The per-build split, or ``None`` for a pre-183 index (R5.6) — never a computed fallback.

        A fallback would put the GROUP BY this stamp exists to avoid back on the answer path, and an
        empty dict would claim a one-language graph for an index that simply never measured itself.
        """
        raw = self.get_meta(EDGE_HEALTH_BY_LANGUAGE_KEY)
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # An unreadable stamp is one we cannot report, not a one-language graph.
            return None
        if not isinstance(parsed, dict) or "by_language" not in parsed:
            return None
        return dict(parsed)

    def stamped_emitted_kinds_by_language(self) -> dict[str, list[str]] | None:
        """Per-language emitted edge kinds from the last build, or ``None`` pre-186 (R5.6)."""
        raw = self.get_meta(EMITTED_KINDS_BY_LANGUAGE_KEY)
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return {str(name): [str(k) for k in kinds] for name, kinds in parsed.items()}

    def unmodelled_resolution_by_language(self) -> dict[str, list[str]]:
        """Union File.extra unmodelled_resolution strategies per files.language (279).

        Empty dict when no File carries the key — callers omit the meta stamp (061).
        """
        from code_atlas.contract import UNMODELLED_RESOLUTION

        by_lang: dict[str, set[str]] = {}
        for language, raw in self._conn.execute(
            "SELECT files.language, nodes.extra FROM nodes "
            "JOIN files ON files.path = nodes.file_path "
            "WHERE nodes.kind = 'File' AND nodes.extra IS NOT NULL AND nodes.extra != ''"
        ):
            try:
                extra = json.loads(raw) if isinstance(raw, str) else {}
            except json.JSONDecodeError:
                continue
            if not isinstance(extra, dict):
                continue
            strategies = extra.get(UNMODELLED_RESOLUTION)
            if not isinstance(strategies, list) or not strategies:
                continue
            key = str(language) if language else ""
            bucket = by_lang.setdefault(key, set())
            for item in strategies:
                if isinstance(item, str) and item:
                    bucket.add(item)
        return {name: sorted(items) for name, items in sorted(by_lang.items()) if items}

    def stamped_unmodelled_resolution_by_language(self) -> dict[str, list[str]] | None:
        """Per-language unmodelled resolution strategies from the last build, or ``None`` (279)."""
        raw = self.get_meta(UNMODELLED_RESOLUTION_BY_LANGUAGE_KEY)
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict) or not parsed:
            return None
        out: dict[str, list[str]] = {}
        for name, strategies in parsed.items():
            if isinstance(strategies, list) and strategies:
                out[str(name)] = [str(s) for s in strategies if isinstance(s, str)]
        return out or None


    def stamped_symbol_shapes(self) -> dict[str, dict[str, object]]:
        """Per-language suffixes and grep shapes from the last build; empty before v13 (345)."""
        raw = self.get_meta(SYMBOL_SHAPES_BY_LANGUAGE_KEY)
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}
        return {str(name): dict(entry) for name, entry in parsed.items() if isinstance(entry, dict)}

    def stamped_capabilities_by_language(self) -> dict[str, dict[str, bool]] | None:
        """Per-language R1.6 capability flags from the last build, or ``None`` pre-231 (R5.6)."""
        raw = self.get_meta(CAPABILITIES_BY_LANGUAGE_KEY)
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        out: dict[str, dict[str, bool]] = {}
        for name, caps in parsed.items():
            if isinstance(caps, dict):
                out[str(name)] = {str(k): bool(v) for k, v in caps.items()}
        return out

    def stamped_cross_language_edges(self) -> dict[str, object] | None:
        """The cross-language link census from the last build, or ``None`` pre-204 (R5.6).

        Nested inside the edge-health stamp since 204, so 221 reads it there rather than stamping a
        second copy of one census that two keys could drift apart on.
        """
        stamped = self.stamped_edge_health_by_language()
        block = (stamped or {}).get("cross_language")
        return dict(block) if isinstance(block, dict) and "linked" in block else None

    def language_emits_none_of(self, language: str, kinds: Sequence[str]) -> bool | None:
        """Has this language emitted NONE of ``kinds`` in this index? ``None`` = cannot say (R5.6).

        ``None`` for a pre-186 index and for a language the stamp does not name: an index that
        never measured itself is not evidence of absence, which is the claim this answers. A
        language measured with zero edges is named with an empty list, so it answers ``True``.
        """
        stamped = self.stamped_emitted_kinds_by_language()
        if stamped is None or language not in stamped:
            return None
        emitted = set(stamped[language])
        return not any(kind in emitted for kind in kinds)

    def language_of_file(self, path: str) -> str | None:
        """The indexed language of one file, or ``None`` when the file is not indexed."""
        row = self._conn.execute(
            "SELECT language FROM files WHERE path = ?", (path,)
        ).fetchone()
        if row is None or not row[0]:
            return None
        return str(row[0])

    def dependency_edges(self) -> list[tuple[str, str]]:
        """Distinct resolved dependency pairs ``(source, target)``, self-loops excluded (task 083).

        ``target_qname IS NOT NULL`` keeps resolved edges only: ``ALIASES`` carry ``target_raw``,
        not ``target_qname``, so they drop out with no kind branch (R1.1). ``GROUP BY`` dedupes;
        the ``ORDER BY`` is stable for byte-reproducible metrics (R4.2).
        """
        cursor = self._conn.execute(
            "SELECT source_qname, target_qname FROM edges "
            "WHERE target_qname IS NOT NULL AND source_qname <> target_qname "
            "GROUP BY source_qname, target_qname "
            "ORDER BY source_qname, target_qname"
        )
        return [(str(source), str(target)) for source, target in cursor]

    def dependency_edges_with_tier(self) -> list[tuple[str, str, str]]:
        """Distinct resolved pairs with a winning tier — RESOLVED beats HEURISTIC beats DYNAMIC.

        Same pair set as :meth:`dependency_edges`; the extra column is what 143's dashed arrows
        need. ``GROUP BY`` still dedupes; ``ORDER BY`` is stable (R4.2).
        """
        resolved, heuristic, dynamic = CONFIDENCE_TIERS
        cursor = self._conn.execute(
            "SELECT source_qname, target_qname, "
            "CASE WHEN SUM(CASE WHEN confidence_tier = ? THEN 1 ELSE 0 END) > 0 THEN ? "
            "WHEN SUM(CASE WHEN confidence_tier = ? THEN 1 ELSE 0 END) > 0 THEN ? "
            "ELSE ? END "
            "FROM edges "
            "WHERE target_qname IS NOT NULL AND source_qname <> target_qname "
            "GROUP BY source_qname, target_qname "
            "ORDER BY source_qname, target_qname",
            (resolved, resolved, heuristic, heuristic, dynamic),
        )
        return [(str(source), str(target), str(tier)) for source, target, tier in cursor]

    def flow_edges(self, kinds: Sequence[str]) -> list[tuple[str, str, str, str, int | None]]:
        """Distinct pairs with KIND, winning tier and that tier's earliest ``line`` (197/225).

        ``dependency_edges_with_tier`` drops the kind, so a ``WRITES`` hop and a ``Table`` sink are
        indistinguishable in it. The line is ``MIN(line)`` **within the winning tier**, not across
        the whole group: a plain ``MIN(line)`` could hand a RESOLVED edge the call line of a losing
        DYNAMIC row to the same target, and the caller attests order on that line (225). ``None``
        when the winning tier has no line. Filtering in SQL bounds the pull (R4.3); ``ORDER BY`` is
        stable (R4.2).
        """
        if not kinds:
            return []
        resolved, heuristic, dynamic = CONFIDENCE_TIERS
        placeholders = ", ".join("?" for _ in kinds)
        cursor = self._conn.execute(
            "SELECT source_qname, target_qname, kind, "
            "CASE WHEN SUM(CASE WHEN confidence_tier = ? THEN 1 ELSE 0 END) > 0 THEN ? "
            "WHEN SUM(CASE WHEN confidence_tier = ? THEN 1 ELSE 0 END) > 0 THEN ? "
            "ELSE ? END, "
            "COALESCE("
            "MIN(CASE WHEN confidence_tier = ? THEN line END), "
            "MIN(CASE WHEN confidence_tier = ? THEN line END), "
            "MIN(CASE WHEN confidence_tier = ? THEN line END)) "
            "FROM edges "
            f"WHERE target_qname IS NOT NULL AND source_qname <> target_qname "
            f"AND kind IN ({placeholders}) "
            "GROUP BY source_qname, target_qname, kind "
            "ORDER BY source_qname, target_qname, kind",
            (resolved, resolved, heuristic, heuristic, dynamic,
             resolved, heuristic, dynamic, *kinds),
        )
        return [
            (str(s), str(t), str(k), str(tier), None if ln is None else int(ln))
            for s, t, k, tier, ln in cursor
        ]

    def node_universe(self) -> list[tuple[str, str]]:
        """Every ``(qualified_name, file_path)`` — the node set + qname→module map (task 083).

        A qname can map to more than one file (duplicate/ambiguous decls, ``UNIQUE(qname, path)``);
        the pure caller (``onboarding.metrics``) dedupes it. Stable ``ORDER BY`` (R4.2).
        """
        cursor = self._conn.execute(
            "SELECT qualified_name, file_path FROM nodes "
            "GROUP BY qualified_name, file_path "
            "ORDER BY qualified_name, file_path"
        )
        return [(str(qname), str(path)) for qname, path in cursor]

    def node_kind_counts(self) -> tuple[tuple[str, int], ...]:
        """Node totals per ``kind`` — the onboarding dataset's kind census (task 112).

        One GROUP BY pass, bounded by the kind vocabulary (``contract.NODE_KINDS``) not the node
        count. A NULL kind reads as ``''`` and sorts first; stable ``ORDER BY`` (R4.2).
        """
        cursor = self._conn.execute(
            "SELECT COALESCE(kind, ''), COUNT(*) FROM nodes GROUP BY kind ORDER BY kind"
        )
        return tuple((str(kind), int(count)) for kind, count in cursor)

    def edge_kind_counts(self) -> tuple[tuple[str, int], ...]:
        """Edge totals per ``kind`` (task 112). Bounded by the edge vocabulary; stable (R4.2)."""
        cursor = self._conn.execute(
            "SELECT COALESCE(kind, ''), COUNT(*) FROM edges GROUP BY kind ORDER BY kind"
        )
        return tuple((str(kind), int(count)) for kind, count in cursor)

    def module_hubs(self, *, limit: int) -> tuple[tuple[str, int, int], ...]:
        """Top ``limit`` files by module fan-in: ``(file, fan_in, fan_out)`` (task 112).

        Fan-in/out count *distinct other files*, the same module grain ``compute_metrics`` uses, so
        a hub's fan-in equals its module metric (R6.7 — one definition, not two). Bounded by
        ``limit``; ties break on ``file_path`` for a byte-stable ranking (R4.2).
        """
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        cursor = self._conn.execute(
            "WITH me AS ("
            "  SELECT DISTINCT src.file_path AS s, tgt.file_path AS t FROM edges e "
            "  JOIN nodes src ON src.qualified_name = e.source_qname "
            "  JOIN nodes tgt ON tgt.qualified_name = e.target_qname "
            "  WHERE e.target_qname IS NOT NULL AND e.source_qname <> e.target_qname "
            "    AND src.file_path <> tgt.file_path"
            "), fin AS (SELECT t AS f, COUNT(*) AS fan_in FROM me GROUP BY t), "
            "fout AS (SELECT s AS f, COUNT(*) AS fan_out FROM me GROUP BY s) "
            "SELECT fin.f, fin.fan_in, COALESCE(fout.fan_out, 0) "
            "FROM fin LEFT JOIN fout ON fout.f = fin.f "
            "ORDER BY fin.fan_in DESC, fin.f ASC LIMIT ?",
            (limit,),
        )
        return tuple((str(f), int(fi), int(fo)) for f, fi, fo in cursor)

    def largest_classes(self, *, limit: int) -> tuple[tuple[str, str, int], ...]:
        """Top ``limit`` classes by member count: ``(qualified_name, file, members)`` (task 112).

        Members are ``Method`` nodes sharing the class's file — the mockup's file-grain heuristic
        (a file with several classes over-counts; refined presentation is 116/117). ``'Class'`` /
        ``'Method'`` are contract node kinds, not repo names (R2). Bounded by ``limit``; ties break
        on ``qualified_name`` then ``file`` (R4.2).
        """
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        cursor = self._conn.execute(
            "SELECT c.qualified_name, c.file_path, COUNT(m.id) AS members FROM nodes c "
            "LEFT JOIN nodes m ON m.file_path = c.file_path AND m.kind = 'Method' "
            "WHERE c.kind = 'Class' GROUP BY c.id "
            "ORDER BY members DESC, c.qualified_name ASC, c.file_path ASC LIMIT ?",
            (limit,),
        )
        return tuple((str(q), str(f), int(m)) for q, f, m in cursor)

    def file_class_counts(self) -> tuple[tuple[str, int], ...]:
        """Per-file class count ``(file, classes)`` — the business-module table's substrate (114).

        One GROUP BY pass, same shape and bound as ``file_symbol_counts`` (R4.3). ``'Class'`` is
        a contract node kind, not a repo name (``largest_classes`` precedent). Stable order (R4.2).
        """
        cursor = self._conn.execute(
            "SELECT file_path, COUNT(*) FROM nodes WHERE file_path IS NOT NULL AND kind = 'Class' "
            "GROUP BY file_path ORDER BY file_path"
        )
        return tuple((str(path), int(count)) for path, count in cursor)

    def file_kind_counts(self) -> tuple[tuple[str, str, int], ...]:
        """Per-file, per-kind counts ``(file, kind, count)`` — the layer composition bar (task 116).

        One GROUP BY pass; rows bounded by files x ``contract.NODE_KINDS``, not by node count
        (R4.3). A NULL kind reads as ``''``. Stable ``ORDER BY`` (R4.2).
        """
        cursor = self._conn.execute(
            "SELECT file_path, COALESCE(kind, ''), COUNT(*) FROM nodes "
            "WHERE file_path IS NOT NULL GROUP BY file_path, kind "
            "ORDER BY file_path, kind"
        )
        return tuple((str(path), str(kind), int(count)) for path, kind, count in cursor)

    def file_symbol_counts(self) -> tuple[tuple[str, int], ...]:
        """Per-file symbol count ``(file, symbols)`` — the directory-tree substrate (task 112).

        One GROUP BY pass over ``nodes``. O(files), same class as ``file_paths``/``node_universe``:
        no recursive walk (R4.3). The caller rolls these up by directory and prunes at a symbol
        threshold, so what the dataset keeps is bounded. Stable ``ORDER BY`` (R4.2).
        """
        cursor = self._conn.execute(
            "SELECT file_path, COUNT(*) FROM nodes WHERE file_path IS NOT NULL "
            "GROUP BY file_path ORDER BY file_path"
        )
        return tuple((str(path), int(count)) for path, count in cursor)

    def tour_subgraph(
        self, *, max_nodes: int, files: Sequence[str] | None = None
    ) -> TourSubgraph:
        """Budgeted module-grain walk covering every file the budget admits (task 087 / R4.3).

        Round 1 seeds files with no inbound cross-file resolved edge, **preferring roots that
        lead somewhere** (out-degree > 0) and ranked by out-degree, capped at a quarter of the
        budget so expansion always has room — alphabetical zero-outbound seeds bought lint and
        bootstrap files and never a front controller (tasks 106, 131). A component no seed reaches
        (it must hold a cycle) would otherwise be silently absent, so later rounds re-seed the
        widest-reaching unseen files until the budget binds. Earlier rounds outrank later ones
        under the prune. ``truncated`` means files were left out.

        ``files`` is an optional membership universe (task 206). Unset walks the whole index.
        The prefix predicate that produced the list lives elsewhere — this cut is membership only.
        """
        if max_nodes < 1:
            raise ValueError(f"max_nodes must be >= 1, got {max_nodes}")
        conn = self._conn
        self._tour_drop_temps()
        try:
            conn.execute(
                "CREATE TEMP TABLE tour_universe (file_path TEXT PRIMARY KEY)"
            )
            if files is None:
                conn.execute(
                    "INSERT OR IGNORE INTO temp.tour_universe (file_path) "
                    "SELECT DISTINCT file_path FROM nodes WHERE file_path IS NOT NULL"
                )
            else:
                conn.executemany(
                    "INSERT OR IGNORE INTO temp.tour_universe (file_path) VALUES (?)",
                    [(path,) for path in files],
                )
            conn.execute(
                "CREATE TEMP TABLE tour_seen ("
                "file_path TEXT PRIMARY KEY, depth INT NOT NULL, is_seed INT NOT NULL, "
                "round INT NOT NULL)"
            )
            conn.execute(
                "CREATE TEMP TABLE tour_frontier (file_path TEXT PRIMARY KEY, depth INT NOT NULL)"
            )
            self._tour_build_out_degree()
            seed_cap = max(1, max_nodes // _TOUR_SEED_BUDGET_DIVISOR)
            seeds = self._tour_entry_seeds(seed_cap)
            entries = set(seeds)
            if not seeds:  # the whole graph is one cycle: start at the widest-reaching file
                seeds = self._tour_ranked_unseen(seed_cap)
            if not seeds:
                return TourSubgraph((), (), False)
            walked = 0
            self._tour_admit_seeds(seeds, walked)
            self._tour_expand(max_nodes, walked)
            # A component no entry point reaches is not absent — it is the next round (087 review).
            # The seed cap orders budget spend, it does not cut coverage: this loop refills what
            # expansion left unused, so an edgeless repo still fills the budget (106).
            while (room := max_nodes - self._tour_seen_count()) > 0:
                later = self._tour_ranked_unseen(min(room, seed_cap))
                if not later:
                    break
                walked += 1
                self._tour_admit_seeds(later, walked)
                self._tour_expand(max_nodes, walked)
            files = tuple(
                str(row[0])
                for row in conn.execute(
                    "SELECT file_path FROM temp.tour_seen ORDER BY file_path"
                )
            )
            edges = tuple(
                (str(src), str(tgt))
                for src, tgt in conn.execute(
                    "SELECT DISTINCT src.file_path, tgt.file_path "
                    "FROM edges e "
                    "JOIN nodes src ON src.qualified_name = e.source_qname "
                    "JOIN nodes tgt ON tgt.qualified_name = e.target_qname "
                    "JOIN temp.tour_seen a ON a.file_path = src.file_path "
                    "JOIN temp.tour_seen b ON b.file_path = tgt.file_path "
                    "WHERE e.target_qname IS NOT NULL AND src.file_path <> tgt.file_path "
                    "ORDER BY src.file_path, tgt.file_path"
                )
            )
            # One honest signal: truncated means a universe file did not make the tour.
            left_out = conn.execute(
                "SELECT 1 FROM temp.tour_universe "
                "WHERE file_path NOT IN (SELECT file_path FROM temp.tour_seen) LIMIT 1"
            ).fetchone()
            return TourSubgraph(
                files,
                edges,
                left_out is not None,
                tuple(path for path in files if path in entries),
            )
        finally:
            self._tour_drop_temps()

    def nodes_by_name(self, name: str, *, kind: str | None = None, limit: int) -> list[Row]:
        """Single-key lookup via the batch path; prefer ``nodes_by_names`` in a loop."""
        return self.nodes_by_names([name], kind=kind, limit=limit).get(name, [])

    def nodes_by_qualified_name(
        self, qname: str, *, kind: str | None = None, limit: int
    ) -> list[Row]:
        """Single-key lookup via the batch path; prefer ``nodes_by_qualified_names`` in a loop."""
        return self.nodes_by_qualified_names([qname], kind=kind, limit=limit).get(qname, [])

    def nodes_by_names(
        self,
        names: Sequence[str],
        *,
        kind: str | None = None,
        limit: int,
        language: str | None = None,
        distinct_qnames: bool = False,
    ) -> dict[str, list[Row]]:
        """Per-name top-``limit`` nodes (``_NODE_ORDER`` within each name).

        ``language`` restricts candidates to nodes declared in files of that language, inside the
        statement that truncates — so ``limit`` selects from the legal set rather than being spent
        on candidates a caller would then discard (R5.8, task 204). ``distinct_qnames`` counts
        ``limit`` in qnames, one row each, so one qname's twins cannot hide another (334).
        """
        return self._nodes_batched(
            key_column="name",
            keys=names,
            kind=kind,
            limit=limit,
            language=language,
            distinct_qnames=distinct_qnames,
        )

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

    def count_nodes_by_file(self, path: str) -> int:
        """How many symbols live on ``path`` (same set ``nodes_by_file`` pages)."""
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM nodes WHERE file_path = ?",
            (path,),
        )
        row = cursor.fetchone()
        assert row is not None
        return int(row[0])

    def node_kinds_by_file(self, path: str) -> dict[str, int]:
        """Per-kind symbol counts on ``path`` — the outline spread substrate (task 123)."""
        cursor = self._conn.execute(
            "SELECT COALESCE(kind, ''), COUNT(*) FROM nodes WHERE file_path = ? "
            "GROUP BY kind ORDER BY kind",
            (path,),
        )
        return {str(kind): int(count) for kind, count in cursor}

    def nodes_by_file(self, path: str, *, limit: int, offset: int = 0) -> list[Row]:
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        sql = (
            f"SELECT id, {_NODE_COLUMNS} FROM nodes WHERE file_path = ? "
            f"ORDER BY {_NODE_ORDER} LIMIT ? OFFSET ?"
        )
        return self._rows(NODE_ROW_KEYS, sql, (path, limit, offset))

    def edges_by_source(
        self,
        qname: str,
        *,
        kinds: Sequence[str] | None = None,
        limit: int,
        offset: int = 0,
    ) -> list[Row]:
        return self._edges("edges.source_qname = ?", qname, kinds, limit, offset=offset)

    def count_edges_by_source(
        self, qname: str, *, kinds: Sequence[str] | None = None
    ) -> int:
        """How many edges leave ``qname`` (same kind filter as ``edges_by_source``)."""
        return self._count_edges("edges.source_qname = ?", qname, kinds)

    def edges_matching_kind(self, kind: str, *, limit: int) -> list[Row]:
        """Up to ``limit`` edges of ``kind`` in store order (enrichment scans — task 062)."""
        return self._edges("edges.kind = ?", kind, None, limit)

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
        confidence_tier: str | None = None,
        exclude_test_sources: bool = False,
        distinct_sources: bool = False,
        path_prefix: str | None = None,
    ) -> list[Row]:
        """Edges whose resolved ``target_qname`` is ``qname``.

        Optional ``kinds`` narrows the set (e.g. CALLER_KINDS); ``args_at`` narrows to call sites
        whose argument at a 1-based position has a given shape (task 049).
        ``confidence_tier`` narrows to one tier in the store query (task 251) — not a post-filter.
        ``offset`` skips leading rows in tier-first order (tasks 057 / 265).
        ``distinct_sources`` keeps one edge per ``source_qname`` (273).
        ``path_prefix`` narrows to edges whose ``file_path`` is under that prefix (315).
        """
        return self._edges(
            "edges.target_qname = ?",
            qname,
            kinds,
            limit,
            offset=offset,
            extra=_combine_predicates(
                _args_predicate(args_at),
                _tier_predicate(confidence_tier),
                _exclude_test_sources_predicate(exclude_test_sources),
                _path_prefix_predicate(path_prefix),
            ),
            order=_EDGE_ORDER_TIER_FIRST,
            distinct_sources=distinct_sources,
        )

    def edges_by_targets(
        self,
        qnames: Sequence[str],
        *,
        kinds: Sequence[str] | None = None,
        limit: int,
        offset: int = 0,
        confidence_tier: str | None = None,
        exclude_test_sources: bool = False,
        path_prefix: str | None = None,
    ) -> list[Row]:
        """Inbound edges whose ``target_qname`` is any of ``qnames``, tier-first paged (265).

        One statement for the class-level ``via_members`` union so cost scales with the page,
        not with each member's whole inbound set.
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        if not qnames:
            return []
        placeholders = ", ".join("?" for _ in qnames)
        where = f"edges.target_qname IN ({placeholders})"
        extra = _combine_predicates(
            _tier_predicate(confidence_tier),
            _exclude_test_sources_predicate(exclude_test_sources),
            _path_prefix_predicate(path_prefix),
        )
        clause, params = self._edge_where(where, kinds, extra)
        sql = (
            f"SELECT id, {_EDGE_COLUMNS} FROM edges WHERE {clause} "
            f"ORDER BY {_EDGE_ORDER_TIER_FIRST} LIMIT ? OFFSET ?"
        )
        return self._rows(
            EDGE_ROW_KEYS, sql, (*qnames, *params, limit, offset)
        )

    def count_write_statements_by_targets(
        self,
        qnames: Sequence[str],
        *,
        kinds: Sequence[str] | None = None,
        exclude_test_sources: bool = False,
        path_prefix: str | None = None,
    ) -> int:
        """Count distinct writing statements ``(source, file, line)`` across targets (329)."""
        if not qnames:
            return 0
        placeholders = ", ".join("?" for _ in qnames)
        where = f"edges.target_qname IN ({placeholders})"
        extra = _combine_predicates(
            _exclude_test_sources_predicate(exclude_test_sources),
            _path_prefix_predicate(path_prefix),
        )
        clause, params = self._edge_where(where, kinds, extra)
        sql = (
            "SELECT COUNT(*) FROM ("
            f"SELECT 1 FROM edges WHERE {clause} "
            "GROUP BY source_qname, file_path, line"
            ")"
        )
        return int(self._conn.execute(sql, (*qnames, *params)).fetchone()[0])

    def write_statements_by_targets(
        self,
        qnames: Sequence[str],
        *,
        kinds: Sequence[str] | None = None,
        limit: int,
        offset: int = 0,
        exclude_test_sources: bool = False,
        path_prefix: str | None = None,
    ) -> list[Row]:
        """Page distinct writing statements; fold named columns into each row (329).

        One SQL page — never a Python pass over an unbounded fetch (R1.4). Column names
        from Column targets are sorted deterministically (R4.2). Table-target edges add
        no column name (column-less write).
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        if not qnames:
            return []
        placeholders = ", ".join("?" for _ in qnames)
        where = f"edges.target_qname IN ({placeholders})"
        extra = _combine_predicates(
            _exclude_test_sources_predicate(exclude_test_sources),
            _path_prefix_predicate(path_prefix),
        )
        clause, params = self._edge_where(where, kinds, extra)
        # Best tier in the group (RESOLVED first) — same rank expression as list order.
        sql = (
            "SELECT MIN(id) AS id, source_qname, kind, "
            "GROUP_CONCAT(DISTINCT target_qname) AS target_qnames, "
            "file_path, line, "
            f"MIN({_EDGE_TIER_RANK}) AS tier_rank "
            f"FROM edges WHERE {clause} "
            "GROUP BY source_qname, file_path, line "
            "ORDER BY tier_rank, source_qname, file_path, line "
            "LIMIT ? OFFSET ?"
        )
        cursor = self._conn.execute(sql, (*qnames, *params, limit, offset))
        names = [column[0] for column in cursor.description]
        rows: list[Row] = []
        for values in cursor.fetchall():
            record = dict(zip(names, values, strict=True))
            # _EDGE_TIER_RANK enumerates CONFIDENCE_TIERS in order; ELSE rank has no tier.
            rank = int(record.pop("tier_rank"))
            targets = str(record.pop("target_qnames") or "").split(",")
            hit: Row = dict.fromkeys(EDGE_ROW_KEYS)
            hit.update(record)
            hit["confidence_tier"] = (
                CONFIDENCE_TIERS[rank] if rank < len(CONFIDENCE_TIERS) else None
            )
            hit["columns"] = sorted({t.rsplit("::", 1)[-1] for t in targets if "::" in t})
            rows.append(hit)
        return rows

    def inbound_write_statement_test_rows(
        self,
        qnames: Sequence[str],
        *,
        kinds: Sequence[str] | None = None,
    ) -> list[tuple[int, str, int]]:
        """``(is_test, source file_path, statement_count)`` for Table writer census (329)."""
        if not qnames:
            return []
        placeholders = ", ".join("?" for _ in qnames)
        where = f"edges.target_qname IN ({placeholders})"
        clause, params = self._edge_where(where, kinds, None)
        one_src = (
            "JOIN nodes src ON src.rowid = ("
            "SELECT n.rowid FROM nodes n WHERE n.qualified_name = edges.source_qname "
            "ORDER BY n.file_path LIMIT 1)"
        )
        sql = (
            "SELECT COALESCE(src.is_test, 0), COALESCE(src.file_path, ''), COUNT(*) "
            "FROM ("
            f"SELECT source_qname, file_path, line FROM edges WHERE {clause} "
            "GROUP BY source_qname, file_path, line"
            f") edges {one_src} GROUP BY 1, 2"
        )
        return [
            (int(is_test), str(path), int(count))
            for is_test, path, count in self._conn.execute(
                sql, (*qnames, *params)
            ).fetchall()
        ]

    def count_edges_by_targets(
        self,
        qnames: Sequence[str],
        *,
        kinds: Sequence[str] | None = None,
        confidence_tier: str | None = None,
        exclude_test_sources: bool = False,
        path_prefix: str | None = None,
    ) -> int:
        """Count inbound edges for any of qnames (same filters as edges_by_targets)."""
        if not qnames:
            return 0
        placeholders = ", ".join("?" for _ in qnames)
        where = f"edges.target_qname IN ({placeholders})"
        extra = _combine_predicates(
            _tier_predicate(confidence_tier),
            _exclude_test_sources_predicate(exclude_test_sources),
            _path_prefix_predicate(path_prefix),
        )
        clause, params = self._edge_where(where, kinds, extra)
        sql = f"SELECT COUNT(*) FROM edges WHERE {clause}"
        return int(self._conn.execute(sql, (*qnames, *params)).fetchone()[0])

    def count_edges_by_target(
        self,
        qname: str,
        *,
        kinds: Sequence[str] | None = None,
        args_at: tuple[int, str] | None = None,
        confidence_tier: str | None = None,
        exclude_test_sources: bool = False,
        distinct_sources: bool = False,
        path_prefix: str | None = None,
    ) -> int:
        """How many edges (or distinct sources) target ``qname`` (same filters as the list)."""
        return self._count_edges(
            "edges.target_qname = ?",
            qname,
            kinds,
            extra=_combine_predicates(
                _args_predicate(args_at),
                _tier_predicate(confidence_tier),
                _exclude_test_sources_predicate(exclude_test_sources),
                _path_prefix_predicate(path_prefix),
            ),
            distinct_sources=distinct_sources,
        )
    def call_lines_by_source(
        self,
        qname: str,
        sources: Sequence[str],
        *,
        kinds: Sequence[str] | None = None,
        args_at: tuple[int, str] | None = None,
        confidence_tier: str | None = None,
        exclude_test_sources: bool = False,
    ) -> dict[tuple[str, str], list[int]]:
        """Sorted distinct lines per ``(source_qname, file_path)`` into ``qname`` (338).

        One statement for a whole page of ``sources``, under the same filters as the page read.
        """
        if not sources:
            return {}
        clause, params = self._edge_where(
            "edges.target_qname = ?",
            kinds,
            _combine_predicates(
                _args_predicate(args_at),
                _tier_predicate(confidence_tier),
                _exclude_test_sources_predicate(exclude_test_sources),
                (
                    f"edges.source_qname IN ({', '.join('?' for _ in sources)})",
                    tuple(sources),
                ),
            ),
        )
        sql = (
            "SELECT DISTINCT source_qname, file_path, line FROM edges "
            f"WHERE {clause} AND line IS NOT NULL ORDER BY source_qname, file_path, line"
        )
        found: dict[tuple[str, str], list[int]] = {}
        for source, file_path, line in self._conn.execute(sql, (qname, *params)):
            found.setdefault((str(source), str(file_path)), []).append(int(line))
        return found

    def inbound_test_rows(
        self,
        qname: str,
        *,
        kinds: Sequence[str] | None = None,
        args_at: tuple[int, str] | None = None,
        confidence_tier: str | None = None,
        distinct_sources: bool = False,
    ) -> list[tuple[int, str, int]]:
        """``(is_test, source file_path, count)`` per inbound group (262). One grouped read.

        ``distinct_sources`` counts each ``source_qname`` once so callers match the BFS set (273).
        One node per qname — a second definition must not multiply the count (258).
        """
        clause, params = self._edge_where(
            "edges.target_qname = ?",
            kinds,
            _combine_predicates(
                _args_predicate(args_at),
                _tier_predicate(confidence_tier),
            ),
        )
        one_src = (
            "JOIN nodes src ON src.rowid = ("
            "SELECT n.rowid FROM nodes n WHERE n.qualified_name = edges.source_qname "
            "ORDER BY n.file_path LIMIT 1)"
        )
        if distinct_sources:
            from_sql = (
                "FROM (SELECT source_qname FROM edges "
                f"WHERE {clause} GROUP BY source_qname) edges {one_src}"
            )
            sql = (
                "SELECT COALESCE(src.is_test, 0), COALESCE(src.file_path, ''), COUNT(*) "
                f"{from_sql} GROUP BY 1, 2"
            )
        else:
            sql = (
                "SELECT COALESCE(src.is_test, 0), COALESCE(src.file_path, ''), COUNT(*) "
                f"FROM edges {one_src} WHERE {clause} GROUP BY 1, 2"
            )
        return [
            (int(is_test), str(file_path), int(count))
            for is_test, file_path, count in self._conn.execute(sql, (qname, *params))
        ]

    def tier_census_by_target(
        self,
        qname: str,
        *,
        kinds: Sequence[str] | None = None,
        args_at: tuple[int, str] | None = None,
    ) -> dict[str, int]:
        """``confidence_tier`` → count over every edge targeting ``qname`` (task 251).

        Same ``kinds`` / ``args_at`` filters as ``count_edges_by_target`` (no tier filter — the
        census *is* the tier breakdown). Ordered by tier name so the dict is deterministic (R4.2).
        """
        clause, params = self._edge_where(
            "target_qname = ?", kinds, _args_predicate(args_at)
        )
        sql = (
            f"SELECT confidence_tier, COUNT(*) FROM edges WHERE {clause} "
            "GROUP BY confidence_tier ORDER BY confidence_tier"
        )
        return {
            str(tier): int(count)
            for tier, count in self._conn.execute(sql, (qname, *params))
        }

    def edge_subtrees_by_target(
        self,
        qname: str,
        *,
        kinds: Sequence[str] | None = None,
        args_at: tuple[int, str] | None = None,
        confidence_tier: str | None = None,
        path_prefix: str | None = None,
    ) -> dict[str, int]:
        """Top-level path segment → count over the full set targeting ``qname`` (task 067).

        Same filters as ``count_edges_by_target``, so the numbers reconcile. ``JOIN files``
        drops the synthetic rule bookmark (no ``files`` row since 068), leaving only real
        source subtrees. The segment is the path text before the first ``/`` — structural,
        never a repo name (R2); ``GROUP BY``/``ORDER BY`` keep the dict deterministic (R4.2).
        """
        clause, params = self._edge_where(
            "edges.target_qname = ?",
            kinds,
            _combine_predicates(
                _args_predicate(args_at),
                _tier_predicate(confidence_tier),
                _path_prefix_predicate(path_prefix),
            ),
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
        return self._count_edges(
            "edges.target_qname = ?", qname, kinds, extra=("edges.args IS NULL", ())
        )

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

    def indexed_dotted_module_keys(self) -> set[str]:
        """Every dotted name an indexed file could be imported as, naming no language (R1.1).

        A path's own dotted form and its directory's — a package initialiser makes the
        directory importable — each contributing every suffix, since a root may be any prefix.
        """
        keys: set[str] = set()
        for path in self.file_paths():
            segments = path.split("/")
            stem = segments[-1].rsplit(".", 1)[0]
            if not stem:
                continue
            own = [*segments[:-1], stem]
            for parts in (own, own[:-1]):
                for start in range(len(parts)):
                    keys.add(".".join(parts[start:]))
        keys.discard("")
        return keys

    def count_source_root_hint_imports(self) -> int:
        """Unlinked dotted ``IMPORTS`` naming a module the index already holds (230).

        Operator signal: the name is in the index under a directory the importer's climb
        cannot reach — configure ``source_roots``. Path-shaped raws resolved already.
        """
        keys = self.indexed_dotted_module_keys()
        if not keys:
            return 0
        sql = (
            "SELECT target_raw FROM edges WHERE kind = 'IMPORTS' "
            "AND (target_qname IS NULL OR target_qname = '')"
        )
        count = 0
        for (raw,) in self._conn.execute(sql):
            name = str(raw)
            if name and "/" not in name and name in keys:
                count += 1
        return count

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

    def unlinked_kinds_by_target_raw(
        self, raws: Sequence[str], *, kinds: Sequence[str]
    ) -> list[str]:
        """Distinct unlinked edge kinds among ``kinds`` that name any of ``raws`` (255)."""
        cleaned = tuple(raw for raw in raws if raw)
        if not cleaned or not kinds:
            return []
        kind_marks = ",".join("?" * len(kinds))
        raw_marks = ",".join("?" * len(cleaned))
        sql = (
            f"SELECT DISTINCT kind FROM edges WHERE kind IN ({kind_marks}) "
            f"AND target_raw IN ({raw_marks}) "
            "AND (target_qname IS NULL OR target_qname = '') "
            "ORDER BY kind"
        )
        return [str(row[0]) for row in self._conn.execute(sql, (*kinds, *cleaned))]

    def has_unlinked_writes_relating_to(self, table: str) -> bool:
        """True when an unlinked ``WRITES`` still names ``table`` under casefold (task 215).

        The tool cannot see writers that never emitted an edge; this is the incompleteness it
        *can* know — a write site that reached the graph but never linked.
        """
        return self.count_unlinked_writes_relating_to(table) > 0

    def count_unlinked_writes_relating_to(self, table: str) -> int:
        """How many unlinked ``WRITES`` still name ``table`` under casefold (215/278).

        Bounded by ``_WALK_UNLINKED`` — the same cap as the boolean probe (R4.3).
        """
        if not table:
            return 0
        folded = table.casefold()
        bare = folded.rsplit(".", 1)[-1]
        sql = (
            "SELECT target_raw FROM edges WHERE kind = 'WRITES' "
            "AND (target_qname IS NULL OR target_qname = '') "
            f"ORDER BY {_EDGE_ORDER} LIMIT ?"
        )
        return sum(
            1
            for (raw,) in self._conn.execute(sql, (_WALK_UNLINKED,))
            if _writes_raw_relates_to(str(raw), folded, bare)
        )

    def nodes_by_qualified_names_casefold(
        self,
        qnames: Sequence[str],
        *,
        kind: str | None = None,
        limit: int,
        distinct_qnames: bool = False,
    ) -> dict[str, list[Row]]:
        """Per-qname top-``limit`` nodes matched case-insensitively (task 215 WRITES).

        Keys stay the caller's original spelling; values are store rows whose
        ``qualified_name`` casefolds equal to that key's casefold.
        """
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        ordered = list(dict.fromkeys(qnames))
        if not ordered:
            return {}
        grouped: dict[str, list[Row]] = {key: [] for key in ordered}
        by_fold: dict[str, list[str]] = {}
        for key in ordered:
            by_fold.setdefault(key.casefold(), []).append(key)
        kind_sql = " AND kind = ?" if kind is not None else ""
        rank, keep = _rank_window("LOWER(qualified_name)", "qualified_name", distinct_qnames)
        for chunk in _chunks(list(by_fold), _IN_CHUNK):
            placeholders = ", ".join("?" for _ in chunk)
            sql = (
                f"SELECT id, {_NODE_COLUMNS} FROM ("
                f"  SELECT id, {_NODE_COLUMNS}, {rank} "
                f"  FROM nodes WHERE LOWER(qualified_name) IN ({placeholders})"
                f"{kind_sql}"
                f") WHERE {keep}rn <= ? "
                f"ORDER BY {_NODE_ORDER}"
            )
            params: list[object] = [*chunk]
            if kind is not None:
                params.append(kind)
            params.append(limit)
            for row in self._rows(NODE_ROW_KEYS, sql, params):
                fold = str(row["qualified_name"]).casefold()
                for key in by_fold.get(fold, ()):
                    grouped[key].append(row)
        return grouped

    def nodes_by_names_casefold(
        self,
        names: Sequence[str],
        *,
        kind: str | None = None,
        limit: int,
        distinct_qnames: bool = False,
    ) -> dict[str, list[Row]]:
        """Per-name top-``limit`` nodes matched case-insensitively (task 215 WRITES)."""
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        ordered = list(dict.fromkeys(names))
        if not ordered:
            return {}
        grouped: dict[str, list[Row]] = {key: [] for key in ordered}
        by_fold: dict[str, list[str]] = {}
        for key in ordered:
            by_fold.setdefault(key.casefold(), []).append(key)
        kind_sql = " AND kind = ?" if kind is not None else ""
        rank, keep = _rank_window("LOWER(name)", "qualified_name", distinct_qnames)
        for chunk in _chunks(list(by_fold), _IN_CHUNK):
            placeholders = ", ".join("?" for _ in chunk)
            sql = (
                f"SELECT id, {_NODE_COLUMNS} FROM ("
                f"  SELECT id, {_NODE_COLUMNS}, {rank} "
                f"  FROM nodes WHERE LOWER(name) IN ({placeholders})"
                f"{kind_sql}"
                f") WHERE {keep}rn <= ? "
                f"ORDER BY {_NODE_ORDER}"
            )
            params: list[object] = [*chunk]
            if kind is not None:
                params.append(kind)
            params.append(limit)
            for row in self._rows(NODE_ROW_KEYS, sql, params):
                fold = str(row["name"]).casefold()
                for key in by_fold.get(fold, ()):
                    grouped[key].append(row)
        return grouped

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

    def count_nodes_by_name(
        self, name: str, *, kind: str | None = None, language: str | None = None
    ) -> int:
        """How many nodes share ``name`` (optional kind/language), via ``idx_nodes_name``."""
        clauses = ["name = ?"]
        params: list[object] = [name]
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind)
        if language is not None:
            clauses.append(
                "file_path IN (SELECT path FROM files WHERE language = ?)"
            )
            params.append(language)
        sql = f"SELECT COUNT(*) FROM nodes WHERE {' AND '.join(clauses)}"
        return int(self._conn.execute(sql, params).fetchone()[0])

    def unresolved_caller_sites(
        self,
        bare_name: str,
        *,
        kinds: Sequence[str] | None = None,
        language: str | None = None,
    ) -> list[Row]:
        """CALLS/NEW sites that still name ``bare_name`` with no linked target (task 258).

        One row per unresolved site — the cartesian product is no longer materialised at build.
        """
        clauses = ["target_qname IS NULL", "target_raw = ?"]
        params: list[object] = [bare_name]
        if kinds is not None:
            if not kinds:
                raise ValueError("kinds must be non-empty")
            clauses.append(f"kind IN ({', '.join('?' for _ in kinds)})")
            params.extend(kinds)
        if language is not None:
            clauses.append(
                "file_path IN (SELECT path FROM files WHERE language = ?)"
            )
            params.append(language)
        sql = (
            f"SELECT id, {_EDGE_COLUMNS} FROM edges WHERE {' AND '.join(clauses)} "
            f"ORDER BY {_EDGE_ORDER}"
        )
        return self._rows(EDGE_ROW_KEYS, sql, params)

    def file_languages(self) -> dict[str, str]:
        """Map indexed path → its language, for files that carry one (task 204).

        Built once per resolve pass beside the alias and hierarchy maps: the bare-name fallback
        needs the CALL SITE's language, and a per-edge lookup would be one round per edge.
        """
        rows = self._conn.execute(
            "SELECT path, language FROM files WHERE language IS NOT NULL AND language != ''"
        ).fetchall()
        return {str(path): str(language) for path, language in rows}

    def alias_targets(self) -> dict[str, str]:
        """Map alias FQN → real FQN from ``ALIASES`` edges (``source_qname`` → ``target_raw``)."""
        rows = self._conn.execute(
            "SELECT source_qname, target_raw FROM edges WHERE kind = 'ALIASES'"
        ).fetchall()
        return {str(source): str(target) for source, target in rows}

    def declared_types(self, qnames: Sequence[str]) -> dict[str, str]:
        """Map member qname → its declared type from ``extra['type']``, for those that carry one.

        The store owns the JSON column, so it owns decoding it (R1.4). Absent, empty and
        unparseable all mean "this member declares no type" — never a guess at one.
        """
        found: dict[str, str] = {}
        for qname, rows in self.nodes_by_qualified_names(qnames, limit=1).items():
            if not rows:
                continue
            raw = rows[0].get("extra")
            if not isinstance(raw, str) or not raw:
                continue
            try:
                extra = json.loads(raw)
            except json.JSONDecodeError:
                continue
            declared = extra.get("type") if isinstance(extra, dict) else None
            if isinstance(declared, str) and declared:
                found[qname] = declared
        return found

    def hierarchy_parents(self) -> dict[str, tuple[str, ...]]:
        """Map class-like qname → what it inherits from, in ``INHERIT_KINDS`` order.

        Keyed on ``target_raw``, not ``target_qname``: the resolver walks this *while* it is
        resolving, when the hierarchy edges may not be linked yet — and an adapter emits these
        already qualified (R3.3). Two ancestors declaring one member are two real declarations,
        so the contract's own kind order is the tiebreak — a fixed one, never a per-language one.
        """
        rank = {kind: index for index, kind in enumerate(contract.INHERIT_KINDS)}
        placeholders = ", ".join("?" for _ in contract.INHERIT_KINDS)
        rows = self._conn.execute(
            f"SELECT source_qname, kind, target_raw FROM edges WHERE kind IN ({placeholders}) "
            "ORDER BY source_qname, kind, target_raw, file_path, line, id",
            contract.INHERIT_KINDS,
        ).fetchall()
        grouped: dict[str, list[tuple[int, str]]] = {}
        for source, kind, target in rows:
            grouped.setdefault(str(source), []).append((rank[str(kind)], str(target)))
        return {
            source: tuple(dict.fromkeys(target for _, target in sorted(parents)))
            for source, parents in grouped.items()
        }

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
        delta: DeltaScope | None = None,
    ) -> Iterator[list[Row]]:
        """Stream unresolved edges in ``id`` order so a large graph need not load at once (§8.2 M4).

        ``batch_size`` is validated immediately (not deferred to first ``next()``).
        ``skip_dynamic`` omits unlinkable ``DYNAMIC`` rows (not ``DYNAMIC_LINKED_KINDS`` — those
        carry an FQN and must still resolve, tasks 094 / 321).
        ``file_path`` scopes to edges emitted by one file (read-through reparse).
        ``delta`` narrows the key-resolved kinds to what one incremental could have changed
        the answer for; every other kind streams unscoped (task 096). The caller owns the
        taxonomy — this method re-lists no kind.
        """
        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {batch_size}")
        return self._iter_unresolved_edges(
            batch_size, skip_dynamic=skip_dynamic, file_path=file_path, delta=delta
        )

    def _iter_unresolved_edges(
        self,
        batch_size: int,
        *,
        skip_dynamic: bool,
        file_path: str | None = None,
        delta: DeltaScope | None = None,
    ) -> Iterator[list[Row]]:
        last_id = 0
        linked = ", ".join(f"'{kind}'" for kind in contract.DYNAMIC_LINKED_KINDS)
        dynamic_clause = (
            f" AND (confidence_tier != 'DYNAMIC' OR kind IN ({linked}))"
            if skip_dynamic
            else ""
        )
        path_clause = " AND file_path = ?" if file_path is not None else ""
        delta_clause = ""
        delta_params: tuple[object, ...] = ()
        if delta is not None:
            kinds = ", ".join("?" for _ in delta.scoped_kinds)
            delta_clause = (
                f" AND (kind NOT IN ({kinds})"
                " OR file_path IN (SELECT path FROM temp.delta_files)"
                " OR target_raw IN (SELECT key FROM temp.delta_keys))"
            )
            delta_params = tuple(delta.scoped_kinds)
        sql = (
            f"SELECT id, {_EDGE_COLUMNS} FROM edges "
            f"WHERE target_qname IS NULL{dynamic_clause}{path_clause}{delta_clause} "
            f"AND id > ? ORDER BY id LIMIT ?"
        )
        if delta is not None:
            self._fill_delta_temps(delta)
        try:
            while True:
                head: tuple[object, ...] = () if file_path is None else (file_path,)
                params = (*head, *delta_params, last_id, batch_size)
                batch = self._rows(EDGE_ROW_KEYS, sql, params)
                if not batch:
                    return
                last_id = int(str(batch[-1]["id"]))
                yield batch
        finally:
            if delta is not None:
                self._drop_delta_temps()

    def _fill_delta_temps(self, delta: DeltaScope) -> None:
        """Stage the delta's files and lookup keys so the scan joins instead of binding N params."""
        self._drop_delta_temps()
        conn = self._conn
        with conn:
            conn.execute("CREATE TEMP TABLE delta_files (path TEXT PRIMARY KEY)")
            conn.execute("CREATE TEMP TABLE delta_keys (key TEXT PRIMARY KEY)")
            conn.executemany(
                "INSERT OR IGNORE INTO temp.delta_files (path) VALUES (?)",
                [(path,) for path in delta.files],
            )
            conn.executemany(
                "INSERT OR IGNORE INTO temp.delta_keys (key) VALUES (?)",
                [(key,) for key in delta.keys],
            )

    def _drop_delta_temps(self) -> None:
        self._conn.execute("DROP TABLE IF EXISTS temp.delta_files")
        self._conn.execute("DROP TABLE IF EXISTS temp.delta_keys")

    def node_names_in_files(self, paths: Sequence[str], *, kind: str) -> tuple[str, ...]:
        """Bare ``name`` of each ``kind`` node under ``paths`` — the bare-name lookup keys (096)."""
        if not paths:
            return ()
        found: set[str] = set()
        for chunk in _chunks(paths, _IN_CHUNK):
            placeholders = ", ".join("?" * len(chunk))
            rows = self._conn.execute(
                f"SELECT DISTINCT name FROM nodes WHERE kind = ? AND file_path IN ({placeholders})",
                (kind, *chunk),
            )
            found.update(str(row[0]) for row in rows)
        return tuple(sorted(found))

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

    def file_fingerprint(self, path: str) -> str | None:
        """Whitespace-normalised fingerprint for ``path``, or ``None`` when unset / missing."""
        row = self._conn.execute(
            "SELECT fingerprint FROM files WHERE path = ?", (path,)
        ).fetchone()
        if row is None or row[0] is None:
            return None
        return str(row[0])

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
        path_prefix: str | None = None,
        exclude_test_sources: bool = False,
        limit: int,
        offset: int = 0,
    ) -> list[Row]:
        """Search symbols by FTS (trigram) or, for queries shorter than 3 chars, name prefix.

        Trigram FTS cannot match terms under three characters, so short queries use a
        ``name``/``qualified_name`` prefix ``LIKE`` instead (restores ``DB`` / ``Us`` / ``Go``).

        Optional ``namespace`` is matched case-insensitively: exact or continues
        with ``\\``, ``.``, or ``::``. Optional ``path_prefix`` narrows to the stored
        POSIX file path under that prefix (315). ``exclude_test_sources`` drops test-role
        nodes before paging (332). ``offset`` pages in search order (task 057).

        Exact/prefix matches come first, near-misses after, BM25 rank as the tie-break inside each
        band (task 180) — banding the whole result set, not the page, so ``offset`` walks it.
        Within a band, hits CONTAINED by a direct-match parent rank after non-members (292/297).
        """
        if len(query) < 3:
            return self._search_short(
                query,
                kind=kind,
                namespace=namespace,
                path_prefix=path_prefix,
                exclude_test_sources=exclude_test_sources,
                limit=limit,
                offset=offset,
            )
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        where, params = self._fts_search_clause(
            query,
            kind=kind,
            namespace=namespace,
            path_prefix=path_prefix,
            exclude_test_sources=exclude_test_sources,
        )
        contains_sql, contains_params = _search_contains_demote(
            query, kind=kind, namespace=namespace, path_prefix=path_prefix
        )
        sql = (
            f"SELECT nodes.id, {_NODE_COLUMNS_JOINED} FROM nodes "
            f"JOIN nodes_fts ON nodes_fts.rowid = nodes.id "
            f"WHERE {where} ORDER BY {_SEARCH_BAND}, {contains_sql} ASC, "
            f"{_SEARCH_MIRROR}, {_SEARCH_ORDER} LIMIT ? OFFSET ?"
        )
        return self._rows(
            NODE_ROW_KEYS, sql, (*params, query, *contains_params, limit, offset)
        )

    def count_search_nodes(
        self,
        query: str,
        *,
        kind: str | None = None,
        namespace: str | None = None,
        path_prefix: str | None = None,
        exclude_test_sources: bool = False,
    ) -> int:
        """Exact hit count for ``search_nodes`` filters (no LIMIT)."""
        if len(query) < 3:
            return self._count_search_short(
                query,
                kind=kind,
                namespace=namespace,
                path_prefix=path_prefix,
                exclude_test_sources=exclude_test_sources,
            )
        where, params = self._fts_search_clause(
            query,
            kind=kind,
            namespace=namespace,
            path_prefix=path_prefix,
            exclude_test_sources=exclude_test_sources,
        )
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
        path_prefix: str | None = None,
        exclude_test_sources: bool = False,
    ) -> tuple[str, tuple[object, ...]]:
        where, params = _narrow("nodes_fts MATCH ?", fts_term(query), kind, "nodes.kind = ?")
        where, params = _with_namespace(
            where, params, namespace, qname_column="nodes.qualified_name"
        )
        where, params = _with_path_prefix(where, params, path_prefix, column="nodes.file_path")
        return _with_exclude_test_nodes(where, params, exclude_test_sources)

    def impact_radius(
        self,
        seeds: Sequence[str],
        *,
        depth: int,
        max_nodes: int,
        kinds: Sequence[str] | None = None,
        exclude_test_sources: bool = False,
    ) -> ImpactResult:
        """Bounded best-score blast radius via iterative SQL waves (§12).

        Walks **incoming** edges of impact kinds (callers / subtypes / includers). All
        tiers appear in the result; only ``RESOLVED`` expands the frontier (A2 / nav-013).
        Seeds outrank discovered nodes under the ``max_nodes`` prune. Temp tables live
        in a ``try/finally`` so a mid-wave error cannot leak them onto a long-lived store.
        ``kinds`` defaults to every IMPACT kind; a subset is for architecture rules (138).
        ``exclude_test_sources`` drops test sources inside the wave, so they never spend the node
        budget or expand — filtered before the prune, not after the page (313).
        """
        if depth < 0:
            raise ValueError(f"depth must be >= 0, got {depth}")
        if max_nodes < 1:
            raise ValueError(f"max_nodes must be >= 1, got {max_nodes}")
        walk_kinds = tuple(kinds) if kinds is not None else contract.IMPACT_KINDS
        if not walk_kinds:
            raise ValueError("kinds must be non-empty")
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
                [(kind, IMPACT_WEIGHTS[kind]) for kind in walk_kinds],
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
            test_filter = _exclude_test_sources_predicate(exclude_test_sources, edges="e")
            if test_filter is not None:
                expand_sql += f" AND {test_filter[0]}"
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
        kinds: Sequence[str] | None = None,
    ) -> ReachabilityResult:
        """Bounded forward reachability over outgoing IMPACT_KINDS (task 031).

        ``depth=None`` walks until the frontier empties or ``max_nodes`` binds (closure).
        Only ``RESOLVED`` edges expand the frontier. HEURISTIC/DYNAMIC neighbors are
        recorded as unproven and never expand. A reached member keeps its container
        qnames alive via :func:`contract.split_qname` (no CONTAINS expand).
        ``kinds`` defaults to every IMPACT kind; a subset is for architecture rules (138).
        """
        if depth is not None and depth < 0:
            raise ValueError(f"depth must be >= 0, got {depth}")
        if max_nodes < 1:
            raise ValueError(f"max_nodes must be >= 1, got {max_nodes}")
        walk_kinds = tuple(kinds) if kinds is not None else contract.IMPACT_KINDS
        if not walk_kinds:
            raise ValueError("kinds must be non-empty")
        # No empty-seed short-circuit: the walk below already returns exactly the empty result, and
        # returning early skipped both the temps `retain_temps` promises and the drop that keeps a
        # previous walk from being re-read (task 187).
        ordered_seeds = list(dict.fromkeys(q for q in seeds if q))
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
                [(kind,) for kind in walk_kinds],
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
            budget_exhausted = seen_count >= max_nodes or unproven_total > max_nodes
            truncated = depth_exhausted or budget_exhausted
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
                reachable, unproven, skipped, truncated, depth_exhausted, budget_exhausted
            )
        finally:
            if not retain_temps:
                self._reach_drop_temps()

    def find_orphans(
        self,
        seeds: Sequence[str],
        *,
        depth: int | None,
        max_nodes: int,
        limit: int,
        offset: int = 0,
    ) -> OrphanResult:
        """Orphans = indexed nodes outside reachable∪unproven∪seeds, with why (task 031)."""
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
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
            orphan_total = int(
                conn.execute(
                    "SELECT COUNT(*) FROM nodes n "
                    "WHERE n.qualified_name NOT IN (SELECT qname FROM temp.reach_excluded)"
                ).fetchone()[0]
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
                "LIMIT ? OFFSET ?"
            )
            rows = self._rows(
                ("qname", "kind") + ("file", "line_start", "why"),
                sql,
                (*contract.IMPACT_KINDS, limit, offset),
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
            # `truncated` describes this page only, so a pager terminates; the walk hitting its
            # own budget is `walk_truncated` — a different fact, and it never ends (057/124).
            page_truncated = offset + len(orphans) < orphan_total
            # Both already computed for the walk's own budget check — no extra pass (task 182).
            reached = int(conn.execute("SELECT COUNT(*) FROM temp.reach_seen").fetchone()[0])
            nodes_total = int(conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])
            return OrphanResult(
                orphans,
                reach.unproven,
                orphan_total,
                page_truncated,
                reach.depth_exhausted,
                reach.truncated,
                reached,
                nodes_total,
                reach.budget_exhausted,
            )
        finally:
            conn.execute("DROP TABLE IF EXISTS temp.reach_excluded")
            self._reach_drop_temps()

    def subtree_dependency_report(
        self,
        subtree: str,
        *,
        counterpart: str | None = None,
        max_list: int,
    ) -> SubtreeDependencyResult:
        """Crossing edges at subtree grain with duplicate-declaration attribution (task 120).

        Inbound: sources outside ``subtree`` targeting symbols declared under it. Outbound: the
        reverse. Each edge is ``attributable`` when its target qname is declared only on one side
        of the boundary, ``unattributable`` when both sides declare it. Tier is never flattened.
        ``dynamic_bridges`` lists files whose only link is ``DYNAMIC`` — alias bridges with no
        static edge. Ranked lists cap at ``max_list``; totals are over the full graph (R4.3).
        Only ``inbound`` carries lists — the ticket asks for the dependent files outside and the
        depended-on paths inside; ``outbound`` is counts-only, so its lists stay empty.
        """
        if max_list < 1:
            raise ValueError(f"max_list must be >= 1, got {max_list}")
        subtree_clause, subtree_params = _path_under(subtree, "path")
        inbound = self._subtree_crossing(
            source_outside=subtree_clause,
            source_params=subtree_params,
            target_inside=subtree_clause,
            target_params=subtree_params,
            counterpart=counterpart,
            counterpart_on="source",
            max_list=max_list,
        )
        outbound = self._subtree_crossing(
            source_outside=subtree_clause,
            source_params=subtree_params,
            target_inside=subtree_clause,
            target_params=subtree_params,
            counterpart=counterpart,
            counterpart_on="target",
            inbound=False,
            with_lists=False,
            max_list=max_list,
        )
        bridges, bridge_total = self._subtree_dynamic_bridges(
            subtree_clause, subtree_params, max_list
        )
        lists_truncated = (
            inbound.file_total > max_list
            or inbound.path_total > max_list
            or bridge_total > max_list
        )
        return SubtreeDependencyResult(
            inbound, outbound, bridges, bridge_total, lists_truncated
        )

    def _subtree_crossing(
        self,
        *,
        source_outside: str,
        source_params: tuple[str, ...],
        target_inside: str,
        target_params: tuple[str, ...],
        counterpart: str | None,
        counterpart_on: str,
        inbound: bool = True,
        with_lists: bool = True,
        max_list: int,
    ) -> SubtreeCrossingReport:
        """One crossing direction: tier×attribution counts, plus ranked lists when asked.

        ``with_lists=False`` skips the four list/total aggregates — four whole-table scans a
        caller that never reads them should not pay for (AC5).
        """
        st_under = target_inside.replace("path", "n.file_path")
        st_under_n2 = target_inside.replace("path", "n2.file_path")
        st_under_e = source_outside.replace("path", "e.file_path")
        where_params: list[object] = list(source_params)
        if inbound:
            source_filter = f"NOT ({st_under_e})"
            target_exists = (
                "EXISTS (SELECT 1 FROM nodes n "
                f"WHERE n.qualified_name = e.target_qname AND ({st_under}))"
            )
            where_params.extend(target_params)
            attrib_outside = (
                "EXISTS (SELECT 1 FROM nodes n2 "
                "WHERE n2.qualified_name = e.target_qname "
                f"AND NOT ({st_under_n2}))"
            )
            path_join = (
                "JOIN nodes n ON n.qualified_name = e.target_qname "
                f"AND ({st_under})"
            )
            path_params_base = list(target_params)
        else:
            source_filter = f"({st_under_e})"
            target_exists = (
                "EXISTS (SELECT 1 FROM nodes n "
                f"WHERE n.qualified_name = e.target_qname AND NOT ({st_under}))"
            )
            where_params.extend(target_params)
            attrib_outside = (
                "EXISTS (SELECT 1 FROM nodes n2 "
                "WHERE n2.qualified_name = e.target_qname "
                f"AND ({st_under_n2}))"
            )
            path_join = (
                "JOIN nodes n ON n.qualified_name = e.target_qname "
                f"AND NOT ({st_under})"
            )
            path_params_base = list(target_params)
        counterpart_filter = ""
        cp_path_params: list[str] = []
        if counterpart:
            cp_clause, cp_params = _path_under(counterpart, "path")
            cp_path_params = list(cp_params)
            if counterpart_on == "source":
                counterpart_filter = (
                    f" AND ({cp_clause.replace('path', 'e.file_path')})"
                )
                where_params.extend(cp_params)
            else:
                cp_node = cp_clause.replace("path", "nc.file_path")
                counterpart_filter = (
                    " AND EXISTS (SELECT 1 FROM nodes nc "
                    f"WHERE nc.qualified_name = e.target_qname AND ({cp_node}))"
                )
                where_params.extend(cp_params)
                path_join += f" AND ({cp_clause.replace('path', 'n.file_path')})"
                path_params_base.extend(cp_path_params)
        base_where = (
            f"{source_filter} AND {target_exists} "
            "AND e.target_qname IS NOT NULL AND e.target_qname != ''"
            f"{counterpart_filter}"
        )
        bind_params: list[object] = [
            _RESOLVED,
            *target_params,
            *source_params,
            *target_params,
        ]
        if counterpart:
            bind_params.extend(cp_path_params)
        attrib_case = (
            f"CASE WHEN {attrib_outside} THEN 'unattributable' ELSE 'attributable' END"
        )
        tier_sql = (
            f"SELECT COALESCE(e.confidence_tier, ?) AS tier, {attrib_case} AS attribution, "
            f"COUNT(*) FROM edges e WHERE {base_where} "
            "GROUP BY tier, attribution ORDER BY tier, attribution"
        )
        by_tier: dict[str, SubtreeTierAttribution] = {}
        for tier, attribution, count in self._conn.execute(
            tier_sql, tuple(bind_params)
        ):
            bucket = by_tier.setdefault(
                str(tier), SubtreeTierAttribution(0, 0)
            )
            if str(attribution) == "unattributable":
                by_tier[str(tier)] = SubtreeTierAttribution(
                    bucket.attributable, bucket.unattributable + int(count)
                )
            else:
                by_tier[str(tier)] = SubtreeTierAttribution(
                    bucket.attributable + int(count), bucket.unattributable
                )
        where_tuple = tuple(where_params)
        if not with_lists:
            return SubtreeCrossingReport(by_tier, [], [], 0, 0)
        file_sql = (
            "SELECT e.file_path AS path, COUNT(*) AS edges FROM edges e "
            f"WHERE {base_where} GROUP BY e.file_path "
            "ORDER BY edges DESC, path ASC LIMIT ?"
        )
        ranked_files = self._rows(
            ("path", "edges"),
            file_sql,
            (*where_tuple, max_list),
        )
        file_total = int(
            self._conn.execute(
                f"SELECT COUNT(DISTINCT e.file_path) FROM edges e WHERE {base_where}",
                where_tuple,
            ).fetchone()[0]
        )
        path_sql = (
            f"SELECT n.file_path AS path, COUNT(*) AS edges FROM edges e {path_join} "
            f"WHERE {base_where} GROUP BY n.file_path "
            "ORDER BY edges DESC, path ASC LIMIT ?"
        )
        path_query_params = tuple(path_params_base + list(where_params) + [max_list])
        path_count_params = tuple(path_params_base + list(where_params))
        ranked_paths = self._rows(
            ("path", "edges"),
            path_sql,
            path_query_params,
        )
        path_total = int(
            self._conn.execute(
                f"SELECT COUNT(DISTINCT n.file_path) FROM edges e {path_join} "
                f"WHERE {base_where}",
                path_count_params,
            ).fetchone()[0]
        )
        return SubtreeCrossingReport(
            by_tier, ranked_files, ranked_paths, file_total, path_total
        )

    def _subtree_dynamic_bridges(
        self, subtree_clause: str, subtree_params: tuple[str, ...], max_list: int
    ) -> tuple[list[Row], int]:
        """Files whose only link into ``subtree`` symbols is ``DYNAMIC`` (task 120 AC4)."""
        target_inside = subtree_clause.replace("path", "n.file_path")
        where = (
            "e.confidence_tier = 'DYNAMIC' "
            "AND e.target_qname IS NOT NULL AND e.target_qname != '' "
            f"AND EXISTS (SELECT 1 FROM nodes n WHERE n.qualified_name = e.target_qname "
            f"AND ({target_inside})) "
            "AND NOT EXISTS ("
            "  SELECT 1 FROM edges e2 WHERE e2.file_path = e.file_path "
            "  AND e2.target_qname = e.target_qname AND e2.confidence_tier = ?"
            ")"
        )
        params = (*subtree_params, _RESOLVED)
        total = int(
            self._conn.execute(
                f"SELECT COUNT(DISTINCT e.file_path) FROM edges e WHERE {where}",
                params,
            ).fetchone()[0]
        )
        rows = self._rows(
            ("path", "edges"),
            f"SELECT e.file_path AS path, COUNT(*) AS edges FROM edges e WHERE {where} "
            "GROUP BY e.file_path ORDER BY edges DESC, path ASC LIMIT ?",
            (*params, max_list),
        )
        return rows, total

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
        for name in _REACH_TEMPS:
            self._conn.execute(f"DROP TABLE IF EXISTS temp.{name}")

    def _tour_drop_temps(self) -> None:
        for name in (
            "tour_seen",
            "tour_frontier",
            "tour_next",
            "tour_before",
            "tour_out_degree",
            "tour_universe",
        ):
            self._conn.execute(f"DROP TABLE IF EXISTS temp.{name}")

    def _tour_prune_seen(self, max_nodes: int) -> None:
        """Earliest round first, then seeds, then shallowest depth (tie: file_path ASC).

        ``round`` leads so a later re-seed round can only fill room the entry-seeded walk
        left over — it never evicts a file the entry points reached.
        """
        self._conn.execute(
            "DELETE FROM temp.tour_seen WHERE file_path NOT IN ("
            "  SELECT file_path FROM ("
            "    SELECT file_path FROM temp.tour_seen "
            "    ORDER BY round ASC, is_seed DESC, depth ASC, file_path ASC LIMIT ?"
            "  )"
            ")",
            (max_nodes,),
        )

    def _tour_seen_count(self) -> int:
        (count,) = self._conn.execute("SELECT COUNT(*) FROM temp.tour_seen").fetchone()
        return int(count)

    def _tour_build_out_degree(self) -> None:
        """One pass: each module's out-degree — how many distinct modules it depends on (106).

        Out-degree, not total degree: what the reading order wants next is a file that *leads*
        somewhere. One grouped scan, so ranking never traverses the graph (R4.3).
        """
        self._conn.execute(
            "CREATE TEMP TABLE tour_out_degree AS "
            "SELECT src.file_path AS file_path, "
            "       COUNT(DISTINCT tgt.file_path) AS out_degree "
            "FROM edges e "
            "JOIN nodes src ON src.qualified_name = e.source_qname "
            "JOIN nodes tgt ON tgt.qualified_name = e.target_qname "
            "WHERE e.target_qname IS NOT NULL AND src.file_path <> tgt.file_path "
            "GROUP BY src.file_path"
        )
        self._conn.execute(
            "CREATE UNIQUE INDEX temp.idx_tour_out_degree ON tour_out_degree (file_path)"
        )

    def _tour_entry_seeds(self, limit: int) -> list[str]:
        """The reading order's roots: no inbound cross-file edge, heaviest first (087 / 106 / 131).

        Prefer roots that lead somewhere (out-degree > 0). A zero-outbound root is not a place to
        start reading (131); only when every root is isolated do we fall back to path/degree order.
        """
        inbound = (
            "SELECT DISTINCT tgt.file_path FROM edges e "
            "JOIN nodes src ON src.qualified_name = e.source_qname "
            "JOIN nodes tgt ON tgt.qualified_name = e.target_qname "
            "WHERE e.target_qname IS NOT NULL AND src.file_path <> tgt.file_path"
        )
        leading = self._tour_ranked(
            f"n.file_path NOT IN ({inbound}) AND COALESCE(d.out_degree, 0) > 0", limit
        )
        if leading:
            return leading
        return self._tour_ranked(f"n.file_path NOT IN ({inbound})", limit)

    def _tour_ranked_unseen(self, limit: int) -> list[str]:
        """The widest-reaching indexed files the walk has not admitted yet (R4.2)."""
        return self._tour_ranked(
            "n.file_path NOT IN (SELECT file_path FROM temp.tour_seen)", limit
        )

    def _tour_ranked(self, where: str, limit: int) -> list[str]:
        """Candidates by out-degree DESC then ``file_path`` ASC — total over a unique key (R4.2)."""
        return [
            str(row[0])
            for row in self._conn.execute(
                "SELECT n.file_path, COALESCE(d.out_degree, 0) AS out_degree FROM nodes n "
                "JOIN temp.tour_universe u ON u.file_path = n.file_path "
                "LEFT JOIN temp.tour_out_degree d ON d.file_path = n.file_path "
                f"WHERE {where} "
                "GROUP BY n.file_path ORDER BY out_degree DESC, n.file_path ASC LIMIT ?",
                (limit,),
            )
        ]

    def _tour_admit_seeds(self, seeds: Sequence[str], round_no: int) -> None:
        """Plant this round's seeds in both ``tour_seen`` and the frontier."""
        self._conn.executemany(
            "INSERT OR IGNORE INTO temp.tour_seen (file_path, depth, is_seed, round) "
            "VALUES (?, 0, 1, ?)",
            [(path, round_no) for path in seeds],
        )
        self._conn.executemany(
            "INSERT OR IGNORE INTO temp.tour_frontier (file_path, depth) VALUES (?, 0)",
            [(path,) for path in seeds],
        )

    def _tour_expand(self, max_nodes: int, round_no: int) -> None:
        """Drain the frontier wave by wave; only newly admitted files expand the next wave."""
        conn = self._conn
        expand_sql = (
            "INSERT INTO temp.tour_next (file_path, depth) "
            "SELECT DISTINCT tgt.file_path, f.depth + 1 "
            "FROM temp.tour_frontier f "
            "JOIN nodes src ON src.file_path = f.file_path "
            "JOIN edges e ON e.source_qname = src.qualified_name "
            "JOIN nodes tgt ON tgt.qualified_name = e.target_qname "
            "WHERE e.target_qname IS NOT NULL AND tgt.file_path <> src.file_path "
            "AND tgt.file_path IN (SELECT file_path FROM temp.tour_universe)"
        )
        while conn.execute("SELECT 1 FROM temp.tour_frontier LIMIT 1").fetchone() is not None:
            conn.execute("DROP TABLE IF EXISTS temp.tour_next")
            conn.execute(
                "CREATE TEMP TABLE tour_next (file_path TEXT NOT NULL, depth INT NOT NULL)"
            )
            conn.execute(expand_sql)
            conn.execute("DROP TABLE IF EXISTS temp.tour_before")
            conn.execute(
                "CREATE TEMP TABLE tour_before AS SELECT file_path FROM temp.tour_seen"
            )
            before = self._tour_seen_count()
            conn.execute(
                "INSERT OR IGNORE INTO temp.tour_seen (file_path, depth, is_seed, round) "
                "SELECT n.file_path, MIN(n.depth), 0, ? FROM temp.tour_next n "
                "GROUP BY n.file_path",
                (round_no,),
            )
            self._tour_prune_seen(max_nodes)
            conn.execute("DELETE FROM temp.tour_frontier")
            if self._tour_seen_count() <= before:  # nothing new admitted: cycle or budget
                break
            conn.execute(
                "INSERT INTO temp.tour_frontier (file_path, depth) "
                "SELECT s.file_path, s.depth FROM temp.tour_seen s "
                "WHERE s.file_path NOT IN (SELECT file_path FROM temp.tour_before)"
            )

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

    def names_defined_in_files(
        self, file_paths: Sequence[str], names: Sequence[str]
    ) -> frozenset[tuple[str, str]]:
        """``(file_path, name)`` pairs that have ≥1 node — one DISTINCT query (331)."""
        files = list(dict.fromkeys(p for p in file_paths if p))
        name_list = list(dict.fromkeys(n for n in names if n))
        if not files or not name_list:
            return frozenset()
        placeholders_f = ",".join("?" * len(files))
        placeholders_n = ",".join("?" * len(name_list))
        sql = (
            f"SELECT DISTINCT file_path, name FROM nodes "
            f"WHERE file_path IN ({placeholders_f}) AND name IN ({placeholders_n})"
        )
        return frozenset(
            (str(path), str(name))
            for path, name in self._conn.execute(sql, (*files, *name_list))
        )

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
        path_prefix: str | None = None,
        exclude_test_sources: bool = False,
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
        where, params = _with_path_prefix(where, params, path_prefix, column="file_path")
        where, params = _with_exclude_test_nodes(
            where, params, exclude_test_sources, column="is_test"
        )
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
        language: str | None = None,
        distinct_qnames: bool = False,
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
        kind_sql = " AND nodes.kind = ?" if kind is not None else ""
        # The language predicate rides the same statement as the row limit, never a post-filter.
        source = "nodes JOIN files ON files.path = nodes.file_path" if language else "nodes"
        language_sql = " AND files.language = ?" if language else ""
        grouped: dict[str, list[Row]] = {key: [] for key in ordered_keys}
        # Full `_NODE_ORDER` inside the partition — required for `name` keys where
        # `qualified_name` still varies within the partition (R4.2 / AC1).
        rank, keep = _rank_window(f"nodes.{key_column}", "nodes.qualified_name", distinct_qnames)
        for chunk in _chunks(ordered_keys, _IN_CHUNK):
            placeholders = ", ".join("?" for _ in chunk)
            sql = (
                f"SELECT id, {_NODE_COLUMNS} FROM ("
                f"  SELECT nodes.id, {_NODE_COLUMNS_JOINED}, {rank} "
                f"  FROM {source} WHERE nodes.{key_column} IN ({placeholders})"
                f"{kind_sql}{language_sql}"
                f") WHERE {keep}rn <= ? "
                f"ORDER BY {_NODE_ORDER}"
            )
            params: list[object] = [*chunk]
            if kind is not None:
                params.append(kind)
            if language:
                params.append(language)
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
        order: str = _EDGE_ORDER,
        distinct_sources: bool = False,
    ) -> list[Row]:
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        clause, params = self._edge_where(where, kinds, extra)
        if distinct_sources:
            sql = (
                f"SELECT id, {_EDGE_COLUMNS} FROM edges WHERE id IN ("
                f"SELECT MIN(id) FROM edges WHERE {clause} GROUP BY source_qname"
                f") ORDER BY {order} LIMIT ? OFFSET ?"
            )
        else:
            sql = (
                f"SELECT id, {_EDGE_COLUMNS} FROM edges WHERE {clause} "
                f"ORDER BY {order} LIMIT ? OFFSET ?"
            )
        return self._rows(EDGE_ROW_KEYS, sql, (value, *params, limit, offset))

    def _count_edges(
        self,
        where: str,
        value: str,
        kinds: Sequence[str] | None,
        *,
        extra: _Predicate = None,
        distinct_sources: bool = False,
    ) -> int:
        clause, params = self._edge_where(where, kinds, extra)
        expr = "COUNT(DISTINCT edges.source_qname)" if distinct_sources else "COUNT(*)"
        sql = f"SELECT {expr} FROM edges WHERE {clause}"
        return int(self._conn.execute(sql, (value, *params)).fetchone()[0])

    @staticmethod
    def _edge_where(
        where: str, kinds: Sequence[str] | None, extra: _Predicate
    ) -> tuple[str, tuple[object, ...]]:
        """One WHERE builder for both the row read and its count, so they cannot diverge.

        Every column it emits is ``edges.``-qualified, and so is every ``where`` it is given: a
        read that joins ``nodes`` shares column names with it, and an unqualified one is a
        silent ambiguity rather than an error (262).
        """
        clauses: list[str] = [where]
        params: list[object] = []
        if kinds is not None:
            if not kinds:
                raise ValueError("kinds must be non-empty")
            clauses.append(f"edges.kind IN ({', '.join('?' for _ in kinds)})")
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
        path_prefix: str | None = None,
        exclude_test_sources: bool = False,
    ) -> int:
        pattern = f"{_like_literal(query.lower())}%"
        where = "(LOWER(name) LIKE ? ESCAPE '!' OR LOWER(qualified_name) LIKE ? ESCAPE '!')"
        params: tuple[object, ...] = (pattern, pattern)
        if kind is not None:
            where = f"{where} AND kind = ?"
            params = (*params, kind)
        where, params = _with_namespace(where, params, namespace, qname_column="qualified_name")
        where, params = _with_path_prefix(where, params, path_prefix, column="file_path")
        where, params = _with_exclude_test_nodes(
            where, params, exclude_test_sources, column="is_test"
        )
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


def _path_under(prefix: str, column: str) -> tuple[str, tuple[str, str]]:
    """SQL predicate: ``column`` is the prefix or a path beneath it (task 120)."""
    normalized = prefix if prefix.endswith("/") else f"{prefix}/"
    bare = normalized.rstrip("/")
    return (
        f"({column} LIKE ? ESCAPE '!' OR {column} = ?)",
        (f"{_like_literal(normalized)}%", bare),
    )


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


def _with_path_prefix(
    where: str,
    params: tuple[object, ...],
    path_prefix: str | None,
    *,
    column: str,
) -> tuple[str, tuple[object, ...]]:
    """AND a path-under predicate; ``None`` leaves the clause unchanged (315)."""
    if path_prefix is None:
        return where, params
    clause, extras = _path_under(path_prefix, column)
    return f"({where}) AND {clause}", (*params, *extras)


def _with_exclude_test_nodes(
    where: str,
    params: tuple[object, ...],
    exclude_test_sources: bool,
    *,
    column: str = "nodes.is_test",
) -> tuple[str, tuple[object, ...]]:
    """AND ``is_test = 0`` when filtering; default leaves the clause unchanged (332)."""
    if not exclude_test_sources:
        return where, params
    return f"({where}) AND COALESCE({column}, 0) = 0", params


def _path_prefix_predicate(path_prefix: str | None) -> _Predicate:
    """Edge-source path filter for find_references (315); reuses ``_path_under``."""
    if path_prefix is None:
        return None
    clause, extras = _path_under(path_prefix, "edges.file_path")
    return clause, extras
