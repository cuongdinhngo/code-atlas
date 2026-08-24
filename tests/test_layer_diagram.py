"""Task 143 — mermaid layer flowchart from the matrix, no Node, no CDN."""

from __future__ import annotations

from code_atlas.onboarding.layer_diagram import (
    HEURISTIC,
    RESOLVED,
    DiagramEdge,
    diagram_edges,
    module_edge_tiers,
    render_layer_flowchart,
    validate_mermaid_flowchart,
)
from code_atlas.onboarding.layers import LayerAssignment, ModuleLayer

_LAYERS = ("HTTP / Entry", "Services", "Domain / Data")
_GOLDEN = (
    "flowchart LR\n"
    'N0["HTTP / Entry"]\n'
    'N1["Services"]\n'
    'N2["Domain / Data"]\n'
    'N0 -->|"3"| N1\n'
    'N1 -.->|"2"| N2\n'
)


def _assignment() -> LayerAssignment:
    modules = (
        ModuleLayer("app/http/A.aa", "HTTP / Entry", 0),
        ModuleLayer("app/services/B.aa", "Services", 1),
        ModuleLayer("app/domain/C.aa", "Domain / Data", 2),
    )
    return LayerAssignment(_LAYERS, modules, "dominant-subtree")


def test_ac1_fixture_matrix_is_byte_identical() -> None:
    edges = (
        DiagramEdge("HTTP / Entry", "Services", 3, False),
        DiagramEdge("Services", "Domain / Data", 2, True),
    )
    diagram = render_layer_flowchart(_LAYERS, edges, node_cap=50)
    assert diagram.mermaid == _GOLDEN
    validate_mermaid_flowchart(diagram.mermaid)


def test_ac2_arrow_labels_sum_to_matrix_cells() -> None:
    edges = (
        DiagramEdge("HTTP / Entry", "Services", 3, False),
        DiagramEdge("Services", "Domain / Data", 2, True),
    )
    diagram = render_layer_flowchart(_LAYERS, edges, node_cap=50)
    labels = [
        int(line.split('|"', 1)[1].split('"|', 1)[0])
        for line in diagram.mermaid.splitlines()
        if '|"' in line
    ]
    assert sum(labels) == sum(edge.count for edge in edges)


def test_ac3_heuristic_only_arrow_is_dashed() -> None:
    nodes = [
        ("\\A", "app/http/A.aa"),
        ("\\B", "app/services/B.aa"),
        ("\\C", "app/domain/C.aa"),
    ]
    edges = [
        ("\\A", "\\B", RESOLVED),
        ("\\B", "\\C", HEURISTIC),
        ("\\B", "\\C", HEURISTIC),
    ]
    drawn, omitted = diagram_edges(module_edge_tiers(nodes, edges), _assignment())
    assert omitted == 0
    by_pair = {(edge.source, edge.target): edge for edge in drawn}
    assert by_pair[("HTTP / Entry", "Services")].heuristic_only is False
    assert by_pair[("Services", "Domain / Data")].heuristic_only is True
    mermaid = render_layer_flowchart(_LAYERS, drawn, node_cap=50).mermaid
    assert "-.->" in mermaid
    assert 'N1 -.->|"1"| N2' in mermaid


def test_ac4_capped_diagram_says_so() -> None:
    edges = (DiagramEdge("HTTP / Entry", "Services", 1, False),)
    diagram = render_layer_flowchart(_LAYERS, edges, node_cap=1)
    assert diagram.truncated is True
    assert diagram.shown_layers == 1
    assert diagram.total_layers == 3
    assert "N1" not in diagram.mermaid
    text = (
        f"- layers: {diagram.shown_layers} shown of {diagram.total_layers}"
        + ("; the graph is capped" if diagram.truncated else "")
    )
    assert "1 shown of 3" in text
    assert "capped" in text
    # The cap did not only hide a node: HTTP / Entry -> Services lost its arrow. A layer count
    # alone lets a reader take the diagram for the whole matrix (108/124).
    assert diagram.omitted_capped == 1


def test_ac5_syntax_subset_rejects_unknown_lines() -> None:
    validate_mermaid_flowchart(_GOLDEN)
    try:
        validate_mermaid_flowchart("flowchart LR\nclick N0 callback")
    except ValueError as err:
        assert "unrecognised" in str(err)
    else:
        raise AssertionError("expected ValueError")


def test_the_overview_says_how_many_arrows_the_cap_cost() -> None:
    """A crossing still listed in the table but absent from the diagram must be counted."""
    from code_atlas.onboarding.artifact import LayerRow, OnboardingArtifact, render_overview

    artifact = OnboardingArtifact(
        method="dominant-subtree",
        truncated=False,
        summary={"layers": 3, "modules": 3, "symbols": 3, "cross_layer_edges": 1},
        layers=tuple(
            LayerRow(
                layer=name,
                rank=index,
                modules=1,
                fan_in=0,
                fan_out=0,
                entry_points=0,
                description="d",
            )
            for index, name in enumerate(_LAYERS)
        ),
        crossings=(("HTTP / Entry", "Services", 1),),
        stops=(),
        pages=(),
        diagram_edges=(DiagramEdge("HTTP / Entry", "Services", 1, False),),
    )
    md = render_overview(artifact, node_cap=1)
    assert "1 shown of 3" in md
    assert "crossings with no arrow because their layer is outside the cap: 1" in md
    # The crossing is still listed below the diagram that has no arrow for it.
    assert "`HTTP / Entry` \u2192 `Services` (1)" in md
    assert 'N0 -->' not in md


def test_a_newline_in_a_layer_name_cannot_break_the_diagram() -> None:
    """A dominant-subtree layer name is a directory name, not a vetted vocabulary word."""
    diagram = render_layer_flowchart(("a\nb",), (), node_cap=5)
    validate_mermaid_flowchart(diagram.mermaid)
    assert diagram.mermaid == 'flowchart LR\nN0["a b"]\n'
