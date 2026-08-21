"""Opt-in LLM enrichment for Phase-3 onboarding (tasks 090/091, M12).

This package lives **outside** ``code_atlas/`` on purpose (mirroring ``adapters/``): it is the one
and only place an LLM touches this project, injected through the 085 ``Summarizer`` seam (090),
the 091 ``LayerRefiner`` seam and the 117 ``ProseWriter`` seam. The core never imports it — an
operator opts in by installing the ``llm`` extra, setting ``CA_ONBOARDING_SUMMARIZER`` /
``CA_ONBOARDING_LAYER_REFINER`` / ``CA_ONBOARDING_PROSE``, and running
the ``code-atlas-llm`` entry point (:func:`onboarding_llm.server.run`). Deterministic replay comes
from a content-hash cache, so a committed cache keeps runs and diffs stable (R4.2).
"""

from onboarding_llm.cache import ContentHashCache
from onboarding_llm.layer_refiner import DEFAULT_LAYER_MODEL, LLMLayerRefiner
from onboarding_llm.prose import DEFAULT_PROSE_MODEL, LLMProseWriter
from onboarding_llm.summarizer import DEFAULT_MODEL, LLMSummarizer

__all__ = [
    "ContentHashCache",
    "LLMSummarizer",
    "DEFAULT_MODEL",
    "LLMLayerRefiner",
    "DEFAULT_LAYER_MODEL",
    "LLMProseWriter",
    "DEFAULT_PROSE_MODEL",
]
