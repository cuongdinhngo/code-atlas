"""Task 252: class-level find_references unions member CALLS/NEW in one call."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references
from code_atlas.tools.nav_result import (
    REASON_OK,
    REASON_RELATIONSHIP_NOT_MODELLED,
    REASON_VIA_MEMBERS,
    TRY_INSTEAD_HINT_METHOD_QNAME,
    TRY_INSTEAD_SEARCH_SYMBOL,
)
from tests.test_nav_tools import db_config, edge, node, seed_file


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def _plant_class_with_unlinked_ref(
    tmp_path: Path,
    store: GraphStore,
    *,
    members: list[tuple[str, str]],
    callers: list[tuple[str, str, str]],
    subject_kind: str = "Class",
    subject_qname: str = "\\App\\PhotoResolver",
) -> None:
    subject_nodes = [
        node(subject_kind, "PhotoResolver", subject_qname, "cls.php"),
        *[node("Method", name, qn, "cls.php") for name, qn in members],
    ]
    contains = [
        edge("CONTAINS", subject_qname, qn, "cls.php", target_qname=qn)
        for _name, qn in members
    ]
    seed_file(store, "cls.php", subject_nodes, contains, root=tmp_path)
    seed_file(
        store,
        "mention.php",
        [node("Class", "Mention", "\\App\\Mention", "mention.php")],
        [
            edge(
                "REFERENCES",
                "\\App\\Mention",
                subject_qname,
                "mention.php",
            )
        ],
        root=tmp_path,
    )
    if not callers:
        return
    caller_nodes = [
        node("Function", src.rsplit("\\", 1)[-1], src, "call.php") for src, _tgt, _ in callers
    ]
    # Unique by qname — two calls from one function share a node.
    uniq: dict[str, dict[str, object]] = {str(n["qualified_name"]): n for n in caller_nodes}
    seed_file(
        store,
        "call.php",
        list(uniq.values()),
        [
            edge("CALLS", src, tgt, "call.php", target_qname=tgt, line=line)
            for src, tgt, line in callers
        ],
        root=tmp_path,
    )


def test_class_with_called_members_returns_via_members_union(
    tmp_path: Path, store: GraphStore
) -> None:
    """Proving guard: on main this is the n+1 route, not a via_members page."""
    _plant_class_with_unlinked_ref(
        tmp_path,
        store,
        members=[
            ("resolve", "\\App\\PhotoResolver::resolve"),
            ("storedValue", "\\App\\PhotoResolver::storedValue"),
        ],
        callers=[
            ("\\useResolve", "\\App\\PhotoResolver::resolve", 4),
            ("\\useStored", "\\App\\PhotoResolver::storedValue", 8),
        ],
    )
    payload = find_references.create(db_config(tmp_path))(
        "\\App\\PhotoResolver", detail_level="minimal"
    )
    assert payload["reason"] == REASON_VIA_MEMBERS
    assert payload["reason"] != REASON_OK
    assert payload["total_count"] == 2
    assert "try_instead" not in payload
    via = {hit["via_member"]: hit["qname"] for hit in payload["results"]}
    assert via == {
        "\\App\\PhotoResolver::resolve": "\\useResolve",
        "\\App\\PhotoResolver::storedValue": "\\useStored",
    }
    assert all(hit["confidence_tier"] == "RESOLVED" for hit in payload["results"])


def test_class_members_with_no_callers_is_via_members_zero(
    tmp_path: Path, store: GraphStore
) -> None:
    _plant_class_with_unlinked_ref(
        tmp_path,
        store,
        members=[("resolve", "\\App\\PhotoResolver::resolve")],
        callers=[],
    )
    payload = find_references.create(db_config(tmp_path))(
        "\\App\\PhotoResolver", detail_level="minimal"
    )
    assert payload["reason"] == REASON_VIA_MEMBERS
    assert payload["results"] == []
    assert payload["total_count"] == 0
    assert "try_instead" not in payload


def test_class_without_contains_keeps_065_route(tmp_path: Path, store: GraphStore) -> None:
    _plant_class_with_unlinked_ref(
        tmp_path, store, members=[], callers=[]
    )
    payload = find_references.create(db_config(tmp_path))(
        "\\App\\PhotoResolver", detail_level="minimal"
    )
    assert payload["reason"] == REASON_RELATIONSHIP_NOT_MODELLED
    assert payload["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_METHOD_QNAME


def test_interface_subject_keeps_065_route(tmp_path: Path, store: GraphStore) -> None:
    _plant_class_with_unlinked_ref(
        tmp_path,
        store,
        members=[("resolve", "\\App\\PhotoResolver::resolve")],
        callers=[("\\useResolve", "\\App\\PhotoResolver::resolve", 3)],
        subject_kind="Interface",
    )
    payload = find_references.create(db_config(tmp_path))(
        "\\App\\PhotoResolver", detail_level="minimal"
    )
    assert payload["reason"] == REASON_RELATIONSHIP_NOT_MODELLED
    assert payload["try_instead"] == TRY_INSTEAD_SEARCH_SYMBOL


def test_via_members_pages_like_other_nav_answers(tmp_path: Path, store: GraphStore) -> None:
    _plant_class_with_unlinked_ref(
        tmp_path,
        store,
        members=[
            ("a", "\\App\\PhotoResolver::a"),
            ("b", "\\App\\PhotoResolver::b"),
        ],
        callers=[
            ("\\c1", "\\App\\PhotoResolver::a", 1),
            ("\\c2", "\\App\\PhotoResolver::a", 2),
            ("\\c3", "\\App\\PhotoResolver::b", 3),
        ],
    )
    refs = find_references.create(db_config(tmp_path))
    page = refs("\\App\\PhotoResolver", detail_level="minimal", limit=2, offset=0)
    assert page["reason"] == REASON_VIA_MEMBERS
    assert page["total_count"] == 3
    assert page["truncated"] is True
    assert len(page["results"]) == 2
    rest = refs("\\App\\PhotoResolver", detail_level="minimal", limit=2, offset=2)
    assert len(rest["results"]) == 1
    assert rest["truncated"] is False


def test_method_subject_is_unchanged_ok(tmp_path: Path, store: GraphStore) -> None:
    _plant_class_with_unlinked_ref(
        tmp_path,
        store,
        members=[("resolve", "\\App\\PhotoResolver::resolve")],
        callers=[("\\useResolve", "\\App\\PhotoResolver::resolve", 4)],
    )
    payload = find_references.create(db_config(tmp_path))(
        "\\App\\PhotoResolver::resolve", detail_level="minimal"
    )
    assert payload["reason"] == REASON_OK
    assert any(hit["kind"] == "CALLS" for hit in payload["results"])
    callers = find_callers.create(db_config(tmp_path))(
        "\\App\\PhotoResolver::resolve", detail_level="minimal"
    )
    assert callers["total_count"] == 1
