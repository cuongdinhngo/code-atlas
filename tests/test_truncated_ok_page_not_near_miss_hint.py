"""Task 326 — a truncated reason=ok page must not carry the near-miss hint.

Field shape: search_symbol on a bare method / Table that floods past max_results still leads
with an exact hit (reason=ok), but _needs_narrowing_route's truncated arm attached
TRY_INSTEAD_HINT_NARROW_BY_QNAME ("substring near-misses, not hits"). Agents learned to ignore
the one hint that exists to stop them. Split: near-miss keeps today's hint; truncated-ok gets
HINT_NARROW_BY_FILTER (or would get none — design chose the filter hint per 245's same-finding
rule). AC1 red-arm on today's predicate; AC2/AC3 regression on substring + batch.
"""

from __future__ import annotations

from pathlib import Path

from code_atlas.store import GraphStore
from code_atlas.tools import search_symbol
from code_atlas.tools.nav_result import (
    REASON_OK,
    REASON_SUBSTRING_MATCH,
    TRY_INSTEAD_HINT_NARROW_BY_FILTER,
    TRY_INSTEAD_HINT_NARROW_BY_QNAME,
    TRY_INSTEAD_SEARCH_SYMBOL,
)
from tests.test_nav_tools import (  # noqa: F401 — store is a fixture
    db_config,
    node,
    seed_file,
    store,
)

NAME = "display"
NEAR_MISS_QUERY = "QuickAccess"
LIMIT = 5
HIT_COUNT = 15


def _seed_exact_method_flood(graph: GraphStore, root: Path) -> None:
    """Many exact-name Method hits so page 1 is truncated and still reason=ok."""
    for i in range(HIT_COUNT):
        path = f"src/Page{i}.php"
        qname = f"App\\Page{i}::{NAME}"
        seed_file(
            graph,
            path,
            [node("Method", NAME, qname, path)],
            [],
            root=root,
        )


def _seed_substring_flood(graph: GraphStore, root: Path) -> None:
    """Substring near-misses only — today's 245 shape, for AC2 regression."""
    for i in range(HIT_COUNT):
        path = f"src/Sub{i}.php"
        # Mid-string class token so FTS hits but is_direct_match is false (245).
        name = f"get{NEAR_MISS_QUERY}Thing{i}"
        qname = f"App\\Sub{i}::{name}"
        seed_file(
            graph,
            path,
            [node("Method", name, qname, path)],
            [],
            root=root,
        )


def test_truncated_ok_page_carries_filter_hint_not_near_miss(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC1: truncated reason=ok leading with exact hits → filter hint, never near-miss prose."""
    _seed_exact_method_flood(store, tmp_path)
    payload = search_symbol.create(db_config(tmp_path))(NAME, kind="Method", limit=LIMIT)
    assert payload["reason"] == REASON_OK
    assert payload["truncated"] is True
    assert payload["total_count"] == HIT_COUNT
    assert len(payload["results"]) == LIMIT  # type: ignore[arg-type]
    assert payload["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_NARROW_BY_FILTER
    assert payload["try_instead_hint"] != TRY_INSTEAD_HINT_NARROW_BY_QNAME


def test_substring_near_miss_keeps_today_hint(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC2: first page of only substring hits still carries HINT_NARROW_BY_QNAME."""
    _seed_substring_flood(store, tmp_path)
    payload = search_symbol.create(db_config(tmp_path))(
        NEAR_MISS_QUERY, kind="Method", limit=LIMIT
    )
    assert payload["reason"] == REASON_SUBSTRING_MATCH
    assert payload["truncated"] is True
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_NARROW_BY_QNAME


def test_batch_path_splits_the_two_findings(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC3: queries=[…] sweep carries each hint inside its subject, never on the envelope."""
    _seed_exact_method_flood(store, tmp_path)
    _seed_substring_flood(store, tmp_path)
    envelope = search_symbol.create(db_config(tmp_path))(
        queries=[NAME, NEAR_MISS_QUERY], kind="Method", limit=LIMIT
    )
    assert "try_instead" not in envelope
    assert "try_instead_hint" not in envelope
    by_q = {str(s["query"]): s for s in envelope["subjects"]}  # type: ignore[index]
    exact = by_q[NAME]
    assert exact["reason"] == REASON_OK
    assert exact["truncated"] is True
    assert exact["try_instead_hint"] == TRY_INSTEAD_HINT_NARROW_BY_FILTER
    near = by_q[NEAR_MISS_QUERY]
    assert near["reason"] == REASON_SUBSTRING_MATCH
    assert near["try_instead_hint"] == TRY_INSTEAD_HINT_NARROW_BY_QNAME
