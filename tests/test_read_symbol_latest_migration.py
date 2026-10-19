"""Task 403 — a routine several versioned migrations redefine reads as its latest definition.

On ``main`` any qname with two definitions refused as ``subject_ambiguous`` (394's test copies the
only tie-break), so a procedure Flyway-style migrations redefine could not be read at all. The
SQL adapter stamps the file's migration version; the highest one answers and the rest are listed.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol, search_symbol

REPO = Path(__file__).resolve().parent.parent
SQL_ENTRY = REPO / "adapters" / "sql" / "index.js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="needs node (SQL adapter)")


def _proc(marker: str) -> str:
    return f"CREATE OR ALTER PROCEDURE dbo.P AS\nBEGIN\n    SELECT '{marker}' AS v;\nEND\nGO\n"


def _built(root: Path, files: dict[str, str]) -> Config:
    for path, body in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "init")):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=root,
            check=True,
            capture_output=True,
        )
    config = load_config(
        root,
        {"CA_WORKERS": "1", "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"])},
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    return config


def _sites(payload: dict[str, object]) -> list[str]:
    return [str(site["file"]) for site in payload["ambiguous_definitions"]]  # type: ignore[union-attr]


@needs_node
def test_ac1_the_latest_migration_answers_and_names_the_earlier(tmp_path: Path) -> None:
    config = _built(
        tmp_path,
        {"db/V1__p.sql": _proc("one"), "db/V7__p.sql": _proc("seven")},
    )
    read = read_symbol.create(config)("dbo.P")

    assert read["reason"] == "ok", read
    assert "'seven'" in str(read["source"]) and read["file"] == "db/V7__p.sql"
    assert read["ambiguity"] == "migration_redefinitions"
    assert _sites(read) == ["db/V1__p.sql"]


@needs_node
def test_versions_compare_as_numbers_not_text(tmp_path: Path) -> None:
    """V10 runs after V9 under Flyway; a text sort would answer V9."""
    config = _built(
        tmp_path,
        {
            "db/V9__p.sql": _proc("nine"),
            "db/V10__p.sql": _proc("ten"),
            "db/V1_5__p.sql": _proc("x"),
        },
    )
    read = read_symbol.create(config)("dbo.P")

    assert read["file"] == "db/V10__p.sql", read
    assert _sites(read) == ["db/V9__p.sql", "db/V1_5__p.sql"]


@needs_node
def test_ac2_two_unordered_definitions_still_refuse(tmp_path: Path) -> None:
    config = _built(tmp_path, {"a/p.sql": _proc("a"), "b/p.sql": _proc("b")})
    read = read_symbol.create(config)("dbo.P")

    assert read["reason"] == "subject_ambiguous", read
    assert sorted(_sites(read)) == ["a/p.sql", "b/p.sql"]


@needs_node
def test_an_unversioned_definition_beside_migrations_still_refuses(tmp_path: Path) -> None:
    """A baseline schema file has no place in the migration order, so nothing outranks it."""
    config = _built(tmp_path, {"db/schema.sql": _proc("base"), "db/V7__p.sql": _proc("seven")})

    assert read_symbol.create(config)("dbo.P")["reason"] == "subject_ambiguous"


@needs_node
def test_a_path_prefix_over_the_migrations_answers_the_latest(tmp_path: Path) -> None:
    """The field's second symptom: a prefix kept every redefinition and still refused."""
    config = _built(
        tmp_path,
        {"db/V1__p.sql": _proc("one"), "db/V7__p.sql": _proc("seven"), "x/p.sql": _proc("x")},
    )
    read = read_symbol.create(config)("dbo.P", path_prefix="db/")

    assert read["reason"] == "ok" and read["file"] == "db/V7__p.sql", read


@needs_node
def test_search_lists_the_latest_first_with_the_same_label(tmp_path: Path) -> None:
    """One rule for every reader of several definitions (R1.8)."""
    config = _built(
        tmp_path,
        {"db/V1__p.sql": _proc("one"), "db/V7__p.sql": _proc("seven")},
    )
    hits = search_symbol.create(config)("dbo.P", kind="Function")["results"]

    assert [hit["file"] for hit in hits] == ["db/V7__p.sql", "db/V1__p.sql"]  # type: ignore[index]
    assert {hit["ambiguity"] for hit in hits} == {"migration_redefinitions"}  # type: ignore[index]
