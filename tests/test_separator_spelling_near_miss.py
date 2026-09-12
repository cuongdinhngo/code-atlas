"""Task 249 — a miss whose only defect is the separator spelling gets the near-miss route.

Field shape: agent guesses ``dbo.T.col``; indexed form is ``dbo.T::col``. Substring/trigram
paths yield an empty candidate set, so 245's route never fires. Normalise the last separator
to MEMBER_SEPARATOR only on an empty primary answer, and label the hit ``separator_normalised``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from code_atlas import contract
from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol, search_symbol
from code_atlas.tools.nav_result import (
    REASON_INDEX_STALE,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_OK,
    REASON_SEPARATOR_NORMALISED,
    REASON_TOKEN_CANDIDATES,
    TRY_INSTEAD_FILE_OUTLINE,
    TRY_INSTEAD_HINT_MEMBER_SEPARATOR,
    TRY_INSTEAD_SEARCH_SYMBOL,
)
from tests.test_nav_tools import (  # noqa: F401 — store is a fixture
    db_config,
    node,
    seed_file,
    store,
)

COL_PATH = "schema/benefit.sql"
COL_QNAME = "dbo.Benefit::psi_file"
COL_DOTTED = "dbo.Benefit.psi_file"
PY_QNAME = "pkg.Thing"


def _seed_column(graph: GraphStore, root: Path) -> None:
    seed_file(
        graph,
        COL_PATH,
        [node("Column", "psi_file", COL_QNAME, COL_PATH)],
        [],
        root=root,
    )


def _count_searches(tool, query: str) -> tuple[dict[str, object], int]:
    real = GraphStore.search_nodes
    calls = {"n": 0}

    def wrapped(self: GraphStore, *args: object, **kwargs: object) -> object:
        calls["n"] += 1
        return real(self, *args, **kwargs)

    with patch.object(GraphStore, "search_nodes", wrapped):
        return tool(query), calls["n"]


def test_member_separator_variant_moves_only_the_last_separator() -> None:
    assert contract.member_separator_variant(COL_DOTTED) == COL_QNAME
    assert contract.member_separator_variant(r"\Ns\Class.method") == r"\Ns\Class::method"
    assert contract.member_separator_variant(COL_QNAME) is None
    assert contract.member_separator_variant("Foo") is None
    assert contract.member_separator_variant("") is None


def test_search_dotted_column_is_separator_normalised_near_miss(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC1: dotted guess → separator_normalised near-miss with FILE_OUTLINE route."""
    _seed_column(store, tmp_path)
    payload = search_symbol.create(db_config(tmp_path))(COL_DOTTED)
    assert payload["reason"] == REASON_SEPARATOR_NORMALISED
    assert payload["reason"] != REASON_OK
    assert payload["reason"] != REASON_NO_MATCHES
    assert payload["total_count"] == 1
    results = payload["results"]
    assert isinstance(results, list) and len(results) == 1
    assert results[0]["qname"] == COL_QNAME
    assert payload["try_instead"] == TRY_INSTEAD_FILE_OUTLINE
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_MEMBER_SEPARATOR


def test_read_dotted_column_is_separator_normalised_near_miss(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC2: read_symbol on the dotted guess returns the body as a named near-miss, not ok."""
    _seed_column(store, tmp_path)
    payload = read_symbol.create(db_config(tmp_path))(COL_DOTTED, detail_level="minimal")
    assert payload["reason"] == REASON_SEPARATOR_NORMALISED
    assert payload["reason"] != REASON_OK
    assert payload["found"] is True
    assert payload["qname"] == COL_DOTTED
    assert payload["source"]
    assert payload["try_instead"] == TRY_INSTEAD_FILE_OUTLINE
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_MEMBER_SEPARATOR


def test_double_miss_stays_byte_identical_no_matches(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC3 (249) + 253: separator retry empty then token arm labels the exhausted search."""
    _seed_column(store, tmp_path)
    tool = search_symbol.create(db_config(tmp_path))
    payload, n = _count_searches(tool, "dbo.Missing.col")
    assert n >= 2  # primary + separator retry (+ token searches when tokens remain)
    assert payload["reason"] == REASON_TOKEN_CANDIDATES
    assert payload["results"] == []
    assert payload["total_count"] == 0
    assert payload["candidates"] == []
    assert payload["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL
    assert "try_instead_hint" in payload


def test_no_separator_runs_exactly_one_lookup(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC4: bare name → one store search; helper yields no variant."""
    assert contract.member_separator_variant("psi_file") is None
    _seed_column(store, tmp_path)
    tool = search_symbol.create(db_config(tmp_path))
    _payload, n = _count_searches(tool, "psi_file")
    assert n == 1


def test_existing_dotted_qname_is_exact_hit_without_retry(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC5: a real ``.``-separated qname that is indexed returns ok on the primary lookup."""
    path = "pkg/thing.py"
    seed_file(
        store,
        path,
        [node("Class", "Thing", PY_QNAME, path)],
        [],
        root=tmp_path,
    )
    tool = search_symbol.create(db_config(tmp_path))
    payload, n = _count_searches(tool, PY_QNAME)
    assert n == 1
    assert payload["reason"] == REASON_OK
    results = payload["results"]
    assert isinstance(results, list) and results[0]["qname"] == PY_QNAME


def test_read_both_spellings_miss_stays_no_such_symbol(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC3 sibling on read: dotted miss with no :: form stays no_such_symbol."""
    _seed_column(store, tmp_path)
    payload = read_symbol.create(db_config(tmp_path))("dbo.Missing.col")
    assert payload["reason"] == REASON_NO_SUCH_SYMBOL
    assert payload["found"] is False


def test_retry_owes_the_same_freshness_verdict_as_the_correct_spelling(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """Review: a misspelled separator must not out-answer the spelling the guard refuses.

    The retry reads the same rows the ``::`` query reads, so an unrepairable subject file has to
    refuse on both — otherwise ``.`` is a route around the freshness verdict (R5.6).
    """
    _seed_column(store, tmp_path)
    (tmp_path / COL_PATH).unlink()
    tool = search_symbol.create(db_config(tmp_path))
    assert tool(COL_QNAME)["reason"] == REASON_INDEX_STALE
    assert tool(COL_DOTTED)["reason"] == REASON_INDEX_STALE
    assert read_symbol.create(db_config(tmp_path))(COL_DOTTED)["reason"] == REASON_INDEX_STALE
