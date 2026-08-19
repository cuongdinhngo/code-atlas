"""Task 090 — the opt-in LLM summarizer behind the 085 seam.

Every test here is hermetic: the ``anthropic`` client is a hand-rolled fake, so the LLM path never
executes and no network is touched (AC1 — "stub-only in the CI gate"). The proving test drives a
second run against a client that *raises if called*, so a green result proves the summary came from
the content-hash cache, byte-identical (AC2). A filesystem confinement check proves the core never
imports the LLM (AC1/AC3), matching the SQL/language-confinement guards.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from code_atlas.onboarding.metrics import NodeMetric
from code_atlas.onboarding.summary import (
    NodeFacts,
    StructuralSummarizer,
    summaries_as_dict,
    summarize_modules,
)
from onboarding_llm.cache import ContentHashCache
from onboarding_llm.summarizer import LLMSummarizer

CORE = Path(__file__).resolve().parent.parent / "code_atlas"
# `import anthropic` / `from onboarding_llm ...` in any form — a leak of the LLM into the core.
LLM_IMPORT = re.compile(r"^\s*(?:from|import)\s+(anthropic|onboarding_llm)\b", re.MULTILINE)

FACTS = [
    NodeFacts("class Foo", "The user model.", NodeMetric("app/Foo.php", 1, 2, "mixed")),
    NodeFacts("class Bar", "A leaf helper.", NodeMetric("app/Bar.php", 3, 0, "sink")),
]


class _FakeBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = [_FakeBlock(text)]


class _RecordingClient:
    """A stand-in for ``anthropic.Anthropic`` that returns a canned sentence and counts calls."""

    def __init__(self, text: str = "A generated one-liner.") -> None:
        self._text = text
        self.calls = 0

    @property
    def messages(self) -> _RecordingClient:
        return self

    def create(self, **kwargs: object) -> _FakeMessage:
        self.calls += 1
        return _FakeMessage(self._text)


class _RaisingClient:
    """Fails loudly if the LLM is called — used to prove a run is served entirely from cache."""

    @property
    def messages(self) -> _RaisingClient:
        return self

    def create(self, **kwargs: object) -> _FakeMessage:
        raise AssertionError("the LLM was called on what should have been a cache hit")


def _summarizer(client: object, cache_path: Path) -> LLMSummarizer:
    return LLMSummarizer(client, "claude-sonnet-5", ContentHashCache(cache_path))  # type: ignore[arg-type]


def test_llm_overrides_only_the_docline(tmp_path: Path) -> None:
    """The LLM sets ``docline``; signature and the 083 role stay structural (091 owns role)."""
    client = _RecordingClient("Foo is the user model.")
    summary = _summarizer(client, tmp_path / "cache.json").summarize(FACTS[0])
    structural = StructuralSummarizer().summarize(FACTS[0])

    assert summary.docline == "Foo is the user model."
    assert summary.signature == structural.signature  # verbatim
    assert summary.role == structural.role == "connector"  # mixed → connector, unchanged
    assert client.calls == 1


def test_cache_replays_without_a_second_call(tmp_path: Path) -> None:
    """Proving test (AC2): a second run over the same facts is served from the committed cache, so a
    client that raises if called returns the identical ``Summary`` byte-for-byte."""
    cache_path = tmp_path / "cache.json"
    first = _summarizer(_RecordingClient("Cached line."), cache_path).summarize(FACTS[0])

    second = _summarizer(_RaisingClient(), cache_path).summarize(FACTS[0])  # would raise on a miss

    assert second.to_json() == first.to_json()
    assert second.docline == "Cached line."


def test_empty_generation_falls_back_and_is_not_cached(tmp_path: Path) -> None:
    """A refusal or truncation gives an empty string: fall back to the structural docline and do NOT
    cache the blank, so a one-off API hiccup can't poison a committed summary."""
    cache_path = tmp_path / "cache.json"
    structural = StructuralSummarizer().summarize(FACTS[0])

    first = _summarizer(_RecordingClient(""), cache_path).summarize(FACTS[0])
    assert first.docline == structural.docline == "The user model."  # structural fallback
    assert not cache_path.exists()  # nothing was written — the blank is not persisted

    # A later run with a working client still generates a real summary (the blank did not stick).
    second = _summarizer(_RecordingClient("A real line."), cache_path).summarize(FACTS[0])
    assert second.docline == "A real line."


