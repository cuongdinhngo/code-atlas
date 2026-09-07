"""Mermaid ``sequenceDiagram`` from one capability trace (task 225).

A flowchart asserts only *reaches*; a sequence asserts *this happened, then this*. That extra claim
is honest only where the walk established call order, so this renderer draws a solid arrow for a hop
proven in order (a RESOLVED edge carrying a call line) and a DASHED arrow plus a ``%%`` note for one
it cannot order — a same-line sibling, an unrecorded line, or a HEURISTIC/DYNAMIC hop — and notes a
truncated walk (R5.6). ``flowchart LR`` (197) stays; the two answer different questions.

Participants are the containers ``contract.split_qname`` already yields, addressed by positional id
so a qname never becomes a mermaid identifier (the rule 144 holds). Pure derivation over the steps
the caller already walked: no SQL, no LLM, no language branch (R1.1/R4). Identical input yields a
byte-identical diagram (R4.2).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from code_atlas.contract import CONFIDENCE_TIERS, split_qname
from code_atlas.onboarding.flows import FlowStep

__all__ = [
    "render_sequence_diagram",
    "validate_mermaid_sequence_diagram",
]

RESOLVED = CONFIDENCE_TIERS[0]

_PARTICIPANT = re.compile(r'^participant P\d+ as "[^"]*"$')
_MESSAGE = re.compile(r"^P\d+ (->>|-->>) P\d+: .*$")

TRUNCATED_NOTE = "walk truncated: any order beyond this point is under-reported"


def _participant(qname: str) -> str:
    """The container a hop participates as — ``App\\Foo`` for ``App\\Foo::bar``, else the name."""
    container, _member = split_qname(qname)
    return container or qname


def _label(name: str) -> str:
    """Quotes end a label and a newline breaks the line; a colon would end a message early."""
    return name.replace('"', "").replace("\r", " ").replace("\n", " ").replace(":", " ")


def render_sequence_diagram(
    steps: Sequence[FlowStep], *, walk_truncated: bool = False
) -> str:
    """Deterministic ``sequenceDiagram`` for one flow's ordered steps. Counts are interpolated."""
    ids: dict[str, str] = {}
    for step in steps:
        actor = _participant(step.qname)
        if actor not in ids:
            ids[actor] = f"P{len(ids)}"
    lines = ["sequenceDiagram"]
    for actor, ident in ids.items():
        lines.append(f'participant {ident} as "{_label(actor)}"')
    for position in range(1, len(steps)):
        prev, step = steps[position - 1], steps[position]
        src, dst = ids[_participant(prev.qname)], ids[_participant(step.qname)]
        proven = step.tier == RESOLVED and step.line is not None
        arrow = "->>" if proven else "-->>"
        lines.append(f"{src} {arrow} {dst}: {_label(step.kind)}")
        if not proven:
            reason = (
                f"reached through a {step.tier} edge"
                if step.tier != RESOLVED
                else "call line not established (unrecorded or shared with a sibling)"
            )
            lines.append(f"%% order unknown {src}->{dst}: {reason}")
    if walk_truncated:
        lines.append(f"%% {TRUNCATED_NOTE}")
    text = "\n".join(lines) + "\n"
    # Validate what we hand back, not only what a benchmark renders (143's gap, same shape).
    validate_mermaid_sequence_diagram(text)
    return text


def validate_mermaid_sequence_diagram(text: str) -> None:
    """Python-side syntax-subset check — no Node, no npm. Raises ValueError on a miss."""
    lines = text.strip().splitlines()
    if not lines or lines[0] != "sequenceDiagram":
        raise ValueError("mermaid must start with 'sequenceDiagram'")
    for line in lines[1:]:
        if _PARTICIPANT.match(line) or _MESSAGE.match(line) or line.startswith("%% "):
            continue
        raise ValueError(f"unrecognised mermaid line: {line!r}")
