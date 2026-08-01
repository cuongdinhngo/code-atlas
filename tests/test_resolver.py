"""Task 011: cross-file edge resolver — unit cases and the proving integration test (§8.2)."""

import shlex
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.indexer import full_build
from code_atlas.resolver import resolve_edges
from code_atlas.store import GraphStore

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


def seed_file(store: GraphStore, path: str, nodes: list[dict], edges: list[dict]) -> None:
    store.upsert_file(path, "h", "lang")
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
    tier: str | None = None,
    target_qname: str | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "kind": kind,
        "source_qname": source,
        "target_raw": target_raw,
        "file_path": path,
        "line": 3,
    }
    if tier is not None:
        row["confidence_tier"] = tier
    if target_qname is not None:
        row["target_qname"] = target_qname
    return row


def test_one_fqn_candidate_links_as_resolved(store: GraphStore) -> None:
    seed_file(
        store,
        "a.x",
        [
            node("Class", "Child", "\\Ns\\Child", "a.x"),
            node("Class", "Parent", "\\Ns\\Parent", "a.x"),
        ],
        [edge("EXTENDS", "\\Ns\\Child", "\\Ns\\Parent", "a.x")],
    )

    resolve_edges(store, max_candidates=50)

    linked = store.edges_by_source("\\Ns\\Child", kind="EXTENDS", limit=10)
    assert len(linked) == 1
    assert linked[0]["target_qname"] == "\\Ns\\Parent"
    assert linked[0]["confidence_tier"] == "RESOLVED"


def test_heuristic_fqn_match_is_not_promoted_to_resolved(store: GraphStore) -> None:
    """R5.2: a unique qname hit does not upgrade an adapter's HEURISTIC claim (PR review item 1)."""
    seed_file(
        store,
        "a.x",
        [
            node("Method", "save", "\\Ns\\Repo::save", "a.x"),
            node("Method", "put", "\\Ns\\Repo::put", "a.x"),
        ],
        [edge("CALLS", "\\Ns\\Repo::save", "\\Ns\\Repo::put", "a.x", tier="HEURISTIC")],
    )

    resolve_edges(store, max_candidates=50)

    linked = store.edges_by_source("\\Ns\\Repo::save", kind="CALLS", limit=10)
    assert linked[0]["target_qname"] == "\\Ns\\Repo::put"
    assert linked[0]["confidence_tier"] == "HEURISTIC"


def test_many_fqn_candidates_expand_as_heuristic_top_n(store: GraphStore) -> None:
    store.upsert_file("a.x", "h", "lang")
    store.upsert_file("b.x", "h", "lang")
    store.replace_file_rows(
        "a.x",
        [node("Class", "Child", "\\Ns\\Child", "a.x"), node("Class", "Dup", "\\Ns\\Dup", "a.x")],
        [edge("EXTENDS", "\\Ns\\Child", "\\Ns\\Dup", "a.x")],
    )
    store.replace_file_rows(
        "b.x",
        [node("Class", "Dup", "\\Ns\\Dup", "b.x")],
        [],
    )

    resolve_edges(store, max_candidates=50)

    linked = store.edges_by_source("\\Ns\\Child", kind="EXTENDS", limit=10)
    assert len(linked) == 2
    assert {row["target_qname"] for row in linked} == {"\\Ns\\Dup"}
    assert {row["file_path"] for row in store.nodes_by_qualified_name("\\Ns\\Dup", limit=10)} == {
        "a.x",
        "b.x",
    }
    assert all(row["confidence_tier"] == "HEURISTIC" for row in linked)


def test_many_method_name_matches_respect_max_candidates(store: GraphStore) -> None:
    seed_file(
        store,
        "a.x",
        [
            node("Method", "save", "\\A::save", "a.x"),
            node("Method", "put", "\\A::put", "a.x"),
            node("Method", "put", "\\B::put", "a.x"),
            node("Method", "put", "\\C::put", "a.x"),
        ],
        [edge("CALLS", "\\A::save", "put", "a.x", tier="HEURISTIC")],
    )

    resolve_edges(store, max_candidates=2)

    linked = store.edges_by_source("\\A::save", kind="CALLS", limit=10)
    assert len(linked) == 2
    assert [row["target_qname"] for row in linked] == ["\\A::put", "\\B::put"]
    assert all(row["confidence_tier"] == "HEURISTIC" for row in linked)


