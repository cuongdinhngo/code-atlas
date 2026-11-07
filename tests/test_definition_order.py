"""Task 437 — a declared definition order names the one live definition of a redefined routine.

A procedure is created in three Flyway migrations and copied into a snapshot. ``definition_order``
in ``.code-atlas.toml`` ranks the migrations by version over the snapshot, so exactly one
definition is ``live`` and the others name it in ``superseded_by``. Built through the real SQL
adapter; with no rule nothing is live (R5.6).
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, ConfigError, load_config
from code_atlas.enrichment import load_indirection_rules
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol
from code_atlas.tools.symbol_pointers import declared_precedence, definition_states

NODE = shutil.which("node")
SQL_ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
pytestmark = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {SQL_ENTRY}")

PROC = "dbo.P"
LATEST = "db/migrations/V10__p.sql"
SNAPSHOT = "db/snapshot/p.sql"
SOURCES = {
    "db/migrations/V1__p.sql": "CREATE PROCEDURE dbo.P AS SELECT 1;\nGO\n",
    "db/migrations/V2__p.sql": "CREATE OR ALTER PROCEDURE dbo.P AS SELECT 2;\nGO\n",
    LATEST: "CREATE OR ALTER PROCEDURE dbo.P AS SELECT 10;\nGO\n",
    SNAPSHOT: "CREATE PROCEDURE dbo.P AS SELECT 99;\nGO\n",
}
ORDER = 'definition_order = ["db/migrations/V<n>__*.sql", "db/snapshot/*.sql"]\n'


def build(root: Path, toml: str | None, extra: dict[str, str] | None = None) -> Config:
    root.mkdir(parents=True)
    for path, text in {**SOURCES, **(extra or {})}.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    if toml is not None:
        (root / ".code-atlas.toml").write_text(toml, encoding="utf-8")
    env = {
        "CA_WORKERS": "1",
        "CA_DB_PATH": str(root / ".code-atlas" / "graph.db"),
        "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"]),
    }
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    config = load_config(root, env)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    return config


def states(config: Config) -> dict[str, dict[str, object]]:
    with GraphStore(config.db_path) as store:
        rows = list(store.nodes_by_qualified_name(PROC, limit=50))
        found = definition_states(rows, declared_precedence(store))
    return {str(state["file"]): state for state in found}


@pytest.fixture(scope="module")
def ordered(tmp_path_factory: pytest.TempPathFactory) -> Config:
    return build(tmp_path_factory.mktemp("order") / "repo", ORDER)


def test_ac1_the_highest_versioned_migration_is_the_one_live_definition(ordered: Config) -> None:
    """AC1 (proving test): V10 beats V2 numerically, and every other definition names it."""
    found = states(ordered)

    assert [path for path, state in found.items() if state["state"] == "live"] == [LATEST]
    for path, state in found.items():
        if path != LATEST:
            assert state["state"] == "superseded", state
            assert state["superseded_by"] == {"qname": PROC, "file": LATEST, "line": 1}
    ordinals = {path: state["definition_ordinal"] for path, state in found.items()}
    assert ordinals == {
        SNAPSHOT: 1,
        "db/migrations/V1__p.sql": 2,
        "db/migrations/V2__p.sql": 3,
        LATEST: 4,
    }


def test_ac1_read_symbol_answers_the_live_definition(ordered: Config) -> None:
    answer = read_symbol.create(ordered)(qname=PROC)

    assert answer["reason"] == "ok", answer
    assert answer["file"] == LATEST and "10" in str(answer["source"])
    assert answer["ambiguity"] == "definition_precedence"
    assert answer["definition_state"] == "live"
    others = answer["ambiguous_definitions"]
    assert {site["definition_state"] for site in others} == {"superseded"}
    assert {site["superseded_by"]["file"] for site in others} == {LATEST}


def test_ac2_with_no_rule_nothing_is_live(tmp_path: Path) -> None:
    """AC2: an unknown is never ``ok`` — every definition stays unranked, and the read refuses."""
    config = build(tmp_path / "repo", None)

    assert {state["state"] for state in states(config).values()} == {"unranked"}
    assert {state["definition_ordinal"] for state in states(config).values()} == {None}
    assert read_symbol.create(config)(qname=PROC)["reason"] == "subject_ambiguous"


def test_a_tied_version_names_no_live_definition(tmp_path: Path) -> None:
    """``V10`` and ``V10.0`` are one version in two folders: a tie, never a guess."""
    order = 'definition_order = ["db/*/V<n>__*.sql"]\n'
    config = build(tmp_path / "repo", order, {"db/other/V10.0__p.sql": SOURCES[LATEST]})

    assert "live" not in {state["state"] for state in states(config).values()}


def test_a_cut_fetch_names_no_live_definition(ordered: Config) -> None:
    """An unseen row may rank higher, so a fetch that hit its limit holds nothing live."""
    with GraphStore(ordered.db_path) as store:
        rows = list(store.nodes_by_qualified_name(PROC, limit=50))
        found = definition_states(rows, declared_precedence(store), complete=False)

    assert {state["state"] for state in found} == {"unranked"}


@pytest.mark.parametrize(
    "toml",
    [
        'definition_order = "db/migrations/*"\n',
        "definition_order = [1, 2]\n",
        'definition_order = ["db/V<n>_<n>.sql"]\n',
        'definition_order = [""]\n',
        'definition_order = ["db/V[<n>]__*.sql"]\n',
    ],
)
def test_ac4_a_toml_value_that_is_not_a_list_of_globs_fails_loud(tmp_path: Path, toml: str) -> None:
    (tmp_path / ".code-atlas.toml").write_text(toml, encoding="utf-8")

    with pytest.raises(ConfigError, match="definition_order"):
        load_config(tmp_path, {})


def test_a_rules_file_precedence_takes_the_same_version_check(tmp_path: Path) -> None:
    (tmp_path / "rules.json").write_text(
        '{"definitions": {"precedence": ["V<n>_<n>.sql"]}}', encoding="utf-8"
    )
    config = load_config(tmp_path, {"CA_INDIRECTION_RULES": "rules.json"})

    with pytest.raises(ConfigError, match="more than once"):
        load_indirection_rules(config)


def test_the_glob_reader_still_understands_fnmatch() -> None:
    """A Python whose ``fnmatch.translate`` changed shape would fail here, not mis-rank silently."""
    from code_atlas.tools.symbol_pointers import _rank

    assert _rank("db/V2_1__x.sql", ("db/V<n>__*.sql",)) == (1, (2, 1))
    assert _rank("db/sub/V2__x.sql", ("db/V<n>__*.sql",)) is None
    assert _rank("db/a.sql", ("db/V<n>__*.sql", "db/*")) == (1, ())
