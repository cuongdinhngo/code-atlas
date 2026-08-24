"""Task 145 Phase A: ``artifact.json`` is a versioned published shape, not a free-form cache.

The adapter contract lives in ``tests/contract/``. This file is the same discipline for the
onboarding artifact a second renderer would read: a version, a pinned key-path set, and a
made-to-fail so a shape change that leaves ``ARTIFACT_VERSION`` where it is cannot go green.

The pin is taken over an artifact ``generate_onboarding`` actually writes, not over a hand-built
sample: ``summary`` is a free-form ``Mapping`` on the dataclass, so a sample can only pin the keys
the sample happens to carry. **What the fixture cannot reach is not pinned** — a path under an
empty ``mirrors.pairs`` or ``business_modules.containers`` has no row here.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from code_atlas.onboarding.artifact import (
    ARTIFACT_VERSION,
    LayerRow,
    ModulePage,
    OnboardingArtifact,
    cache_json,
)
from code_atlas.onboarding.layer_diagram import DiagramEdge
from code_atlas.onboarding.steps import TourStep
from code_atlas.onboarding.tour import TourStop
from code_atlas.tools import generate_onboarding
from tests.test_guided_tour import _cycle_repo

# Frozen at version 1. A bump earns its own entry in KEY_PATHS_BY_VERSION (AC2) — the pin is per
# version, so "bump without re-pinning" is red and "re-shape without bumping" is red.
V1_KEY_PATHS = frozenset(
    {
        "crossings",
        "crossings[].count",
        "crossings[].source",
        "crossings[].target",
        "diagram_edges",
        "diagram_edges[].count",
        "diagram_edges[].heuristic_only",
        "diagram_edges[].source",
        "diagram_edges[].target",
        "isolated",
        "layers",
        "layers[].description",
        "layers[].entry_points",
        "layers[].fan_in",
        "layers[].fan_out",
        "layers[].layer",
        "layers[].modules",
        "layers[].rank",
        "method",
        "omitted_dynamic",
        "pages",
        "pages[].docline",
        "pages[].fan_in",
        "pages[].fan_out",
        "pages[].file",
        "pages[].incoming",
        "pages[].index",
        "pages[].layer",
        "pages[].of",
        "pages[].outgoing",
        "pages[].rank",
        "pages[].rationale",
        "pages[].relpath",
        "pages[].role",
        "pages[].scc",
        "steps",
        "steps[].covers",
        "steps[].cycle_size",
        "steps[].modules",
        "steps[].order",
        "steps[].title",
        "steps[].why",
        "stops",
        "stops[].file",
        "stops[].rationale",
        "stops[].scc",
        "summary",
        "summary.business_modules",
        "summary.business_modules.containers",
        "summary.business_modules.coverage",
        "summary.business_modules.coverage.covered",
        "summary.business_modules.coverage.excluded",
        "summary.business_modules.coverage.note",
        "summary.business_modules.coverage.percent",
        "summary.business_modules.coverage.total",
        "summary.business_modules.modules",
        "summary.business_modules.refused",
        "summary.business_modules.truncated",
        "summary.cross_layer_edges",
        "summary.layers",
        "summary.method",
        "summary.mirrors",
        "summary.mirrors.caveat",
        "summary.mirrors.pairs",
        "summary.module_entry_points",
        "summary.modules",
        "summary.reachability",
        "summary.reachability.buckets",
        "summary.reachability.buckets[].bucket",
        "summary.reachability.buckets[].count",
        "summary.reachability.buckets[].label",
        "summary.reachability.buckets[].note",
        "summary.reachability.buckets[].sample",
        "summary.reachability.buckets[].sample_truncated",
        "summary.reachability.buckets[].signal",
        "summary.reachability.buckets[].signals",
        "summary.reachability.buckets[].signals.declared",
        "summary.reachability.buckets[].signals.structure",
        "summary.reachability.buckets[].signals.vocabulary",
        "summary.reachability.caveat",
        "summary.reachability.dropped",
        "summary.reachability.patterns",
        "summary.reachability.total",
        "summary.symbols",
        "truncated",
        "version",
    }
)

KEY_PATHS_BY_VERSION: dict[int, frozenset[str]] = {1: V1_KEY_PATHS}

# The bounded-sample and caveat vocabulary (113 / 130 / 131) a second renderer is most likely to
# drop. Named here so a rename is a contract break by name, not only by set difference.
HONESTY_KEY_PATHS = frozenset(
    {
        "summary.business_modules.coverage.note",
        "summary.business_modules.refused",
        "summary.business_modules.truncated",
        "summary.mirrors.caveat",
        "summary.reachability.buckets[].count",
        "summary.reachability.buckets[].sample",
        "summary.reachability.buckets[].sample_truncated",
        "summary.reachability.caveat",
        "summary.reachability.dropped",
        "truncated",
    }
)


def _sample() -> OnboardingArtifact:
    return OnboardingArtifact(
        method="dominant-subtree",
        truncated=False,
        summary={"layers": 1},
        layers=(
            LayerRow(
                layer="App",
                rank=0,
                modules=1,
                fan_in=0,
                fan_out=1,
                entry_points=1,
                description="d",
            ),
        ),
        crossings=(("App", "Lib", 1),),
        stops=(TourStop(file="a.py", rationale="entry point", scc=()),),
        pages=(
            ModulePage(
                file="a.py",
                relpath="modules/a.py.md",
                layer="App",
                rank=0,
                role="entry-point",
                docline="hello",
                rationale="entry point",
                scc=(),
                index=1,
                of=1,
                outgoing=("b.py",),
                incoming=(),
                fan_in=0,
                fan_out=1,
            ),
        ),
        steps=(
            TourStep(
                order=1,
                title="start",
                modules=("a.py",),
                why="entry",
                covers=1,
                cycle_size=0,
            ),
        ),
        isolated=("lonely.py",),
        diagram_edges=(DiagramEdge("App", "Lib", 1, False),),
        omitted_dynamic=0,
    )


def key_paths(payload: Mapping[str, Any]) -> frozenset[str]:
    """Every dotted key-path in the document, at any depth. List members use ``section[].field``.

    Recursive and union-over-all-elements on purpose: stopping at the top level, or reading only
    ``value[0]``, would leave the whole ``summary`` sub-document out of a pin that claims to hold
    the published shape.
    """
    found: set[str] = set()
    _walk(payload, "", found)
    return frozenset(found)


def _walk(value: Any, prefix: str, found: set[str]) -> None:
    if isinstance(value, Mapping):
        for key, inner in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            found.add(path)
            _walk(inner, path, found)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _walk(item, f"{prefix}[]", found)


def _generated(tmp_path: Path) -> dict[str, Any]:
    """The artifact.json ``generate_onboarding`` actually writes — the shape a renderer reads."""
    generate_onboarding.create(_cycle_repo(tmp_path))()
    written = tmp_path / ".code-atlas" / "onboarding" / "artifact.json"
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_ac1_artifact_json_carries_version_and_pins_the_shape(tmp_path: Path) -> None:
    real = _generated(tmp_path)
    assert real["version"] == ARTIFACT_VERSION
    assert ARTIFACT_VERSION in KEY_PATHS_BY_VERSION
    assert key_paths(real) == KEY_PATHS_BY_VERSION[ARTIFACT_VERSION]
    assert HONESTY_KEY_PATHS <= key_paths(real)


def test_ac1_the_hand_built_sample_introduces_no_path_the_pin_lacks() -> None:
    """The dataclass path, without a store: a sample may cover less, never more."""
    payload = _sample().as_dict()
    assert payload["version"] == ARTIFACT_VERSION
    assert key_paths(payload) <= KEY_PATHS_BY_VERSION[ARTIFACT_VERSION]


def test_ac2_a_new_key_without_a_version_bump_fails(tmp_path: Path) -> None:
    """Made-to-fail on the real document, including inside ``summary`` (145 Phase A)."""
    real = _generated(tmp_path)
    pinned = KEY_PATHS_BY_VERSION[ARTIFACT_VERSION]
    for planted in (
        {**real, "planted_top_level": 1},
        {**real, "summary": {**real["summary"], "planted_nested": 1}},
    ):
        assert key_paths(planted) != pinned


def test_ac2_a_version_bump_without_a_new_pin_fails() -> None:
    """The pin is per version: a bump that re-pins nothing leaves AC1 with no set to match."""
    assert max(KEY_PATHS_BY_VERSION) == ARTIFACT_VERSION
    assert ARTIFACT_VERSION + 1 not in KEY_PATHS_BY_VERSION


def test_ac3_standing_docs_do_not_call_the_file_a_free_form_cache() -> None:
    """AC3: the published-contract wording, not the 088 cache description."""
    banned = ("gitignored regenerable cache", "free-form cache")
    roots = (
        "README.md",
        "docs/PLAN.md",
        "docs/CONVENTION.md",
        "docs/phase3-onboarding/ROADMAP.md",
        "onboarding_llm/README.md",
        "code_atlas/onboarding/artifact.py",
        "code_atlas/tools/generate_onboarding.py",
    )
    repo = Path(__file__).resolve().parent.parent
    for relative in roots:
        text = (repo / relative).read_text(encoding="utf-8").lower()
        for phrase in banned:
            assert phrase not in text, f"{relative} still says {phrase!r}"


def test_ac4_identical_input_is_byte_identical(tmp_path: Path) -> None:
    assert cache_json(_sample()) == cache_json(_sample())
    first = cache_json(_sample())
    for stamp in ("built_at", "timestamp", "generated_at"):
        assert stamp not in first
    written = _generated(tmp_path)
    assert json.dumps(written, sort_keys=True) == json.dumps(
        _generated(tmp_path), sort_keys=True
    )
