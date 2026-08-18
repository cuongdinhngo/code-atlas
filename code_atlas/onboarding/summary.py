"""Deterministic summarizer seam for Phase-3 onboarding (task 085, M10).

The one seam (R1.2) that keeps the LLM out of the core: a ``Summarizer`` Protocol with a
deterministic ``StructuralSummarizer`` default, so a later LLM impl (090/091) plugs in from
**outside** ``code_atlas/`` without the core ever importing an LLM (R4/R4.1). The split is two
callables — ``summarize_modules`` (enrichment, the only stage that touches graph facts / the seam)
and ``summaries_as_dict`` (presentation, consumes only ``Summary``) — so a CI test can prove
graph → enrichment → presentation with the middle faked. Pure arithmetic over generic strings: no
SQL, no network, no language branches (R1.1/R1.4); identical input → byte-identical output (R4.2).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from code_atlas.onboarding.metrics import DIRECTION_LABELS, NodeMetric

# Role tag derived from 083's direction label. Derived-from-source: a pin test asserts this map's
# key set equals DIRECTION_LABELS, so a new metrics label cannot ship unmapped (R6.7).
_ROLE_BY_DIRECTION: dict[str, str] = {
    "source": "entry-point",  # depends on others, nothing depends on it — a top-level caller
    "sink": "foundation",  # depended-upon, depends on nothing — a leaf/utility
    "mixed": "connector",  # both directions — sits between layers
    "isolated": "standalone",  # neither — no dependency edge
}

# The role vocabulary, ordered to match DIRECTION_LABELS for a stable, greppable surface (R6.7).
ROLE_LABELS: tuple[str, ...] = tuple(_ROLE_BY_DIRECTION[label] for label in DIRECTION_LABELS)


@dataclass(frozen=True)
class NodeFacts:
    """The enrichment input: one node's raw structural facts plus its 083 metric (role source)."""

    signature: str
    doc: str
    metric: NodeMetric


@dataclass(frozen=True)
class Summary:
    """One node's structural summary — the enrichment output the presentation stage renders."""

    key: str
    signature: str
    docline: str
    role: str

    def as_dict(self) -> dict[str, object]:
        """A plain, order-stable dict view — the serialisation consumers (086) build on."""
        return {
            "key": self.key,
            "signature": self.signature,
            "docline": self.docline,
            "role": self.role,
        }

    def to_json(self) -> str:
        """Deterministic JSON — the byte-stability surface (R4.2)."""
        return json.dumps(self.as_dict(), sort_keys=True, ensure_ascii=False)


class Summarizer(Protocol):
    """The one seam: turn a node's facts into a ``Summary``. The LLM impl (090) matches this shape
    from outside ``code_atlas/`` — a Protocol, so it imports no core base-class (R1.2/R4.1)."""

    def summarize(self, facts: NodeFacts) -> Summary: ...


def _first_line(doc: str) -> str:
    """The docblock's first non-empty line, stripped — generic, no per-language parse (R1.1)."""
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


class StructuralSummarizer:
    """The deterministic default: signature verbatim, docblock first line, role tag from 083's
    metric. No SQL, no network, no LLM (R4/R4.1). Byte-stable given identical facts (R4.2)."""

    def summarize(self, facts: NodeFacts) -> Summary:
        return Summary(
            key=facts.metric.key,
            signature=facts.signature,
            docline=_first_line(facts.doc),
            role=_ROLE_BY_DIRECTION[facts.metric.direction],
        )


def summarize_modules(
    facts: Iterable[NodeFacts], summarizer: Summarizer
) -> tuple[Summary, ...]:
    """Enrichment stage — the ONLY stage that touches graph facts, through the seam. Order-stable by
    key so identical input yields byte-identical output (R4.2)."""
    summaries = [summarizer.summarize(fact) for fact in facts]
    return tuple(sorted(summaries, key=lambda summary: summary.key))


def summaries_as_dict(summaries: Iterable[Summary]) -> dict[str, object]:
    """Presentation stage — consumes only ``Summary`` (never ``NodeFacts``/graph), so it cannot read
    the graph directly. A plain, order-stable dict the 086 tool renders."""
    return {"summaries": [summary.as_dict() for summary in summaries]}
