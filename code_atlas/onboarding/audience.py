"""Who the committed artifact was written for, and what that reader gets (task 210, M12).

`detail_level` gated only fields of the MCP response, which the caller reads once and drops, so the
**written** tree was byte-identical at every level: one shape for a first-week developer and for an
engineer auditing coupling, and on a large repo that shape is megabytes of the wrong thing for both.

**This module is the one place that decides what an audience emits** (R1.8). The markdown writer,
the dataset and the viewer read :data:`CONTRACTS`; none of them re-derives it, which is 127's
lesson. Each section carries the sentence saying *why that reader needs it* — a content contract,
not a verbosity dial (Scope 2): an audience whose sections are another's minus a few would be a
configuration flag wearing a bigger name, and R7.4 says that is the finding, not the feature.

Deterministic: an audience is a resolved setting, never inferred from who is reading (R4.1/R4.2).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

FULL = "full"
NEWCOMER = "newcomer"
MAINTAINER = "maintainer"

#: Resolution order, and the default. ``full`` is today's artifact, kept as an explicit third
#: audience rather than a fourth state: a tree committed before this ticket is still describable.
AUDIENCES: tuple[str, ...] = (FULL, NEWCOMER, MAINTAINER)
DEFAULT_AUDIENCE = FULL

# Section keys. Named here rather than by heading text so a heading can be reworded without
# silently re-partitioning the audiences (R6.7 — the invariant, not the spelling).
ORIENTATION = "orientation"
SUMMARY = "summary"
MIRRORS = "mirrors"
COMMUNITY = "community"
MODULES = "modules"
REACHABILITY = "reachability"
LAYERS = "layers"
DIAGRAM = "diagram"
CROSSINGS = "crossings"
PROVENANCE = "provenance"

#: Written files an audience may receive, by the constant each renderer already uses.
TOUR_DOC = "tour"
FLOWS_DOC = "flows"
VIEWER_DOC = "viewer"

__all__ = [
    "AUDIENCES",
    "COMMUNITY",
    "CONTRACTS",
    "CROSSINGS",
    "DEFAULT_AUDIENCE",
    "DIAGRAM",
    "FLOWS_DOC",
    "FULL",
    "LAYERS",
    "MAINTAINER",
    "MIRRORS",
    "MODULES",
    "NEWCOMER",
    "ORIENTATION",
    "PROVENANCE",
    "REACHABILITY",
    "SUMMARY",
    "TOUR_DOC",
    "VIEWER_DOC",
    "AudienceContract",
    "contract_for",
    "resolve_audience",
]


@dataclass(frozen=True)
class AudienceContract:
    """One audience: the sections and documents it gets, and why it needs each of them."""

    audience: str
    purpose: str
    sections: Mapping[str, str]
    documents: Mapping[str, str]

    def wants(self, section: str) -> bool:
        """Whether this audience gets ``section``. An unknown key is NOT emitted (fail closed)."""
        return section in self.sections

    def wants_document(self, document: str) -> bool:
        return document in self.documents

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict view — the dataset's byte-stability surface (R4.2)."""
        return {
            "audience": self.audience,
            "documents": {key: self.documents[key] for key in sorted(self.documents)},
            "purpose": self.purpose,
            "sections": {key: self.sections[key] for key in sorted(self.sections)},
        }


_FULL = AudienceContract(
    audience=FULL,
    purpose=(
        "Everything the graph and the declared files can say. The shape every artifact had before "
        "210, kept so a committed tree is still reproducible and so neither reader's contract has "
        "to be the union of the other's."
    ),
    sections={
        ORIENTATION: "Day-one commands, quoted and cited (207).",
        SUMMARY: "The aggregate counts the whole document is built from.",
        MIRRORS: "Subtrees that are near-copies of each other (115).",
        COMMUNITY: "Import-graph communities that straddle two vocabulary layers (211).",
        MODULES: "The capability table and the coverage it does not claim (114).",
        REACHABILITY: "Zero-inbound modules by population, with what each count does not prove.",
        LAYERS: "Every layer, its rank and its fan.",
        DIAGRAM: "The layer x layer matrix as a flowchart (143).",
        CROSSINGS: "Every cross-layer edge, one row each.",
        PROVENANCE: "Which implementation wrote the text (209).",
    },
    documents={
        TOUR_DOC: "A reading order over the budgeted subgraph.",
        FLOWS_DOC: "Request traces end to end (197).",
        VIEWER_DOC: "The same dataset as one offline page.",
    },
)

_NEWCOMER = AudienceContract(
    audience=NEWCOMER,
    purpose=(
        "A first-week developer who needs to start work: where their code lives, how to run and "
        "test it, and a short list of files to open. Aggregates over tens of thousands of modules "
        "answer none of that and crowd out what does."
    ),
    sections={
        ORIENTATION: "The whole point of day one — how to run it, how to test it, what it is.",
        SUMMARY: "Enough scale to know what they have walked into; four lines, not a table.",
        LAYERS: "The vocabulary the tour's steps are named in; unreadable without it.",
        PROVENANCE: "So an empty summary reads as a fact about the run, not about the repo (209).",
    },
    documents={
        TOUR_DOC: "Ten files to open, in an order with a reason.",
        FLOWS_DOC: "How a request actually moves — the shape of the system they will edit.",
        VIEWER_DOC: "The same, offline, for someone not living in a terminal.",
    },
)

_MAINTAINER = AudienceContract(
    audience=MAINTAINER,
    purpose=(
        "An engineer auditing the system: coupling hotspots, duplicated subtrees and what is "
        "unreachable. They already know the layout, so a reading order and a run command are noise "
        "— what they need is every aggregate, with the confidence attribution beside it."
    ),
    sections={
        SUMMARY: "The aggregates are the whole value here.",
        MIRRORS: "Duplicated subtrees are the finding they came for (115).",
        COMMUNITY: "Where the import graph disagrees with the path vocabulary (211).",
        MODULES: "The capability table, and what its coverage does not claim (114).",
        REACHABILITY: "What is unreachable, and which counts are unasked questions (208).",
        LAYERS: "Every layer, its rank and its fan.",
        DIAGRAM: "The matrix as a flowchart — the coupling shape at a glance (143).",
        CROSSINGS: "Every crossing, one row each; this is the coupling evidence.",
        PROVENANCE: "Which implementation wrote any prose they are about to quote (209).",
    },
    documents={
        FLOWS_DOC: "Traces are evidence about coupling, not a reading order (197).",
        VIEWER_DOC: "The same dataset as one offline page.",
    },
)

CONTRACTS: Mapping[str, AudienceContract] = {
    FULL: _FULL,
    NEWCOMER: _NEWCOMER,
    MAINTAINER: _MAINTAINER,
}


def resolve_audience(requested: str | None) -> str:
    """The audience to write for. Unknown or unset falls back to :data:`DEFAULT_AUDIENCE`.

    Fails soft on purpose: an unrecognised value must not stop a build from producing an artifact,
    and the artifact states which audience it actually used, so the fallback is never silent (AC3).
    """
    name = (requested or "").strip().lower()
    return name if name in CONTRACTS else DEFAULT_AUDIENCE


def contract_for(audience: str | None) -> AudienceContract:
    """The one contract every renderer reads. Never a second derivation (R1.8)."""
    return CONTRACTS[resolve_audience(audience)]
