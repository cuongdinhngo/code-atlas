"""The ``code-atlas-llm`` entry point (tasks 090/091) — the core server with LLM enrichment added.

This lives outside ``code_atlas/`` so the core never imports the LLM (R4.1). It reuses the core's
``build_server`` and ``load_config`` unchanged and injects an :class:`LLMSummarizer` (085 seam) and
an :class:`LLMLayerRefiner` (091 seam) **only when opted in**: each has its own on/off switch
(``CA_ONBOARDING_SUMMARIZER`` / ``CA_ONBOARDING_LAYER_REFINER`` = ``llm``/``claude``); with neither
set this binary behaves exactly like ``code-atlas`` — the deterministic defaults. ``anthropic`` is
imported lazily here, so nothing pulls the SDK or the network unless an operator opts in.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from code_atlas.config import Config, load_config
from code_atlas.main import build_server
from code_atlas.onboarding.layers import LayerRefiner
from code_atlas.onboarding.summary import Summarizer
from onboarding_llm.cache import ContentHashCache
from onboarding_llm.layer_refiner import DEFAULT_LAYER_MODEL, LLMLayerRefiner
from onboarding_llm.summarizer import DEFAULT_MODEL, LLMSummarizer

# The opt-in switches and their knobs. Off/other value → None → the deterministic default.
SUMMARIZER_ENV = "CA_ONBOARDING_SUMMARIZER"
MODEL_ENV = "CA_ONBOARDING_LLM_MODEL"
CACHE_ENV = "CA_ONBOARDING_LLM_CACHE"
LAYER_REFINER_ENV = "CA_ONBOARDING_LAYER_REFINER"
LAYER_MODEL_ENV = "CA_ONBOARDING_LLM_LAYER_MODEL"
LAYER_CACHE_ENV = "CA_ONBOARDING_LLM_LAYER_CACHE"
_ENABLED = frozenset({"llm", "claude"})

# Regenerable cache locations by default (gitignored, like 088's onboarding cache); point the CACHE
# env at a tracked path to commit the results and make every run replay from the repo.
DEFAULT_CACHE = ".code-atlas/onboarding-llm-cache.json"
DEFAULT_LAYER_CACHE = ".code-atlas/onboarding-llm-layers.json"


def build_summarizer(config: Config, env: Mapping[str, str]) -> Summarizer | None:
    """The opt-in ``Summarizer``: an :class:`LLMSummarizer` when enabled, else ``None`` (off)."""
    if env.get(SUMMARIZER_ENV, "").strip().lower() not in _ENABLED:
        return None
    model = env.get(MODEL_ENV, "").strip() or DEFAULT_MODEL
    cache_path = config.root / (env.get(CACHE_ENV, "").strip() or DEFAULT_CACHE)
    import anthropic  # deferred: optional `llm` extra, never imported by the core or the CI gate

    return LLMSummarizer(anthropic.Anthropic(), model, ContentHashCache(cache_path))


def build_layer_refiner(config: Config, env: Mapping[str, str]) -> LayerRefiner | None:
    """The opt-in ``LayerRefiner``: an :class:`LLMLayerRefiner` when on, else ``None`` (off)."""
    if env.get(LAYER_REFINER_ENV, "").strip().lower() not in _ENABLED:
        return None
    model = env.get(LAYER_MODEL_ENV, "").strip() or DEFAULT_LAYER_MODEL
    cache_path = config.root / (env.get(LAYER_CACHE_ENV, "").strip() or DEFAULT_LAYER_CACHE)
    import anthropic  # deferred: optional `llm` extra, never imported by the core or the CI gate

    return LLMLayerRefiner(anthropic.Anthropic(), model, ContentHashCache(cache_path))


def run() -> None:
    """Serve this repo over stdio with the LLM enrichment injected when opted in."""
    config = load_config(Path.cwd(), os.environ)
    summarizer = build_summarizer(config, os.environ)
    layer_refiner = build_layer_refiner(config, os.environ)
    build_server(config, summarizer, layer_refiner).run()


if __name__ == "__main__":
    run()
