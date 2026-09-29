"""264 — empty-answer honesty is one derived mapping + one shared predicate.

The mapping is NODE_KINDS → UNLINKED_EVIDENCE_KINDS (derived, no contract_version bump).
A nav tool that reaches bare no_matches without consulting the shared predicate fails here.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.contract import (
    CONTRACT_VERSION,
    INBOUND_KINDS_BY_SUBJECT,
    NODE_KINDS,
    UNLINKED_EVIDENCE_KINDS,
    inbound_kinds_for,
)
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_implementations, find_references
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_RELATIONSHIP_NOT_MODELLED,
    apply_empty_inbound_honesty,
    unmeasured_inbound_for_subject,
)
from tests.test_nav_tools import (  # noqa: F401 — store fixture
    db_config,
    edge,
    node,
    store,
)

_TOOLS = Path(__file__).resolve().parents[1] / "code_atlas" / "tools"
# Inbound nav tools that can emit no_matches for an indexed subject (264 AC).
_INBOUND_NAV_MODULES = (
    "find_references.py",
    "find_callers.py",
    "find_implementations.py",
    "include_graph.py",
)
_SHARED_PREDICATE = "apply_empty_inbound_honesty"


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


def test_contract_version_unchanged() -> None:
    """AC: derive-do-not-extend — vocabulary bump is forbidden for this ticket."""
    assert CONTRACT_VERSION == 13


def test_inbound_mapping_is_derived_from_node_and_evidence_kinds() -> None:
    """Mapping keys are every NODE_KIND; values are UNLINKED_EVIDENCE_KINDS (R6.7)."""
    assert set(INBOUND_KINDS_BY_SUBJECT) == set(NODE_KINDS)
    for kind in NODE_KINDS:
        assert inbound_kinds_for(kind) == UNLINKED_EVIDENCE_KINDS
        assert INBOUND_KINDS_BY_SUBJECT[kind] == UNLINKED_EVIDENCE_KINDS
    assert inbound_kinds_for("NotAKind") == ()


@pytest.mark.parametrize("subject_kind", list(NODE_KINDS))
@pytest.mark.parametrize("edge_kind", list(UNLINKED_EVIDENCE_KINDS))
def test_matrix_subject_times_inbound_kind_not_bare_no_matches(
    tmp_path: Path,
    store,  # noqa: F811
    subject_kind: str,
    edge_kind: str,
) -> None:
    """AC matrix: every (subject kind × inbound kind) the contract holds."""
    qname = f"m.{subject_kind}.{edge_kind}"
    path = f"m/{subject_kind}_{edge_kind}.src"
    _seed(
        store,
        tmp_path,
        path,
        [node(subject_kind, f"{subject_kind}_{edge_kind}", qname, path)],
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
        language="php",
    )
    payload = find_references.create(db_config(tmp_path))(qname, detail_level="minimal")
    assert payload["reason"] != REASON_NO_MATCHES, (
        f"{subject_kind} × {edge_kind} must not be bare no_matches"
    )
    assert edge_kind in payload.get("unlinked_edge_kinds", [])


def test_255_table_writes_fixture_still_passes(tmp_path: Path, store) -> None:  # noqa: F811
    """255 UserNotes shape unchanged under the shared predicate."""
    path = "schema/staff.sql"
    _seed(
        store,
        tmp_path,
        path,
        [node("Table", "UserNotes", "dbo.UserNotes", path)],
        [
            edge(
                "WRITES",
                "writer.site",
                "dbo.UserNotes",
                path,
                target_qname="",
                tier="DYNAMIC",
            )
        ],
        language="sql",
    )
    payload = find_references.create(db_config(tmp_path))(
        "dbo.UserNotes", detail_level="minimal"
    )
    assert payload["reason"] == REASON_RELATIONSHIP_NOT_MODELLED
    assert payload["unlinked_edge_kinds"] == ["WRITES"]


def test_php_class_references_fixture_still_passes(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """255/065 PHP class + unlinked REFERENCES still upgrades off no_matches."""
    path = "a.php"
    _seed(
        store,
        tmp_path,
        path,
        [node("Class", "Target", "\\App\\Target", path)],
        [
            edge(
                "REFERENCES",
                "\\App\\Src",
                "\\App\\Target",
                path,
                target_qname="",
                tier="HEURISTIC",
            )
        ],
        language="php",
    )
    payload = find_references.create(db_config(tmp_path))(
        "\\App\\Target", detail_level="minimal"
    )
    assert payload["reason"] != REASON_NO_MATCHES


def test_find_implementations_uses_shared_predicate(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """A Class with unlinked WRITES is not bare no_matches on find_implementations."""
    path = "c.php"
    _seed(
        store,
        tmp_path,
        path,
        [node("Class", "Iface", "\\App\\Iface", path)],
        [
            edge(
                "WRITES",
                "writer.site",
                "\\App\\Iface",
                path,
                target_qname="",
                tier="DYNAMIC",
            )
        ],
        language="php",
    )
    payload = find_implementations.create(db_config(tmp_path))(
        "\\App\\Iface", detail_level="minimal"
    )
    assert payload["reason"] == REASON_RELATIONSHIP_NOT_MODELLED
    assert "WRITES" in payload.get("unlinked_edge_kinds", [])


def test_shared_predicate_is_the_only_widened_evidence_reader() -> None:
    """Bypass guard: every inbound nav tool must call apply_empty_inbound_honesty."""
    for name in _INBOUND_NAV_MODULES:
        source = (_TOOLS / name).read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        } | {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        }
        assert _SHARED_PREDICATE in names, (
            f"{name} reaches no_matches without calling {_SHARED_PREDICATE}"
        )
        # No tool may re-import the evidence set for a parallel widened arm.
        assert "UNLINKED_EVIDENCE_KINDS" not in names, (
            f"{name} must not re-list UNLINKED_EVIDENCE_KINDS — use the shared predicate"
        )


def test_apply_empty_inbound_honesty_upgrades_only_no_matches(
    tmp_path: Path, store  # noqa: F811
) -> None:
    path = "t.sql"
    _seed(
        store,
        tmp_path,
        path,
        [node("Table", "T", "dbo.T", path)],
        [
            edge(
                "WRITES",
                "w",
                "dbo.T",
                path,
                target_qname="",
                tier="DYNAMIC",
            )
        ],
        language="sql",
    )
    reason, kinds = apply_empty_inbound_honesty(
        REASON_NO_MATCHES,
        store,
        subject_kind="Table",
        raws=("dbo.T",),
    )
    assert reason == REASON_RELATIONSHIP_NOT_MODELLED
    assert kinds == ["WRITES"]
    assert unmeasured_inbound_for_subject(
        store, subject_kind="Table", raws=("dbo.T",)
    ) == ["WRITES"]


def test_inbound_mapping_export_stays_opt_in_for_tier2_sweep() -> None:
    """INBOUND_KINDS_BY_SUBJECT keys include Table/Column by design — join the opt-in set."""
    assert "Table" in INBOUND_KINDS_BY_SUBJECT
    assert "Column" in INBOUND_KINDS_BY_SUBJECT
    # Values inherit WRITES via UNLINKED_EVIDENCE_KINDS, not via a second hand list.
    assert "WRITES" in INBOUND_KINDS_BY_SUBJECT["Table"]
    assert contract.INBOUND_KINDS_BY_SUBJECT is INBOUND_KINDS_BY_SUBJECT


def test_find_callers_names_the_unmeasured_kinds(
    tmp_path: Path, store  # noqa: F811
) -> None:
    """The shared predicate sets find_callers' reason, so it must name the kinds too."""
    path = "d.php"
    _seed(
        store,
        tmp_path,
        path,
        [node("Class", "Sink", "\\App\\Sink", path)],
        [
            edge(
                "WRITES",
                "writer.site",
                "\\App\\Sink",
                path,
                target_qname="",
                tier="DYNAMIC",
            )
        ],
        language="php",
    )
    payload = find_callers.create(db_config(tmp_path))(
        "\\App\\Sink", detail_level="minimal"
    )
    assert payload["reason"] == REASON_RELATIONSHIP_NOT_MODELLED
    assert payload["unlinked_edge_kinds"] == ["WRITES"]
