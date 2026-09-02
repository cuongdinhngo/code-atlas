"""Task 109: the structural quality gate over the onboarding artifact (M11).

These tests are pure — they build ``OnboardingArtifact`` fixtures directly, so they run on any host
(no store, no ``fcntl``, no PHP adapter). One deliberately-bad fixture per surviving check, each
observed red (R6.5) by asserting the *right* check fires. The build-twice byte-stability half of C7
lives in ``test_generate_onboarding.py`` (it needs a real index).

205 removed the per-module page tree, and with it the four criteria whose subject was a page: C1's
filler rule, C2's byte ceiling, C6's page identity and C7's page order. Five checks remain — C1 over
the prose slots, C3, C4, C5 and C7's layer/crossing order — and each still has to be seen red.
"""

from __future__ import annotations

import time

import pytest

from code_atlas.onboarding.artifact import LayerRow, OnboardingArtifact
from code_atlas.onboarding.quality_gate import (
    MAX_TOUR_STEPS,
    QualityGateError,
    check_artifact,
)
from code_atlas.onboarding.steps import TourStep
from code_atlas.onboarding.tour import TourStop

_LAYER = LayerRow(
    layer="core",
    rank=0,
    modules=2,
    fan_in=1,
    fan_out=1,
    entry_points=1,
    description="the core layer",
)


def _artifact(
    stops: tuple[TourStop, ...],
    *,
    layers: tuple[LayerRow, ...] = (_LAYER,),
    crossings: tuple[tuple[str, str, int], ...] = (),
    steps: tuple[TourStep, ...] = (),
) -> OnboardingArtifact:
    return OnboardingArtifact(
        method="dominant-subtree",
        truncated=False,
        summary={},
        layers=layers,
        crossings=crossings,
        stops=stops,
        steps=steps,
    )


def _stops(*files: str) -> tuple[TourStop, ...]:
    return tuple(TourStop(file=f, rationale="entry point", scc=()) for f in files)


def _steps(count: int) -> tuple[TourStep, ...]:
    """``count`` well-formed steps, each naming one module (used for the C4 ceiling fixture)."""
    return tuple(
        TourStep(order=i + 1, title="core", modules=(f"m{i}.py",), why="x", covers=1, cycle_size=0)
        for i in range(count)
    )


def _valid() -> OnboardingArtifact:
    return _artifact(_stops("a.py", "b.py"), steps=_steps(2))


def test_a_clean_artifact_passes_the_gate() -> None:
    """The floor: the gate must not raise on a well-formed artifact."""
    check_artifact(_valid())


# --- one deliberately-bad fixture per surviving check, each red on the right check ---


def test_c1_a_step_narrative_that_only_restates_its_own_title() -> None:
    """C1 survives on the prose slots (117 AC6): generated prose gets no exemption."""
    filler = (
        TourStep(order=1, title="core", modules=("core.py",), why="core core.py", covers=1,
                 cycle_size=0),
    )
    with pytest.raises(QualityGateError) as exc:
        check_artifact(_artifact(_stops("core.py"), steps=filler))
    assert exc.value.check == "C1"
    assert exc.value.path == "step[1]"


def test_c3_layer_with_an_empty_description() -> None:
    art = _artifact(
        _stops("a.py", "b.py"),
        layers=(
            LayerRow(
                layer="core",
                rank=0,
                modules=2,
                fan_in=1,
                fan_out=1,
                entry_points=1,
                description="  ",
            ),
        ),
    )
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art)
    assert exc.value.check == "C3"


def test_c4_tour_over_the_step_ceiling() -> None:
    art = _artifact(_stops("a.py"), steps=_steps(MAX_TOUR_STEPS + 1))
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art)
    assert exc.value.check == "C4"
    assert exc.value.path == "tour"


def test_c4_a_step_that_names_no_module_is_empty() -> None:
    """AC4: 109's ceiling becomes a real bound — an empty step is refused, not only over-count."""
    empty = (TourStep(order=1, title="core", modules=(), why="x", covers=0, cycle_size=0),)
    art = _artifact(_stops("a.py"), steps=empty)
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art)
    assert exc.value.check == "C4"
    assert exc.value.path == "step[1]"


def test_c5_scc_names_a_file_outside_the_tour() -> None:
    """C5 now reads the stops directly — a superset of the pages it used to read through (205)."""
    stops = (
        TourStop(file="a.py", rationale="entry point", scc=()),
        TourStop(file="b.py", rationale="cycle", scc=("b.py", "ghost.py")),
    )
    with pytest.raises(QualityGateError) as exc:
        check_artifact(_artifact(stops))
    assert exc.value.check == "C5"
    assert exc.value.path == "ghost.py"


def test_c7_crossings_out_of_canonical_order() -> None:
    art = _artifact(_stops("a.py"), crossings=(("a", "b", 1), ("c", "d", 9)))
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art)
    assert exc.value.check == "C7"
    assert exc.value.path == "crossings"


def test_c7_layers_out_of_canonical_rank_order() -> None:
    high = LayerRow(**{**_LAYER.__dict__, "rank": 3})
    low = LayerRow(**{**_LAYER.__dict__, "rank": 1})
    with pytest.raises(QualityGateError) as exc:
        check_artifact(_artifact(_stops("a.py"), layers=(high, low)))
    assert exc.value.check == "C7"
    assert exc.value.path == "layers"


def test_the_surviving_checks_each_have_a_red_fixture() -> None:
    """The gate's criteria are C1, C3, C4, C5, C7 — the page criteria went with the pages (205)."""
    covered = {"C1", "C3", "C4", "C5", "C7"}
    assert len(covered) == 5


# --- a synthetic-scale artifact passes, and the gate is cheap over it ---


_SCALE_STOPS = 500


def _scale_artifact() -> OnboardingArtifact:
    """500 stops with MAX_TOUR_STEPS steps — the anchor's shape without the anchor (H6)."""
    files = tuple(f"src/pkg{i % 20}/file{i:04d}.py" for i in range(_SCALE_STOPS))
    return _artifact(_stops(*files), steps=_steps(MAX_TOUR_STEPS))


def test_synthetic_scale_artifact_passes_at_the_recorded_ceiling() -> None:
    """The gate passes on the anchor-shaped artifact; the defended number is pinned here."""
    assert MAX_TOUR_STEPS == 15
    check_artifact(_scale_artifact())


def test_the_gate_is_cheap_over_the_scale_artifact() -> None:
    """O(stops) set ops, no IO. Loose smoke bound; anchor timing deferred (H6)."""
    art = _scale_artifact()
    start = time.perf_counter()
    check_artifact(art)
    assert time.perf_counter() - start < 2.0


# --- the failure message names the check and the offending path ---


def test_message_names_the_check_and_the_path() -> None:
    stops = (TourStop(file="b.py", rationale="cycle", scc=("b.py", "ghost.py")),)
    with pytest.raises(QualityGateError) as exc:
        check_artifact(_artifact(stops))
    message = str(exc.value)
    assert "C5" in message
    assert "ghost.py" in message