def test_dynamic_edges_stay_unlinked(store: GraphStore) -> None:
    seed_file(
        store,
        "a.x",
        [node("File", "a.x", "a.x", "a.x")],
        [edge("INCLUDES", "a.x", "(dynamic)", "a.x", tier="DYNAMIC")],
    )

    resolve_edges(store, max_candidates=50)

    assert store.unresolved_edges()[0]["target_qname"] is None
    assert store.unresolved_edges()[0]["confidence_tier"] == "DYNAMIC"


def test_literal_include_resolves_relative_to_includer(store: GraphStore) -> None:
    store.upsert_file("src/app.x", "h", "lang")
    store.upsert_file("src/lib.x", "h", "lang")
    store.replace_file_rows(
        "src/app.x",
        [node("File", "src/app.x", "src/app.x", "src/app.x")],
        [edge("INCLUDES", "src/app.x", "lib.x", "src/app.x")],
    )
    store.replace_file_rows(
        "src/lib.x",
        [node("File", "src/lib.x", "src/lib.x", "src/lib.x")],
        [],
    )

    resolve_edges(store, max_candidates=50)

    linked = store.edges_by_source("src/app.x", kind="INCLUDES", limit=10)
    assert linked[0]["target_qname"] == "src/lib.x"
    assert linked[0]["confidence_tier"] == "RESOLVED"


def test_prelinked_edges_are_left_alone(store: GraphStore) -> None:
    seed_file(
        store,
        "a.x",
        [node("Class", "Child", "\\Ns\\Child", "a.x")],
        [
            edge(
                "EXTENDS",
                "\\Ns\\Child",
                "\\Vendor\\Base",
                "a.x",
                target_qname="\\Vendor\\Base",
                tier="RESOLVED",
            )
        ],
    )

    resolve_edges(store, max_candidates=50)

    linked = store.edges_by_source("\\Ns\\Child", kind="EXTENDS", limit=10)
    assert linked[0]["target_qname"] == "\\Vendor\\Base"
    assert linked[0]["confidence_tier"] == "RESOLVED"


def test_external_fqn_stays_unlinked(store: GraphStore) -> None:
    seed_file(
        store,
        "a.x",
        [node("Class", "Child", "\\Ns\\Child", "a.x")],
        [edge("EXTENDS", "\\Ns\\Child", "\\Vendor\\Missing", "a.x")],
    )

    resolve_edges(store, max_candidates=50)

    assert store.edges_by_source("\\Ns\\Child", kind="EXTENDS", limit=10)[0]["target_qname"] is None


@needs_php
def test_full_build_resolves_a_known_caller_chain_on_fixtures(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2 proving test: fails pre-change (no linker), passes once resolve_edges is wired."""
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

    extends = store.edges_by_source("\\App\\User", kind="EXTENDS", limit=10)
    assert extends[0]["target_qname"] == "\\App\\Base"
    assert extends[0]["confidence_tier"] == "RESOLVED"

    helper_calls = [
        row
        for row in store.edges_by_source("\\App\\User::save", kind="CALLS", limit=20)
        if row["target_raw"] == "\\App\\helper"
    ]
    assert len(helper_calls) == 1
    assert helper_calls[0]["target_qname"] == "\\App\\helper"
    assert helper_calls[0]["confidence_tier"] == "RESOLVED"

    put_calls = [
        row
        for row in store.edges_by_source("\\App\\User::save", kind="CALLS", limit=20)
        if row["target_raw"] == "put"
    ]
    assert len(put_calls) == 1
    assert put_calls[0]["target_qname"] == "\\App\\Repo::put"
    assert put_calls[0]["confidence_tier"] == "HEURISTIC"

    callers = store.edges_by_target("\\App\\Repo::put", kind="CALLS", limit=10)
    assert [row["source_qname"] for row in callers] == ["\\App\\User::save"]
