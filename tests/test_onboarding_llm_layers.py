"""Task 091 — the opt-in LLM layer-name refiner behind the 091 seam.

Hermetic like 090: the ``anthropic`` client is a hand-rolled fake, so the LLM path never executes
and no network is touched (AC1). The proving test drives a second run against a client that *raises
if called*, so a green result proves the rename came from the content-hash cache (deterministic).
The AC3 test proves that with refinement off the layer output is byte-identical to 084. Confinement
is covered by 090's filesystem sweep (``test_no_core_module_imports_an_llm``), which greps all of
``code_atlas/`` — this module adds no core file, so that guard already covers 091.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from code_atlas.onboarding.layers import (
    IdentityLayerRefiner,
    assign_layers,
    refine_layers,
)
from code_atlas.onboarding.metrics import compute_metrics
from onboarding_llm.cache import ContentHashCache
from onboarding_llm.layer_refiner import LLMLayerRefiner

# A flat, directory-less repo → 084 falls back to dependency-direction band names (the weak case 091
# targets): a.php (source) → b.php (mixed) → c.php (sink).
NODES = [("A", "a.php"), ("B", "b.php"), ("C", "c.php")]
EDGES = [("A", "B"), ("B", "C")]

# A namespaced repo → 084's dominant-subtree names the layers after real directories; nothing weak.
NS_NODES = [("A", "src/Http/A.php"), ("B", "src/Domain/B.php"), ("C", "src/Infra/C.php")]
NS_EDGES = [("A", "B"), ("B", "C")]


def _metrics(nodes: list[tuple[str, str]], edges: list[tuple[str, str]]):
    return compute_metrics(nodes, edges)


class _FakeBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = [_FakeBlock(text)]


def _heuristic_name(kwargs: object) -> str:
    """Pull the ``Current heuristic layer name:`` line out of the injected prompt."""
    messages = kwargs["messages"]  # type: ignore[index]
    content = messages[0]["content"]
    for line in content.splitlines():
        if line.startswith("Current heuristic layer name:"):
            return line.split(":", 1)[1].strip()
    return "?"


class _NamingClient:
    """Returns a distinct name per layer (``The <layer> tier``) and counts calls."""

    def __init__(self) -> None:
        self.calls = 0

    @property
    def messages(self) -> _NamingClient:
        return self

    def create(self, **kwargs: object) -> _FakeMessage:
        self.calls += 1
        return _FakeMessage(f"The {_heuristic_name(kwargs)} tier")


class _EmptyClient:
    """Simulates a refusal/truncation — returns nothing."""

    @property
    def messages(self) -> _EmptyClient:
        return self

    def create(self, **kwargs: object) -> _FakeMessage:
        return _FakeMessage("")


class _RaisingClient:
    """Fails loudly if called — used to prove a run is served entirely from cache."""

    @property
    def messages(self) -> _RaisingClient:
        return self

    def create(self, **kwargs: object) -> _FakeMessage:
        raise AssertionError("the LLM was called on what should have been a cache hit")


def _refiner(client: object, cache_path: Path) -> LLMLayerRefiner:
    return LLMLayerRefiner(client, "claude-opus-5", ContentHashCache(cache_path))  # type: ignore[arg-type]


def test_off_by_default_is_byte_identical_to_084(tmp_path: Path) -> None:
    """AC3 — the Identity default leaves 084's assignment byte-for-byte unchanged."""
    metrics = _metrics(NODES, EDGES)
    base = assign_layers(metrics)
    refined = refine_layers(base, metrics, IdentityLayerRefiner())
    assert refined.to_json() == base.to_json()


def test_empty_rename_map_returns_the_same_object(tmp_path: Path) -> None:
    """A refiner that proposes nothing is a pure no-op — the applier returns the input unchanged."""
    metrics = _metrics(NODES, EDGES)
    base = assign_layers(metrics)
    refined = refine_layers(base, metrics, _refiner(_EmptyClient(), tmp_path / "c.json"))
    assert refined is base  # nothing to apply → not even a rebuild


def test_llm_renames_weak_layers(tmp_path: Path) -> None:
    """The fallback direction-band layers get human names; coverage and count are preserved."""
    metrics = _metrics(NODES, EDGES)
    base = assign_layers(metrics)
    assert base.method == "dependency-direction-fallback"
    assert set(base.layers) == {"source", "mixed", "sink"}

    refined = refine_layers(base, metrics, _refiner(_NamingClient(), tmp_path / "c.json"))
    assert set(refined.layers) == {"The source tier", "The mixed tier", "The sink tier"}
    assert {m.module for m in refined.modules} == {"a.php", "b.php", "c.php"}  # coverage intact
    assert refined.method == base.method  # method pin untouched (091 renames names only)


