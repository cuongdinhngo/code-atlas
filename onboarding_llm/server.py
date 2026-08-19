"""The ``code-atlas-llm`` entry point (task 090) — the core server with the LLM summarizer injected.

This lives outside ``code_atlas/`` so the core never imports the LLM (R4.1). It reuses the core's
``build_server`` and ``load_config`` unchanged and injects an :class:`LLMSummarizer` through the 085
seam **only when opted in**: ``CA_ONBOARDING_SUMMARIZER`` must be ``llm``/``claude`` (otherwise this
binary behaves exactly like ``code-atlas`` — the deterministic default). ``anthropic`` is imported
lazily here, so nothing pulls the SDK or the network unless an operator opts in.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from code_atlas.config import Config, load_config
from code_atlas.main import build_server
from code_atlas.onboarding.summary import Summarizer
from onboarding_llm.cache import ContentHashCache
from onboarding_llm.summarizer import DEFAULT_MODEL, LLMSummarizer

# The opt-in switch and its knobs. Off/other value → None → the deterministic StructuralSummarizer.
SUMMARIZER_ENV = "CA_ONBOARDING_SUMMARIZER"
MODEL_ENV = "CA_ONBOARDING_LLM_MODEL"
CACHE_ENV = "CA_ONBOARDING_LLM_CACHE"
_ENABLED = frozenset({"llm", "claude"})

# Regenerable cache location by default (gitignored, like 088's onboarding cache); point CACHE_ENV
# at a tracked path to commit the summaries and make every run replay from the repo.
DEFAULT_CACHE = ".code-atlas/onboarding-llm-cache.json"


def build_summarizer(config: Config, env: Mapping[str, str]) -> Summarizer | None:
    """The opt-in ``Summarizer``: an :class:`LLMSummarizer` when enabled, else ``None`` (off)."""
    if env.get(SUMMARIZER_ENV, "").strip().lower() not in _ENABLED:
        return None
    model = env.get(MODEL_ENV, "").strip() or DEFAULT_MODEL
    cache_path = config.root / (env.get(CACHE_ENV, "").strip() or DEFAULT_CACHE)
    import anthropic  # deferred: optional `llm` extra, never imported by the core or the CI gate

    return LLMSummarizer(anthropic.Anthropic(), model, ContentHashCache(cache_path))


def run() -> None:
    """Serve this repo over stdio with the LLM summarizer injected when opted in."""
    config = load_config(Path.cwd(), os.environ)
    build_server(config, build_summarizer(config, os.environ)).run()


if __name__ == "__main__":
    run()
