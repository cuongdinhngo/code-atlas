"""Task 222 — keyed_calls rule: string-keyed CALLS via target_template.

AC1: with a rule, find_callers on the fixture proc returns HEURISTIC + rule:true callers.
R6.5: without the rule, the same fixture returns the 221 answer (relation_unmodelled).
AC2: rules off ⇒ byte-identical graph.
AC4: a rule whose targets never link reports rules_unresolved on BuildReport.
AC3: view_data untouched (existing 062/063 tests); AC5: run separately in verification.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.config import ConfigError, load_config
from code_atlas.enrichment import INDIRECTION_FILE, load_indirection_rules
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from code_atlas.tools.nav_result import REASON_RELATION_UNMODELLED_FOR_LANGUAGE

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
SQL_ENTRY = REPO / "adapters" / "sql" / "index.js"
FIXTURES = REPO / "tests" / "fixtures" / "keyed_calls"

PHP = shutil.which("php")
NODE = shutil.which("node")
needs_adapters = pytest.mark.skipif(
    PHP is None or NODE is None or not PHP_AUTOLOAD.is_file(),
    reason="needs php+composer vendor and node for the SQL adapter",
)

PROC = "dbo.getUnplannedChange"
NODE_COLUMNS = ", ".join(contract.NODE_FIELDS)
EDGE_COLUMNS = ", ".join(contract.EDGE_FIELDS)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / ".code-atlas" / "graph.db") as opened:
        yield opened


def _plant(root: Path, *, rules: str | None) -> None:
    src = root / "src"
    src.mkdir()
    shutil.copy(FIXTURES / "caller.php", src / "caller.php")
    shutil.copy(FIXTURES / "proc.sql", src / "proc.sql")
    if rules is not None:
        rules_dir = root / "rules"
        rules_dir.mkdir()
        shutil.copy(FIXTURES / rules, rules_dir / "rules.json")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)


def _env(root: Path, *, rules: bool) -> dict[str, str]:
    env = {
        "CA_WORKERS": "2",
        "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        "CA_SQL_CMD": shlex.join([str(NODE), str(SQL_ENTRY), "--server"]),
    }
    if rules:
        env["CA_INDIRECTION_RULES"] = "rules/rules.json"
    return env


def _graph_rows(store: GraphStore) -> tuple[list[tuple], list[tuple]]:
    nodes = store._conn.execute(
        f"SELECT {NODE_COLUMNS} FROM nodes ORDER BY qualified_name, file_path, line_start"
    ).fetchall()
    edges = store._conn.execute(
        f"SELECT {EDGE_COLUMNS} FROM edges "
        "ORDER BY kind, source_qname, target_raw, file_path, line"
    ).fetchall()
    return nodes, edges


@needs_adapters
def test_keyed_calls_find_callers_are_heuristic_rule(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1 — with keyed_calls rule, find_callers returns HEURISTIC callers with rule: true."""
    _plant(tmp_path, rules="rules.json")
    config = load_config(tmp_path, _env(tmp_path, rules=True))
    report = full_build(config, store)
    assert report.failed == 0
    assert report.rules_unresolved == 0

    payload = find_callers.create(config)(PROC, detail_level="minimal")
    assert payload["reason"] == "ok", payload
    assert payload["total_count"] >= 1
    hits = payload["results"]
    assert any(hit.get(contract.RULE_FLAG) is True for hit in hits), hits
    assert any(hit.get("confidence_tier") == "HEURISTIC" for hit in hits), hits
    assert any(hit.get(contract.RULE_FLAG) is True and hit.get("confidence_tier") == "HEURISTIC"
               for hit in hits)


@needs_adapters
def test_keyed_calls_without_rule_keeps_221_answer(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1 R6.5 — without the rule, find_callers returns the 221 relation_unmodelled answer."""
    _plant(tmp_path, rules=None)
    config = load_config(tmp_path, _env(tmp_path, rules=False))
    assert full_build(config, store).failed == 0

    payload = find_callers.create(config)(PROC, detail_level="minimal")
    assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE, payload
    assert payload["total_count"] == 0


@needs_adapters
def test_keyed_calls_off_is_byte_identical(tmp_path: Path, store: GraphStore) -> None:
    """AC2 — no CA_INDIRECTION_RULES ⇒ two builds produce identical rows."""
    _plant(tmp_path, rules=None)
    config = load_config(tmp_path, _env(tmp_path, rules=False))
    first = full_build(config, store)
    assert first.failed == 0
    assert first.rules_unresolved == 0
    assert INDIRECTION_FILE not in store.file_paths()
    snap = _graph_rows(store)

    with GraphStore(tmp_path / "second.db") as other:
        second = full_build(load_config(tmp_path, _env(tmp_path, rules=False)), other)
        assert second.failed == 0
        assert _graph_rows(other) == snap


@needs_adapters
def test_keyed_calls_unresolved_reported_on_build_report(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC4 — a keyed_calls rule whose targets never link sets BuildReport.rules_unresolved."""
    _plant(tmp_path, rules="rules_unresolved.json")
    config = load_config(tmp_path, _env(tmp_path, rules=True))
    report = full_build(config, store)
    assert report.failed == 0
    assert report.rules_unresolved >= 1, report

    # Edges were emitted (not a silent zero of extraction) — they just did not link.
    rule_calls = [
        row
        for row in store.calls_by_target_raw("nosuch.getUnplannedChange")
        if row.get("file_path") == INDIRECTION_FILE
    ]
    assert rule_calls, "expected synthetic CALLS edges from the misconfigured rule"
    assert all(not row.get("target_qname") for row in rule_calls)


def test_keyed_calls_template_must_be_exactly_key(tmp_path: Path) -> None:
    """Scope 3 / R5.3 — bad templates fail at load, before parse."""
    rules = tmp_path / "rules.json"
    rules.write_text(
        '{"keyed_calls":[{"setter":"querySP","key_arg":1,'
        '"target_template":"dbo.{name}"}]}',
        encoding="utf-8",
    )
    config = load_config(
        tmp_path,
        {"CA_INDIRECTION_RULES": "rules.json", "CA_PHP_CMD": "php unused"},
    )
    with pytest.raises(ConfigError, match=r"exactly the placeholder"):
        load_indirection_rules(config)
