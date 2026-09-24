"""``check_column_defaults`` — which writers of a table omit a defaulted column? (task 194).

Field retro round 12 §15 named this question verbatim and answered it by hand: four grep passes, a
purpose-built script mapping each write to its enclosing routine, and two live-database round-trips.
Tier 2 (022) put those facts in the graph; this reads them back in one call.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Literal

from code_atlas.config import Config, clamp_limit
from code_atlas.store import GraphStore
from code_atlas.tools.coverage import attach_coverage_note, covered_languages
from code_atlas.tools.nav_result import (
    AMBIGUOUS_DEFINITIONS,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_NOT_INDEXED,
    REASON_OK,
    REASON_SUBJECT_AMBIGUOUS,
    TRY_INSTEAD_SEARCH_SYMBOL,
    attach_limit_capped,
    attach_resolved_qname,
    attach_try_instead,
    definition_sites,
)

NAME = "check_column_defaults"

DetailLevel = Literal["minimal", "standard"]

# This tool's own status vocabulary, beside the payload's fixed nav REASON codes (the same split
# ``architecture_rules.py`` keeps). A table nothing writes is UNMEASURED, never "nobody omits it".
STATUS_CHECKED = "checked"
STATUS_NO_WRITERS = "table_has_no_writers"
# Present only when linked writers exist AND unlinked WRITES still name this table (215).
WRITERS_PARTIAL_KEY = "writers_partial"
WRITERS_PARTIAL_HINT_KEY = "writers_partial_hint"
WRITERS_PARTIAL_HINT = (
    "Unlinked WRITES still name this table (case or schema mismatch, "
    "or forms that emit no edge: dynamic SQL / CREATE-inside-string)."
)

# A missed table name routes to the search that lists the schema-qualified tables (320).
TRY_INSTEAD_HINT_TABLE = (
    'search_symbol(query=<table name>, kind="Table") lists the schema-qualified tables; '
    "pass one of those qnames as `table`."
)

_WRITES = ("WRITES",)
_CONTAINS = ("CONTAINS",)
# One page of the graph's own edges, not of the answer: the arithmetic needs every writer, and the
# caller's ``limit`` pages the COLUMNS it gets back.
_WALK = 10_000

__all__ = [
    "NAME",
    "STATUS_CHECKED",
    "STATUS_NO_WRITERS",
    "WRITERS_PARTIAL_KEY",
    "WRITERS_PARTIAL_HINT_KEY",
    "WRITERS_PARTIAL_HINT",
    "TRY_INSTEAD_HINT_TABLE",
    "create",
]


def _sources(store: GraphStore, target: str) -> set[str]:
    """Every routine with a ``WRITES`` edge onto ``target``."""
    return {
        str(row["source_qname"])
        for row in store.edges_by_target(target, kinds=_WRITES, limit=_WALK)
    }


def _declared_default(node: dict[str, object]) -> str | None:
    """The DEFAULT expression a ``Column`` node declares, or None when it declares none."""
    raw = node.get("extra")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        extra = json.loads(raw)
    except json.JSONDecodeError:
        return None
    value = extra.get("default") if isinstance(extra, dict) else None
    return value if isinstance(value, str) else None


def _columns_of(
    store: GraphStore, table: str
) -> tuple[list[str], list[tuple[str, str]], dict[str, int]]:
    """Every column of ``table`` in qname order, the DEFAULT subset, and CONTAINS multiplicity.

    Both lists are needed and they differ: the DEFAULT subset is what gets reported, while
    ``writers_total`` is *"the total that write the table"* (R2) — a routine writing only
    undefaulted columns is still a writer, and omitting it understates every ratio's denominator.
    Multiplicity (215): two CONTAINS edges for one column must not yield two rows.
    """
    declarations: dict[str, int] = {}
    for edge in store.edges_by_source(table, kinds=_CONTAINS, limit=_WALK):
        qname = str(edge["target_raw"])
        declarations[qname] = declarations.get(qname, 0) + 1
    qnames = sorted(declarations)
    if not qnames:
        return [], [], {}
    found = store.nodes_by_qualified_names(qnames, kind="Column", limit=1)
    columns = [qname for qname in qnames if found.get(qname)]
    defaulted: list[tuple[str, str]] = []
    for qname in columns:
        declared = _declared_default((found[qname])[0])
        if declared is not None:
            defaulted.append((qname, declared))
    return columns, defaulted, declarations


def _row(
    column: str,
    declared: str,
    *,
    named: set[str],
    unmeasured: set[str],
    writers: set[str],
    detail_level: DetailLevel,
    declarations: int,
) -> dict[str, object]:
    """One column's verdict. ``omitted_by`` is ABSENT when no writer was measurable (R5.6)."""
    omitted = writers - named - unmeasured
    row: dict[str, object] = {
        "column": column,
        "default": declared,
        "status": STATUS_CHECKED if writers else STATUS_NO_WRITERS,
        "writers_total": len(writers),
    }
    if declarations > 1:
        row["declarations"] = declarations
    if not writers:
        # No `omitted_by`, no `omitted_count`: an empty list here reads as "nobody omits it", which
        # is the modelled zero this tool exists to avoid answering.
        return row
    row["omitted_count"] = len(omitted)
    if detail_level == "standard":
        row["omitted_by"] = sorted(omitted)
        row["named_by"] = sorted(named)
        if unmeasured:
            row["unmeasured"] = sorted(unmeasured)
    return row


