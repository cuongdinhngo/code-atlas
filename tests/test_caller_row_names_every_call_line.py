"""Task 338 — a caller row names every line it calls the subject from; the count stays callers."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools.find_callers import create as create_find_callers
from code_atlas.tools.nav_result import REASON_OK
from tests.php_adapter_cli import ENTRY, PHP, needs_php

pytestmark = needs_php

CTX = "\\App\\Db::ctx"
# ``init`` calls ctx() twice (main path + fallback); ``once`` calls it once.
SOURCE = """<?php
namespace App;
class Db
{
    public function ctx(): int { return 1; }
}
class Svc
{
    public function init(Db $db): int
    {
        if ($db->ctx() > 0) {
            return 1;
        }
        return $db->ctx();
    }
    public function once(Db $db): int { return $db->ctx(); }
}
"""


def _line_of(needle: str, nth: int = 0) -> int:
    hits = [i for i, text in enumerate(SOURCE.splitlines(), start=1) if needle in text]
    return hits[nth]


def _index(tmp_path: Path) -> Config:
    src = tmp_path / "src"
    src.mkdir()
    (src / "Svc.php").write_text(SOURCE, encoding="utf-8")
    for git in (["git", "init", "-q"], ["git", "add", "-A"]):
        subprocess.run(git, cwd=tmp_path, check=True, capture_output=True)
    db_path = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_DB_PATH": str(db_path),
            "CA_PHP_CMD": shlex.join([str(PHP), str(ENTRY), "--server"]),
        },
    )
    with GraphStore(db_path) as store:
        assert full_build(config, store).failed == 0
    return config


def _rows(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    assert payload["reason"] == REASON_OK
    results = payload["results"]
    assert isinstance(results, list)
    return {str(row["qname"]): row for row in results}


def test_a_caller_with_two_sites_names_both_lines(tmp_path: Path) -> None:
    """AC1: the ``init`` row carries ``call_lines`` [first, second]; ``line`` stays the first."""
    rows = _rows(create_find_callers(_index(tmp_path))(CTX, depth=1))
    first, second = _line_of("$db->ctx() > 0"), _line_of("return $db->ctx();")
    init = rows["\\App\\Svc::init"]
    assert init["call_lines"] == [first, second]
    assert init["line"] == first


def test_a_caller_with_one_site_is_unchanged(tmp_path: Path) -> None:
    """AC2: one call site → no ``call_lines`` and no ``call_sources`` (061)."""
    tool = create_find_callers(_index(tmp_path))
    once = _rows(tool(CTX, depth=1))["\\App\\Svc::once"]
    assert "call_lines" not in once
    quoted = _rows(tool(CTX, depth=1, include_source=True))["\\App\\Svc::once"]
    assert "call_sources" not in quoted
    assert "call_lines" not in quoted
    assert "$db->ctx()" in str(quoted["source"])


def test_include_source_quotes_each_listed_line(tmp_path: Path) -> None:
    """Scope 2: ``include_source`` quotes every line in ``call_lines``, in the same order."""
    payload = create_find_callers(_index(tmp_path))(CTX, depth=1, include_source=True)
    init = _rows(payload)["\\App\\Svc::init"]
    assert init["call_sources"] == [
        "if ($db->ctx() > 0) {",
        "return $db->ctx();",
    ]
    assert init["source"] == init["call_sources"][0]


def test_the_count_is_still_callers(tmp_path: Path) -> None:
    """C1 / 273: three call sites from two callers are two callers, and the partition sums."""
    payload = create_find_callers(_index(tmp_path))(CTX, depth=1)
    assert payload["total_count"] == 2
    assert int(payload.get("production_count") or 0) + int(
        payload.get("test_count") or 0
    ) == payload["total_count"]
