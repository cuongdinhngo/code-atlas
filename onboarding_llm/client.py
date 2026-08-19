"""The tiny slice of the ``anthropic`` client the opt-in enrichment impls share (tasks 090/091).

A ``Protocol`` (not the SDK type) so tests inject a fake and no network is touched, plus the one
helper that pulls the first text block out of a message. Kept here so the summarizer (090) and the
layer refiner (091) share one shape rather than each re-declaring it (DRY, R7.4).
"""

from __future__ import annotations

from typing import Protocol


class Messages(Protocol):
    def create(self, **kwargs: object) -> object: ...


class Client(Protocol):
    """The slice of ``anthropic.Anthropic`` used here — a test injects a fake (no network)."""

    @property
    def messages(self) -> Messages: ...


def first_text(message: object) -> str:
    """The first text block of an Anthropic message, tolerant of the fake client used in tests."""
    for block in getattr(message, "content", None) or []:
        if getattr(block, "type", None) == "text":
            return getattr(block, "text", "") or ""
    return ""
