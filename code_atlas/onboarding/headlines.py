"""The headline facts a newcomer needs first — candidates derived, wording written (task 117, M12).

The mockup's overview opened on six numbers, each with what it *meant*, and the meaning was the only
hand-written thing on the page. That split is the design here: **which** facts are noteworthy is
decided structurally, from the aggregate dataset's own bounded fields, and each one arrives with a
complete factual sentence. The 117 prose seam may rewrite that sentence; it can never add, remove or
re-rank a headline, so the enrichment cannot smuggle in a fact the index does not hold.

A family is emitted **only when its structural precondition holds**, so an absent fact yields no
sentence rather than a hollow one — which is also what keeps 109's C1 non-vacuous here.

Pure derivation over primitives: no SQL, no LLM, no language branch (R1.1/R1.4/R4). Sorted and
fixed-order throughout, so identical input yields identical headlines (R4.2).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from code_atlas.contract import CALLABLE_KINDS, TYPE_KINDS
from code_atlas.onboarding.mirrors import MirrorReport
from code_atlas.onboarding.modules import ModuleMap
from code_atlas.onboarding.prose import SLOT_HEADLINE, ProseRequest, ProseRun
from code_atlas.onboarding.reachability import ReachabilitySplit

# The reading order, and the whole set — ``prose.SLOT_LIMITS`` bounds the slot by this length, and a
# pin test derives that bound from here rather than trusting a second copy (R6.7).
HEADLINE_FAMILIES: tuple[str, ...] = (
    "duplication",
    "concentration",
    "abstraction",
    "confidence",
    "reachability",
    "coverage",
)

# The exact tier's name in the store's edge-health census; every other tier is a heuristic match.
EXACT_TIER = "EXACT"

__all__ = ["EXACT_TIER", "HEADLINE_FAMILIES", "Headline", "headline_candidates"]

# What one family contributes: its factual sentence, the facts an impl may show a model, and the
# identifiers the prose must not merely restate (``prose.is_filler``).
_Candidate = tuple[str, tuple[tuple[str, str], ...], tuple[str, ...]]


@dataclass(frozen=True)
class Headline:
    """One headline fact: a stable key, a short label, and the sentence a reader sees."""

    key: str
    label: str
    text: str

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict view — what every renderer serialises (R4.2)."""
        return {"key": self.key, "label": self.label, "text": self.text}


def _share(part: int, whole: int) -> int:
    """``part`` as a whole-number percentage of ``whole``; 0 when there is nothing to divide."""
    return 0 if whole <= 0 else round(100 * part / whole)


def _duplication(mirrors: MirrorReport) -> _Candidate:
    """The largest mirrored sibling pair (115). Ranked first: it is the costliest fact to miss."""
    pair = mirrors.pairs[0]
    text = (
        f"{pair.left} and {pair.right} hold {pair.shared} relative paths in common — "
        f"{round(pair.overlap * 100)} % of everything either side contains. "
        f"{mirrors.caveat}"
    )
    facts = (
        ("left subtree", pair.left),
        ("right subtree", pair.right),
        ("shared relative paths", str(pair.shared)),
        ("overlap", f"{round(pair.overlap * 100)} %"),
        ("only on the left", str(pair.left_only)),
        ("only on the right", str(pair.right_only)),
    )
    return text, facts, (pair.left, pair.right)


def _concentration(hubs: Sequence[tuple[str, int, int]], edges: int) -> _Candidate:
    """The single most depended-upon file, and how much of the graph points at it."""
    path, fan_in, fan_out = hubs[0]
    text = (
        f"The most depended-upon file is {path}, with {fan_in} incoming dependencies — "
        f"{_share(fan_in, edges)} % of the {edges} the index resolved, and more direct "
        f"dependents than any other file."
    )
    facts = (
        ("busiest file", path),
        ("incoming dependencies", str(fan_in)),
        ("outgoing dependencies", str(fan_out)),
        ("resolved dependencies in total", str(edges)),
    )
    return text, facts, (path,)


