"""One request from its entry point to the data it writes — a trace, not a syllabus (task 197).

Every other onboarding surface is an aggregate: the layer table, the layer x layer matrix, the hubs,
113's zero-inbound split, 114's capability table. None follows a single capability *running*.
This module does, and it is falsifiable line by line: every hop is an edge carrying a confidence
tier, a hop that cannot be proven **terminates** the trace instead of being bridged (R5.6 / R5.2),
and a walk that exhausts its budget says so rather than reading as complete.

That falsifiability is what keeps this inside 121's narrowing: 121 removed a *curated reading order*
— a pedagogical claim nothing can disprove — and a trace is the opposite kind of object.

Pure derivation over rows the caller already pulled: no SQL, no LLM, no language branch
(R1.1/R1.4/R4). Sorted throughout, so identical input yields byte-identical flows (R4.2).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from code_atlas.contract import (
    CONFIDENCE_TIERS,
    IMPACT_KINDS,
    PROVIDES_VIEW_DATA,
    WRITES,
)
from code_atlas.ignore import translate_path_pattern
from code_atlas.onboarding.layers import (
    READING_SEED_LAYER_RANK,
    RESPONSIBILITY_KEYWORDS,
    reading_seed_rank,
)
from code_atlas.onboarding.modules import module_of_path
from code_atlas.onboarding.reachability import SIGNAL_DECLARED, SIGNAL_VOCABULARY

RESOLVED, HEURISTIC, DYNAMIC = CONFIDENCE_TIERS

# The edges a trace may cross: the impact walk plus the write that gives it somewhere to END.
# DERIVED, never re-listed (R6.7), and it lives HERE rather than in `contract` because which subset
# a consumer walks is the consumer's business (138's `rule.kinds`) — and because 022 AC3's guard
# requires the tier-2 words to join no named subset the contract exports.
FLOW_KINDS: tuple[str, ...] = IMPACT_KINDS + (WRITES,)

# here — one definition site, so a renamed layer cannot leave this module pointing at nothing.
# here — one definition site, so a renamed layer cannot orphan this module (R6.7).
SINK_LAYER: str = RESPONSIBILITY_KEYWORDS["model"]
# Where a request comes IN. Same single definition site 113 reads, so the two surfaces cannot drift.
ENTRY_LAYER: str = RESPONSIBILITY_KEYWORDS["controller"]
# 131 ranks a real request entry here; a test or vendor path sinks below it on any segment.
_ENTRY_RANK: int = READING_SEED_LAYER_RANK[ENTRY_LAYER]

# Why a trace stopped. `sink` is the only ending that reached what it was looking for; the other
# three are honest terminations, and every one of them is rendered rather than dropped.
END_SINK = "sink"
END_NO_SINK = "no-sink"
END_UNPROVEN_HOP = "unproven-hop"
END_BUDGET = "budget-exhausted"

# A flow whose walk stopped early under-reports everything derived from it — the same sentence 140
# put on `impact_modules`, kept identical so a reader meets one wording, not two.
TRUNCATED_NOTE = (
    "the walk stopped at the node budget, so every count below is an under-estimate — "
    "a flow that is absent may simply not have been reached"
)
NO_SEEDS = (
    "no entry point to trace from: neither a declared entry_points glob nor the responsibility "
    "vocabulary named one indexed file, so there is nothing this surface can honestly show"
)
COVERAGE_NOTE = (
    "coverage is over every seed found, not over the flows emitted — a capped list is not a "
    "smaller repo"
)

__all__ = [
    "COVERAGE_NOTE",
    "ENTRY_LAYER",
    "FLOW_KINDS",
    "END_BUDGET",
    "END_NO_SINK",
    "END_SINK",
    "END_UNPROVEN_HOP",
    "Flow",
    "FlowSet",
    "FlowStep",
    "NO_SEEDS",
    "SINK_LAYER",
    "TRUNCATED_NOTE",
    "build_flows",
    "seed_files",
    "seed_symbols",
]


@dataclass(frozen=True)
class FlowStep:
    """One hop. ``tier`` is the confidence of the edge that REACHED this node, not of the node."""

    qname: str
    file: str
    layer: str
    kind: str
    tier: str

    def as_dict(self) -> dict[str, object]:
        return {
            "qname": self.qname,
            "file": self.file,
            "layer": self.layer,
            "kind": self.kind,
            "tier": self.tier,
        }


@dataclass(frozen=True)
class Flow:
    """One capability trace: an ordered path from one entry symbol to at most one end."""

    seed: str
    seed_file: str
    signal: str
    module: str | None
    steps: tuple[FlowStep, ...]
    ended: str
    sink: str | None
    walk_truncated: bool

    @property
    def layers(self) -> tuple[str, ...]:
        """The distinct layers crossed, in the order the trace crossed them."""
        seen: list[str] = []
        for step in self.steps:
            if step.layer and step.layer not in seen:
                seen.append(step.layer)
        return tuple(seen)

    def as_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "seed_file": self.seed_file,
            "signal": self.signal,
            "module": self.module,
            "steps": [step.as_dict() for step in self.steps],
            "layers": list(self.layers),
            "ended": self.ended,
            "sink": self.sink,
            "walk_truncated": self.walk_truncated,
        }


@dataclass(frozen=True)
class FlowSet:
    """The ranked, capped flows plus what the cap and the budget removed."""

    flows: tuple[Flow, ...]
    seeds_found: int
    seeds_traced: int
    flows_found: int
    flows_cut: int
    unattributed: tuple[str, ...]
    walk_truncated: bool
    refused: str | None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "flows": [flow.as_dict() for flow in self.flows],
            "seeds_found": self.seeds_found,
            "seeds_traced": self.seeds_traced,
            "flows_found": self.flows_found,
            "flows_cut": self.flows_cut,
            "unattributed": list(self.unattributed),
            "walk_truncated": self.walk_truncated,
            "coverage_note": COVERAGE_NOTE,
        }
        # A caveat rides on the payload that carries the defect, never on a neighbouring one (127).
        if self.walk_truncated:
            payload["walk_truncated_note"] = TRUNCATED_NOTE
        if self.refused is not None:
            payload["refused"] = self.refused
        return payload


def seed_symbols(
    entry_symbols: Sequence[str],
    seed_files: Sequence[tuple[str, str]],
    file_of: Mapping[str, str],
) -> tuple[tuple[str, str], ...]:
    """Entry SYMBOLS whose file is a seed file, each keeping its file's signal (W3 + 119).

    The seed unit is the symbol, not the file: one controller with fifteen actions is fifteen
    requests, and combining them into one walk would answer a question nobody asked.
    """
    signal_of = dict(seed_files)
    return tuple(
        sorted(
            (q, signal_of[file_of[q]])
            for q in entry_symbols
            if file_of.get(q, "") in signal_of
        )
    )


def seed_files(
    paths: Sequence[str],
    declared: Sequence[str],
    stub_roots: Sequence[str] = (),
) -> tuple[tuple[str, str], ...]:
    """Files a request can enter through, with the signal that named each one (119).

    The operator's declaration outranks the vocabulary, because it is that operator's statement
    about their own repo. The vocabulary signal is 131's ``reading_seed_rank``, NOT a bare
    ``responsibility_layer`` — that one is deepest-wins, so ``tests/controllers/FooTest`` and
    ``vendor/x/src/controllers/Y`` both read as request entries, which is defect 130's family.
    131 already sinks a test or vendor path on ANY segment; reusing it keeps one definition site.
    """
    import re

    rules = [re.compile(translate_path_pattern(pattern)) for pattern in declared if pattern]
    stubs = [re.compile(translate_path_pattern(f"{root}/**")) for root in stub_roots if root]
    hits: dict[str, str] = {}
    for path in paths:
        if any(rule.match(path) for rule in stubs):
            continue
        if any(rule.match(path) for rule in rules):
            hits[path] = SIGNAL_DECLARED
        elif reading_seed_rank(path) == _ENTRY_RANK:
            hits[path] = SIGNAL_VOCABULARY
    return tuple(sorted(hits.items()))


def _adjacency(
    edges: Sequence[tuple[str, str, str, str]],
) -> dict[str, tuple[tuple[str, str, str], ...]]:
    """``source -> ((target, kind, tier), ...)``, sorted so the walk is order-stable (R4.2)."""
    out: dict[str, list[tuple[str, str, str]]] = {}
    for source, target, kind, tier in edges:
        out.setdefault(source, []).append((target, kind, tier))
    return {source: tuple(sorted(set(rows))) for source, rows in out.items()}


def _is_hard_sink(kind: str) -> bool:
    """A write or a view hand-off — the data the request actually produced. Terminal."""
    return kind in (WRITES, PROVIDES_VIEW_DATA)


def _trace(
    seed: str,
    adjacency: Mapping[str, tuple[tuple[str, str, str], ...]],
    file_of: Mapping[str, str],
    layer_of: Mapping[str, str],
    budget: int,
) -> tuple[list[str], list[str], dict[str, tuple[str, str, str]], bool, bool]:
    """BFS from one seed. Returns (hard_sinks, soft_sinks, parents, hit_unproven, hit_budget).

    Arriving in the domain layer is a SOFT sink: it does not stop the walk, because the write the
    request came for usually sits one hop past the repository that performs it. It is used only when
    the trace found no write and no view hand-off at all.

    Only RESOLVED expands the frontier — the rule ``store.reachable_from`` already holds. A
    HEURISTIC/DYNAMIC neighbour is recorded as an ending and never expanded (R5.2).
    """
    parents: dict[str, tuple[str, str, str]] = {}
    seen = {seed}
    frontier = [seed]
    hard: list[str] = []
    soft: list[str] = []
    hit_unproven = False
    hit_budget = False
    while frontier:
        if len(seen) >= budget:
            hit_budget = True
            break
        node = frontier.pop(0)
        for target, kind, tier in adjacency.get(node, ()):
            if target in seen:
                continue
            seen.add(target)
            parents[target] = (node, kind, tier)
            layer = layer_of.get(file_of.get(target, ""), "")
            if _is_hard_sink(kind):
                hard.append(target)
                continue
            if layer == SINK_LAYER:
                soft.append(target)
            if tier != RESOLVED:
                hit_unproven = True
                continue
            frontier.append(target)
    return hard, soft, parents, hit_unproven, hit_budget


def _path_to(
    seed: str,
    target: str,
    parents: Mapping[str, tuple[str, str, str]],
    file_of: Mapping[str, str],
    layer_of: Mapping[str, str],
) -> tuple[FlowStep, ...]:
    """Walk the parent pointers back to the seed, then read the path forwards."""
    chain: list[tuple[str, str, str]] = []
    node = target
    while node != seed:
        source, kind, tier = parents[node]
        chain.append((node, kind, tier))
        node = source
    seed_file = file_of.get(seed, "")
    steps = [FlowStep(seed, seed_file, layer_of.get(seed_file, ""), "", RESOLVED)]
    for qname, kind, tier in reversed(chain):
        file = file_of.get(qname, "")
        steps.append(FlowStep(qname, file, layer_of.get(file, ""), kind, tier))
    return tuple(steps)


def _endpoint(parents: Mapping[str, tuple[str, str, str]]) -> str | None:
    """One representative node a sinkless trace reached: the sorted-last discovered qname.

    Deliberately NOT "the furthest" — no depth is recorded, and inventing a depth to rank on would
    be a claim the walk cannot back. Sorted, so the pick is deterministic (R4.2).
    """
    return sorted(parents)[-1] if parents else None


def build_flows(
    seeds: Sequence[tuple[str, str]],
    edges: Sequence[tuple[str, str, str, str]],
    file_of: Mapping[str, str],
    layer_of: Mapping[str, str],
    owner_of_dir: Mapping[str, str],
    *,
    max_flows: int,
    max_nodes: int,
) -> FlowSet:
    """Rank the seeds, trace the ones the cap admits, then rank and cap the flows (W1a).

    The cap is applied to the SEED list before any tracing, so the ceiling bounds the work rather
    than only the output — a per-element cap would leave the total unbounded.
    """
    if not seeds:
        return FlowSet((), 0, 0, 0, 0, (), False, NO_SEEDS)
    adjacency = _adjacency(edges)
    # Seeds that lead somewhere first, then path — the rule 131 gave the tour, for the same reason:
    # spending the budget on isolated files buys nothing.
    ranked_seeds = sorted(seeds, key=lambda s: (-len(adjacency.get(s[0], ())), s[0]))
    traced = ranked_seeds[:max_flows] if max_flows > 0 else []
    budget = max(1, max_nodes // max(1, len(traced))) if traced else 1
    found: list[Flow] = []
    unattributed: list[str] = []
    truncated = False
    for seed, signal in traced:
        seed_file = file_of.get(seed, "")
        module = module_of_path(seed_file, owner_of_dir) if seed_file else None
        if module is None:
            unattributed.append(seed)
        hard, soft, parents, hit_unproven, hit_budget = _trace(
            seed, adjacency, file_of, layer_of, budget
        )
        truncated = truncated or hit_budget
        sinks = hard or soft
        if sinks:
            # One flow per (seed, sink) pair (W4): each is a path with exactly one end.
            for sink in sorted(set(sinks)):
                found.append(
                    Flow(
                        seed, seed_file, signal, module,
                        _path_to(seed, sink, parents, file_of, layer_of),
                        END_SINK, sink, hit_budget,
                    )
                )
            continue
        end = END_BUDGET if hit_budget else (END_UNPROVEN_HOP if hit_unproven else END_NO_SINK)
        endpoint = _endpoint(parents)
        steps = (
            _path_to(seed, endpoint, parents, file_of, layer_of)
            if endpoint is not None
            else (FlowStep(seed, seed_file, layer_of.get(seed_file, ""), "", RESOLVED),)
        )
        found.append(Flow(seed, seed_file, signal, module, steps, end, None, hit_budget))
    # Rank for display by what a reader wants first: breadth of layers, then depth, then path.
    ordered = sorted(found, key=lambda f: (-len(f.layers), -len(f.steps), f.seed))
    emitted = tuple(ordered[:max_flows]) if max_flows > 0 else ()
    return FlowSet(
        flows=emitted,
        seeds_found=len(seeds),
        seeds_traced=len(traced),
        flows_found=len(found),
        flows_cut=len(found) - len(emitted),
        unattributed=tuple(sorted(unattributed)),
        walk_truncated=truncated,
        refused=None,
    )
