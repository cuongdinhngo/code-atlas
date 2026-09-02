"""Task 204: the bare-name `CALLS` fallback never asks what language the call was written in.

On the anchor monorepo that linked 186,417 JavaScript calls to PHP methods — every one of them a
callee that cannot be called, and 100 % of them produced by this one fallback.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.resolver import resolve_edges
from code_atlas.store import GraphStore

from tests.test_resolver import edge, node


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def seed(store: GraphStore, path: str, language: str, nodes: list, edges: list) -> None:
    store.upsert_file(path, "h", language)
    store.replace_file_rows(path, nodes, edges)


def _two_language_repo(store: GraphStore) -> None:
    """One bare name, three declarations of it: two PHP, one same-language.

    The same-language declaration is what makes this fixture able to FAIL for the right reason —
    without it a green run could mean "the predicate works" or "nothing was linkable at all".
    """
    seed(
        store,
        "vendor/LoggerNDC.php",
        "php",
        [node("Method", "push", "\\LoggerNDC::push", "vendor/LoggerNDC.php")],
        [],
    )
    seed(
        store,
        "vendor/Stack.php",
        "php",
        [node("Method", "push", "\\PHPExcel_Token_Stack::push", "vendor/Stack.php")],
        [],
    )
    seed(
        store,
        "src/queue.ts",
        "typescript",
        [node("Method", "push", "queue.ts::Queue::push", "src/queue.ts")],
        [],
    )
    seed(
        store,
        "src/controller.js",
        "typescript",
        [node("Function", "render", "controller.js::render", "src/controller.js")],
        [edge("CALLS", "controller.js::render", "push", "src/controller.js", tier="HEURISTIC")],
    )


def _targets(store: GraphStore) -> list[str]:
    linked = store.edges_by_source("controller.js::render", kinds=("CALLS",), limit=50)
    return sorted(str(row["target_qname"]) for row in linked if row["target_qname"])


def test_a_bare_name_call_never_links_across_a_language_boundary(store: GraphStore) -> None:
    """AC1. Red before the fix: `\\LoggerNDC::push` and `\\PHPExcel_Token_Stack::push` are linked."""
    _two_language_repo(store)

    resolve_edges(store, max_candidates=50)

    assert _targets(store) == ["queue.ts::Queue::push"]


def test_the_same_language_bare_name_link_still_happens(store: GraphStore) -> None:
    """AC3's direction: the predicate removes the false link, never the fallback itself."""
    _two_language_repo(store)

    resolve_edges(store, max_candidates=50)

    linked = store.edges_by_source("controller.js::render", kinds=("CALLS",), limit=50)
    assert len(linked) == 1
    assert linked[0]["confidence_tier"] == "HEURISTIC"


def test_an_unattributed_call_site_keeps_the_unfiltered_candidate_set(store: GraphStore) -> None:
    """A file row carrying no language is a real state — `edge_language_census` buckets it too.

    Such a call site is not KNOWN to cross a boundary, so it keeps the pre-204 candidate set rather
    than silently losing edges: the fallback narrows on evidence, never on the absence of it.
    """
    seed(
        store,
        "vendor/LoggerNDC.php",
        "php",
        [node("Method", "push", "\\LoggerNDC::push", "vendor/LoggerNDC.php")],
        [],
    )
    seed(
        store,
        "orphan.js",
        "",
        [node("Function", "render", "orphan.js::render", "orphan.js")],
        [edge("CALLS", "orphan.js::render", "push", "orphan.js", tier="HEURISTIC")],
    )

    resolve_edges(store, max_candidates=50)

    linked = store.edges_by_source("orphan.js::render", kinds=("CALLS",), limit=50)
    assert [str(row["target_qname"]) for row in linked] == ["\\LoggerNDC::push"]
