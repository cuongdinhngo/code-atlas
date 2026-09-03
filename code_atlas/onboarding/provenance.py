"""Which implementation wrote the artifact's text — one derivation for every stamp (task 209).

A committed artifact is read months later, and *"no doc comment"* is indistinguishable from *"no
summarizer beyond the structural one ran"* unless the tree says which side of the seam produced it
(R5.6). Every name here is read off the object that actually ran, never off the config that asked
for it — a label derived from a side-channel is right only while the bookkeeping happens to agree
(LESSONS 201-C2).

R4.1-safe: the core reads a class name from an object it was handed and imports no implementation.
Deterministic — a function of the injected seams, never of the wall clock (R4.2).
"""

from __future__ import annotations

from dataclasses import dataclass

#: What a seam with nothing injected reports. The deterministic path has no implementation object
#: to name, and inventing a class name for it would attest past what the payload can distinguish.
NONE = "none"

__all__ = ["NONE", "Provenance", "implementation_name"]


def implementation_name(seam: object | None) -> str:
    """The class name of the implementation behind a seam, or :data:`NONE` when none is injected."""
    return NONE if seam is None else type(seam).__name__


@dataclass(frozen=True)
class Provenance:
    """The three onboarding seams, each named by the implementation that ran behind it.

    ``summarizer`` is 085's module summary, ``prose`` is 117's four wording slots, ``layers`` is
    091's layer renaming. All three write text a reader cannot otherwise attribute.
    """

    summarizer: str = NONE
    prose: str = NONE
    layers: str = NONE

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict view — the dataset's byte-stability surface (R4.2)."""
        return {"layers": self.layers, "prose": self.prose, "summarizer": self.summarizer}
