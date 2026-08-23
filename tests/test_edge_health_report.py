"""Task 136: the HEURISTIC cause breakdown — the classifier, without php or a network.

`scripts/edge_health_report.py` is the instrument a decision rests on, so its taxonomy needs its
own guard: an emission site the adapter grows and the report does not know must FAIL, not fold
silently into a bucket that flatters whichever answer the reader wanted.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.store import GraphStore

REPO = Path(__file__).resolve().parent.parent
REPORTER = REPO / "scripts" / "edge_health_report.py"


def _load():
    spec = importlib.util.spec_from_file_location("edge_health_report", REPORTER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_r = _load()
PATH = "a.php"


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / ".code-atlas" / "graph.db") as opened:
        yield opened


def _node(kind: str, qname: str) -> dict[str, object]:
    return {
        "kind": kind,
        "name": qname.rpartition("::")[2] or qname,
        "qualified_name": qname,
        "file_path": PATH,
        "line_start": 1,
    }


def _edge(kind: str, source: str, raw: str, **rest: object) -> dict[str, object]:
    row: dict[str, object] = {
        "kind": kind,
        "source_qname": source,
        "target_raw": raw,
        "file_path": PATH,
        "line": 7,
        "confidence_tier": "HEURISTIC",
    }
    row.update(rest)
    return row


def _seed(
    store: GraphStore, nodes: list[dict[str, object]], edges: list[dict[str, object]]
) -> None:
    store.upsert_file(PATH, "h", "php")
    store.replace_file_rows(PATH, nodes, edges)


def _causes(store: GraphStore) -> dict[str, int]:
    labelled = _r.classify(store, _r.heuristic_edges(store))
    counted: dict[str, int] = {}
    for cause, _edge in labelled:
        counted[cause] = counted.get(cause, 0) + 1
    return counted


def test_a_bare_method_call_with_no_declaring_ancestor_is_an_unknown_receiver(
    store: GraphStore,
) -> None:
    _seed(
        store,
        [_node("Class", "\\App\\Svc"), _node("Method", "\\App\\Svc::run")],
        [_edge("CALLS", "\\App\\Svc::run", "fetch")],
    )
    assert _causes(store) == {"unknown_receiver": 1}


def test_a_bare_method_the_parent_declares_is_the_inherited_cause(store: GraphStore) -> None:
    """Settled by walking EXTENDS, which the graph already holds — no type inference needed."""
    _seed(
        store,
        [
            _node("Class", "\\App\\Child"),
            _node("Method", "\\App\\Child::run"),
            _node("Class", "\\App\\Base"),
            _node("Method", "\\App\\Base::fetch"),
        ],
        [
            _edge("EXTENDS", "\\App\\Child", "\\App\\Base", target_qname="\\App\\Base"),
            _edge("CALLS", "\\App\\Child::run", "fetch"),
        ],
    )
    assert _causes(store)["inherited_or_trait_receiver"] == 1


def test_a_trait_method_counts_as_inherited_too(store: GraphStore) -> None:
    _seed(
        store,
        [
            _node("Class", "\\App\\User"),
            _node("Method", "\\App\\User::run"),
            _node("Trait", "\\App\\Clocks"),
            _node("Method", "\\App\\Clocks::now"),
        ],
        [
            _edge("USES_TRAIT", "\\App\\User", "\\App\\Clocks", target_qname="\\App\\Clocks"),
            _edge("CALLS", "\\App\\User::run", "now"),
        ],
    )
    assert _causes(store)["inherited_or_trait_receiver"] == 1


def test_a_qualified_heuristic_target_is_late_binding_not_a_missing_type(
    store: GraphStore,
) -> None:
    """`static::m()` / `'C::m'` already know the name; no local type table changes them."""
    _seed(
        store,
        [_node("Class", "\\App\\Svc"), _node("Method", "\\App\\Svc::run")],
        [_edge("CALLS", "\\App\\Svc::run", "\\App\\Other::m")],
    )
    assert _causes(store) == {"late_bound_or_string_name": 1}


def test_a_string_local_new_is_recorded_as_a_win_not_a_gap(store: GraphStore) -> None:
    _seed(
        store,
        [_node("Class", "\\App\\Svc"), _node("Method", "\\App\\Svc::run")],
        [_edge("NEW", "\\App\\Svc::run", "\\App\\Made")],
    )
    assert _causes(store) == {"new_from_string_local": 1}


def test_only_heuristic_edges_are_classified(store: GraphStore) -> None:
    _seed(
        store,
        [_node("Class", "\\App\\Svc"), _node("Method", "\\App\\Svc::run")],
        [
            _edge("CALLS", "\\App\\Svc::run", "fetch", confidence_tier="RESOLVED"),
            _edge("CALLS", "\\App\\Svc::run", "other", confidence_tier="DYNAMIC"),
            _edge("CALLS", "\\App\\Svc::run", "third"),
        ],
    )
    assert _causes(store) == {"unknown_receiver": 1}


def test_an_emission_site_the_taxonomy_does_not_know_fails_the_check(store: GraphStore) -> None:
    """The proving test: an unexplained cause must fail, not be absorbed by the nearest bucket."""
    _seed(
        store,
        [_node("Class", "\\App\\Svc"), _node("Method", "\\App\\Svc::run")],
        [_edge("REFERENCES", "\\App\\Svc::run", "\\App\\Thing")],
    )
    labelled = _r.classify(store, _r.heuristic_edges(store))
    assert [cause for cause, _ in labelled] == ["other_references"]
    problems = _r.check(labelled, len(labelled))
    assert problems and "other_references" in problems[0]


def test_the_check_passes_when_every_cause_is_explained(store: GraphStore) -> None:
    _seed(
        store,
        [_node("Class", "\\App\\Svc"), _node("Method", "\\App\\Svc::run")],
        [_edge("CALLS", "\\App\\Svc::run", "fetch")],
    )
    labelled = _r.classify(store, _r.heuristic_edges(store))
    assert _r.check(labelled, len(labelled)) == []


def test_the_ceiling_excludes_a_settleable_cause_whose_target_has_no_node(
    store: GraphStore,
) -> None:
    """Knowing the receiver's type cannot promote an edge that has nothing to link to."""
    _seed(
        store,
        [_node("Class", "\\App\\Svc"), _node("Method", "\\App\\Svc::run")],
        [
            _edge("CALLS", "\\App\\Svc::run", "fetch"),
            _edge("CALLS", "\\App\\Svc::run", "kept", target_qname="\\App\\Svc::run", line=9),
        ],
    )
    report = _r.format_report(store, _r.classify(store, _r.heuristic_edges(store)))
    assert "cause is local type information: 2/2" in report
    assert "target is INDEXED: 1/2" in report


def test_every_named_cause_says_whether_the_spec_can_settle_it() -> None:
    """The report's whole purpose is that number, so no cause may ship without the verdict."""
    for cause, (settleable, why) in _r.CAUSES.items():
        assert isinstance(settleable, bool), cause
        assert len(why) > 40, f"{cause} has no explanation a reader could check"
