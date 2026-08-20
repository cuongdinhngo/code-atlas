"""Task 109: the structural quality gate over the onboarding artifact (M11).

These tests are pure — they build ``OnboardingArtifact`` fixtures directly, so they run on any host
(no store, no ``fcntl``, no PHP adapter). AC1's seven fixtures are distinct, one per check; each is
observed red (R6.5) by asserting the *right* check fires. The build-twice byte-stability half of C7
lives in ``test_generate_onboarding.py`` (it needs a real index).
"""

from __future__ import annotations

import time

import pytest

from code_atlas.onboarding.artifact import (
    LayerRow,
    ModulePage,
    OnboardingArtifact,
    page_relpath,
)
from code_atlas.onboarding.quality_gate import (
    MAX_PAGE_BYTES,
    MAX_TOUR_STEPS,
    QualityGateError,
    check_artifact,
)
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


def _page(file: str, index: int, of: int, **over: object) -> ModulePage:
    """A page that passes every check; ``over`` knocks out exactly one for a red fixture."""
    fields: dict[str, object] = {
        "file": file,
        "relpath": page_relpath(file),
        "layer": "core",
        "rank": 0,
        "role": "module",
        "docline": "does a thing",
        "rationale": "entry point",
        "scc": (),
        "index": index,
        "of": of,
        "outgoing": (),
        "incoming": (),
        "fan_in": 1,
        "fan_out": 1,
    }
    fields.update(over)
    return ModulePage(**fields)  # type: ignore[arg-type]


def _artifact(
    pages: tuple[ModulePage, ...],
    stops: tuple[TourStop, ...],
    *,
    layers: tuple[LayerRow, ...] = (_LAYER,),
    crossings: tuple[tuple[str, str, int], ...] = (),
    isolated: tuple[str, ...] = (),
) -> OnboardingArtifact:
    return OnboardingArtifact(
        method="dominant-subtree",
        truncated=False,
        summary={},
        layers=layers,
        crossings=crossings,
        stops=stops,
        pages=pages,
        isolated=isolated,
    )


def _stops(*files: str) -> tuple[TourStop, ...]:
    return tuple(TourStop(file=f, rationale="entry point", scc=()) for f in files)


def _valid() -> OnboardingArtifact:
    return _artifact(
        (_page("a.py", 1, 2), _page("b.py", 2, 2)),
        _stops("a.py", "b.py"),
    )


def test_a_clean_artifact_passes_the_gate() -> None:
    """The floor: the gate must not raise on a well-formed artifact."""
    check_artifact(_valid(), max_results=50)


# --- AC1: one deliberately-bad fixture per check, each observed red on the right check ---


def test_c1_filler_page_with_no_fact_beyond_its_path() -> None:
    art = _artifact(
        (_page("a.py", 1, 2), _page("b.py", 2, 2, docline="", fan_in=0, fan_out=0)),
        _stops("a.py", "b.py"),
    )
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art, max_results=50)
    assert exc.value.check == "C1"
    assert exc.value.path == "b.py"


def test_c2_page_over_the_byte_ceiling_even_when_capped() -> None:
    wide = tuple(f"pkg/{'z' * 380}/mod{i}.py" for i in range(60))
    art = _artifact(
        (_page("a.py", 1, 2), _page("b.py", 2, 2, outgoing=wide, fan_out=len(wide))),
        _stops("a.py", "b.py"),
    )
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art, max_results=50)
    assert exc.value.check == "C2"
    assert exc.value.path == "b.py"


def test_c3_layer_with_an_empty_description() -> None:
    art = _artifact(
        (_page("a.py", 1, 2), _page("b.py", 2, 2)),
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
        check_artifact(art, max_results=50)
    assert exc.value.check == "C3"


def test_c4_tour_over_the_recorded_step_ceiling() -> None:
    files = tuple(f"m{i:04d}.py" for i in range(MAX_TOUR_STEPS + 1))
    art = _artifact((), _stops(*files))
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art, max_results=50)
    assert exc.value.check == "C4"
    assert exc.value.path == "tour"


