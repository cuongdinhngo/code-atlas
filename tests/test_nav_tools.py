"""Task 013: navigation tools over the resolved graph (§12).

Proving path is integration: build the resolve fixtures, then call the tools — the same layer where
a missing linker, a wrong kind filter, or a silent DYNAMIC drop would fail.
"""

from __future__ import annotations

import hashlib
import shlex
import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.build_info import server_provenance
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_implementations, find_references
from code_atlas.tools.find_callers import _callers

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
RESOLVE_FIXTURES = REPO / "tests" / "fixtures" / "php" / "resolve"

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def db_config(tmp_path: Path) -> Config:
    return replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")


def seed_file(
    store: GraphStore, path: str, nodes: list[dict], edges: list[dict], *, root: Path
) -> None:
    """Plant rows and matching on-disk bytes so FreshnessGuard does not treat the path as stale."""
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    body = b"# planted\n"
    target.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    store.upsert_file(path, digest, "lang")
    store.replace_file_rows(path, nodes, edges)


def node(kind: str, name: str, qname: str, path: str) -> dict[str, object]:
    return {
        "kind": kind,
        "name": name,
        "qualified_name": qname,
        "file_path": path,
        "line_start": 1,
    }


def edge(
    kind: str,
    source: str,
    target_raw: str,
    path: str,
    *,
    target_qname: str | None = None,
    tier: str = "RESOLVED",
    line: int = 1,
) -> dict[str, object]:
    row: dict[str, object] = {
        "kind": kind,
        "source_qname": source,
        "target_raw": target_raw,
        "file_path": path,
        "line": line,
        "confidence_tier": tier,
    }
    if target_qname is not None:
        row["target_qname"] = target_qname
    return row


