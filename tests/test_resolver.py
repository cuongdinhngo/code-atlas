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

    linked = store.edges_by_source("\\Ns\\Child", kinds=("EXTENDS",), limit=10)
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

    linked = store.edges_by_source("\\Ns\\Repo::save", kinds=("CALLS",), limit=10)
    assert linked[0]["target_qname"] == "\\Ns\\Repo::put"
    assert linked[0]["confidence_tier"] == "HEURISTIC"


def test_one_qname_in_many_files_links_once_and_stays_resolved(store: GraphStore) -> None:
    """Task 046: multiplicity across files is not ambiguity — an edge records a qname, not a file.

    Before, each extra node became a sibling that differed from the original in nothing, and the
    node count downgraded the edge to HEURISTIC.
    """
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

    linked = store.edges_by_source("\\Ns\\Child", kinds=("EXTENDS",), limit=10)
    assert len(linked) == 1, "one qname resolved, so one edge — not one per declaring file"
    assert linked[0]["target_qname"] == "\\Ns\\Dup"
    assert linked[0]["confidence_tier"] == "RESOLVED"
    # Nothing is lost: both declarations are still nodes, so search/outline still show both files.
    assert {row["file_path"] for row in store.nodes_by_qualified_name("\\Ns\\Dup", limit=10)} == {
        "a.x",
        "b.x",
    }


def test_multi_file_qname_never_promotes_an_adapter_heuristic_claim(store: GraphStore) -> None:
    """R5.2 still governs: computing RESOLVED must not upgrade a weaker incoming tier."""
    store.upsert_file("a.x", "h", "lang")
    store.upsert_file("b.x", "h", "lang")
    store.replace_file_rows(
        "a.x",
        [node("Class", "Child", "\\Ns\\Child", "a.x"), node("Class", "Dup", "\\Ns\\Dup", "a.x")],
        [edge("CALLS", "\\Ns\\Child", "\\Ns\\Dup", "a.x", tier="HEURISTIC")],
    )
    store.replace_file_rows("b.x", [node("Class", "Dup", "\\Ns\\Dup", "b.x")], [])

    resolve_edges(store, max_candidates=50)

    linked = store.edges_by_source("\\Ns\\Child", kinds=("CALLS",), limit=10)
    assert len(linked) == 1
    assert linked[0]["confidence_tier"] == "HEURISTIC"


def test_resolve_is_idempotent_on_an_already_resolved_store(store: GraphStore) -> None:
    """A second pass must add nothing — otherwise duplicates return by another route."""
    store.upsert_file("a.x", "h", "lang")
    store.upsert_file("b.x", "h", "lang")
    store.replace_file_rows(
        "a.x",
        [node("Class", "Child", "\\Ns\\Child", "a.x"), node("Class", "Dup", "\\Ns\\Dup", "a.x")],
        [edge("EXTENDS", "\\Ns\\Child", "\\Ns\\Dup", "a.x")],
    )
    store.replace_file_rows("b.x", [node("Class", "Dup", "\\Ns\\Dup", "b.x")], [])

    resolve_edges(store, max_candidates=50)
    first = store.edges_by_source("\\Ns\\Child", kinds=("EXTENDS",), limit=50)
    resolve_edges(store, max_candidates=50)
    second = store.edges_by_source("\\Ns\\Child", kinds=("EXTENDS",), limit=50)

    assert first == second


def test_no_exact_duplicate_edge_rows_survive_a_resolve(store: GraphStore) -> None:
    """The store-level statement of the defect: no group of rows equal in every column but id."""
    store.upsert_file("a.x", "h", "lang")
    for path in ("b.x", "c.x", "d.x"):
        store.upsert_file(path, "h", "lang")
    store.replace_file_rows(
        "a.x",
        [
            node("Class", "Child", "\\Ns\\Child", "a.x"),
            node("Class", "Dup", "\\Ns\\Dup", "a.x"),
            node("Class", "Dup", "\\Ns\\Dup", "b.x"),
            node("Class", "Dup", "\\Ns\\Dup", "c.x"),
            node("Class", "Dup", "\\Ns\\Dup", "d.x"),
        ],
        [edge("EXTENDS", "\\Ns\\Child", "\\Ns\\Dup", "a.x")],
    )

    resolve_edges(store, max_candidates=50)

    groups = store._conn.execute(
        "SELECT count(*) FROM (SELECT kind, source_qname, target_qname, target_raw, file_path, "
        "line, confidence_tier, count(*) n FROM edges GROUP BY 1,2,3,4,5,6,7 HAVING n > 1)"
    ).fetchone()[0]
    assert groups == 0


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

    linked = store.edges_by_source("\\A::save", kinds=("CALLS",), limit=10)
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

    linked = store.edges_by_source("src/app.x", kinds=("INCLUDES",), limit=10)
    assert linked[0]["target_qname"] == "src/lib.x"
    assert linked[0]["confidence_tier"] == "RESOLVED"


