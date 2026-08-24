"""Mermaid flowchart of the layer × layer matrix (task 143).

Confirmed arrows are solid; HEURISTIC-only are dashed. DYNAMIC-only crossings are omitted.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from code_atlas.contract import CONFIDENCE_TIERS
from code_atlas.onboarding.layers import LayerAssignment

RESOLVED, HEURISTIC, DYNAMIC = CONFIDENCE_TIERS

_NODE = re.compile(r'^[A-Za-z][A-Za-z0-9_]*\["[^"]*"\]$')
_EDGE = re.compile(
    r'^[A-Za-z][A-Za-z0-9_]*\s+(-->|-.->)\|"(0|[1-9][0-9]*)"\|\s+[A-Za-z][A-Za-z0-9_]*$'
)

__all__ = [
    "DiagramEdge",
    "HEURISTIC",
    "LayerDiagram",
    "RESOLVED",
    "diagram_edges",
    "module_edge_tiers",
    "render_layer_flowchart",
    "validate_mermaid_flowchart",
]


@dataclass(frozen=True, slots=True)
class DiagramEdge:
    """One layer → layer arrow: count is the matrix cell; heuristic_only is AC3's ink."""

    source: str
    target: str
    count: int
    heuristic_only: bool


@dataclass(frozen=True, slots=True)
class LayerDiagram:
    """Rendered mermaid plus the cap / omit disclosures that must not be silent (108/124)."""

    mermaid: str
    shown_layers: int
    total_layers: int
    omitted_dynamic: int
    omitted_capped: int
    truncated: bool


def module_edge_tiers(
    nodes: Iterable[tuple[str, str]],
    edges: Iterable[tuple[str, str, str]],
) -> tuple[tuple[str, str, str], ...]:
    """Distinct file pairs with a winning tier — RESOLVED beats HEURISTIC beats DYNAMIC."""
    files: dict[str, set[str]] = {}
    for qname, file_path in nodes:
        files.setdefault(qname, set()).add(file_path)
    best: dict[tuple[str, str], str] = {}
    rank = {RESOLVED: 2, HEURISTIC: 1, DYNAMIC: 0}
    for source, target, tier in edges:
        if source == target:
            continue
        won = rank.get(tier, 0)
        for src_file in files.get(source, ()):
            for tgt_file in files.get(target, ()):
                if src_file == tgt_file:
                    continue
                key = (src_file, tgt_file)
                prev = best.get(key)
                if prev is None or won > rank.get(prev, 0):
                    best[key] = tier if tier in rank else DYNAMIC
    return tuple(sorted((src, tgt, best[(src, tgt)]) for src, tgt in best))


def diagram_edges(
    module_tiers: Sequence[tuple[str, str, str]],
    assignment: LayerAssignment,
) -> tuple[tuple[DiagramEdge, ...], int]:
    """Layer crossings split by winning tier. Same-layer pairs are not crossings.

    Returns ``(edges, omitted_dynamic)``. A cell is heuristic_only when every contributing
    module-pair is HEURISTIC (no RESOLVED evidence). DYNAMIC-only pairs are omitted.
    """
    layer_of = {module.module: module.layer for module in assignment.modules}
    resolved: dict[tuple[str, str], int] = {}
    heuristic: dict[tuple[str, str], int] = {}
    omitted = 0
    for source, target, tier in module_tiers:
        pair = (layer_of.get(source), layer_of.get(target))
        if pair[0] is None or pair[1] is None or pair[0] == pair[1]:
            continue
        key = (pair[0], pair[1])
        if tier == RESOLVED:
            resolved[key] = resolved.get(key, 0) + 1
        elif tier == HEURISTIC:
            heuristic[key] = heuristic.get(key, 0) + 1
        else:
            omitted += 1
    keys = sorted(
        set(resolved) | set(heuristic),
        key=lambda key: (-_cell(resolved, heuristic, key), key),
    )
    edges = tuple(
        DiagramEdge(
            source,
            target,
            _cell(resolved, heuristic, (source, target)),
            heuristic_only=(source, target) not in resolved,
        )
        for source, target in keys
    )
    return edges, omitted


def render_layer_flowchart(
    layers: Sequence[str],
    edges: Sequence[DiagramEdge],
    *,
    node_cap: int,
    omitted_dynamic: int = 0,
) -> LayerDiagram:
    """Deterministic mermaid ``flowchart LR``. Counts are interpolated, never literals."""
    total = len(layers)
    shown = layers[: max(node_cap, 0)]
    kept = set(shown)
    ids = {name: f"N{index}" for index, name in enumerate(shown)}
    visible = [edge for edge in edges if edge.source in kept and edge.target in kept]
    lines = ["flowchart LR"]
    for name in shown:
        lines.append(f'{ids[name]}["{_label(name)}"]')
    for edge in visible:
        arrow = "-.->" if edge.heuristic_only else "-->"
        lines.append(f'{ids[edge.source]} {arrow}|"{edge.count}"| {ids[edge.target]}')
    return LayerDiagram(
        mermaid="\n".join(lines) + "\n",
        shown_layers=len(shown),
        total_layers=total,
        omitted_dynamic=omitted_dynamic,
        # A crossing whose layer fell outside the cap leaves no arrow; the cross-layer table
        # below still lists it, so the count of dropped arrows must be said out loud (108/124).
        omitted_capped=len(edges) - len(visible),
        truncated=len(shown) < total,
    )


def validate_mermaid_flowchart(text: str) -> None:
    """Python-side syntax-subset check — no Node, no npm (AC5). Raises ValueError on a miss."""
    body = text.strip()
    lines = body.splitlines()
    if not lines or lines[0] != "flowchart LR":
        raise ValueError("mermaid must start with 'flowchart LR'")
    for line in lines[1:]:
        if _NODE.match(line) or _EDGE.match(line):
            continue
        raise ValueError(f"unrecognised mermaid line: {line!r}")


def _cell(
    resolved: dict[tuple[str, str], int],
    heuristic: dict[tuple[str, str], int],
    key: tuple[str, str],
) -> int:
    return resolved.get(key, 0) + heuristic.get(key, 0)


def _label(name: str) -> str:
    """Quotes end the label and a newline would break the line structure; drop both."""
    return name.replace('"', "").replace("\r", " ").replace("\n", " ")
