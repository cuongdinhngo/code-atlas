"""Read-through module facts for the 085 summarizer seam (task 118).

A module is one indexed file. The representative declaration and its leading doc comment are read
from disk at build time — the same slice ``read_symbol`` uses — because the graph carries no doc
field (R1.2 / no contract bump). Pure path + store rows in; no SQL, no network (R1.4).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from code_atlas.onboarding.metrics import NodeMetric
from code_atlas.onboarding.summary import NodeFacts
from code_atlas.source_slice import comment_block
from code_atlas.store import Row

_KIND_ORDER = ("Class", "Interface", "Trait", "Enum", "Function", "Method")


def signature_for(node: Mapping[str, object]) -> str:
    """A short, language-agnostic declaration label from indexed node fields."""
    kind = str(node["kind"]).lower()
    name = str(node["name"])
    params = node.get("params")
    if params:
        return f"{kind} {name}({params})"
    return f"{kind} {name}"


def representative_node(nodes: Sequence[Row]) -> Row | None:
    """Declaration whose docblock best represents the file — types first, then earliest line."""
    if not nodes:
        return None
    order = {kind: index for index, kind in enumerate(_KIND_ORDER)}

    def sort_key(node: Row) -> tuple[int, int]:
        kind_rank = order.get(str(node["kind"]), len(_KIND_ORDER))
        line = node.get("line_start", 0)
        return kind_rank, line if isinstance(line, int) else 0

    return min(nodes, key=sort_key)


def module_facts(
    root: Path,
    path: str,
    metric: NodeMetric,
    nodes: Sequence[Row],
) -> NodeFacts:
    """Build ``NodeFacts`` for one module file via read-through (118)."""
    node = representative_node(nodes)
    if node is None:
        return NodeFacts("", "", metric)
    start = node.get("line_start")
    if not isinstance(start, int) or start < 1:
        return NodeFacts("", "", metric)
    doc = comment_block(root / path, start, root=root)
    return NodeFacts(signature_for(node), doc, metric)
