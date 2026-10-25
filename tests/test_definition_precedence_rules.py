"""Task 414 — the order ``one_definition_first`` applies, on hand-built rows (no adapter needed).

Test copies settle first (394), the declared precedence next (414), migration versions after (403);
a cut fetch or a page that may hide a definition applies neither of the last two.
"""

from __future__ import annotations

import json

from code_atlas import contract
from code_atlas.tools.symbol_pointers import (
    DEFINITION_PRECEDENCE,
    MIGRATION_REDEFINITIONS,
    one_definition_first,
)

PRECEDENCE = ("schema/**",)


def row(path: str, *, is_test: bool = False, version: str | None = None) -> dict[str, object]:
    extra = json.dumps({contract.MIGRATION_VERSION_KEY: version}) if version else ""
    return {"file_path": path, "is_test": is_test, "extra": extra}


def files(rows: list[dict[str, object]]) -> list[object]:
    return [found["file_path"] for found in rows]


def test_a_test_copy_does_not_stop_the_precedence_deciding_between_two_productions() -> None:
    rows = [row("migrations/V2__t.sql"), row("tests/t.sql", is_test=True), row("schema/t.sql")]
    ordered, why = one_definition_first(rows, precedence=PRECEDENCE)

    assert why == DEFINITION_PRECEDENCE and files(ordered)[0] == "schema/t.sql"


def test_a_precedence_no_production_row_matches_falls_through_to_the_migration_rule() -> None:
    rows = [row("migrations/V1__t.sql", version="1"), row("migrations/V2__t.sql", version="2")]
    ordered, why = one_definition_first(rows, precedence=PRECEDENCE)

    assert why == MIGRATION_REDEFINITIONS and files(ordered)[0] == "migrations/V2__t.sql"


def test_a_cut_page_or_fetch_names_no_preferred_definition() -> None:
    rows = [row("migrations/V2__t.sql"), row("schema/t.sql")]

    assert one_definition_first(rows, every_version=False, precedence=PRECEDENCE)[1] is None
    assert one_definition_first(rows, complete=False, precedence=PRECEDENCE)[1] is None