def resolve_repo(tmp_path: Path, store: GraphStore) -> None:
    src = tmp_path / "src"
    src.mkdir()
    for fixture in sorted(RESOLVE_FIXTURES.glob("*.php")):
        shutil.copy(fixture, src / fixture.name)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    config = load_config(
        tmp_path,
        {
            "CA_WORKERS": "2",
            "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        },
    )
    report = full_build(config, store)
    assert report.parsed == 4 and report.failed == 0


@needs_php
def test_find_callers_matches_resolve_fixture_baseline(tmp_path: Path, store: GraphStore) -> None:
    """AC1 proving test: known callers of ``\\App\\Repo::put`` match the manual resolve baseline."""
    resolve_repo(tmp_path, store)
    result = find_callers.create(db_config(tmp_path))(
        "\\App\\Repo::put", depth=1, detail_level="minimal"
    )

    assert result["indexed"] is True
    hits = result["results"]
    assert len(hits) == 1
    assert hits[0]["qname"] == "\\App\\User::save"
    assert hits[0]["kind"] == "CALLS"
    # `Repo $repo` types the receiver, so the caller is known rather than name-matched (137).
    assert hits[0]["confidence_tier"] == "RESOLVED"
    assert hits[0]["file"]
    assert hits[0]["line"]
    assert hits[0]["depth"] == 1
    assert result["truncated"] is False
    assert result["frontier_skipped_non_resolved"] == 0

    deep = find_callers.create(db_config(tmp_path))(
        "\\App\\Repo::put", depth=3, detail_level="minimal"
    )
    assert len(deep["results"]) == 1
    assert deep["depth"] == 3
    # This fixture no longer has a non-RESOLVED frontier edge to skip: its one HEURISTIC hop was
    # `$repo->put()`, which the receiver's type now settles (137). The counter itself is proven on
    # a store built for it, below and in test_impact.py — not incidentally, here.
    assert deep["frontier_skipped_non_resolved"] == 0


def test_dynamic_edges_are_flagged_and_not_traversed(tmp_path: Path, store: GraphStore) -> None:
    """AC2 / A3: DYNAMIC appears in results; the BFS does not walk through it."""
    seed_file(
        store,
        "a.x",
        [
            node("Function", "entry", "\\entry", "a.x"),
            node("Function", "mid", "\\mid", "a.x"),
            node("Function", "leaf", "\\leaf", "a.x"),
        ],
        [
            # entry → mid is RESOLVED; mid → leaf is DYNAMIC — depth=2 must not reach entry.
            edge("CALLS", "\\entry", "mid", "a.x", target_qname="\\mid", tier="RESOLVED", line=2),
            edge("CALLS", "\\mid", "leaf", "a.x", target_qname="\\leaf", tier="DYNAMIC", line=3),
        ],
        root=tmp_path,
    )

    direct = _callers(store, "\\leaf", hops=1, limit=50)
    assert [(h["qname"], h["confidence_tier"]) for h in direct.results] == [("\\mid", "DYNAMIC")]
    assert direct.frontier_skipped_non_resolved == 0

    deep = _callers(store, "\\leaf", hops=2, limit=50)
    assert [h["qname"] for h in deep.results] == ["\\mid"]
    assert deep.frontier_skipped_non_resolved == 1


def test_heuristic_edges_are_not_traversed_at_depth(tmp_path: Path, store: GraphStore) -> None:
    seed_file(
        store,
        "a.x",
        [
            node("Function", "a", "\\a", "a.x"),
            node("Function", "b", "\\b", "a.x"),
            node("Function", "c", "\\c", "a.x"),
        ],
        [
            edge("CALLS", "\\a", "b", "a.x", target_qname="\\b", tier="RESOLVED"),
            edge("CALLS", "\\b", "c", "a.x", target_qname="\\c", tier="HEURISTIC"),
        ],
        root=tmp_path,
    )
    # HEURISTIC b→c is returned; RESOLVED a→b is not reached because b is not enqueued.
    outcome = _callers(store, "\\c", hops=2, limit=50)
    assert [h["qname"] for h in outcome.results] == ["\\b"]
    assert outcome.results[0]["confidence_tier"] == "HEURISTIC"
    assert outcome.frontier_skipped_non_resolved == 1


def test_find_implementations_are_direct_only(tmp_path: Path, store: GraphStore) -> None:
    seed_file(
        store,
        "a.x",
        [
            node("Class", "Base", "\\Base", "a.x"),
            node("Class", "Child", "\\Child", "a.x"),
            node("Class", "Grand", "\\Grand", "a.x"),
        ],
        [
            edge("EXTENDS", "\\Child", "\\Base", "a.x", target_qname="\\Base"),
            edge("EXTENDS", "\\Grand", "\\Child", "a.x", target_qname="\\Child"),
        ],
        root=tmp_path,
    )
    result = find_implementations.create(db_config(tmp_path))("\\Base", detail_level="minimal")
    assert [h["qname"] for h in result["results"]] == ["\\Child"]
    assert result["results"][0]["kind"] == "EXTENDS"


def test_find_references_returns_seeded_linked_kinds(tmp_path: Path, store: GraphStore) -> None:
    """Seeded filter check: any linked kind targeting the qname is returned (SQL path)."""
    seed_file(
        store,
        "a.x",
        [
            node("Class", "T", "\\T", "a.x"),
            node("Class", "U", "\\U", "a.x"),
            node("Function", "f", "\\f", "a.x"),
        ],
        [
            edge("EXTENDS", "\\U", "\\T", "a.x", target_qname="\\T"),
            edge("CALLS", "\\f", "\\T", "a.x", target_qname="\\T", tier="HEURISTIC"),
            edge("NEW", "\\f", "\\T", "a.x", target_qname="\\T"),
        ],
        root=tmp_path,
    )
    result = find_references.create(db_config(tmp_path))("\\T", detail_level="minimal")
    assert sorted(h["kind"] for h in result["results"]) == ["CALLS", "EXTENDS", "NEW"]
    assert {h["confidence_tier"] for h in result["results"]} >= {"RESOLVED", "HEURISTIC"}
    assert result["truncated"] is False


@needs_php
def test_find_references_matches_resolve_fixture_extends(tmp_path: Path, store: GraphStore) -> None:
    """End-to-end: adapter + resolver link EXTENDS for ``\\App\\User`` → ``\\App\\Base``."""
    resolve_repo(tmp_path, store)
    result = find_references.create(db_config(tmp_path))("\\App\\Base", detail_level="minimal")
    assert result["indexed"] is True
    assert any(
        h["qname"] == "\\App\\User"
        and h["kind"] == "EXTENDS"
        and h["confidence_tier"] == "RESOLVED"
        for h in result["results"]
    )


def test_missing_database_does_not_create_one(tmp_path: Path) -> None:
    config = load_config(tmp_path, {})
    assert not config.db_path.is_file()
    result = find_callers.create(config)("\\X", detail_level="minimal")
    assert result == {
        "indexed": False,
        "qname": "\\X",
        "results": [],
        "truncated": False,
        "reason": "not_indexed",
        "total_count": 0,
        "index_root": str(config.root.resolve()),
    }
    assert "server_version" not in result  # 223: minimal leaves identity to status
    assert not config.db_path.is_file()
    standard = find_callers.create(config)("\\X", detail_level="standard")
    identity = ("server_version", "server_build", "server_stale_process")
    assert {k: standard[k] for k in identity} == {
        k: server_provenance()[k] for k in identity
    }


def test_exact_qname_does_not_expand_to_members(tmp_path: Path, store: GraphStore) -> None:
    seed_file(
        store,
        "a.x",
        [
            node("Class", "T", "\\T", "a.x"),
            node("Method", "m", "\\T::m", "a.x"),
            node("Function", "f", "\\f", "a.x"),
        ],
        [
            edge("CALLS", "\\f", "\\T::m", "a.x", target_qname="\\T::m"),
            edge("NEW", "\\f", "\\T", "a.x", target_qname="\\T"),
        ],
        root=tmp_path,
    )
    assert [h["kind"] for h in _callers(store, "\\T", hops=1, limit=50).results] == ["NEW"]
    assert [h["qname"] for h in _callers(store, "\\T::m", hops=1, limit=50).results] == ["\\f"]


def test_nav_results_flag_truncation(tmp_path: Path, store: GraphStore) -> None:
    nodes = [node("Function", f"f{i}", f"\\f{i}", "a.x") for i in range(5)]
    nodes.append(node("Function", "t", "\\t", "a.x"))
    edges = [
        edge("CALLS", f"\\f{i}", "\\t", "a.x", target_qname="\\t") for i in range(5)
    ]
    seed_file(store, "a.x", nodes, edges, root=tmp_path)
    config = replace(db_config(tmp_path), max_results=2)
    result = find_callers.create(config)("\\t", detail_level="minimal")
    assert len(result["results"]) == 2
    assert result["truncated"] is True
    assert result["total_count"] == 5
    assert result["reason"] == "ok"


def test_depth_below_one_fails_loud(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="depth must be >= 1"):
        find_callers.create(db_config(tmp_path))("\\X", depth=0)