def _abstraction(kinds: Mapping[str, int]) -> _Candidate:
    """Types against callables — whether logic sits behind a declared type or in procedures."""
    types = sum(kinds.get(kind, 0) for kind in TYPE_KINDS)
    callables = sum(kinds.get(kind, 0) for kind in CALLABLE_KINDS)
    total = types + callables
    text = (
        f"{types} indexed symbols declare a type and {callables} are callables, so "
        f"{_share(types, total)} % of the {total} together are types."
    )
    facts = (
        ("symbols declaring a type", str(types)),
        ("callable symbols", str(callables)),
        ("kinds counted as types", ", ".join(TYPE_KINDS)),
        ("kinds counted as callables", ", ".join(CALLABLE_KINDS)),
    )
    return text, facts, ()


def _confidence(confidence: Mapping[str, int]) -> _Candidate:
    """How much of the dependency graph is a heuristic match rather than a proven one."""
    total = sum(confidence.values())
    heuristic = total - confidence.get(EXACT_TIER, 0)
    text = (
        f"{_share(heuristic, total)} % of the {total} resolved dependencies sit below the exact "
        f"confidence tier, so {heuristic} of them are a heuristic match rather than a proven one."
    )
    facts = tuple(("tier " + tier, str(confidence[tier])) for tier in sorted(confidence))
    return text, facts, ()


def _reachability(split: ReachabilitySplit) -> _Candidate:
    """The zero-inbound set as populations (113) — a count, never a verdict on deadness."""
    largest = max(split.buckets, key=lambda bucket: (bucket.count, bucket.bucket))
    text = (
        f"{split.total} modules have nothing in the index pointing at them. The largest "
        f"population is {largest.label.lower()}, at {largest.count} of them — {largest.note}"
    )
    facts = tuple((bucket.label, str(bucket.count)) for bucket in split.buckets)
    return text, facts, ()


def _coverage(modules: ModuleMap) -> _Candidate:
    """How much of the tree the 114 capability table accounts for, and what it set aside."""
    text = (
        f"{modules.percent} % of indexed files ({modules.covered} of {modules.total}) sit under a "
        f"named capability; a further {modules.excluded} are vendored or test code and were "
        f"set aside rather than counted."
    )
    facts = (
        ("files under a named capability", str(modules.covered)),
        ("indexed files", str(modules.total)),
        ("set aside as vendored or test code", str(modules.excluded)),
        ("named capabilities", str(len(modules.modules))),
    )
    return text, facts, tuple(module.module for module in modules.modules)


def headline_candidates(
    *,
    node_kind_counts: Sequence[tuple[str, int]],
    edge_kind_counts: Sequence[tuple[str, int]],
    confidence: Mapping[str, int],
    hubs: Sequence[tuple[str, int, int]],
    reachability: ReachabilitySplit,
    modules: ModuleMap,
    mirrors: MirrorReport,
    prose: ProseRun | None = None,
) -> tuple[Headline, ...]:
    """The headline facts this index actually supports, in reading order (see module docstring).

    Each family contributes at most one row and only when it has something to say, so the count
    varies with the repo and never with a model. ``prose`` may rewrite a sentence; with it unset (or
    declining) every row keeps its structural wording, byte-identically (AC1).
    """
    kinds = dict(node_kind_counts)
    edges = sum(count for _, count in edge_kind_counts)
    built: list[tuple[str, str, tuple[tuple[str, str], ...], tuple[str, ...]]] = []
    if mirrors.pairs:
        built.append(("duplication", *_duplication(mirrors)))
    if hubs and edges:
        built.append(("concentration", *_concentration(hubs, edges)))
    if any(kinds.get(kind) for kind in (*TYPE_KINDS, *CALLABLE_KINDS)):
        built.append(("abstraction", *_abstraction(kinds)))
    if sum(confidence.values()):
        built.append(("confidence", *_confidence(confidence)))
    if reachability.buckets:
        built.append(("reachability", *_reachability(reachability)))
    if modules.total:
        built.append(("coverage", *_coverage(modules)))
    order = {family: index for index, family in enumerate(HEADLINE_FAMILIES)}
    built.sort(key=lambda row: order[row[0]])
    return tuple(
        Headline(
            key=key,
            label=key.capitalize(),
            text=(
                default
                if prose is None
                else prose.text(
                    ProseRequest(
                        slot=SLOT_HEADLINE,
                        key=key,
                        default=default,
                        facts=facts,
                        names=names,
                    )
                )
            ),
        )
        for key, default, facts, names in built
    )