def test_ranks_are_renormalised_and_order_preserved(tmp_path: Path) -> None:
    """Renaming keeps the dependency order (source-like first) and yields contiguous 0..N ranks."""
    metrics = _metrics(NODES, EDGES)
    refined = refine_layers(
        assign_layers(metrics), metrics, _refiner(_NamingClient(), tmp_path / "c.json")
    )
    ranks = sorted({m.rank for m in refined.modules})
    assert ranks == list(range(len(refined.layers)))
    first = next(m.layer for m in refined.modules if m.module == "a.php")  # the source module
    assert refined.layers[0] == first  # most source-like layer still leads


def test_named_layers_are_left_alone(tmp_path: Path) -> None:
    """Dominant-subtree layers already carry real directory names — the LLM is never consulted."""
    metrics = _metrics(NS_NODES, NS_EDGES)
    base = assign_layers(metrics)
    assert base.method == "dominant-subtree"
    client = _NamingClient()
    refined = refine_layers(base, metrics, _refiner(client, tmp_path / "c.json"))
    assert refined.to_json() == base.to_json()
    assert client.calls == 0  # no weak layer → no LLM call


def test_cache_replays_without_a_second_call(tmp_path: Path) -> None:
    """AC2 — a second run over the same layers is served from the committed cache, so a client that
    raises if called still produces the identical rename."""
    metrics = _metrics(NODES, EDGES)
    base = assign_layers(metrics)
    cache_path = tmp_path / "layers.json"
    first = refine_layers(base, metrics, _refiner(_NamingClient(), cache_path))

    second = refine_layers(base, metrics, _refiner(_RaisingClient(), cache_path))  # would raise

    assert second.to_json() == first.to_json()


def test_empty_generation_is_skipped_and_not_cached(tmp_path: Path) -> None:
    """A refusal/truncation leaves the layer name unchanged and writes nothing, so a one-off API
    hiccup cannot poison a committed cache."""
    metrics = _metrics(NODES, EDGES)
    base = assign_layers(metrics)
    cache_path = tmp_path / "layers.json"

    refined = refine_layers(base, metrics, _refiner(_EmptyClient(), cache_path))
    assert refined.to_json() == base.to_json()  # unchanged
    assert not cache_path.exists()  # the blank was not persisted

    later = refine_layers(base, metrics, _refiner(_NamingClient(), cache_path))
    assert set(later.layers) == {"The source tier", "The mixed tier", "The sink tier"}


def test_malformed_cache_entry_is_a_miss_not_a_crash(tmp_path: Path) -> None:
    """A hand-edited entry missing ``layer_name`` regenerates instead of raising a ``KeyError``."""
    metrics = _metrics(NODES, EDGES)
    base = assign_layers(metrics)
    cache_path = tmp_path / "layers.json"
    refine_layers(base, metrics, _refiner(_NamingClient(), cache_path))

    entries = json.loads(cache_path.read_text(encoding="utf-8"))
    entries = {key: {"old": value.get("old", "?")} for key, value in entries.items()}  # drop names
    cache_path.write_text(json.dumps(entries), encoding="utf-8")

    refined = refine_layers(base, metrics, _refiner(_NamingClient(), cache_path))  # miss → regen
    assert set(refined.layers) == {"The source tier", "The mixed tier", "The sink tier"}


def test_cache_file_is_committable_sorted_json(tmp_path: Path) -> None:
    """The on-disk cache is byte-stable, sorted-key JSON with no timestamps (R4.2 — committable)."""
    metrics = _metrics(NODES, EDGES)
    cache_path = tmp_path / "layers.json"
    refine_layers(assign_layers(metrics), metrics, _refiner(_NamingClient(), cache_path))

    text = cache_path.read_text(encoding="utf-8")
    entries = json.loads(text)
    assert text == json.dumps(entries, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    assert all("layer_name" in entry and "old" in entry for entry in entries.values())


def test_build_layer_refiner_is_off_by_default() -> None:
    """The opt-in gate: no ``CA_ONBOARDING_LAYER_REFINER`` means the deterministic default (None).

    Imports the entry point, which pulls ``code_atlas.main`` (needs POSIX ``fcntl``); proven in
    Docker, skipped on the Windows dev host per the known platform exclusion (AGENTS.md)."""
    try:
        from code_atlas.config import load_config
        from onboarding_llm.server import build_layer_refiner
    except ImportError:
        pytest.skip("code_atlas.main needs a POSIX host (fcntl); proven in Docker")

    config = load_config(Path.cwd())
    assert build_layer_refiner(config, {}) is None
    assert build_layer_refiner(config, {"CA_ONBOARDING_LAYER_REFINER": "heuristic"}) is None
