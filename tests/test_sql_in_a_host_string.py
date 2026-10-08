"""Task 371 — a TS or Python string that begins a T-SQL write or EXEC emits that edge, as PHP's.

The edge is ``HEURISTIC`` and links through the resolver's ordinary pass onto the SQL adapter's
node (335's machinery), so a table lists its Node and Python writers beside its PHP and SQL ones.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references
from tests.adapter_cli import run_adapter_file
from tests.python_adapter_cli import CLI as PY_CLI
from tests.python_adapter_cli import ENTRY as PY_ENTRY
from tests.sql_adapter_cli import CLI as SQL_CLI
from tests.ts_adapter_cli import CLI as TS_CLI
from tests.ts_adapter_cli import ENTRY as TS_ENTRY
from tests.ts_adapter_cli import NODE, needs_node

pytestmark = needs_node

FILES = {
    "db/schema.sql": (
        "CREATE TABLE dbo.Items (a INT)\nGO\n"
        "CREATE PROCEDURE dbo.Insert_Order @p INT\nAS\nBEGIN\n    SELECT 1;\nEND\nGO\n"
    ),
    "web/items.ts": (
        "export async function save(db: { query(s: string): Promise<void> }, id: number) {\n"  # 1
        '  await db.query("INSERT INTO dbo.Items (a) VALUES (1)");\n'  # 2
        "  await db.query(`DELETE FROM dbo.Items WHERE a = ${id}`);\n"  # 3
        '  await db.query("Update settings");\n'  # 4
        "}\n"
    ),
    "jobs/orders.py": (
        "def place(cursor, order_id):\n"  # 1
        '    cursor.execute("EXEC dbo.Insert_Order ?", order_id)\n'  # 2
        '    cursor.execute(f"UPDATE dbo.Items SET a = {order_id}")\n'  # 3
        '    print("delete this?")\n'  # 4
    ),
}


@pytest.fixture(scope="module")
def config(tmp_path_factory: pytest.TempPathFactory) -> Config:
    root = tmp_path_factory.mktemp("repo")
    for rel, body in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    built = load_config(
        root,
        {
            "CA_WORKERS": "1",
            "CA_TYPESCRIPT_CMD": shlex.join([str(NODE), str(TS_ENTRY), "--server"]),
            "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"]),
            "CA_SQL_CMD": shlex.join([*SQL_CLI.entry_argv, "--server"]),
        },
    )
    with GraphStore(built.db_path) as store:
        assert full_build(built, store).failed == 0
    return built


def _sites(answer: dict[str, object]) -> set[tuple[str, int]]:
    results = answer["results"]
    assert isinstance(results, list)
    return {(str(hit["qname"]), int(hit["line"])) for hit in results}


def test_a_table_lists_its_ts_and_python_writers(config: Config) -> None:
    """AC1 — the TS `INSERT` and template `DELETE`, and the Python f-string `UPDATE`."""
    answer = find_references.create(config)("dbo.Items", detail_level="standard")
    sites = _sites(answer)
    assert {
        ("web/items.ts::save", 2),
        ("web/items.ts::save", 3),
        ("jobs.orders.place", 3),
    } <= sites, answer


def test_a_procedure_lists_its_python_exec_caller(config: Config) -> None:
    """AC2 — `cursor.execute("EXEC dbo.Insert_Order ?")` is a caller of the procedure."""
    answer = find_callers.create(config)("dbo.Insert_Order")
    assert _sites(answer) == {("jobs.orders.place", 2)}, answer


def test_prose_emits_nothing(config: Config) -> None:
    """AC3 — "Update settings" and "delete this?" begin no statement."""
    answer = find_references.create(config)("dbo.Items", detail_level="standard")
    assert not [site for site in _sites(answer) if site[1] == 4]


def _statements(adapter: str, name: str, source: str, tmp_path: Path) -> list[tuple[int, str]]:
    cli = PY_CLI if adapter == "python" else TS_CLI
    (tmp_path / name).write_text(source, encoding="utf-8")
    done = run_adapter_file(cli.entry_argv, name, cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    edges = json.loads(done.stdout)["edges"]
    return sorted(
        (e["line"], e["target_raw"])
        for e in edges
        if e["kind"] in ("WRITES", "DELETES") and e.get("confidence_tier") == "HEURISTIC"
    )


def test_a_ts_string_no_driver_can_run_emits_nothing(tmp_path: Path) -> None:
    """Challenger F1 — a type, a module specifier and a member name are not SQL a program runs."""
    source = (
        'type A = "DELETE FROM dbo.Items WHERE a = 1";\n'  # 1
        'const o = { "UPDATE dbo.Items SET a = 1": 1 };\n'  # 2
        'enum E { "DELETE FROM dbo.Items WHERE b = 1" = 1 }\n'  # 3
        'export const run = "DELETE FROM dbo.Items WHERE c = 1";\n'  # 4 — a value: read
    )
    assert _statements("typescript", "kinds.ts", source, tmp_path) == [(4, "dbo.Items")]


def test_a_python_statement_line_counts_source_line_breaks(tmp_path: Path) -> None:
    """Challenger F2 — an escaped `\\n` stays on its line; a triple-quoted break moves it."""
    source = (
        'a = "\\nDELETE FROM dbo.Items WHERE id = 1"\n'  # 1
        'b = """\n'  # 2
        "UPDATE dbo.Items SET a = 1\n"  # 3
        '"""\n'
    )
    found = _statements("python", "lines.py", source, tmp_path)
    assert found == [(1, "dbo.Items"), (3, "dbo.Items")]
