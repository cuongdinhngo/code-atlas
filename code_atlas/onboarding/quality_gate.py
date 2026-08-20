"""Deterministic structural gate over the onboarding artifact (task 109, M11).

Two defects shipped and were caught only by a human opening the HTML: 500/500 filler pages (107)
and an 82 KB median page (108). Both are mechanically detectable. This module is the missing gate —
seven pure checks over the in-memory ``OnboardingArtifact`` (no IO, no LLM, no language branch,
R1.1/R1.4/R4). ``build_artifact`` runs it and raises rather than emit a bad tree (050 precedent).
"""

from __future__ import annotations

from code_atlas.onboarding.artifact import OnboardingArtifact, render_module

# The numbers the gate defends (task 109 AC3). C2 sits above 108's capped page (6,878 B) and below
# its uncapped one (40,074 B). C4 is the current default tour budget; 111 tightens it to [5, 15].
MAX_PAGE_BYTES = 16384
MAX_TOUR_STEPS = 500

__all__ = ["MAX_PAGE_BYTES", "MAX_TOUR_STEPS", "QualityGateError", "check_artifact"]


class QualityGateError(ValueError):
    """A structural check failed; carries the check id and the offending path (AC4)."""

    def __init__(self, check: str, path: str, detail: str) -> None:
        self.check = check
        self.path = path
        super().__init__(f"onboarding quality gate {check} failed at {path!r}: {detail}")


def _check_canonical(artifact: OnboardingArtifact) -> None:
    """C7: canonical ordering ⇒ byte-stable render (R4.2). One broken order is enough to trip."""
    indexes = [page.index for page in artifact.pages]
    if indexes != sorted(indexes) or len(set(indexes)) != len(indexes):
        raise QualityGateError("C7", "pages", "pages are not in ascending, distinct index order")
    ranks = [row.rank for row in artifact.layers]
    if ranks != sorted(ranks):
        raise QualityGateError("C7", "layers", "layers are not in ascending rank order")
    crossing_keys = [(-count, source, target) for source, target, count in artifact.crossings]
    if crossing_keys != sorted(crossing_keys):
        raise QualityGateError("C7", "crossings", "crossings are not heaviest-first, then by name")
    if list(artifact.isolated) != sorted(artifact.isolated):
        raise QualityGateError("C7", "isolated", "isolated modules are not sorted")


def check_artifact(
    artifact: OnboardingArtifact,
    *,
    max_results: int,
    max_page_bytes: int = MAX_PAGE_BYTES,
    max_tour_steps: int = MAX_TOUR_STEPS,
) -> None:
    """Run C1–C7 over ``artifact``; raise ``QualityGateError`` on the first violation.

    Pure and deterministic: identical input raises identically or not at all. ``max_results`` is the
    cap ``render_module`` uses so C2 measures the bytes the tree would actually carry (108).
    """
    stop_files = {stop.file for stop in artifact.stops}
    seen: set[str] = set()
    for page in artifact.pages:
        if page.relpath in seen:  # C6: two pages cannot claim the same file on disk.
            raise QualityGateError("C6", page.relpath, "duplicate page path")
        seen.add(page.relpath)
        if page.file not in stop_files:  # C6: a page for a module the tour never visited.
            raise QualityGateError("C6", page.file, "page for a module absent from the tour")
        if not (page.docline or page.fan_in or page.fan_out):  # C1: the 107 filler rule.
            raise QualityGateError("C1", page.file, "page carries no fact beyond its own path")
        size = len(render_module(page, max_results).encode("utf-8"))
        if size > max_page_bytes:  # C2: the 108 byte ceiling.
            raise QualityGateError("C2", page.file, f"page is {size} bytes (> {max_page_bytes})")
        for member in page.scc:  # C5: a cycle cannot name a file outside the tour.
            if member not in stop_files:
                raise QualityGateError("C5", member, "SCC member is not a tour-stop file")
    for isolated in artifact.isolated:  # C5: isolated modules come from the tour, so must be in it.
        if isolated not in stop_files:
            raise QualityGateError("C5", isolated, "isolated module is not a tour-stop file")
    if len(artifact.stops) > max_tour_steps:  # C4: pre-111 regression ceiling.
        raise QualityGateError("C4", "tour", f"{len(artifact.stops)} stops (> {max_tour_steps})")
    for row in artifact.layers:  # C3: every layer must carry a non-empty description (110).
        if not row.description.strip():
            raise QualityGateError("C3", f"layer[rank {row.rank}]", "layer description is empty")
    _check_canonical(artifact)
