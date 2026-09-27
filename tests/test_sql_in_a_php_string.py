"""Task 335 — a PHP string that begins a T-SQL write or EXEC emits that edge, at HEURISTIC.

Keyed on statement grammar — a leading keyword, one object name, the clause T-SQL requires after
it — never on a wrapper method's name (R2.2). The link is the resolver's ordinary FQN / casefold
pass onto the SQL node (222's machinery); no second resolver.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references
from tests.php_adapter_cli import ENTRY, PHP, ROOT, needs_php, parse_file
from tests.sql_adapter_cli import CLI as SQL_CLI
from tests.sql_adapter_cli import needs_node

# Outside tests/fixtures/php/: the parity corpus globs that directory and expects no PHP WRITES.
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "php_sql_literal" / "repo.php"
FIXTURE = FIXTURE_PATH.relative_to(ROOT)
SOURCE = "\\App\\Repo::save"
SQL = (
    "CREATE TABLE dbo.T (a INT)\nGO\nCREATE TABLE dbo.S (a INT)\nGO\n"
    "CREATE PROCEDURE dbo.Gen @x INT\nAS\nBEGIN\n    SELECT 1;\nEND\nGO\n"
)

pytestmark = [needs_php, needs_node]


def _sql_edges() -> set[tuple[str, str, int, str | None]]:
    edges = parse_file(FIXTURE)["edges"]
    return {
        (e["kind"], e["target_raw"], e["line"], e.get("confidence_tier"))
        for e in edges
        if e["kind"] in ("WRITES", "DELETES") or e["target_raw"].startswith("dbo.")
    }


def _index(root: Path) -> Config:
    (root / "src").mkdir()
    shutil.copy(FIXTURE_PATH, root / "src" / "repo.php")
    (root / "db").mkdir()
    (root / "db" / "schema.sql").write_text(SQL, encoding="utf-8")
    argv = ", ".join(f"'{part}'" for part in (*SQL_CLI.entry_argv, "--server"))
    (root / ".code-atlas.toml").write_text(f"[adapter_cmd]\nsql = [{argv}]\n", encoding="utf-8")
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=root, check=True, capture_output=True)
    db_path = root / ".code-atlas" / "graph.db"
    config = load_config(
        root,
        {
            "CA_TRUST_PROJECT_FILE": "1",
            "CA_WORKERS": "1",
            "CA_DB_PATH": str(db_path),
            "CA_PHP_CMD": shlex.join([str(PHP), str(ENTRY), "--server"]),
        },
    )
    with GraphStore(db_path) as store:
        assert full_build(config, store).failed == 0
    return config


def _sites(payload: dict[str, object]) -> set[tuple[str, int, str]]:
    results = payload["results"]
    assert isinstance(results, list)
    return {(str(hit["qname"]), int(hit["line"]), str(hit["confidence_tier"])) for hit in results}


def test_an_insert_string_is_a_writer_of_its_table(tmp_path: Path) -> None:
    """AC1 — ``find_references dbo.T`` lists the PHP method at the INSERT's line, HEURISTIC."""
    config = _index(tmp_path)
    payload = find_references.create(config)("dbo.T", detail_level="standard")
    assert (SOURCE, 9, "HEURISTIC") in _sites(payload)


def test_an_exec_string_is_a_caller_of_its_proc(tmp_path: Path) -> None:
    """AC2 — ``find_callers dbo.Gen`` lists the PHP method."""
    config = _index(tmp_path)
    payload = find_callers.create(config)("dbo.Gen", detail_level="standard")
    assert (SOURCE, 10, "HEURISTIC") in _sites(payload)


def test_each_statement_shape_emits_its_kind() -> None:
    """Scope 1 — DELETE FROM is DELETES; a heredoc MERGE is WRITES on the keyword's own line."""
    edges = _sql_edges()
    assert ("DELETES", "dbo.T", 13, "HEURISTIC") in edges
    assert ("WRITES", "dbo.T", 17, "HEURISTIC") in edges


def test_the_return_code_exec_form_is_a_call() -> None:
    """AC2 — ``EXEC @rc = dbo.Gen …`` captures a return code; it still calls ``dbo.Gen``."""
    assert ("CALLS", "dbo.Gen", 26, "HEURISTIC") in _sql_edges()


def test_what_is_not_a_statement_emits_nothing() -> None:
    """AC3 / AC4 — an interpolated target, a mention, prose (also after a real qualified name),
    and a name a concatenation extends."""
    lines = {line for _, _, line, _ in _sql_edges()}
    assert lines == {9, 10, 13, 17, 26}, "lines 11, 12, 14, 15, 27 must emit nothing"
