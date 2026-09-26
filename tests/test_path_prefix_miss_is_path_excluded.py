"""Task 339 — a path_prefix that excludes every definition answers path_excluded, not absence."""

from __future__ import annotations

from pathlib import Path

from code_atlas.tools import read_symbol, search_symbol
from code_atlas.tools.nav_result import REASON_NO_SUCH_SYMBOL, REASON_PATH_EXCLUDED
from tests.test_nav_tools import db_config, node, seed_file, store  # noqa: F401

MIGRATION = "db/migrations/V1__gen.sql"


def _seed(graph, root: Path) -> None:  # noqa: ANN001
    seed_file(graph, MIGRATION, [node("Function", "Gen", "dbo.Gen", MIGRATION)], [], root=root)


def test_a_file_name_prefix_names_the_file_it_excluded(tmp_path: Path, store) -> None:  # noqa: F811
    """AC1: a file-name prefix is not a directory — the miss says excluded and names the file."""
    _seed(store, tmp_path)
    result = read_symbol.create(db_config(tmp_path))(
        "dbo.Gen", path_prefix="db/migrations/V1"
    )
    assert result["found"] is False
    assert result["reason"] == REASON_PATH_EXCLUDED
    assert result["path_excluded"] == [MIGRATION]
    assert result["path_prefix"] == "db/migrations/V1"


def test_the_shape_matches_search_symbol(tmp_path: Path, store) -> None:  # noqa: F811
    """C2 / R6.7: both tools answer the same miss with the same reason and the same list."""
    _seed(store, tmp_path)
    config = db_config(tmp_path)
    read = read_symbol.create(config)("dbo.Gen", path_prefix="db/migrations/V1")
    search = search_symbol.create(config)("dbo.Gen", path_prefix="db/migrations/V1")
    assert search["reason"] == read["reason"] == REASON_PATH_EXCLUDED
    assert search["path_excluded"] == read["path_excluded"]


def test_a_qname_that_does_not_exist_is_still_no_such_symbol(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """AC2: absence stays absence, whatever the prefix."""
    _seed(store, tmp_path)
    tool = read_symbol.create(db_config(tmp_path))
    for prefix in ("db/migrations/V1", "db/", "elsewhere/"):
        result = tool("dbo.Missing", path_prefix=prefix)
        assert result["reason"] == REASON_NO_SUCH_SYMBOL, prefix
        assert "path_excluded" not in result
