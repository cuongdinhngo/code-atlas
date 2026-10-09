"""Task 371 — the PHP, TS and Python adapters read a SQL statement in a string literal alike.

Each adapter ports ``SqlLiteral.php``'s *shape* in its own parser (R1.1/R2). One table drives all
three, so the copies cannot drift: every literal is written into a source file in the adapter's own
spelling, the adapter's ``--file`` mode runs over it, and the edge on that line must be the table's.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.adapter_cli import AdapterCli, run_adapter_file
from tests.php_adapter_cli import CLI as PHP_CLI
from tests.python_adapter_cli import CLI as PY_CLI
from tests.ts_adapter_cli import CLI as TS_CLI

TABLE = json.loads((Path(__file__).parent / "sql_literal_cases.json").read_text(encoding="utf-8"))
_KINDS = ("WRITES", "DELETES", "CALLS")


def _php(text: str, is_open: bool) -> str:
    if is_open:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
        return f'$v = "{escaped}{{$x}}";'
    return "$v = '" + text.replace("\\", "\\\\").replace("'", "\\'") + "';"


def _ts(text: str, is_open: bool) -> str:
    if is_open:
        escaped = text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
        return f"v = `{escaped}${{x}}`;"
    return f"v = {json.dumps(text)};"


def _python(text: str, is_open: bool) -> str:
    if is_open:
        escaped = json.dumps(text.replace("{", "{{").replace("}", "}}"))
        return f"v = f{escaped[:-1]}{{x}}{escaped[-1]}"
    return f"v = {json.dumps(text)}"


SPELLINGS = {
    "php": (PHP_CLI, "case.php", "<?php", _php),
    "typescript": (TS_CLI, "case.ts", "let v: string; declare const x: string;", _ts),
    "python": (PY_CLI, "case.py", "x = ''", _python),
}


def _rows() -> list[tuple[str, bool, dict[str, Any] | None, str]]:
    rows = [(c["text"], c["open"], c["expect"], "") for c in TABLE["cases"]]
    for case in TABLE["markers"]:
        for adapter, expect in case["expect_by_adapter"].items():
            rows.append((case["text"], case["open"], expect, adapter))
    return rows


def _edges(adapter: str, tmp_path: Path) -> dict[int, list[tuple[str, str]]]:
    cli, name, header, spell = SPELLINGS[adapter]
    lines = [header] + [spell(text, is_open) for text, is_open, _, _ in _rows()]
    (tmp_path / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    done = run_adapter_file(cli.entry_argv, name, cwd=tmp_path)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["ok"], result
    found: dict[int, list[tuple[str, str]]] = {}
    for edge in result["edges"]:
        if edge["kind"] in _KINDS and edge.get("confidence_tier") == "HEURISTIC":
            found.setdefault(edge["line"], []).append((edge["kind"], edge["target_raw"]))
    return found


@pytest.mark.parametrize("adapter", sorted(SPELLINGS))
def test_every_adapter_reads_the_shared_literal_table(adapter: str, tmp_path: Path) -> None:
    """AC5 — the same literal gives the same edge, or none, in PHP, TS and Python."""
    cli: AdapterCli = SPELLINGS[adapter][0]
    if cli.availability.args and cli.availability.args[0]:
        pytest.skip(cli.availability.kwargs.get("reason", "adapter unavailable"))
    found = _edges(adapter, tmp_path)
    wrong = []
    for line, (text, _is_open, expect, only) in enumerate(_rows(), start=2):
        if only and only != adapter:
            continue
        want = [(expect["kind"], expect["target"])] if expect else []
        if found.get(line, []) != want:
            wrong.append((text, want, found.get(line, [])))
    assert wrong == []
