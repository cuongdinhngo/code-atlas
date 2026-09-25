"""Task 336 — a PHP static property read is a REFERENCES edge onto the property, not a silent zero.

The fixture's ``Use1`` type hint makes PHP emit ``REFERENCES`` (232), so before this the
per-language honesty check let ``find_references`` on ``\\App\\Cfg::$flag`` answer ``no_matches``.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools.find_references import create as create_find_references
from code_atlas.tools.nav_result import REASON_OK
from tests.php_adapter_cli import ENTRY, FIXTURES, PHP, ROOT, needs_php, parse_file

FIXTURE = FIXTURES.relative_to(ROOT) / "static_property_fetch.php"
FLAG = "\\App\\Cfg::$flag"

pytestmark = needs_php


def _property_refs() -> list[tuple[str, str, int, str | None]]:
    edges = parse_file(FIXTURE)["edges"]
    return [
        (e["source_qname"], e["target_raw"], e["line"], e.get("confidence_tier"))
        for e in edges
        if e["kind"] == "REFERENCES" and "::$" in e["target_raw"]
    ]


def _index(tmp_path: Path) -> Config:
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(FIXTURES / "static_property_fetch.php", src / "cfg.php")
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


def test_static_property_read_is_listed_by_find_references(tmp_path: Path) -> None:
    """AC1 — the retro's probe: ``Cfg::$flag`` in ``Db::init`` is a hit at line 8."""
    payload = create_find_references(_index(tmp_path))(FLAG, detail_level="standard")
    assert payload["reason"] == REASON_OK
    results = payload["results"]
    assert isinstance(results, list)
    sites = {(str(hit["qname"]), hit["line"]) for hit in results}
    assert ("\\App\\Db::init", 8) in sites


def test_self_names_the_enclosing_class() -> None:
    """AC2 — ``self::$flag`` inside ``Cfg`` targets the same qname, at the default tier."""
    assert ("\\App\\Cfg::me", FLAG, 5, None) in _property_refs()


def test_a_dynamic_class_or_name_emits_nothing() -> None:
    """AC3 — ``$cls::$flag`` and ``Cfg::$$n`` are never guessed: ``Db::dyn`` emits no edge."""
    assert [ref for ref in _property_refs() if ref[0] == "\\App\\Db::dyn"] == []