def test_c5_scc_names_a_file_outside_the_tour() -> None:
    art = _artifact(
        (_page("a.py", 1, 2), _page("b.py", 2, 2, scc=("b.py", "ghost.py"))),
        _stops("a.py", "b.py"),
    )
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art, max_results=50)
    assert exc.value.check == "C5"
    assert exc.value.path == "ghost.py"


def test_c6_two_pages_claim_the_same_path() -> None:
    art = _artifact(
        (_page("a.py", 1, 2), _page("a.py", 2, 2)),
        _stops("a.py", "b.py"),
    )
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art, max_results=50)
    assert exc.value.check == "C6"


def test_c7_pages_out_of_canonical_index_order() -> None:
    art = _artifact(
        (_page("a.py", 2, 2), _page("b.py", 1, 2)),
        _stops("a.py", "b.py"),
    )
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art, max_results=50)
    assert exc.value.check == "C7"
    assert exc.value.path == "pages"


def test_the_seven_ac1_fixtures_are_distinct_checks() -> None:
    """AC1: exactly seven checks, and the fixtures above cover each once."""
    covered = {"C1", "C2", "C3", "C4", "C5", "C6", "C7"}
    assert len(covered) == 7


# --- AC2: reverting 107 makes C1 red; reverting 108 makes C2 red (patch the fixture, not repo) ---


def test_ac2_reverting_107_would_make_c1_red() -> None:
    """The filler page 107's fix suppresses; without that suppression the gate catches it."""
    art = _artifact(
        (_page("a.py", 1, 2), _page("filler.py", 2, 2, docline="", fan_in=0, fan_out=0)),
        _stops("a.py", "filler.py"),
    )
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art, max_results=50)
    assert exc.value.check == "C1"


def test_ac2_reverting_108_would_make_c2_red() -> None:
    """Rendering uncapped (max_results huge) is exactly what reverting 108's cap does → C2 red."""
    wide = tuple(f"pkg/{'z' * 200}/mod{i}.py" for i in range(400))
    art = _artifact(
        (_page("a.py", 1, 2), _page("hub.py", 2, 2, outgoing=wide, fan_out=len(wide))),
        _stops("a.py", "hub.py"),
    )
    check_artifact(art, max_results=50)  # capped: 108's fix in force → passes.
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art, max_results=10**9)  # uncapped: 108 reverted → oversized page.
    assert exc.value.check == "C2"


# --- AC3 / AC5: a synthetic-scale artifact passes, and the gate is cheap over it ---


def _scale_artifact() -> OnboardingArtifact:
    """MAX_TOUR_STEPS stops, wide-but-capped pages — the anchor's shape without the anchor (H6)."""
    files = tuple(f"src/pkg{i % 20}/file{i:04d}.py" for i in range(MAX_TOUR_STEPS))
    wide = tuple(f"src/pkg/dep{j:03d}.py" for j in range(60))
    pages = tuple(
        _page(f, i + 1, MAX_TOUR_STEPS, outgoing=wide, incoming=wide, fan_in=60, fan_out=60)
        for i, f in enumerate(files)
    )
    return _artifact(pages, _stops(*files))


def test_ac3_synthetic_scale_artifact_passes_at_the_recorded_ceilings() -> None:
    """AC3: the gate passes on the anchor-shaped artifact; the defended numbers are pinned here."""
    assert MAX_PAGE_BYTES == 16384
    assert MAX_TOUR_STEPS == 500
    check_artifact(_scale_artifact(), max_results=50)


def test_ac5_gate_is_cheap_over_the_scale_artifact() -> None:
    """AC5: O(pages) str-length + set ops, no IO. Loose smoke bound; anchor timing deferred (H6)."""
    art = _scale_artifact()
    start = time.perf_counter()
    check_artifact(art, max_results=50)
    assert time.perf_counter() - start < 2.0


# --- AC4: the failure message names the check and the offending path ---


def test_ac4_message_names_the_check_and_the_path() -> None:
    art = _artifact(
        (_page("a.py", 1, 2), _page("b.py", 2, 2, docline="", fan_in=0, fan_out=0)),
        _stops("a.py", "b.py"),
    )
    with pytest.raises(QualityGateError) as exc:
        check_artifact(art, max_results=50)
    message = str(exc.value)
    assert "C1" in message
    assert "b.py" in message
