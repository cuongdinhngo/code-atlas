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
def test_contract_version_is_current() -> None:
    assert CONTRACT_VERSION == 14


@needs_php
def test_class_alias_emits_aliases_edge() -> None:
    result = parse_file(FIXTURES.relative_to(ROOT) / "alias_indirection.php")
    aliases = [e for e in _interesting(result) if e.get("kind") == "ALIASES"]
    assert {
        (e["source_qname"], e["target_raw"]) for e in aliases
    } == {
        ("\\App\\Alias\\Aka", "\\App\\Alias\\Real"),
        ("\\App\\Alias\\Aka2", "\\App\\Alias\\Aka"),
    }


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
    # Non-literal call_user_func → DYNAMIC (finding 6).
    cuf_dynamic = [
        e
        for e in _interesting(result)
        if e.get("kind") == "CALLS"
        and e.get("target_raw") == "(dynamic)"
        and e.get("confidence_tier") == "DYNAMIC"
        and e.get("source_qname") == "\\App\\Dyn\\literals"
    ]
    assert len(cuf_dynamic) >= 2  # call_user_func($cb) + $obj->$method()
    # AssignOp / foreach invalidate → DYNAMIC new (finding 3).
    stale = [
        e
        for e in _interesting(result)
        if e.get("kind") == "NEW"
        and e.get("source_qname") == "\\App\\Dyn\\staleBinding"
    ]
    assert all(e.get("target_raw") == "(dynamic)" for e in stale)
    assert len(stale) == 2
    # Leave clears — afterStale must not reuse prior binding (finding 2).
    after = [
        e
        for e in _interesting(result)
        if e.get("kind") == "NEW"
        and e.get("source_qname") == "\\App\\Dyn\\afterStale"
    ]
    assert len(after) == 1
    assert after[0]["target_raw"] == "(dynamic)"
    # Arrow inherits outer $literal (finding 9).
    arrow_news = [
        e
        for e in _interesting(result)
        if e.get("kind") == "NEW"
        and str(e.get("source_qname", "")).startswith("\\App\\Dyn\\literals::{fn")
        and e.get("target_raw") == "\\App\\Dyn\\Foo"
        and e.get("confidence_tier") == "HEURISTIC"
    ]
    assert len(arrow_news) == 1


@needs_php
def test_string_static_call_rewrites_self() -> None:
    result = parse_file(FIXTURES.relative_to(ROOT) / "literal_dispatch.php")
    shapes = {
        (str(e.get("target_raw")), e.get("confidence_tier"))
        for e in _interesting(result)
        if e.get("kind") == "CALLS"
    }
    assert ("\\App\\Dyn\\SelfString::bar", "HEURISTIC") in shapes
    assert ("\\self::bar", "HEURISTIC") not in shapes
    assert ("\\self::bar", None) not in shapes


@needs_php
def test_literal_dispatch_resolves_heuristic_and_leaves_dynamic(tmp_path: Path) -> None:
    """AC3 on resolved rows: HEURISTIC links; DYNAMIC stays unlinked."""
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(FIXTURES / "literal_dispatch.php", src / "literal_dispatch.php")
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
        assert full_build(config, store).failed == 0
        rows = store.edges_by_source(
            "\\App\\Dyn\\literals", kinds=("CALLS", "NEW"), limit=50
        )
        by_key = [
            (
                str(r["kind"]),
                str(r["target_raw"]),
                str(r["confidence_tier"]),
                r["target_qname"],
            )
            for r in rows
        ]
        assert (
            "CALLS",
            "\\App\\Dyn\\Foo::bar",
            "HEURISTIC",
            "\\App\\Dyn\\Foo::bar",
        ) in by_key
        assert ("NEW", "\\App\\Dyn\\Foo", "HEURISTIC", "\\App\\Dyn\\Foo") in by_key
        assert ("NEW", "(dynamic)", "DYNAMIC", None) in by_key
        assert ("CALLS", "(dynamic)", "DYNAMIC", None) in by_key
        assert (
            sum(
                1
                for s in by_key
                if s[0] == "CALLS"
                and s[1] == "\\App\\Dyn\\Foo::bar"
                and s[2] == "HEURISTIC"
            )
            == 3
        )


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

        chain = store.edges_by_source(
            "\\App\\Alias\\Aka2", kinds=("ALIASES",), limit=10
        )
        assert len(chain) == 1
        assert chain[0]["target_raw"] == "\\App\\Alias\\Aka"
        # Aka is not a Class node — ALIASES may stay unlinked; CALLS/NEW follow the chain.

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

        chained = store.edges_by_source(
            "\\App\\Alias\\callerAgainstChain", kinds=("NEW",), limit=20
        )
        assert len(chained) == 1
        assert chained[0]["target_raw"] == "\\App\\Alias\\Aka2"
        assert chained[0]["target_qname"] == "\\App\\Alias\\Real"

        pings = [
            row
            for row in store.edges_by_source(
                "\\App\\Alias\\callerAgainstAlias", kinds=("CALLS",), limit=20
            )
            if row["target_raw"] == "\\App\\Alias\\Aka::ping"
        ]
        assert len(pings) == 1
        assert pings[0]["target_qname"] == "\\App\\Alias\\Real::ping"

        chain_pings = [
            row
            for row in store.edges_by_source(
                "\\App\\Alias\\callerAgainstChain", kinds=("CALLS",), limit=20
            )
            if row["target_raw"] == "\\App\\Alias\\Aka2::ping"
        ]
        assert len(chain_pings) == 1
        assert chain_pings[0]["target_qname"] == "\\App\\Alias\\Real::ping"

    find_refs = create_find_references(config)
    refs = find_refs("\\App\\Alias\\Real")
    sources = {hit["qname"] for hit in refs["results"]}  # type: ignore[index]
    assert "\\App\\Alias\\Aka" in sources  # ALIASES edge
    assert "\\App\\Alias\\callerAgainstAlias" in sources  # remapped NEW

    find_callers = create_find_callers(config)
    callers = find_callers("\\App\\Alias\\Real")
    caller_sources = {hit["qname"] for hit in callers["results"]}  # type: ignore[index]
    assert "\\App\\Alias\\callerAgainstAlias" in caller_sources
    assert "\\App\\Alias\\callerAgainstChain" in caller_sources


@needs_php
def test_stale_contract_version_forces_full_rebuild(tmp_path: Path) -> None:
    """AC1: meta.contract_version lag → incremental_update rebuilds fully (finding 5)."""
    from code_atlas.indexer import incremental_update
    from code_atlas.store import CONTRACT_VERSION_KEY

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
        assert full_build(config, store).failed == 0
        store.set_meta(CONTRACT_VERSION_KEY, "1")
        report = incremental_update(config, store, ["src/alias_indirection.php"])
        assert report.failed == 0
        assert store.get_meta(CONTRACT_VERSION_KEY) == str(CONTRACT_VERSION)
