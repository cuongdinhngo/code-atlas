"""Task 117 — the opt-in LLM prose writer behind the 117 seam.

Hermetic like 090/091: the ``anthropic`` client is a hand-rolled fake, so the LLM path never
executes and no network is touched. The proving test drives a second run against a client that
*raises if called*, so a green result proves the prose came from the content-hash cache (AC3).
Core confinement is covered by 090's filesystem sweep and 117's own (``test_onboarding_prose``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from code_atlas.onboarding.prose import (
    SLOT_HEADLINE,
    SLOT_LAYER,
    SLOT_LIMITS,
    SLOT_STEP,
    ProseRequest,
    ProseRun,
)
from onboarding_llm.cache import ContentHashCache
from onboarding_llm.prose import MAX_FACTS_SHOWN, LLMProseWriter, prompt

LAYER = ProseRequest(
    slot=SLOT_LAYER,
    key="Services",
    default="Application services and use-cases that coordinate domain logic.",
    facts=(("modules", "4"), ("fan in", "9")),
    names=("Services", "app/service/Billing.aa"),
)
STEP = ProseRequest(
    slot=SLOT_STEP,
    key="2",
    default="Covers 3 module(s).",
    facts=(("layer", "Services"), ("modules covered", "3")),
    names=("Services", "app/service/Billing.aa"),
    previous="The tour began at the request surface.",
)


class _FakeBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = [_FakeBlock(text)]


class _Client:
    """Returns a distinct answer per slot and counts calls."""

    def __init__(self) -> None:
        self.calls = 0
        self.prompts: list[str] = []

    @property
    def messages(self) -> _Client:
        return self

    def create(self, **kwargs: object) -> _FakeMessage:
        self.calls += 1
        messages = kwargs["messages"]  # type: ignore[index]
        self.prompts.append(messages[0]["content"])
        return _FakeMessage("  A written sentence\n  about this slot in particular.  ")


class _Exploding:
    """Raises if the model is reached at all — proves an answer came from the cache."""

    @property
    def messages(self) -> _Exploding:
        return self

    def create(self, **kwargs: object) -> _FakeMessage:
        raise AssertionError("the model was called; the cache should have answered")


class _Empty:
    """A refusal or a truncation — nothing came back."""

    @property
    def messages(self) -> _Empty:
        return self

    def create(self, **kwargs: object) -> _FakeMessage:
        return _FakeMessage("")


def _writer(client: object, path: Path) -> LLMProseWriter:
    return LLMProseWriter(client, "a-test-model", ContentHashCache(path))  # type: ignore[arg-type]


def test_ac3_a_second_run_answers_from_the_cache_without_reaching_a_model(tmp_path: Path) -> None:
    """AC3 proving test — the committed cache is what makes a build replayable."""
    cache = tmp_path / "prose.json"
    client = _Client()
    first = _writer(client, cache).write(LAYER)
    assert client.calls == 1 and first == "A written sentence about this slot in particular."
    assert _writer(_Exploding(), cache).write(LAYER) == first


def test_ac3_an_edit_to_any_fact_is_a_miss(tmp_path: Path) -> None:
    """AC3 — the key folds in every input that can change the answer, so an edit re-asks."""
    cache = tmp_path / "prose.json"
    client = _Client()
    writer = _writer(client, cache)
    writer.write(LAYER)
    writer.write(ProseRequest(**{**LAYER.__dict__, "facts": (("modules", "5"), ("fan in", "9"))}))
    assert client.calls == 2
    # A changed previous step is an edit too: the narrative refers to it.
    writer.write(STEP)
    writer.write(ProseRequest(**{**STEP.__dict__, "previous": "Somewhere else entirely."}))
    assert client.calls == 4


def test_ac3_the_cache_file_is_sorted_key_json_with_no_timestamp(tmp_path: Path) -> None:
    """AC3 — byte-stable and committable: the same content yields the same file, in any order."""
    forward, backward = tmp_path / "a.json", tmp_path / "b.json"
    for path, order in ((forward, (LAYER, STEP)), (backward, (STEP, LAYER))):
        writer = _writer(_Client(), path)
        for request in order:
            writer.write(request)
    assert forward.read_text(encoding="utf-8") == backward.read_text(encoding="utf-8")
    entries = json.loads(forward.read_text(encoding="utf-8"))
    assert list(entries) == sorted(entries)
    assert all(set(entry) == {"prose", "slot", "model"} for entry in entries.values())


def test_a_refusal_declines_and_is_never_cached(tmp_path: Path) -> None:
    """AC4's impl half — an empty answer declines, so the run keeps the structural default."""
    cache = tmp_path / "prose.json"
    assert _writer(_Empty(), cache).write(LAYER) == ""
    assert not cache.exists(), "a blank answer must not be written to the cache"
    assert ProseRun(_writer(_Empty(), cache)).text(LAYER) == LAYER.default


def test_an_unknown_slot_is_declined_rather_than_guessed_at(tmp_path: Path) -> None:
    """A slot this impl has no prompt for gets no prose — never a prompt chosen at random."""
    client = _Client()
    unknown = ProseRequest(slot="something-new", key="k", default="a default")
    assert _writer(client, tmp_path / "prose.json").write(unknown) == ""
    assert client.calls == 0


def test_the_prompt_carries_the_facts_the_default_and_the_previous_step(tmp_path: Path) -> None:
    """The prompt is the request, rendered — structural facts only, never file contents."""
    client = _Client()
    _writer(client, tmp_path / "prose.json").write(STEP)
    text = client.prompts[0]
    assert "layer: Services" in text and "modules covered: 3" in text
    assert STEP.default in text
    assert "Previous step:" in text and STEP.previous in text


def test_the_prompt_fact_list_is_capped_and_says_how_many_it_dropped() -> None:
    """Every list in this project is capped, and a cap that hides its own size is a silent lie."""
    many = tuple((f"fact {index}", str(index)) for index in range(MAX_FACTS_SHOWN + 4))
    text = prompt(ProseRequest(SLOT_HEADLINE, "coverage", "a default", facts=many))
    assert f"fact {MAX_FACTS_SHOWN - 1}" in text
    assert f"fact {MAX_FACTS_SHOWN}" not in text
    assert "...and 4 more facts" in text


@pytest.mark.parametrize("slot", sorted(SLOT_LIMITS))
def test_every_slot_the_seam_declares_has_a_prompt_here(slot: str, tmp_path: Path) -> None:
    """R6.7 — derived from the seam's own slot vocabulary, so a new slot cannot ship promptless."""
    client = _Client()
    request = ProseRequest(slot=slot, key="k", default="a default", facts=(("a", "1"),))
    assert _writer(client, tmp_path / f"{slot}.json").write(request)
    assert client.calls == 1
