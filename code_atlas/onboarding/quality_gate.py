"""Deterministic structural gate over the onboarding artifact (task 109, M11).

Two defects shipped and were caught only by a human opening the HTML: 500/500 filler pages (107)
and an 82 KB median page (108). Both are mechanically detectable. This module is the missing gate —
pure checks over the in-memory ``OnboardingArtifact`` (no IO, no LLM, no language branch,
R1.1/R1.4/R4). ``build_artifact`` runs it and raises rather than emit a bad tree (050 precedent).

205 removed the per-module page tree, so the four criteria whose subject was a page (C1's filler
rule, C2's byte ceiling, C6's page identity, C7's page order) went with it. What is left guards the
prose slots (C1), the layer table (C3), the narrative steps (C4), cycle membership (C5) and
canonical order (C7).
"""

from __future__ import annotations

from code_atlas.onboarding.artifact import OnboardingArtifact
from code_atlas.onboarding.dataset import OnboardingDataset
from code_atlas.onboarding.prose import is_filler

# The number the gate defends (task 109 AC3). C4 bounds narrative steps to [MIN, MAX] (111): MAX is
# the hard ceiling the gate enforces; the floor is build_steps' target, unreachable on a tiny
# subgraph.
MAX_TOUR_STEPS = 15

__all__ = [
    "MAX_TOUR_STEPS",
    "QualityGateError",
    "check_artifact",
    "check_dataset",
]


class QualityGateError(ValueError):
    """A structural check failed; carries the check id and the offending path (AC4)."""

    def __init__(self, check: str, path: str, detail: str) -> None:
        self.check = check
        self.path = path
        super().__init__(f"onboarding quality gate {check} failed at {path!r}: {detail}")


def _check_canonical(artifact: OnboardingArtifact) -> None:
    """C7: canonical ordering ⇒ byte-stable render (R4.2). One broken order is enough to trip."""
    ranks = [row.rank for row in artifact.layers]
    if ranks != sorted(ranks):
        raise QualityGateError("C7", "layers", "layers are not in ascending rank order")
    crossing_keys = [(-count, source, target) for source, target, count in artifact.crossings]
    if crossing_keys != sorted(crossing_keys):
        raise QualityGateError("C7", "crossings", "crossings are not heaviest-first, then by name")


def check_artifact(
    artifact: OnboardingArtifact,
    *,
    max_tour_steps: int = MAX_TOUR_STEPS,
) -> None:
    """Run the surviving criteria over ``artifact``; raise on the first violation.

    Pure and deterministic: identical input raises identically or not at all.
    """
    stop_files = {stop.file for stop in artifact.stops}
    for stop in artifact.stops:
        for member in stop.scc:  # C5: a cycle cannot name a file outside the tour.
            if member not in stop_files:
                raise QualityGateError("C5", member, "SCC member is not a tour-stop file")
    if len(artifact.steps) > max_tour_steps:  # C4: the narrative tour ceiling (111 AC4).
        raise QualityGateError(
            "C4", "tour", f"{len(artifact.steps)} steps (> {max_tour_steps})"
        )
    for step in artifact.steps:  # C4: no step may be empty — 109's ceiling becomes a real bound.
        if not step.modules:
            raise QualityGateError("C4", f"step[{step.order}]", "step names no module")
    for row in artifact.layers:  # C3: every layer must carry a non-empty description (110).
        if not row.description.strip():
            raise QualityGateError("C3", f"layer[rank {row.rank}]", "layer description is empty")
    _check_prose(artifact)
    _check_canonical(artifact)


def _check_prose(artifact: OnboardingArtifact) -> None:
    """C1 over the three prose slots (117 AC6) — generated prose gets no exemption from the gate.

    The seam already discards filler and falls back, so this can only trip on prose that reached the
    artifact some other way — which is exactly what a gate is for, not a duplicate of the seam.
    """
    for row in artifact.layers:
        if is_filler(row.description, row.layer):
            raise QualityGateError(
                "C1", f"layer[{row.layer}]", "description only restates the layer's own name"
            )
    for step in artifact.steps:
        if is_filler(step.why, step.title, *step.modules):
            raise QualityGateError(
                "C1", f"step[{step.order}]", "narrative only restates its own title and modules"
            )


def check_dataset(dataset: OnboardingDataset) -> None:
    """C1 over the dataset's own prose — the headline slot (task 117 AC6).

    The headlines live in the dataset rather than the artifact, so they need the gate applied here;
    the rule and its predicate are the artifact's, not a second one. Pure: raise or return.
    """
    for headline in dataset.headlines:
        if is_filler(headline.text, headline.key, headline.label):
            raise QualityGateError(
                "C1", f"headline[{headline.key}]", "headline only restates its own key"
            )
    for layer in dataset.layers:
        if is_filler(layer.description, layer.layer):
            raise QualityGateError(
                "C1", f"layer[{layer.layer}]", "description only restates the layer's own name"
            )