def test_malformed_cache_entry_is_a_miss_not_a_crash(tmp_path: Path) -> None:
    """A hand-edited entry missing ``docline`` regenerates instead of raising a ``KeyError``."""
    import json

    cache_path = tmp_path / "cache.json"
    _summarizer(_RecordingClient("Original."), cache_path).summarize(FACTS[0])
    entries = json.loads(cache_path.read_text(encoding="utf-8"))
    (only_key,) = entries
    entries[only_key] = {"module": "app/Foo.php"}  # docline dropped, as a bad edit would leave it
    cache_path.write_text(json.dumps(entries), encoding="utf-8")

    summary = _summarizer(_RecordingClient("Regenerated."), cache_path).summarize(FACTS[0])
    assert summary.docline == "Regenerated."  # miss → regenerate, no KeyError


def test_cache_file_is_committable_sorted_json(tmp_path: Path) -> None:
    """The on-disk cache is byte-stable, sorted-key JSON with no timestamps (R4.2 — committable)."""
    import json

    cache_path = tmp_path / "cache.json"
    _summarizer(_RecordingClient(), cache_path).summarize(FACTS[0])
    text = cache_path.read_text(encoding="utf-8")
    entries = json.loads(text)

    assert text == json.dumps(entries, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    assert list(entries.values())[0]["module"] == "app/Foo.php"


def test_llm_summarizer_plugs_into_the_core_seam(tmp_path: Path) -> None:
    """It is a drop-in ``Summarizer`` for the 085 enrichment/presentation split — the injection 090
    is for. Presentation reflects the LLM's doclines, ordered stably by key."""
    llm = _summarizer(_RecordingClient("Same line."), tmp_path / "cache.json")
    rendered = summaries_as_dict(summarize_modules(FACTS, llm))
    doclines = {row["docline"] for row in rendered["summaries"]}

    assert doclines == {"Same line."}
    assert [row["module"] if "module" in row else row["key"] for row in rendered["summaries"]] == [
        "app/Bar.php",
        "app/Foo.php",
    ]  # key-sorted, deterministic


@pytest.mark.parametrize("module", sorted(CORE.rglob("*.py")), ids=lambda p: p.name)
def test_no_core_module_imports_an_llm(module: Path) -> None:
    """AC1/AC3 — the core never imports the LLM SDK or the opt-in package, so the LLM path cannot
    execute in the CI gate and default behaviour is unchanged (R4.1)."""
    found = LLM_IMPORT.findall(module.read_text(encoding="utf-8"))
    assert not found, (
        f"{module.relative_to(CORE.parent)} imports {sorted(set(found))} — the LLM stays outside "
        "code_atlas/ (task 090, R4.1); inject it through build_server(config, summarizer)"
    )


def test_the_confinement_guard_has_something_to_check() -> None:
    """Guards the guard: a broken glob or regex would pass the sweep above vacuously."""
    assert len(list(CORE.rglob("*.py"))) > 40
    assert LLM_IMPORT.search("import anthropic")
    assert LLM_IMPORT.search("from onboarding_llm import x")


def test_build_summarizer_is_off_by_default() -> None:
    """R3 — the opt-in gate: no ``CA_ONBOARDING_SUMMARIZER`` means the deterministic default (None).

    Imports the entry point, which pulls ``code_atlas.main`` (needs POSIX ``fcntl``); proven in
    Docker, skipped on the Windows dev host per the known platform exclusion (AGENTS.md)."""
    try:
        from code_atlas.config import load_config
        from onboarding_llm.server import build_summarizer
    except ImportError:
        pytest.skip("code_atlas.main needs a POSIX host (fcntl); proven in Docker")

    config = load_config(Path.cwd())
    assert build_summarizer(config, {}) is None
    assert build_summarizer(config, {"CA_ONBOARDING_SUMMARIZER": "structural"}) is None
