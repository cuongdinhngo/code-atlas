"""Task 117 — the prose seam: structure stays derived, only the wording is written.

The proving test drives one writer through all three slots and asserts the prose reaches every one
of them; the rest hold the seam to its promises — off is identity, on moves nothing but prose, a
failure degrades, filler is refused, and the per-run ceiling is real. Hermetic: every writer here is
a plain object, so nothing imports an LLM or touches a network (R4.1).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from code_atlas.onboarding.artifact import (
    build_artifact,
    render_overview,
    render_tour,
)
from code_atlas.onboarding.dataset import build_dataset, dataset_json
from code_atlas.onboarding.headlines import HEADLINE_FAMILIES
from code_atlas.onboarding.layers import RESPONSIBILITY_KEYWORDS, UNCATEGORISED
from code_atlas.onboarding.metrics import module_edges
from code_atlas.onboarding.prose import (
    MAX_PROSE_CALLS,
    SLOT_HEADLINE,
    SLOT_LAYER,
    SLOT_LIMITS,
    SLOT_STEP,
    ProseRequest,
    ProseRun,
    is_filler,
    request_key,
)
from code_atlas.onboarding.quality_gate import (
    MAX_TOUR_STEPS,
    QualityGateError,
    check_artifact,
    check_dataset,
)
from code_atlas.onboarding.summary import StructuralSummarizer
from code_atlas.onboarding.viewer import render_viewer

NODES = [
    ("Ctrl", "app/controller/Home.aa"),
    ("Svc", "app/service/Billing.aa"),
    ("Model", "app/model/Invoice.aa"),
    ("Lib", "app/lib/Money.aa"),
    ("View", "app/view/Page.aa"),
    ("Job", "app/job/Nightly.aa"),
]
EDGES = [
    ("Ctrl", "Svc"),
    ("Svc", "Model"),
    ("Model", "Lib"),
    ("Ctrl", "View"),
    ("Job", "Svc"),
]
PATHS = [path for _, path in NODES]
ENTRIES = ["app/controller/Home.aa"]

CORE = Path(__file__).resolve().parent.parent / "code_atlas"
PROSE = "Prose written by the seam, describing responsibility in words of its own."


class _Writer:
    """Answers every request with the same usable sentence, and records what it was asked."""

    def __init__(self, answer: str = PROSE) -> None:
        self.answer = answer
        self.seen: list[tuple[str, str]] = []

    def write(self, request: ProseRequest) -> str:
        self.seen.append((request.slot, request.key))
        return self.answer


class _Raiser:
    """A model that fails — the AC4 case that must not cost the map a field."""

    def __init__(self, error: BaseException) -> None:
        self.error = error

    def write(self, request: ProseRequest) -> str:
        raise self.error


class _Silent:
    """A refusal or a truncation: nothing came back."""

    def write(self, request: ProseRequest) -> str:
        return ""


class _Echo:
    """Answers with the slot's own key — filler by definition, whichever slot asked.

    Echoing a *different* slot's name would not be filler and no mechanical rule could call it one:
    C1 catches prose that restates what it was handed, not prose that is merely wrong.
    """

    def write(self, request: ProseRequest) -> str:
        return request.key


def _dataset(run: ProseRun | None = None, *, reverse: bool = False):
    nodes = list(reversed(NODES)) if reverse else NODES
    edges = list(reversed(EDGES)) if reverse else EDGES
    return build_dataset(
        nodes,
        edges,
        files=len(PATHS),
        parsed=len(PATHS),
        node_kind_counts=[("Class", 6), ("Method", 14)],
        edge_kind_counts=[("CALLS", 5)],
        confidence={"EXACT": 4, "HEURISTIC": 1},
        hubs=[("app/service/Billing.aa", 2, 1)],
        classes=[("Invoice", "app/model/Invoice.aa", 4)],
        file_symbol_counts=[(path, 3) for path in PATHS],
        file_paths=PATHS,
        path_index_max=100,
        module_max=10,
        mirror_sample_max=5,
        reachability_sample_max=5,
        prose=run,
    )


def _artifact(run: ProseRun | None = None):
    artifact = build_artifact(
        NODES,
        EDGES,
        PATHS,
        list(module_edges(NODES, EDGES)),
        ENTRIES,
        False,
        StructuralSummarizer(),
        max_results=50,
        file_paths=PATHS,
        prose=run,
    )
    assert artifact is not None
    return artifact


# --------------------------------------------------------------------------- the proving test


def test_the_prose_seam_reaches_every_slot_and_the_structure_never_moves() -> None:
    """R6.5 proving test — headlines, layer descriptions and step narratives all carry the prose."""
    writer = _Writer()
    dataset, artifact = _dataset(ProseRun(writer)), _artifact(ProseRun(writer))
    assert dataset.headlines and all(row.text == PROSE for row in dataset.headlines)
    assert all(row.description == PROSE for row in dataset.layers)
    assert artifact.steps and all(step.why == PROSE for step in artifact.steps)
    assert {slot for slot, _ in writer.seen} == {SLOT_HEADLINE, SLOT_LAYER, SLOT_STEP}


# --------------------------------------------------------------------------- AC1


def test_ac1_with_the_seam_unset_every_renderer_is_byte_identical_run_to_run() -> None:
    """AC1 — no field waits for a model, and the off path is reproducible across all four files."""
    for run in (None, ProseRun(None)):
        first, second = _dataset(), _dataset(run)
        assert dataset_json(first) == dataset_json(second)
        assert render_viewer(first, 50) == render_viewer(second, 50)
        left, right = _artifact(), _artifact(run)
        assert render_overview(left) == render_overview(right)
        assert render_tour(left, 50) == render_tour(right, 50)


def test_ac1_the_off_path_is_complete_not_merely_empty() -> None:
    """AC1's other half — every prose slot already says something without a model."""
    dataset, artifact = _dataset(), _artifact()
    assert all(row.text.strip() for row in dataset.headlines)
    assert all(row.description.strip() for row in dataset.layers)
    assert all(step.why.strip() for step in artifact.steps)
    assert ProseRun(None).calls == 0