def _envelope(
    *,
    table: str,
    config: Config,
    indexed: bool,
    reason: str,
    results: list[dict[str, object]] | None = None,
    truncated: bool = False,
    total_count: int = 0,
) -> dict[str, object]:
    return {
        "index_root": config.index_root,
        "indexed": indexed,
        "reason": reason,
        "results": results if results is not None else [],
        "table": table,
        "total_count": total_count,
        "truncated": truncated,
    }


def create(config: Config) -> Callable[..., dict[str, object]]:
    """Bind the tool to one repo's configuration."""

    def check_column_defaults(
        table: str,
        column: str | None = None,
        detail_level: DetailLevel = "standard",
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, object]:
        """Which writers of this table omit a column that has a DEFAULT, and what is that DEFAULT?

        Answers the defect class *"a column whose value comes from a DEFAULT because every writer
        omits it"*. With no ``column``, scans every column of ``table`` that declares a DEFAULT;
        with one, reports just that column. Each row carries ``omitted_count`` against
        ``writers_total`` — a ratio, not a bare list — plus ``omitted_by`` and ``named_by`` at
        ``standard``. A writer that named no columns at all is ``unmeasured``, never counted as
        omitting; a table with no recorded writers answers ``status: table_has_no_writers`` and
        carries **no** ``omitted_by``, because an empty list there would claim a zero the graph
        cannot see. When linked writers exist but unlinked ``WRITES`` still name the table, the
        envelope carries ``writers_partial`` and a hint naming the remaining forms (215). Duplicate
        ``CONTAINS`` declarations collapse to one row with ``declarations`` when N>1. Needs a
        SQL-layer index (task 022); ``column`` takes the full member qname
        (``dbo.Trans::ChangeUser``) or the bare column name.

        ``table`` may be bare (``Trans``): one indexed Table of that name is measured and named in
        ``resolved_qname``; several (one per schema) answer ``reason: subject_ambiguous`` with no
        rows and each qualified candidate in ``ambiguous_definitions``; none answers
        ``no_such_symbol`` with ``try_instead: search_symbol`` (320).
        """
        if offset < 0:
            raise ValueError(f"offset must be >= 0, got {offset}")
        cap, limit_clamped = clamp_limit(limit, config.page_limit)
        if cap < 1:
            raise ValueError(f"limit must be >= 1, got {cap}")
        if not config.db_path.is_file():
            return _envelope(
                table=table, config=config, indexed=False, reason=REASON_NOT_INDEXED
            )

        with GraphStore(config.db_path) as store:
            covered = covered_languages(store)
            asked = table
            if not store.nodes_by_qualified_name(table, kind="Table", limit=1):
                resolved, reason, extra = _resolve_bare_table(store, table, limit=config.page_limit)
                if resolved is None:
                    refused = _envelope(table=table, config=config, indexed=True, reason=reason)
                    refused.update(extra)
                    return attach_coverage_note(refused, config, covered, detail_level=detail_level)
                table = resolved
            all_columns, columns, declarations = _columns_of(store, table)
            if column is not None:
                wanted = column if "::" in column else f"{table}::{column}"
                columns = [pair for pair in columns if pair[0] == wanted]
            if not columns:
                return attach_coverage_note(
                    attach_resolved_qname(
                        _envelope(
                            table=asked, config=config, indexed=True, reason=REASON_NO_MATCHES
                        ),
                        asked=asked,
                        answered=table,
                    ),
                    config,
                    covered,
                    detail_level=detail_level,
                )
            # A writer reaching the table itself named no columns (022's discriminator), so it is
            # unmeasured for every column rather than an omitter of each.
            unmeasured = _sources(store, table)
            by_column = {qname: _sources(store, qname) for qname in all_columns}
            named_by_column = {qname: by_column[qname] for qname, _ in columns}
            writers = unmeasured.union(*by_column.values()) if by_column else set(unmeasured)
            rows = [
                _row(
                    qname,
                    declared,
                    named=named_by_column[qname],
                    unmeasured=unmeasured,
                    writers=writers,
                    detail_level=detail_level,
                    declarations=declarations.get(qname, 1),
                )
                for qname, declared in columns
            ]
            page = rows[offset : offset + cap]
            payload = _envelope(
                table=asked,
                config=config,
                indexed=True,
                reason=REASON_OK,
                results=page,
                truncated=offset + len(page) < len(rows),
                total_count=len(rows),
            )
            # Partial only when writers exist: empty stays table_has_no_writers (194 AC2 / 215 AC5).
            if writers and store.has_unlinked_writes_relating_to(table):
                payload[WRITERS_PARTIAL_KEY] = True
                payload[WRITERS_PARTIAL_HINT_KEY] = WRITERS_PARTIAL_HINT
            attach_limit_capped(payload, cap=cap, clamped=limit_clamped)
            # Only on the fallback arm: the answer is about a qname the caller did not type (R5.6).
            attach_resolved_qname(payload, asked=asked, answered=table)
            return attach_coverage_note(payload, config, covered, detail_level=detail_level)

    return check_column_defaults


def _resolve_bare_table(
    store: GraphStore, name: str, *, limit: int
) -> tuple[str | None, str, dict[str, object]]:
    """``(qname, reason, extra)`` for a table name with no exact qname hit (320, 165-C1).

    One Table of that bare name is the subject. Several are a partition: refuse and name each
    qualified candidate rather than measure one schema's table. None keeps ``no_such_symbol``.
    """
    rows = store.nodes_by_name(name, kind="Table", limit=limit)
    qnames = list(dict.fromkeys(str(row["qualified_name"]) for row in rows))
    if len(qnames) == 1:
        return qnames[0], REASON_OK, {}
    if qnames:
        sites = definition_sites(rows)
        for site, row in zip(sites, rows, strict=True):
            site["qname"] = row["qualified_name"]
        return None, REASON_SUBJECT_AMBIGUOUS, {AMBIGUOUS_DEFINITIONS: sites}
    return (
        None,
        REASON_NO_SUCH_SYMBOL,
        attach_try_instead({}, TRY_INSTEAD_SEARCH_SYMBOL, TRY_INSTEAD_HINT_TABLE),
    )
