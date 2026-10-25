"""Task 414 — a declared precedence names the definition that answers for a shared qname.

A table is defined in a schema project and again in a migration. Without a precedence every
question about it is ``subject_ambiguous``; with ``definitions.precedence`` in the rules file the
schema's definition answers ``read_symbol`` and seeds ``impact``, the migration listed beside it.
Built through the real SQL adapter.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from code_atlas.config import Config, ConfigError, load_config
from code_atlas.enrichment import load_indirection_rules
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_references, impact, impact_modules, read_symbol, search_symbol

NODE = shutil.which("node")
SQL_ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
pytestmark = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {SQL_ENTRY}")

TABLE = "dbo.T"
SCHEMA, MIGRATION = "schema/t.sql", "migrations/V2__t.sql"
SOURCES = {
    SCHEMA: "CREATE TABLE dbo.T (Id int NOT NULL);\n",
    MIGRATION: "CREATE TABLE dbo.T (Id int NOT NULL, Note int NULL);\n",
    "procs/p.sql": "CREATE PROCEDURE dbo.P AS\nINSERT INTO dbo.T (Id) VALUES (1);\nGO\n",
    "procs/v.sql": "CREATE VIEW dbo.V AS SELECT Id FROM dbo.T;\nGO\n",
}


def build(root: Path, precedence: list[str] | None) -> Config:
    root.mkdir(parents=True)
    for path, text in SOURCES.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    env = {
        "CA_WORKERS": "1",
        "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
        "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"]),
    }
    if precedence is not None:
        rules = {"definitions": {"precedence": precedence}}
        (root / "rules.json").write_text(json.dumps(rules), encoding="utf-8")
        env["CA_INDIRECTION_RULES"] = "rules.json"
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    config = load_config(root, env)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    return config


@pytest.fixture(scope="module")
def ranked(tmp_path_factory: pytest.TempPathFactory) -> Config:
    return build(tmp_path_factory.mktemp("prec") / "repo", ["vendor/*", "schema/**"])


@pytest.fixture(scope="module")
def plain(tmp_path_factory: pytest.TempPathFactory) -> Config:
    return build(tmp_path_factory.mktemp("plain") / "repo", None)


def test_ac1_read_symbol_answers_from_the_preferred_definition(ranked: Config) -> None:
    """AC1 (proving test): the schema's body, the migration as the one other definition."""
    answer = read_symbol.create(ranked)(qname=TABLE)

    assert answer["reason"] == "ok", answer
    assert answer["file"] == SCHEMA and "Note" not in str(answer["source"])
    assert answer["ambiguity"] == "definition_precedence"
    others: Any = answer["ambiguous_definitions"]
    assert [site["file"] for site in others] == [MIGRATION]


def test_ac2_impact_walks_the_table_and_names_its_other_definition(ranked: Config) -> None:
    """W5: the refusal lifts and the seed sits at its answering definition. ``impact`` walks
    ``IMPACT_KINDS`` only, so a table's readers and writers are ``find_references``' answer —
    for a one-definition table too (the review measured it on ``main``)."""
    answer = impact.create(ranked)(qnames=[TABLE])

    assert answer.get("reason") != "subject_ambiguous", answer
    assert [(row["qname"], row["file"], row["depth"]) for row in answer["results"]] == [
        (TABLE, SCHEMA, 0)
    ]
    assert [(site["qname"], site["file"]) for site in answer["other_definitions"]] == [
        (TABLE, MIGRATION)
    ]


def test_ac2_writers_aggregate_across_both_definitions(ranked: Config, plain: Config) -> None:
    """Scope 3, measured: references target the qname, so they never depended on precedence."""
    for config in (ranked, plain):
        answer = find_references.create(config)(qname=TABLE)
        assert "dbo.P" in {row["qname"] for row in answer["results"]}, answer


def test_a_path_seed_keeps_its_own_file(ranked: Config) -> None:
    """Review M1: the migration a caller names by path is that file's, never moved to the schema."""
    answer = impact.create(ranked)(paths=[MIGRATION])

    assert "other_definitions" not in answer
    assert ("dbo.T::Note", MIGRATION) in {(row["qname"], row["file"]) for row in answer["results"]}
    assert all(row["file"] != SCHEMA for row in answer["results"])


def test_impact_modules_names_the_answering_definition(ranked: Config) -> None:
    """Review M2: the shared seed plan places the seed for every tool that walks it."""
    answer: Any = impact_modules.create(ranked)(qnames=[TABLE])

    assert [row["exemplar"].split(":")[0] for row in answer["results"]] == [SCHEMA]
    assert [site["file"] for site in answer["other_definitions"]] == [MIGRATION]


def test_a_leading_slash_is_repo_relative(tmp_path: Path) -> None:
    config = build(tmp_path / "repo", ["/schema/**"])
    assert read_symbol.create(config)(qname=TABLE)["file"] == SCHEMA


def test_search_lists_the_preferred_definition_first(ranked: Config) -> None:
    hits: Any = search_symbol.create(ranked)(query="T")["results"]
    table = [hit for hit in hits if hit["qname"] == TABLE]
    assert table[0]["file"] == SCHEMA and table[0]["ambiguity"] == "definition_precedence"


def test_ac3_without_a_precedence_the_table_is_ambiguous(plain: Config) -> None:
    assert read_symbol.create(plain)(qname=TABLE)["reason"] == "subject_ambiguous"
    assert impact.create(plain)(qnames=[TABLE])["reason"] == "subject_ambiguous"


def test_two_definitions_under_the_first_matching_glob_stay_ambiguous(tmp_path: Path) -> None:
    """A tie inside the deciding glob is never broken by a guess, nor by a later glob."""
    config = build(tmp_path / "repo", ["migrations/*", "schema/**"])
    (config.root / "migrations" / "V3__t.sql").write_text(SOURCES[MIGRATION], encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=config.root, check=True, capture_output=True)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    assert read_symbol.create(config)(qname=TABLE)["reason"] == "subject_ambiguous"


def test_a_malformed_precedence_fails_the_build(tmp_path: Path) -> None:
    (tmp_path / "rules.json").write_text(json.dumps({"definitions": {"precedence": "schema/**"}}))
    config = load_config(tmp_path, {"CA_INDIRECTION_RULES": "rules.json"})
    with pytest.raises(ConfigError, match="definitions.precedence"):
        load_indirection_rules(config)