def test_ac1_the_off_path_makes_no_call_even_with_a_writer_that_would_explode() -> None:
    """A writer is only ever consulted through a run that has one — ``None`` short-circuits."""
    run = ProseRun(None)
    assert run.text(ProseRequest(SLOT_LAYER, "x", "the structural default")) == (
        "the structural default"
    )
    assert not run.enabled


# --------------------------------------------------------------------------- AC2


def _blanked(payload: dict[str, object]) -> dict[str, object]:
    """The dataset with its three prose fields emptied — everything left must be identical."""
    blanked = dict(payload)
    blanked["headlines"] = [dict(row, text="") for row in payload["headlines"]]  # type: ignore[arg-type,call-overload]
    blanked["layers"] = [dict(row, description="") for row in payload["layers"]]  # type: ignore[arg-type,call-overload]
    return blanked


def test_ac2_only_prose_differs_every_number_ranking_and_grouping_is_unchanged() -> None:
    """AC2 — diff two runs and assert the non-prose fields are equal."""
    plain, written = _dataset(), _dataset(ProseRun(_Writer()))
    assert plain.as_dict() != written.as_dict()  # the prose really did change
    assert _blanked(plain.as_dict()) == _blanked(written.as_dict())
    left, right = _artifact(), _artifact(ProseRun(_Writer()))
    assert [step.why for step in left.steps] != [step.why for step in right.steps]
    for before, after in zip(left.steps, right.steps, strict=True):
        assert (before.order, before.title, before.modules, before.covers, before.cycle_size) == (
            after.order, after.title, after.modules, after.covers, after.cycle_size
        )


# --------------------------------------------------------------------------- AC3 (in-run)