def test_batched_includes_dedupe_shared_path_and_skip_ambiguous(store: GraphStore) -> None:
    """Batch INCLUDES: duplicate resolved paths still link; ambiguous File qname is skipped."""
    for path in ("pkg/a.x", "other/b.x", "x.x", "shared.x", "t1.x", "t2.x"):
        store.upsert_file(path, "h", "lang")
    store.replace_file_rows(
        "shared.x",
        [node("File", "shared.x", "shared.x", "shared.x")],
        [],
    )
    # Same File qname, two file_paths → len(hits) == 2 → skip.
    store.replace_file_rows(
        "t1.x",
        [node("File", "dup.x", "dup.x", "t1.x")],
        [],
    )
    store.replace_file_rows(
        "t2.x",
        [node("File", "dup.x", "dup.x", "t2.x")],
        [],
    )
    store.replace_file_rows(
        "pkg/a.x",
        [node("File", "pkg/a.x", "pkg/a.x", "pkg/a.x")],
        [edge("INCLUDES", "pkg/a.x", "../shared.x", "pkg/a.x")],
    )
    store.replace_file_rows(
        "other/b.x",
        [node("File", "other/b.x", "other/b.x", "other/b.x")],
        [edge("INCLUDES", "other/b.x", "../shared.x", "other/b.x")],
    )
    store.replace_file_rows(
        "x.x",
        [node("File", "x.x", "x.x", "x.x")],
        [edge("INCLUDES", "x.x", "dup.x", "x.x")],
    )

    resolve_edges(store, max_candidates=50)

    for source in ("pkg/a.x", "other/b.x"):
        linked = store.edges_by_source(source, kinds=("INCLUDES",), limit=10)
        assert len(linked) == 1
        assert linked[0]["target_qname"] == "shared.x"
        assert linked[0]["confidence_tier"] == "RESOLVED"
    ambiguous = store.edges_by_source("x.x", kinds=("INCLUDES",), limit=10)
    assert len(ambiguous) == 1
    assert ambiguous[0]["target_qname"] is None


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

    linked = store.edges_by_source("\\Ns\\Child", kinds=("EXTENDS",), limit=10)
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

    linked = store.edges_by_source("\\Ns\\Child", kinds=("EXTENDS",), limit=10)
    assert linked[0]["target_qname"] is None


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

    extends = store.edges_by_source("\\App\\User", kinds=("EXTENDS",), limit=10)
    assert extends[0]["target_qname"] == "\\App\\Base"
    assert extends[0]["confidence_tier"] == "RESOLVED"

    helper_calls = [
        row
        for row in store.edges_by_source("\\App\\User::save", kinds=("CALLS",), limit=20)
        if row["target_raw"] == "\\App\\helper"
    ]
    assert len(helper_calls) == 1
    assert helper_calls[0]["target_qname"] == "\\App\\helper"
    assert helper_calls[0]["confidence_tier"] == "RESOLVED"

    # `Repo $repo` is the receiver's type, so `$repo->put()` names the declaration site and the
    # bare-name fallback this fixture was built for is not reached at all (137).
    put_calls = [
        row
        for row in store.edges_by_source("\\App\\User::save", kinds=("CALLS",), limit=20)
        if row["target_raw"] == "\\App\\Repo::put"
    ]
    assert len(put_calls) == 1
    assert put_calls[0]["target_qname"] == "\\App\\Repo::put"
    assert put_calls[0]["confidence_tier"] == "RESOLVED"

    callers = store.edges_by_target("\\App\\Repo::put", kinds=("CALLS",), limit=10)
    assert [row["source_qname"] for row in callers] == ["\\App\\User::save"]


