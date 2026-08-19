"""Opt-in LLM summarizer for Phase-3 onboarding (task 090, M12).

This package lives **outside** ``code_atlas/`` on purpose (mirroring ``adapters/``): it is the one
and only place an LLM touches this project, injected through the 085 ``Summarizer`` seam. The core
never imports it — an operator opts in by installing the ``llm`` extra, setting
``CA_ONBOARDING_SUMMARIZER``, and running the ``code-atlas-llm`` entry point
(:func:`onboarding_llm.server.run`). Deterministic replay comes from a content-hash cache, so a
committed cache keeps runs and diffs stable (R4.2).
"""

from onboarding_llm.cache import ContentHashCache
from onboarding_llm.summarizer import DEFAULT_MODEL, LLMSummarizer

__all__ = ["ContentHashCache", "LLMSummarizer", "DEFAULT_MODEL"]
