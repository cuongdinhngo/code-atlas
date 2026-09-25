"""Task 144 — mermaid classDiagram from resolved type rows; return types via ``extra['type']``."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from code_atlas.contract import CONTRACT_VERSION
from code_atlas.onboarding.class_diagram import (
    NOTE_ASSOCIATIONS_CAPPED,
    NOTE_NO_ASSOCIATIONS,
    Association,
    ClassBox,
    Inheritance,
    Member,
    render_class_diagram,
    validate_mermaid_class_diagram,
)
from code_atlas.store import GraphStore
from code_atlas.tools import class_diagram as tool
from tests.test_nav_tools import db_config, edge, node, seed_file

REPO = Path(__file__).resolve().parent.parent

_GOLDEN = (
    "classDiagram\n"
    'class N0["\\App\\Child"] {\n'
    "  +run(\\App\\Other $x) void\n"
    "  +\\App\\Other $dep\n"
    "}\n"
    'class N1["\\App\\Parent"]\n'
    'class N2["\\App\\Other"]\n'
    "N1 <|-- N0\n"
    "N0 --> N2 : $dep\n"
    "N0 --> N2 : run\n"
)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[GraphStore]:
    with GraphStore(tmp_path / "graph.db") as opened:
        yield opened


def test_ac1_fixture_class_renders_byte_identical_body() -> None:
    boxes = (
        ClassBox(
            qname="\\App\\Child",
            name="Child",
            kind="Class",
            test=False,
            members=(
                Member(
                    name="run",
                    kind="Method",
                    visibility="+",
                    params=(("$x", "\\App\\Other"),),
                    return_type="void",
                ),
                Member(
                    name="$dep",
                    kind="Property",
                    visibility="+",
                    declared_type="\\App\\Other",
                ),
            ),
            member_total=2,
        ),
        ClassBox(
            qname="\\App\\Parent",
            name="Parent",
            kind="Class",
            test=False,
            members=(),
            member_total=0,
        ),
        ClassBox(
            qname="\\App\\Other",
            name="Other",
            kind="Class",
            test=False,
            members=(),
            member_total=0,
        ),
    )
    inheritance = (Inheritance("\\App\\Child", "\\App\\Parent", "EXTENDS"),)
    associations = (
        Association("\\App\\Child", "\\App\\Other", "$dep"),
        Association("\\App\\Child", "\\App\\Other", "run"),
    )
    mermaid = render_class_diagram(boxes, inheritance, associations, member_cap=50)
    assert mermaid == _GOLDEN
    validate_mermaid_class_diagram(mermaid)


def test_ac2_inferred_calls_do_not_create_associations(
    tmp_path: Path, store: GraphStore
) -> None:
    """CALLS is 137's tier — drawing it as an association would claim a resolved fact."""
    path = "src/pair.php"
    seed_file(
        store,
        path,
        [
            node("Class", "Caller", "\\App\\Caller", path),
            node("Class", "Callee", "\\App\\Callee", path),
            {
                **node("Method", "ping", "\\App\\Caller::ping", path),
                "modifiers": ["public"],
                "params": [],
            },
        ],
        [
            edge(
                "CONTAINS",
                "\\App\\Caller",
                "\\App\\Caller::ping",
                path,
                target_qname="\\App\\Caller::ping",
            ),
            edge(
                "CALLS",
                "\\App\\Caller::ping",
                "\\App\\Callee",
                path,
                target_qname="\\App\\Callee",
            ),
        ],
        root=tmp_path,
    )
    result = tool.create(db_config(tmp_path))(path=path, detail_level="standard")
    assert result["reason"] == "ok"
    markdown = str(result["markdown"])
    assert "-->" not in markdown
    assert NOTE_NO_ASSOCIATIONS in markdown
    assert result["association_note"] == NOTE_NO_ASSOCIATIONS


def test_ac3_no_declared_types_says_inheritance_only() -> None:
    boxes = (
        ClassBox("\\A", "A", "Class", False, (), 0),
        ClassBox("\\B", "B", "Class", False, (), 0),
    )
    inheritance = (Inheritance("\\A", "\\B", "EXTENDS"),)
    mermaid = render_class_diagram(boxes, inheritance, (), member_cap=50)
    assert "%% " + NOTE_NO_ASSOCIATIONS in mermaid
    assert "-->" not in mermaid
    validate_mermaid_class_diagram(mermaid)


def test_ac4_return_types_in_signature_and_contract_is_seven() -> None:
    assert CONTRACT_VERSION == 12
    member = Member(
        name="run",
        kind="Method",
        visibility="+",
        params=(("$n", "int"),),
        return_type="void",
    )
    boxes = (ClassBox("\\A", "A", "Class", False, (member,), 1),)
    mermaid = render_class_diagram(boxes, (), (), member_cap=50)
    assert "+run(int $n) void" in mermaid


