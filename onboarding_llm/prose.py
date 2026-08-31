"""The LLM ``ProseWriter`` impl behind the 117 seam (M12).

``LLMProseWriter`` writes the three things the index cannot derive — a layer's responsibility
line, a tour step's narrative, and the wording of a headline fact — and nothing else. Each request
with a complete structural ``default``, so declining is always safe: return ``""`` and the map keeps
the deterministic sentence. Structural facts only; no file contents are ever sent (the ticket's own
out-of-scope line).

One system prompt per slot, and the memoisation key is the core's own ``request_key``, so a slot the
run already answered and a slot a previous run cached agree by construction (AC3). ``anthropic`` is
imported lazily by the factory alone, so importing this module pulls in no LLM and touches no
network — the CI gate never reaches a model (R4.1).
"""

from __future__ import annotations

from code_atlas.onboarding.prose import (
    SLOT_HEADLINE,
    SLOT_LAYER,
    SLOT_MODULE,
    SLOT_STEP,
    ProseRequest,
    request_key,
)
from onboarding_llm.cache import ContentHashCache, content_key
from onboarding_llm.client import Client, first_text

# Top tier: prose is the highest-judgment slot on the page (PHASE3 §4; 090's per-module
# summaries use a mid tier). Override with CA_ONBOARDING_LLM_PROSE_MODEL.
DEFAULT_PROSE_MODEL = "claude-opus-5"

# Room for a model's adaptive thinking on top of a few sentences (thinking counts against this).
MAX_TOKENS = 2048

# Bump to invalidate cached prose by hand; the prompt text and MAX_TOKENS fold into the key anyway.
PROMPT_VERSION = "1"

# How many fact lines one prompt may show. The key folds in the FULL request, so two slots differing
# only past this cap still get distinct entries (091's pattern).
MAX_FACTS_SHOWN = 12

_COMMON = (
    "You are writing one short piece of prose for an automatically generated codebase onboarding "
    "map. Every number, ranking and grouping on that map is already derived from a static index — "
    "you are given those facts and must not contradict, recompute or add to them. Never invent a "
    "file, directory, framework or language that is not in the facts. Do not restate a path or a "
    "name as if it were an explanation. Output only the prose: no preamble, no markdown, no quotes."
)

_SYSTEM = {
    SLOT_LAYER: (
        f"{_COMMON} Write ONE sentence describing what this architectural layer is responsible "
        "for, inferred from its members and their dependency roles."
    ),
    SLOT_STEP: (
        f"{_COMMON} Write TWO to FOUR sentences introducing this step of a guided reading order: "
        "what a reader will find here and why it comes at this point. If a previous step is given, "
        "connect to it in the first sentence."
    ),
    SLOT_HEADLINE: (
        f"{_COMMON} Rewrite this headline fact as one or two sentences that say what it MEANS for "
        "somebody new to the codebase. Keep every figure exactly as given."
    ),
    SLOT_MODULE: (
        f"{_COMMON} Name the business capability this directory holds, as a SHORT noun phrase of "
        "two to five words — a label for a table cell, not a sentence. Infer it from the facts "
        "given and nothing else; if they do not say what the capability is, answer with an empty "
        "string rather than guessing, and the directory name will stand."
    ),
}

__all__ = ["DEFAULT_PROSE_MODEL", "MAX_FACTS_SHOWN", "MAX_TOKENS", "LLMProseWriter"]


class LLMProseWriter:
    """A ``ProseWriter`` (117 seam) whose prose comes from Claude, cached by request content."""

    def __init__(
        self,
        client: Client,
        model: str,
        cache: ContentHashCache,
        *,
        prompt_version: str = PROMPT_VERSION,
    ) -> None:
        self._client = client
        self._model = model
        self._cache = cache
        self._prompt_version = prompt_version

    def write(self, request: ProseRequest) -> str:
        """This slot's prose from the cache, else from Claude; ``""`` declines and keeps default."""
        system = _SYSTEM.get(request.slot)
        if system is None:  # an unknown slot is declined, never guessed at
            return ""
        key = content_key(
            request_key(request), self._model, self._prompt_version, system, str(MAX_TOKENS)
        )
        cached = self._cache.get(key)
        if cached and cached.get("prose"):  # a missing/empty entry is a miss, not a KeyError
            return cached["prose"]
        prose = self._generate(request, system)
        if not prose:  # a refusal or truncation gives nothing — decline, never cache the blank
            return ""
        self._cache.put(key, {"prose": prose, "slot": request.slot, "model": self._model})
        return prose

    def _generate(self, request: ProseRequest, system: str) -> str:
        # Only params every model and SDK version accept — the model is operator-configurable, so no
        # output_config/thinking knob that a given model or an older `anthropic` could reject.
        message = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": prompt(request)}],
        )
        return " ".join(first_text(message).split())


def prompt(request: ProseRequest) -> str:
    """One slot's facts, one per line — deterministic given an identical request."""
    shown = request.facts[:MAX_FACTS_SHOWN]
    lines = [f"{label}: {value}" for label, value in shown]
    if len(request.facts) > len(shown):
        lines.append(f"...and {len(request.facts) - len(shown)} more facts")
    body = "\n".join(lines)
    previous = f"\n\nPrevious step:\n{request.previous}" if request.previous else ""
    return (
        f"Facts:\n{body}\n\nThe deterministic sentence this replaces "
        f"(keep every figure it states):\n{request.default}{previous}"
    )
