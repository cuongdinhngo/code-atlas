"""255 — find_references honesty is keyed to EDGE_KINDS, not the PHP REFERENCES/IMPORTS pair.

A Table with unlinked WRITES must not return bare no_matches, and the payload must name the
unmeasured relation kinds. The matrix fails on the pre-fix shape at Table × WRITES (R6.5).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from code_atlas.contract import EDGE_KINDS, NODE_KINDS
from code_atlas.store import GraphStore
from code_atlas.tools import find_references
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_OK,
    REASON_RELATIONSHIP_NOT_MODELLED,
)
from tests.test_nav_tools import (  # noqa: F401 — store fixture
    db_config,
    edge,
    node,
    store,
)

# Languages present in the planted fixture index for the AC4 matrix (ticket scope).
_FIXTURE_LANGUAGES = ("sql", "php")


def _seed(
    graph: GraphStore,
    root: Path,
    path: str,
    nodes: list[dict],
    edges: list[dict],
    *,
    language: str,
) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    body = b"# planted\n"
    target.write_bytes(body)
    graph.upsert_file(path, hashlib.sha256(body).hexdigest(), language)
    graph.replace_file_rows(path, nodes, edges)


def _plant_subject_with_unlinked(
    graph: GraphStore,
    root: Path,
    *,
    kind: str,
    name: str,
    qname: str,
    path: str,
    edge_kind: str,
    language: str,
) -> None:
    _seed(
        graph,
        root,
        path,
        [node(kind, name, qname, path)],
        [
            edge(
                edge_kind,
                "writer.site",
                qname,
                path,
                target_qname="",
                tier="DYNAMIC",
            )
        ],
        language=language,
    )


def test_table_with_unlinked_writes_is_not_bare_no_matches(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC1 proving: UserNotes shape — Table + unlinked WRITES; payload names WRITES."""
    _plant_subject_with_unlinked(
        store,
        tmp_path,
        kind="Table",
        name="UserNotes",
        qname="dbo.UserNotes",
        path="schema/staff.sql",
        edge_kind="WRITES",
        language="sql",
    )
    payload = find_references.create(db_config(tmp_path))(
        "dbo.UserNotes", detail_level="minimal"
    )
    assert payload["results"] == []
    assert payload["total_count"] == 0
    assert payload["reason"] != REASON_NO_MATCHES
    assert payload["reason"] == REASON_RELATIONSHIP_NOT_MODELLED
    assert payload["unlinked_edge_kinds"] == ["WRITES"]
    assert "try_instead_hint" in payload


def test_function_honest_zero_path_unchanged(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC2: Function with no unlinked evidence stays a measured zero."""
    _seed(
        store,
        tmp_path,
        "p.sql",
        [node("Function", "only_me", "dbo.only_me", "p.sql")],
        [],
        language="sql",
    )
    payload = find_references.create(db_config(tmp_path))("dbo.only_me", detail_level="minimal")
    assert payload["reason"] == REASON_NO_MATCHES
    assert payload["results"] == []
    assert "unlinked_edge_kinds" not in payload


def test_untouched_table_stays_distinguishable_from_unlinked_writes(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC3: a Table with no edges at all is still no_matches — distinct from AC1."""
    _seed(
        store,
        tmp_path,
        "schema/orphan.sql",
        [node("Table", "Orphan", "dbo.Orphan", "schema/orphan.sql")],
        [],
        language="sql",
    )
    payload = find_references.create(db_config(tmp_path))("dbo.Orphan", detail_level="minimal")
    assert payload["reason"] == REASON_NO_MATCHES
    assert "unlinked_edge_kinds" not in payload


@pytest.mark.parametrize("subject_kind", list(NODE_KINDS))
@pytest.mark.parametrize("edge_kind", list(EDGE_KINDS))
@pytest.mark.parametrize("language", list(_FIXTURE_LANGUAGES))
def test_matrix_subject_relation_language_not_bare_zeros(
    tmp_path: Path,
    store,  # noqa: F811
    subject_kind: str,
    edge_kind: str,
    language: str,
) -> None:
    """AC4: subject kind × inbound relation × fixture language — Table×WRITES fails pre-fix."""
    qname = f"{language}.{subject_kind}.{edge_kind}"
    path = f"{language}/{subject_kind}_{edge_kind}.src"
    _plant_subject_with_unlinked(
        store,
        tmp_path,
        kind=subject_kind,
        name=f"{subject_kind}_{edge_kind}",
        qname=qname,
        path=path,
        edge_kind=edge_kind,
        language=language,
    )
    payload = find_references.create(db_config(tmp_path))(qname, detail_level="minimal")
    assert payload["reason"] != REASON_NO_MATCHES, (
        f"{subject_kind} × {edge_kind} × {language} must not be bare no_matches (255 matrix)"
    )
    assert edge_kind in payload.get("unlinked_edge_kinds", [])


def test_hits_payload_unchanged_when_linked(
    tmp_path: Path,
    store,  # noqa: F811
) -> None:
    """AC5: a linked inbound edge still answers ok with results."""
    path = "a.php"
    _seed(
        store,
        tmp_path,
        path,
        [
            node("Class", "Target", "\\App\\Target", path),
            node("Class", "Src", "\\App\\Src", path),
        ],
        [
            edge(
                "REFERENCES",
                "\\App\\Src",
                "\\App\\Target",
                path,
                target_qname="\\App\\Target",
                tier="RESOLVED",
            )
        ],
        language="php",
    )
    payload = find_references.create(db_config(tmp_path))(
        "\\App\\Target", detail_level="minimal"
    )
    assert payload["reason"] == REASON_OK
    assert payload["total_count"] >= 1
    assert payload["results"]
    assert "unlinked_edge_kinds" not in payload