def test_ac5_capped_members_say_so() -> None:
    members = (
        Member("a", "Method", "+", (), None, None),
        Member("b", "Method", "+", (), None, None),
    )
    boxes = (ClassBox("\\A", "A", "Class", False, members[:1], 2),)
    mermaid = render_class_diagram(boxes, (), (), member_cap=1)
    assert "%% members capped" in mermaid
    assert "+a()" in mermaid
    assert "+b()" not in mermaid


def test_ac6_emitter_names_no_repo_framework_or_language() -> None:
    """R2.2 for the projection — language names live in the adapter handshake, not here."""
    banned = (
        "php",
        "typescript",
        "javascript",
        "csharp",
        "dotnet",
        "magento",
        "symfony",
        "laravel",
    )
    for relative in (
        "code_atlas/onboarding/class_diagram.py",
        "code_atlas/tools/class_diagram.py",
    ):
        text = (REPO / relative).read_text(encoding="utf-8").lower()
        for word in banned:
            assert word not in text, f"{relative} names {word!r}"


def test_tool_qname_walks_ancestry(tmp_path: Path, store: GraphStore) -> None:
    child_path = "src/child.php"
    parent_path = "src/parent.php"
    seed_file(
        store,
        child_path,
        [node("Class", "Child", "\\App\\Child", child_path)],
        [
            edge(
                "EXTENDS",
                "\\App\\Child",
                "\\App\\Parent",
                child_path,
                target_qname="\\App\\Parent",
            ),
        ],
        root=tmp_path,
    )
    seed_file(
        store,
        parent_path,
        [node("Class", "Parent", "\\App\\Parent", parent_path)],
        [],
        root=tmp_path,
    )
    result = tool.create(db_config(tmp_path))(qname="\\App\\Child", detail_level="standard")
    assert result["total_count"] == 2
    assert {row["qname"] for row in result["results"]} == {"\\App\\Child", "\\App\\Parent"}
    assert "<|--" in str(result["markdown"])


def test_tool_minimal_omits_markdown(tmp_path: Path, store: GraphStore) -> None:
    path = "src/one.php"
    seed_file(
        store,
        path,
        [node("Class", "Solo", "\\App\\Solo", path)],
        [],
        root=tmp_path,
    )
    result = tool.create(db_config(tmp_path))(path=path, detail_level="minimal")
    assert "markdown" not in result
    assert result["total_count"] == 1


def test_the_cap_never_turns_a_declared_type_into_no_associations(
    tmp_path: Path, store: GraphStore
) -> None:
    """The cap hides a member; it must not make the diagram claim the type has no dependency."""
    path = "src/cap.php"
    nodes = [
        node("Class", "Holder", "\\App\\Holder", path),
        node("Class", "Dep", "\\App\\Dep", path),
        {
            **node("Property", "$aaa", "\\App\\Holder::$aaa", path),
            "modifiers": ["public"],
        },
        {
            **node("Property", "$zzz", "\\App\\Holder::$zzz", path),
            "modifiers": ["public"],
            "extra": {"type": "\\App\\Dep"},
        },
    ]
    seed_file(
        store,
        path,
        nodes,
        [
            edge("CONTAINS", "\\App\\Holder", "a", path, target_qname="\\App\\Holder::$aaa"),
            edge("CONTAINS", "\\App\\Holder", "z", path, target_qname="\\App\\Holder::$zzz"),
        ],
        root=tmp_path,
    )
    capped = tool.create(db_config(tmp_path))(path=path, limit=1)
    assert "association_note" not in capped
    assert capped["associations_hidden_by_cap"] == 1
    assert NOTE_ASSOCIATIONS_CAPPED in str(capped["markdown"])
    assert NOTE_NO_ASSOCIATIONS not in str(capped["markdown"])
    uncapped = tool.create(db_config(tmp_path))(path=path, limit=10)
    assert "associations_hidden_by_cap" not in uncapped
    assert "-->" in str(uncapped["markdown"])


def test_a_qname_declared_twice_is_one_box_and_says_so(
    tmp_path: Path, store: GraphStore
) -> None:
    """Two boxes would share a positional mermaid id and double total_count (070/078)."""
    for path in ("src/one.php", "src/two.php"):
        seed_file(
            store, path, [node("Class", "Dup", "\\App\\Dup", path)], [], root=tmp_path
        )
    result = tool.create(db_config(tmp_path))(qname="\\App\\Dup")
    assert result["total_count"] == 1
    ids = [line for line in str(result["markdown"]).splitlines() if line.startswith("class ")]
    assert ids == ['class N0["\\App\\Dup"]']
    sites = result["ambiguous_definitions"]
    assert isinstance(sites, list) and len(sites) == 2


def test_a_newline_in_a_member_name_cannot_break_the_diagram() -> None:
    """A name is adapter data, not vocabulary — the emitter validates what it returns."""
    member = Member(name="run\nclassDiagram", kind="Method", visibility="+")
    boxes = (ClassBox("\\A\nB", "A", "Class", False, (member,), 1),)
    mermaid = render_class_diagram(boxes, (), (), member_cap=50)
    validate_mermaid_class_diagram(mermaid)
    assert "run classDiagram" in mermaid
