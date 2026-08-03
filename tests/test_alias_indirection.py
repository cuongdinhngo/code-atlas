"""Task 030: ALIASES + literal-string dispatch (contract v2)."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.contract import CONTRACT_VERSION
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools.find_callers import create as create_find_callers
from code_atlas.tools.find_references import create as create_find_references
from tests.php_adapter_cli import ENTRY, FIXTURES, PHP, ROOT, needs_php, parse_file

PHP_ENTRY = ENTRY


def _interesting(result: dict[str, object]) -> list[dict[str, object]]:
    edges = result.get("edges")
    assert isinstance(edges, list)
    return [
        e
        for e in edges
        if isinstance(e, dict) and e.get("kind") in ("CALLS", "NEW", "ALIASES")
    ]


@needs_php
def test_contract_version_is_two() -> None:
    assert CONTRACT_VERSION == 2


@needs_php
def test_class_alias_emits_aliases_edge() -> None:
    result = parse_file(FIXTURES.relative_to(ROOT) / "alias_indirection.php")
    aliases = [e for e in _interesting(result) if e.get("kind") == "ALIASES"]
    assert len(aliases) == 1
    assert aliases[0]["source_qname"] == "\\App\\Alias\\Aka"
    assert aliases[0]["target_raw"] == "\\App\\Alias\\Real"


@needs_php
def test_literal_dispatch_shapes() -> None:
    result = parse_file(FIXTURES.relative_to(ROOT) / "literal_dispatch.php")
    shapes = {
        (str(e.get("kind")), str(e.get("target_raw")), e.get("confidence_tier"))
        for e in _interesting(result)
    }
    assert ("CALLS", "\\App\\Dyn\\Foo::bar", "HEURISTIC") in shapes
    assert ("NEW", "\\App\\Dyn\\Foo", "HEURISTIC") in shapes
    assert ("NEW", "(dynamic)", "DYNAMIC") in shapes
    assert ("CALLS", "(dynamic)", "DYNAMIC") in shapes
    # Three HEURISTIC CALLS to Foo::bar: string, array, Foo::{'bar'}
    heuristic_bars = [
        e
        for e in _interesting(result)
        if e.get("kind") == "CALLS"
        and e.get("target_raw") == "\\App\\Dyn\\Foo::bar"
        and e.get("confidence_tier") == "HEURISTIC"
    ]
    assert len(heuristic_bars) == 3


@needs_php
def test_alias_remap_surfaces_alias_caller_under_real(tmp_path: Path) -> None:
    """Proving: Alias NEW/CALLS remap onto Real so nav tools see them under Real."""
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(FIXTURES / "alias_indirection.php", src / "alias_indirection.php")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)

    db_path = tmp_path / ".code-atlas" / "graph.db"
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "1",
            "CA_DB_PATH": str(db_path),
            "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        },
    )
    with GraphStore(db_path) as store:
        report = full_build(config, store)
        assert report.failed == 0
        assert report.parsed == 1

        alias_edges = store.edges_by_source(
            "\\App\\Alias\\Aka", kinds=("ALIASES",), limit=10
        )
        assert len(alias_edges) == 1
        assert alias_edges[0]["target_qname"] == "\\App\\Alias\\Real"
        assert alias_edges[0]["confidence_tier"] == "RESOLVED"

        news = [
            row
            for row in store.edges_by_source(
                "\\App\\Alias\\callerAgainstAlias", kinds=("NEW",), limit=20
            )
        ]
        assert len(news) == 1
        assert news[0]["target_raw"] == "\\App\\Alias\\Aka"
        assert news[0]["target_qname"] == "\\App\\Alias\\Real"
        assert news[0]["confidence_tier"] == "RESOLVED"

        pings = [
            row
            for row in store.edges_by_source(
                "\\App\\Alias\\callerAgainstAlias", kinds=("CALLS",), limit=20
            )
            if row["target_raw"] == "\\App\\Alias\\Aka::ping"
        ]
        assert len(pings) == 1
        assert pings[0]["target_qname"] == "\\App\\Alias\\Real::ping"

    find_refs = create_find_references(config)
    refs = find_refs("\\App\\Alias\\Real")
    sources = {hit["qname"] for hit in refs["results"]}  # type: ignore[index]
    assert "\\App\\Alias\\Aka" in sources  # ALIASES edge
    assert "\\App\\Alias\\callerAgainstAlias" in sources  # remapped NEW

    find_callers = create_find_callers(config)
    callers = find_callers("\\App\\Alias\\Real")
    caller_sources = {hit["qname"] for hit in callers["results"]}  # type: ignore[index]
    assert "\\App\\Alias\\callerAgainstAlias" in caller_sources
