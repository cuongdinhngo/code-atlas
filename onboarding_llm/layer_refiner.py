"""The LLM ``LayerRefiner`` impl behind the 091 seam (M12).

``LLMLayerRefiner`` proposes a better human name for each **weak** layer — the generic
dependency-direction bands (source/sink/mixed/isolated) and ``(root)`` that 084 falls back to when a
repo's namespaces are uninformative (flat legacy PHP, the anchor's hard case). It returns a
``{old_layer: new_layer}`` rename map; the core applies it (``refine_layers``) without ever
re-grouping modules, so coverage stays intact. Named layers from the dominant-subtree method are
left alone. Every name is memoised in a content-hash cache keyed on the layer's membership, so a
committed cache replays byte-for-byte (R4.2). ``anthropic`` is imported lazily by the factory alone,
so importing this module pulls in no LLM and touches no network (R4.1: never runs in the CI gate).
"""

from __future__ import annotations

from collections.abc import Mapping

from code_atlas.onboarding.layers import LayerAssignment
from code_atlas.onboarding.metrics import GraphMetrics
from onboarding_llm.cache import ContentHashCache, content_key
from onboarding_llm.client import Client, first_text

# Top tier for the layer-refinement pass per PHASE3 §4 (090's per-module summaries use a mid tier).
# Override with CA_ONBOARDING_LLM_LAYER_MODEL. Model ids: claude-api skill, Current Models.
DEFAULT_LAYER_MODEL = "claude-opus-5"

# Room for a model's adaptive thinking on top of a short name (thinking counts against the budget).
MAX_TOKENS = 2048

# Bump to invalidate cached names by hand; the prompt text and MAX_TOKENS are folded into the key.
PROMPT_VERSION = "1"

# The layers 084 emits when namespaces are uninformative — the only ones worth an LLM name. Mirrors
# _FALLBACK_ORDER + _ROOT_LAYER in layers.py (a real directory name is already good enough).
_WEAK = frozenset({"source", "sink", "mixed", "isolated", "(root)"})

# Cap how many member paths go into one prompt; the cache key still folds in the FULL membership, so
# two layers that differ only past the cap get distinct entries.
_MAX_MEMBERS_IN_PROMPT = 40

_SYSTEM = (
    "You name one architectural layer of a codebase for an onboarding guide. Given the files it "
    "contains and their dependency roles, reply with a short layer name in Title Case (1-3 words, "
    "e.g. 'Controllers', 'Domain Services', 'Data Access'). Output only that name — no preamble, "
    "no punctuation, no quotes."
)


class LLMLayerRefiner:
    """A ``LayerRefiner`` (091 seam) that renames weak layers via Claude, cached by membership."""

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

    def refine_names(
        self, assignment: LayerAssignment, metrics: GraphMetrics
    ) -> Mapping[str, str]:
        """Propose a name for each weak layer; a good directory-derived name is left unchanged."""
        members: dict[str, list[str]] = {}
        for module in assignment.modules:
            members.setdefault(module.layer, []).append(module.module)
        direction_of = {metric.key: metric.direction for metric in metrics.modules}
        renames: dict[str, str] = {}
        for layer in assignment.layers:
            if layer not in _WEAK:
                continue
            name = self._name_for(layer, sorted(members.get(layer, [])), direction_of)
            if name and name != layer:
                renames[layer] = name
        return renames

    def _name_for(self, layer: str, mods: list[str], direction_of: Mapping[str, str]) -> str:
        key = content_key(
            layer, "\n".join(mods), self._model, self._prompt_version, _SYSTEM, str(MAX_TOKENS)
        )
        cached = self._cache.get(key)
        if cached and cached.get("layer_name"):  # a missing/empty entry is a miss, not a KeyError
            return cached["layer_name"]
        name = self._generate(layer, mods, direction_of)
        if not name:  # a refusal or truncation gives nothing — skip, never cache the blank
            return ""
        self._cache.put(key, {"layer_name": name, "old": layer, "model": self._model})
        return name

    def _generate(self, layer: str, mods: list[str], direction_of: Mapping[str, str]) -> str:
        # Only params every model and SDK version accept — the model is operator-configurable, so no
        # output_config/thinking knob that a given model or an older `anthropic` could reject.
        message = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _prompt(layer, mods, direction_of)}],
        )
        return _clean(first_text(message))


def _prompt(layer: str, mods: list[str], direction_of: Mapping[str, str]) -> str:
    """One weak layer's members and their roles — deterministic given identical membership."""
    shown = mods[:_MAX_MEMBERS_IN_PROMPT]
    lines = [f"- {path} ({direction_of.get(path, 'unknown')})" for path in shown]
    if len(mods) > len(shown):
        lines.append(f"- ...and {len(mods) - len(shown)} more")
    return f"Current heuristic layer name: {layer}\nFiles in this layer:\n" + "\n".join(lines)


def _clean(text: str) -> str:
    """The first non-empty line, stripped of any wrapping quotes/backticks; a name is one line."""
    for line in text.splitlines():
        stripped = line.strip().strip("\"'`").strip()
        if stripped:
            return stripped
    return ""