def test_batched_resolve_matches_golden_and_is_o1_selects(
    store: GraphStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task 027 proving: multi-candidate CALLS order + O(1) ``_rows`` SELECTs per batch."""
    nodes = [
        node("Class", "Child", "\\Ns\\Child", "c.x"),
        node("Class", "Parent", "\\Ns\\Parent", "p1.x"),
        node("Class", "Parent", "\\Ns\\Parent", "p2.x"),
        node("Method", "save", "\\A::save", "a.x"),
        node("Method", "put", "\\A::put", "a.x"),
        node("Method", "put", "\\B::put", "b.x"),
        node("Method", "put", "\\C::put", "c.x"),
    ]
    edges = [
        edge("EXTENDS", "\\Ns\\Child", "\\Ns\\Parent", "c.x"),
        *[
            edge("CALLS", "\\A::save", "put", f"call{i}.x", tier="HEURISTIC")
            for i in range(10)
        ],
    ]
    files = sorted({str(n["file_path"]) for n in nodes} | {str(e["file_path"]) for e in edges})
    for path in files:
        store.upsert_file(path, "h", "lang")
    # One replace_file_rows per file would wipe siblings; insert via the first path after upserts.
    store.replace_file_rows(files[0], nodes, edges)

    calls = {"n": 0}
    original = GraphStore._rows

    def counting(
        self: GraphStore, keys: tuple[str, ...], sql: str, params: object
    ) -> list[dict[str, object]]:
        calls["n"] += 1
        return original(self, keys, sql, params)  # type: ignore[arg-type]

    monkeypatch.setattr(GraphStore, "_rows", counting)
    resolve_edges(store, max_candidates=2)

    # Budget: iter_unresolved_edges (batch + empty end) + FQN pass + Method pass.
    # Both node lookups fit one `_IN_CHUNK` here; large batches use ≤3 SELECTs each.
    assert calls["n"] <= 4

    extends = store.edges_by_source("\\Ns\\Child", kinds=("EXTENDS",), limit=10)
    # Both candidates carry the same qname, so they collapse to one RESOLVED edge (task 046).
    assert len(extends) == 1
    assert extends[0]["target_qname"] == "\\Ns\\Parent"
    assert extends[0]["confidence_tier"] == "RESOLVED"

    puts = store.edges_by_source("\\A::save", kinds=("CALLS",), limit=50)
    # 10 CALLS × 2 candidates each (primary + sibling) with identical target set order.
    assert len(puts) == 20
    by_file = {}
    for row in puts:
        by_file.setdefault(row["file_path"], []).append(
            (row["target_qname"], row["confidence_tier"])
        )
    expected = [("\\A::put", "HEURISTIC"), ("\\B::put", "HEURISTIC")]
    for i in range(10):
        assert by_file[f"call{i}.x"] == expected


def test_batch_lookup_caps_per_key_not_globally(store: GraphStore) -> None:
    """AC3: two qnames each with 3 hits → max_candidates=2 keeps 2 per key (not 2 total)."""
    nodes = [
        node("Class", "A", "\\Ns\\A", "a1.x"),
        node("Class", "A", "\\Ns\\A", "a2.x"),
        node("Class", "A", "\\Ns\\A", "a3.x"),
        node("Class", "B", "\\Ns\\B", "b1.x"),
        node("Class", "B", "\\Ns\\B", "b2.x"),
        node("Class", "B", "\\Ns\\B", "b3.x"),
    ]
    for path in sorted({str(n["file_path"]) for n in nodes}):
        store.upsert_file(path, "h", "lang")
    store.replace_file_rows("a1.x", nodes, [])
    found = store.nodes_by_qualified_names(["\\Ns\\A", "\\Ns\\B"], limit=2)
    assert len(found["\\Ns\\A"]) == 2
    assert len(found["\\Ns\\B"]) == 2
    assert [row["file_path"] for row in found["\\Ns\\A"]] == ["a1.x", "a2.x"]
    assert [row["file_path"] for row in found["\\Ns\\B"]] == ["b1.x", "b2.x"]


def test_nodes_by_names_top_n_follows_qualified_name_not_file_path(
    store: GraphStore,
) -> None:
    """Regression: same name, file_path order ≠ qualified_name order (review BLOCK)."""
    nodes = [
        node("Method", "put", "\\Z::put", "a.x"),
        node("Method", "put", "\\A::put", "z.x"),
    ]
    for path in ("a.x", "z.x"):
        store.upsert_file(path, "h", "lang")
    store.replace_file_rows("a.x", nodes, [])

    singular = store.nodes_by_name("put", kind="Method", limit=1)
    batched = store.nodes_by_names(["put"], kind="Method", limit=1)["put"]
    assert [row["qualified_name"] for row in singular] == ["\\A::put"]
    assert [row["qualified_name"] for row in batched] == ["\\A::put"]