def test_ac3_a_repeated_slot_is_memoised_so_the_layer_table_is_paid_for_once() -> None:
    """AC3 in-run — the artifact and the dataset build the same layers; that is one call each."""
    writer = _Writer()
    run = ProseRun(writer)
    _artifact(run)
    before = len([slot for slot, _ in writer.seen if slot == SLOT_LAYER])
    _dataset(run)
    after = len([slot for slot, _ in writer.seen if slot == SLOT_LAYER])
    assert before and after == before, "the shared layer table was priced twice"
    layers = {key for slot, key in writer.seen if slot == SLOT_LAYER}
    assert after == len(layers)


def test_ac3_a_reordered_input_produces_the_same_requests() -> None:
    """AC3 — a reorder upstream must be a hit, so the request identity cannot depend on order."""
    forward, backward = _Writer(), _Writer()
    _dataset(ProseRun(forward))
    _dataset(ProseRun(backward), reverse=True)
    assert sorted(forward.seen) == sorted(backward.seen)


def test_ac3_the_request_identity_moves_only_when_something_that_matters_moves() -> None:
    """AC3 — an edit is a miss; a field that cannot change the answer is not in the key."""
    four, five = (("modules", "4"),), (("modules", "5"),)
    base = ProseRequest(SLOT_LAYER, "Services", "a default", four)
    assert request_key(base) == request_key(
        ProseRequest(SLOT_LAYER, "Services", "a default", four)
    )
    assert request_key(base) != request_key(
        ProseRequest(SLOT_LAYER, "Services", "a default", five)
    )
    assert request_key(base) != request_key(
        ProseRequest(SLOT_STEP, "Services", "a default", four)
    )
    # ``names`` only feeds the filler check, so it cannot change the answer or the key.
    assert request_key(base) == request_key(
        ProseRequest(SLOT_LAYER, "Services", "a default", four, names=("x",))
    )


# --------------------------------------------------------------------------- AC4


@pytest.mark.parametrize(
    "writer",
    [
        _Raiser(RuntimeError("the model refused")),
        _Raiser(TimeoutError("the request timed out")),
        _Silent(),
    ],
    ids=["error", "timeout", "empty"],
)
def test_ac4_a_failure_degrades_to_the_structural_default_and_the_gate_still_passes(
    writer: object,
) -> None:
    """AC4 — never a half-written map: the artifact and the dataset both stay gate-clean."""
    dataset = _dataset(ProseRun(writer))  # type: ignore[arg-type]
    artifact = _artifact(ProseRun(writer))  # type: ignore[arg-type]
    assert dataset.as_dict() == _dataset().as_dict()
    assert render_tour(artifact, 50) == render_tour(_artifact(), 50)
    check_artifact(artifact, max_results=50)
    check_dataset(dataset)


# --------------------------------------------------------------------------- AC5


def test_ac5_each_slot_has_its_own_ceiling_so_no_slot_can_starve_another() -> None:
    """AC5 — the ceiling is enforced per slot, and what it refused is counted, never hidden."""
    run = ProseRun(_Writer(), limits={SLOT_LAYER: 1, SLOT_STEP: 0, SLOT_HEADLINE: 0})
    dataset = _dataset(run)
    described = [row.description for row in dataset.layers]
    assert described.count(PROSE) == 1, "the layer ceiling of one was not enforced"
    assert all(row.text != PROSE for row in dataset.headlines), "a zero ceiling still called"
    assert run.calls == 1
    assert run.declined == len(dataset.headlines) + len(described) - 1


def test_ac5_the_call_ceiling_is_derived_from_the_caps_that_already_exist() -> None:
    """R6.7 — each per-slot cap is asserted against its source, never trusted as a copy."""
    assert SLOT_LIMITS[SLOT_LAYER] == len(set(RESPONSIBILITY_KEYWORDS.values())) + 1
    assert UNCATEGORISED not in set(RESPONSIBILITY_KEYWORDS.values())  # the +1 above
    assert SLOT_LIMITS[SLOT_STEP] == MAX_TOUR_STEPS
    assert SLOT_LIMITS[SLOT_HEADLINE] == len(HEADLINE_FAMILIES)
    assert MAX_PROSE_CALLS == sum(SLOT_LIMITS.values()) == 33


