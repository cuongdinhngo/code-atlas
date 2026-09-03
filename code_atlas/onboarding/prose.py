"""The one prose seam behind the onboarding map (task 117, M12).

Everything on the map is derived: counts, rankings, groupings, the matrix, the treemap. Four things
are not — the per-layer responsibility line, each tour step's narrative, the wording of the headline
facts, and a business module's label (198). This module is the single injection point for those four
slots and nothing else.

One :class:`ProseWriter` Protocol with one method serves all four, so the filler guard, the
failure degradation and the per-run call ceiling each exist exactly **once** (R1.2/R7.1). An impl
lives **outside** ``code_atlas/`` (``onboarding_llm``); with none injected :class:`ProseRun` returns
every slot's structural default, makes no call, and is identity by construction (R4/R4.1, AC1).

No prompt, no model name, no LLM import lives here or anywhere under ``code_atlas/`` (AC7). This
module imports nothing from ``code_atlas.onboarding``, so any of its modules can use it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

SLOT_HEADLINE = "headline"
SLOT_LAYER = "layer"
SLOT_STEP = "step"
SLOT_MODULE = "module"

# Per-slot ceilings, so a repo with hundreds of layers cannot starve the tour of prose. Every number
# is DERIVED from a cap that already exists (110's vocabulary, 109's C4, the headline families) — a
# pin test asserts each against its source rather than trusting this copy (R6.7).
# 198's module slot is the one number here that is NOT derived: the business-module table is
# capped by `config.max_results`, an operator setting, so deriving from it would make this ceiling a
# function of configuration — a repo with max_results=500 would buy 500 calls. 12 is a ratified
# budget constant instead, and the pin test asserts exactly that rather than a false derivation.
MODULE_LABEL_BUDGET = 12
SLOT_LIMITS: Mapping[str, int] = {
    SLOT_HEADLINE: 6,
    SLOT_LAYER: 12,
    SLOT_STEP: 15,
    SLOT_MODULE: MODULE_LABEL_BUDGET,
}
MAX_PROSE_CALLS = sum(SLOT_LIMITS.values())

__all__ = [
    "MAX_PROSE_CALLS",
    "MODULE_LABEL_BUDGET",
    "SLOT_HEADLINE",
    "SLOT_LAYER",
    "SLOT_LIMITS",
    "SLOT_MODULE",
    "SLOT_STEP",
    "ProseRequest",
    "ProseRun",
    "ProseWriter",
    "is_filler",
    "request_key",
]

_WORD = re.compile(r"[a-z0-9]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _words(text: str) -> set[str]:
    """Lowercase word tokens, splitting camel case and every separator a path can hold."""
    return set(_WORD.findall(_CAMEL.sub(" ", text).lower()))


def is_filler(text: str, *names: str) -> bool:
    """True when ``text`` says nothing the ``names`` already say — 109 C1's rule, for prose.

    Filler is prose that only restates the identifiers it was handed, and a bare figure counts too:
    prose has to add a *word*, not only a number. Blank text is filler by the same test.
    """
    own = _words(text) - _words(" ".join(names))
    return not any(word.isalpha() for word in own)


@dataclass(frozen=True)
class ProseRequest:
    """One prose slot's structural context, and the sentence it already has without a model.

    ``default`` is complete on its own — an impl that declines leaves a working map. ``names`` are
    the identifiers the answer must not merely restate (``is_filler``); ``facts`` is the wider
    context an impl may show a model. ``previous`` chains a step to the one before it.
    """

    slot: str
    key: str
    default: str
    facts: tuple[tuple[str, str], ...] = ()
    names: tuple[str, ...] = ()
    previous: str = ""


def request_key(request: ProseRequest) -> str:
    """A stable identity for a request — what a run memoises and an impl caches on (AC3).

    Everything that can change the answer, nothing that cannot, joined in a fixed order so two
    identical slots agree and a reorder upstream is a hit rather than a fresh call.
    """
    return "\n".join(
        [
            request.slot,
            request.key,
            request.default,
            request.previous,
            *(f"{label}={value}" for label, value in request.facts),
        ]
    )


class ProseWriter(Protocol):
    """The 117 seam: write one prose slot, or return ``""`` to decline and keep the default."""

    def write(self, request: ProseRequest) -> str: ...


class ProseRun:
    """One build's prose budget: memoised, counted, capped, and failure-tolerant (task 117).

    Deliberately stateful — a per-run call ceiling cannot be a pure function (AC5) — but still
    deterministic: identical requests in an identical order spend an identical budget. Memoisation
    is load-bearing, not an optimisation: the artifact and the dataset build the same layer table,
    so without it every layer description would be paid for twice.
    """

    def __init__(self, writer: ProseWriter | None, *, limits: Mapping[str, int] | None = None):
        self._writer = writer
        self._limits = dict(SLOT_LIMITS if limits is None else limits)
        self._answers: dict[str, str] = {}
        self._spent: dict[str, int] = {}
        self._declined = 0

    @property
    def enabled(self) -> bool:
        """Whether a writer is injected at all; ``False`` is the deterministic default path."""
        return self._writer is not None

    @property
    def writer(self) -> ProseWriter | None:
        """The injected writer itself, so 209 can name what ran. ``None`` is the default path.

        The object, not a name: this module imports nothing from ``code_atlas.onboarding``, so
        spelling the no-writer sentinel here would be a second copy of it.
        """
        return self._writer

    @property
    def calls(self) -> int:
        """How many times the writer was actually asked — a memo hit is not a call (AC5)."""
        return sum(self._spent.values())

    @property
    def declined(self) -> int:
        """Slots left at their structural default because a slot's ceiling was reached (AC5)."""
        return self._declined

    def text(self, request: ProseRequest) -> str:
        """This slot's prose: the writer's when usable, else the structural default.

        Order of precedence is the guard order: no writer, then the memo, then the ceiling, then the
        call — so a failing or filler answer can never cost the map a field (AC4/AC6).
        """
        if self._writer is None:
            return request.default
        identity = request_key(request)
        memo = self._answers.get(identity)
        if memo is not None:
            return memo
        limit = self._limits.get(request.slot, 0)
        if self._spent.get(request.slot, 0) >= limit:
            self._declined += 1
            return request.default
        self._spent[request.slot] = self._spent.get(request.slot, 0) + 1
        answer = self._ask(request)
        self._answers[identity] = answer
        return answer

    def _ask(self, request: ProseRequest) -> str:
        """Ask the writer, and treat a raise, a refusal and filler as the same answer: default."""
        try:
            written = self._writer.write(request)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001 — AC4: ANY seam failure degrades, never half-writes a map
            return request.default
        text = " ".join(str(written).split())
        if is_filler(text, request.key, *request.names):
            return request.default
        return text
