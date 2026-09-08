"""228: refuse reserved-word names; skip IF NOT EXISTS / ADD COLUMN; declare dialect.

AC1 is the red-first guard: the six-line PostgreSQL fixture used to emit Table IF,
Column m_tenants::COLUMN, no Function, and m_tenants at the ALTER line. The assertions
below are the post-fix contract; the working doc records the pre-change red observation.
"""

from __future__ import annotations

from tests.sql_adapter_cli import needs_node, parse_file

PG = "tests/fixtures/sql/postgres_common_spellings.sql"
RESERVED = "tests/fixtures/sql/reserved_word_unreadable.sql"
CREATE_WINS = "tests/fixtures/sql/create_wins_line_over_alter.sql"


@needs_node
def test_postgres_common_spellings_read_honestly() -> None:
    """AC2: IF NOT EXISTS / ADD COLUMN / OR REPLACE yield the real objects at the CREATE site."""
    result = parse_file(PG)
    assert result["ok"] is True
    nodes = result["nodes"]
    tables = [n for n in nodes if n["kind"] == "Table"]
    columns = {n["name"]: n for n in nodes if n["kind"] == "Column"}
    functions = [n for n in nodes if n["kind"] == "Function"]
    file_node = next(n for n in nodes if n["kind"] == "File")

    assert len(tables) == 1
    assert tables[0]["name"] == "m_tenants"
    assert tables[0]["line_start"] == 1
    assert set(columns) == {"tenant_id", "tenant_code", "nickname"}
    assert len(functions) == 1 and functions[0]["name"] == "gen_uuidv7"
    assert file_node["extra"].get("dialect") == "tsql"
    assert "IF" not in {n["name"] for n in nodes}
    assert "COLUMN" not in {n["name"] for n in nodes}


@needs_node
def test_reserved_word_names_emit_nothing() -> None:
    """AC3: a fixture the readers cannot parse at all yields nothing — not a guess."""
    result = parse_file(RESERVED)
    assert result["ok"] is False
    assert "dialect=tsql" in result["error"]
    assert not result.get("nodes")
    assert not result.get("edges")


@needs_node
def test_existing_tsql_fixtures_keep_schema_shape() -> None:
    """AC4: every pre-228 T-SQL fixture still yields the same Table/Column/Function/edge kinds."""
    # Kind histograms were frozen by 022/184 conformance; dialect on File.extra is AC5's additive.
    from tests.contract.adapter_registry import SQL_CASES
    from tests.contract.test_adapter_conformance import kind_histogram

    for case in SQL_CASES.values():
        if case.nodes is None:
            continue
        result = parse_file(f"tests/fixtures/sql/{case.filename}")
        assert result["ok"] is True, case.filename
        assert kind_histogram(result["nodes"]) == case.nodes, case.filename
        assert kind_histogram(result["edges"]) == case.edges, case.filename
        file_node = next(n for n in result["nodes"] if n["kind"] == "File")
        assert file_node["extra"].get("dialect") == "tsql"


@needs_node
def test_dialect_reaches_file_payload() -> None:
    """AC5: dialect is on File.extra (META_FIELDS frozen); unreadable DDL is not ok:true."""
    good = parse_file(PG)
    file_node = next(n for n in good["nodes"] if n["kind"] == "File")
    assert file_node["extra"]["dialect"] == "tsql"

    bad = parse_file(RESERVED)
    assert bad["ok"] is False
    assert "dialect=tsql" in bad["error"]
    # A complete T-SQL read and a refused-name file are no longer the same success shape.
    assert good["ok"] is not bad["ok"]


@needs_node
def test_create_wins_over_earlier_alter_for_line_start() -> None:
    """Scope 4: CREATE TABLE wins line_start even when ALTER was seen first."""
    result = parse_file(CREATE_WINS)
    assert result["ok"] is True
    table = next(n for n in result["nodes"] if n["kind"] == "Table")
    assert table["name"] == "T"
    assert table["line_start"] == 2
    columns = {n["name"] for n in result["nodes"] if n["kind"] == "Column"}
    assert columns == {"c", "id"}
