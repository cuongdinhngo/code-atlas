"""Task 327 — read_symbol(path_prefix=) picks one ambiguous definition.

078 refused a multi-definition qname and routed to search_symbol, which returns the same
qname — a dead end. path_prefix (315's validator) filters definition rows before the
ambiguity test; the refusal routes back to read_symbol with the argument named (R5.4).
"""

from __future__ import annotations

from pathlib import Path

from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol
from code_atlas.tools.nav_result import (
    AMBIGUOUS_DEFINITIONS,
    REASON_OK,
    REASON_PATH_EXCLUDED,
    REASON_SUBJECT_AMBIGUOUS,
    TRY_INSTEAD_HINT_PATH_PREFIX,
    TRY_INSTEAD_READ_SYMBOL,
)
from tests.test_nav_tools import (  # noqa: F401
    db_config,
    node,
    seed_file,
    store,
)


def _seed_two_trees(graph: GraphStore, root: Path) -> None:
    """Same qname in region/a.php and region/b.php."""
    seed_file(
        graph,
        "region/a.php",
        [node("Function", "dup", "\\dup", "region/a.php")],
        [],
        root=root,
    )
    seed_file(
        graph,
        "region/b.php",
        [node("Function", "dup", "\\dup", "region/b.php")],
        [],
        root=root,
    )


def test_path_prefix_picks_one_definition(tmp_path: Path, store) -> None:  # noqa: F811
    """AC1: path_prefix naming one site returns that body and its file."""
    _seed_two_trees(store, tmp_path)
    result = read_symbol.create(db_config(tmp_path))(
        "\\dup", detail_level="minimal", path_prefix="region/a.php"
    )
    assert result["found"] is True
    assert result["reason"] == REASON_OK
    assert result["file"] == "region/a.php"
    assert result["source"]
    assert AMBIGUOUS_DEFINITIONS not in result


def test_path_prefix_matching_both_still_refuses(tmp_path: Path, store) -> None:  # noqa: F811
    """AC2: path_prefix matching both still refuses, listing both."""
    _seed_two_trees(store, tmp_path)
    result = read_symbol.create(db_config(tmp_path))(
        "\\dup", detail_level="minimal", path_prefix="region/"
    )
    assert result["found"] is False
    assert result["reason"] == REASON_SUBJECT_AMBIGUOUS
    assert result["source"] == ""
    assert {str(s["file"]) for s in result[AMBIGUOUS_DEFINITIONS]} == {
        "region/a.php",
        "region/b.php",
    }


def test_path_prefix_matching_neither_names_the_filter(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """AC3: path_prefix matching neither → path_excluded naming the filter, not a body (339)."""
    _seed_two_trees(store, tmp_path)
    result = read_symbol.create(db_config(tmp_path))(
        "\\dup", detail_level="minimal", path_prefix="other/"
    )
    assert result["found"] is False
    assert result["reason"] == REASON_PATH_EXCLUDED
    assert result["path_excluded"] == ["region/a.php", "region/b.php"]
    assert result["source"] == ""
    assert result["path_prefix"] == "other/"
    assert "file" not in result


def test_refusal_routes_to_read_symbol_with_path_prefix_hint(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """AC4: refusal's try_instead names read_symbol; unique case unchanged."""
    _seed_two_trees(store, tmp_path)
    refused = read_symbol.create(db_config(tmp_path))("\\dup", detail_level="minimal")
    assert refused["try_instead"] == TRY_INSTEAD_READ_SYMBOL
    assert refused["try_instead_hint"] == TRY_INSTEAD_HINT_PATH_PREFIX

    seed_file(
        store,
        "solo.php",
        [node("Function", "solo", "\\solo", "solo.php")],
        [],
        root=tmp_path,
    )
    unique = read_symbol.create(db_config(tmp_path))("\\solo", detail_level="minimal")
    assert unique["found"] is True
    assert unique["file"] == "solo.php"
    assert AMBIGUOUS_DEFINITIONS not in unique
    assert "try_instead" not in unique
