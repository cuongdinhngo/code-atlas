"""Task 386 — a host string that runs `EXEC Proc @p` with no schema calls the procedure.

T-SQL resolves an unqualified procedure in the caller's default schema, `dbo` unless set. The PHP,
TS and Python adapters emit `dbo.<name>`; the SQL adapter aliases a schema-less `CREATE PROCEDURE P`
as `dbo.P`. A dotted target never matches a host-language symbol by name, so 204 holds.
"""

from __future__ import annotations

import shlex
import subprocess
import sys

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from tests.php_adapter_cli import ENTRY as PHP_ENTRY
from tests.php_adapter_cli import PHP, needs_php
from tests.python_adapter_cli import ENTRY as PY_ENTRY
from tests.sql_adapter_cli import CLI as SQL_CLI
from tests.ts_adapter_cli import ENTRY as TS_ENTRY
from tests.ts_adapter_cli import NODE, needs_node

pytestmark = [needs_php, needs_node]

PROCEDURE = "CREATE PROCEDURE {name} @id INT\nAS\nBEGIN\n    SELECT 1;\nEND\nGO\n"
HOSTS = {
    "app/Orders.php": (
        "<?php\n"  # 1
        "namespace App;\n"  # 2
        "class Orders {\n"  # 3
        "    public function place($db) {\n"  # 4
        '        $db->query("EXEC Insert_Order @id");\n'  # 5
        '        $db->query("EXEC [Insert_Order] ?");\n'  # 6
        '        $db->query("exec summary");\n'  # 7
        "        $db->query(\"EXECUTE AS USER = 'x'\");\n"  # 8
        "    }\n"
        "    public function Insert_Order() {}\n"  # 10 — a same-language method of that name
        "}\n"
    ),
    "web/orders.ts": (
        "export async function place(db: { query(s: string): Promise<void> }) {\n"  # 1
        '  await db.query("EXEC Insert_Order @id");\n'  # 2
        '  await db.query("EXEC [Insert_Order] ?");\n'  # 3
        '  await db.query("exec summary");\n'  # 4
        "  await db.query(\"EXECUTE AS USER = 'x'\");\n"  # 5
        "}\n"
        "export function Insert_Order() {}\n"  # 7
    ),
    "jobs/orders.py": (
        "def place(cursor):\n"  # 1
        '    cursor.execute("EXEC Insert_Order @id")\n'  # 2
        '    cursor.execute("EXEC [Insert_Order] ?")\n'  # 3
        '    cursor.execute("exec summary")\n'  # 4
        "    cursor.execute(\"EXECUTE AS USER = 'x'\")\n"  # 5
        "\n\n"
        "def Insert_Order():\n"  # 8
        "    pass\n"
    ),
}
# AC1/AC5: the two forms with a clause link from each host; AC3: prose and EXECUTE AS do not.
CALLERS = {
    ("\\App\\Orders::place", 5),
    ("\\App\\Orders::place", 6),
    ("web/orders.ts::place", 2),
    ("web/orders.ts::place", 3),
    ("jobs.orders.place", 2),
    ("jobs.orders.place", 3),
}
SAME_NAMED = ("\\App\\Orders::Insert_Order", "web/orders.ts::Insert_Order", "jobs.orders.Insert_Order")


@pytest.fixture(scope="module", params=["dbo.Insert_Order", "Insert_Order"])
def built(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> tuple[
    Config, str
]:
    """One repo per way the procedure is created: schema-qualified, and with no schema."""
    procedure = str(request.param)
    root = tmp_path_factory.mktemp("repo")
    files = {"db/procs.sql": PROCEDURE.format(name=procedure), **HOSTS}
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    config = load_config(
        root,
        {
            "CA_WORKERS": "1",
            "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
            "CA_TYPESCRIPT_CMD": shlex.join([str(NODE), str(TS_ENTRY), "--server"]),
            "CA_PYTHON_CMD": shlex.join([sys.executable, str(PY_ENTRY), "--server"]),
            "CA_SQL_CMD": shlex.join([*SQL_CLI.entry_argv, "--server"]),
        },
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    return config, procedure


def _callers(config: Config, qname: str) -> list[dict[str, object]]:
    answer = find_callers.create(config)(qname)
    results = answer.get("results", [])
    assert isinstance(results, list), answer
    return results


def test_every_host_lists_as_a_caller_of_the_procedure(built: tuple[Config, str]) -> None:
    """AC1, AC3, AC5 — both clause forms, from PHP, TS and Python, at HEURISTIC; nothing else."""
    config, procedure = built
    results = _callers(config, procedure)
    # One row per caller; a caller with several call lines carries them all in `call_lines`.
    sites = {
        (str(hit["qname"]), int(line))
        for hit in results
        for line in hit.get("call_lines") or [hit["line"]]  # type: ignore[union-attr]
    }
    assert sites == CALLERS, results
    assert {hit["confidence_tier"] for hit in results} == {"HEURISTIC"}


@pytest.mark.parametrize("qname", SAME_NAMED)
def test_no_edge_lands_on_a_same_named_host_symbol(built: tuple[Config, str], qname: str) -> None:
    """AC2 — the PHP method, TS function and Python function named Insert_Order get no caller."""
    config, _ = built
    assert _callers(config, qname) == []
