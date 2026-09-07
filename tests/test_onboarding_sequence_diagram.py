"""225 — the sequence view over one capability trace.

A flowchart asserts *reaches*; a sequence asserts *this then this*. These tests hold that the
renderer only makes the stronger claim where the walk established call order, and discloses — a
dashed arrow plus a ``%%`` note — every hop it cannot order. Assertions read the RENDERED mermaid
(the consumer), not the ``FlowStep`` field (R6.9).
"""

import pytest

from code_atlas.onboarding.flows import FlowStep
from code_atlas.onboarding.sequence_diagram import (
    render_sequence_diagram,
    validate_mermaid_sequence_diagram,
)


def _step(qname, kind="CALLS", tier="RESOLVED", line=None):
    return FlowStep(qname, f"{qname}.php", "Services", kind, tier, line)


SEED = FlowStep("App\\Ctrl::act", "controllers/Ctrl.php", "HTTP / Entry", "", "RESOLVED", None)


def test_messages_appear_in_call_order_with_proven_arrows() -> None:
    """AC2 — a proven chain renders solid `->>` messages in step order, no order-unknown note."""
    steps = [
        SEED,
        _step("App\\Svc::load", kind="CALLS", line=10),
        _step("App\\Repo::save", kind="WRITES", line=20),
    ]
    text = render_sequence_diagram(steps)
    messages = [ln for ln in text.splitlines() if "->>" in ln]
    assert messages == ["P0 ->> P1: CALLS", "P1 ->> P2: WRITES"]
    assert "order unknown" not in text
    assert "-->>" not in text


def test_participants_use_the_container_not_the_qname() -> None:
    """R3 — a hop's container is the participant; a bare name participates as itself."""
    steps = [SEED, _step("App\\Svc::load", line=10), _step("globalHelper", line=20)]
    text = render_sequence_diagram(steps)
    assert 'participant P0 as "App\\Ctrl"' in text
    assert 'participant P1 as "App\\Svc"' in text
    assert 'participant P2 as "globalHelper"' in text


def test_unproven_hop_is_a_claim_not_an_arrow() -> None:
    """AC3 / R5 — a HEURISTIC/DYNAMIC hop is a dashed message plus a stated reason."""
    steps = [SEED, _step("App\\Dyn::maybe", kind="CALLS", tier="DYNAMIC", line=10)]
    text = render_sequence_diagram(steps)
    assert "P0 -->> P1: CALLS" in text
    assert "%% order unknown P0->P1: reached through a DYNAMIC edge" in text
    assert "P0 ->> P1" not in text


def test_same_line_pair_is_disclosed() -> None:
    """AC3 / R5 — a hop whose order is not established (line None) renders as a claim."""
    steps = [SEED, _step("App\\Svc::load", kind="CALLS", tier="RESOLVED", line=None)]
    text = render_sequence_diagram(steps)
    assert "P0 -->> P1: CALLS" in text
    assert "call line not established" in text


def test_truncated_trace_is_disclosed() -> None:
    """AC3 / R5 — a walk that ran out of budget says so on the diagram (R5.6)."""
    steps = [SEED, _step("App\\Svc::load", kind="CALLS", line=10)]
    text = render_sequence_diagram(steps, walk_truncated=True)
    assert "%% walk truncated" in text
    # The proven hop is still a solid arrow; truncation is a diagram-level caveat.
    assert "P0 ->> P1: CALLS" in text


def test_identical_input_yields_identical_diagram() -> None:
    """AC4 / R4.2 — the renderer is a pure deterministic function of its steps."""
    steps = [
        SEED,
        _step("App\\Svc::load", kind="CALLS", line=10),
        _step("App\\Repo::save", kind="WRITES", line=20),
    ]
    assert render_sequence_diagram(steps) == render_sequence_diagram(steps)


def test_a_traced_flow_renders_its_messages_in_call_order() -> None:
    """AC2 end-to-end — build_flows over a line-ordered fixture, then render the winning flow.

    The seed calls `B` at line 5 and `A` at line 50; the walk follows the earlier call, so the
    rendered messages run S -> B -> T in call order, and `A` is off the path.
    """
    from code_atlas.onboarding.flows import build_flows

    file_of = {"S::a": "c/S.php", "A::z": "l/A.php", "B::y": "l/B.php", "T::c": "db/t.sql"}
    layer_of = {
        "c/S.php": "HTTP / Entry", "l/A.php": "Services",
        "l/B.php": "Services", "db/t.sql": "Domain / Data",
    }
    edges = [
        ("S::a", "B::y", "CALLS", "RESOLVED", 5),
        ("S::a", "A::z", "CALLS", "RESOLVED", 50),
        ("B::y", "T::c", "WRITES", "RESOLVED", 9),
        ("A::z", "T::c", "WRITES", "RESOLVED", 9),
    ]
    flow = build_flows(
        [("S::a", "vocabulary")], edges, file_of, layer_of, {"c": "web"},
        max_flows=5, max_nodes=50,
    ).flows[0]
    text = render_sequence_diagram(flow.steps, walk_truncated=flow.walk_truncated)
    messages = [ln for ln in text.splitlines() if "->>" in ln]
    assert messages == ["P0 ->> P1: CALLS", "P1 ->> P2: WRITES"]
    assert 'participant P1 as "B"' in text and '"A"' not in text


def test_a_single_step_trace_renders_a_lone_participant() -> None:
    """A seed with no traced hop is a valid one-participant diagram, no messages."""
    text = render_sequence_diagram([SEED])
    assert text.splitlines() == ["sequenceDiagram", 'participant P0 as "App\\Ctrl"']


def test_render_output_passes_its_own_validator() -> None:
    """The renderer validates what it hands back (143's gap)."""
    steps = [SEED, _step("App\\Svc::load", kind="CALLS", tier="DYNAMIC", line=None)]
    validate_mermaid_sequence_diagram(render_sequence_diagram(steps))


def test_validator_rejects_a_line_outside_the_subset() -> None:
    """R6.5 — the guard is seen failing on the shape it forbids."""
    with pytest.raises(ValueError):
        validate_mermaid_sequence_diagram("sequenceDiagram\nP0 => P1 hello\n")
    with pytest.raises(ValueError):
        validate_mermaid_sequence_diagram("flowchart LR\n")


def test_a_label_with_a_quote_or_colon_cannot_break_the_line() -> None:
    """A qname is data: quotes and colons are stripped so the mermaid stays parseable."""
    steps = [
        FlowStep('App\\"Odd"::act', 'x.php', "Services", "", "RESOLVED", None),
        _step("App\\Svc::run", kind="CA:LLS", line=10),
    ]
    validate_mermaid_sequence_diagram(render_sequence_diagram(steps))