def test_ac5_a_memo_hit_is_not_a_call_so_the_ceiling_counts_real_spend() -> None:
    """AC5 — the budget measures what the model was asked, not how often it was consulted."""
    run = ProseRun(_Writer())
    request = ProseRequest(SLOT_LAYER, "Services", "a default", (("modules", "4"),))
    assert run.text(request) == PROSE
    assert run.text(request) == PROSE
    assert run.calls == 1


# --------------------------------------------------------------------------- AC6


@pytest.mark.parametrize(
    "text, names",
    [
        ("", ("Services",)),
        ("   ", ("Services",)),
        ("Services", ("Services",)),
        ("app/service/Billing.aa", ("app/service/Billing.aa",)),
        ("AppServiceBilling", ("app/service/Billing.aa",)),
        ("Services services SERVICES", ("Services",)),
        ("42", ("Services",)),
    ],
)
def test_ac6_prose_that_only_restates_its_own_names_is_filler(
    text: str, names: tuple[str, ...]
) -> None:
    """AC6 — 109 C1's rule ("no fact beyond its own path"), applied to a sentence."""
    assert is_filler(text, *names)


def test_ac6_a_real_description_is_not_filler_and_neither_is_any_structural_default() -> None:
    """The gate must not be vacuous, and must never trip on the deterministic path."""
    assert not is_filler("Application services that coordinate domain logic.", "Services")
    dataset, artifact = _dataset(), _artifact()
    check_dataset(dataset)
    check_artifact(artifact, max_results=50)
    for layer in dataset.layers:
        assert not is_filler(layer.description, layer.layer)
    for step in artifact.steps:
        assert not is_filler(step.why, step.title, *step.modules)


def test_ac6_the_seam_discards_filler_and_the_gate_refuses_it_independently() -> None:
    """AC6 — enrichment gets no exemption: the seam falls back, the gate is still the backstop."""
    run = ProseRun(_Echo())
    dataset = _dataset(run)
    assert dataset.as_dict() == _dataset().as_dict()  # the seam fell back to the defaults
    # ...and the same filler, fed straight past the seam, is refused by the gate itself.
    from dataclasses import replace

    hollow = replace(
        dataset,
        headlines=tuple(replace(row, text=row.key) for row in dataset.headlines),
    )
    with pytest.raises(QualityGateError) as raised:
        check_dataset(hollow)
    assert raised.value.check == "C1"


def test_ac6_a_hollow_layer_description_is_refused_by_the_artifact_gate() -> None:
    """AC6 at the layer slot — the same rule, the same predicate, the artifact's own gate."""
    from dataclasses import replace

    artifact = _artifact()
    hollow = replace(
        artifact,
        layers=tuple(replace(row, description=row.layer) for row in artifact.layers),
    )
    with pytest.raises(QualityGateError) as raised:
        check_artifact(hollow, max_results=50)
    assert raised.value.check == "C1"


# --------------------------------------------------------------------------- AC7


def test_ac7_no_prompt_model_name_or_llm_import_lives_under_the_core() -> None:
    """AC7 — enrichment is confined to ``onboarding_llm/``; the core holds none of its machinery."""
    banned = re.compile(
        r"^\s*(?:from|import)\s+(?:anthropic|onboarding_llm)\b"
        r"|claude-[a-z0-9.]|gpt-[0-9]|max_tokens|\bsystem\s*=|no preamble|Output only",
        re.IGNORECASE | re.MULTILINE,
    )
    offenders = [
        module.relative_to(CORE).as_posix()
        for module in sorted(CORE.rglob("*.py"))
        if banned.search(module.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_ac7_the_seam_itself_names_no_model_and_no_prompt() -> None:
    """The seam is the surface an impl plugs into; a prompt there would defeat the confinement."""
    source = (CORE / "onboarding" / "prose.py").read_text(encoding="utf-8")
    assert "You are" not in source and "claude" not in source.lower()
