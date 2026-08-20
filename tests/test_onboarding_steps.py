"""Task 111: narrative reading-steps over the budgeted tour subgraph.

Pure tests over ``build_steps`` and ``render_tour`` — no store, no ``fcntl`` (they run on the
Windows dev host). The proving path is the step construction itself; the anchor-scale measurement
(AC5) rides ``scripts/layer_report``-style Docker runs and the operator's anchor checkout.
"""

from __future__ import annotations

from collections.abc import Sequence

from code_atlas.onboarding.artifact import render_tour
from code_atlas.onboarding.layers import LayerAssignment, assign_layers
from code_atlas.onboarding.metrics import GraphMetrics, compute_metrics
from code_atlas.onboarding.steps import MAX_STEPS, MIN_STEPS, build_steps
from code_atlas.onboarding.tour import ordered_stops

# --- fixtures -------------------------------------------------------------------------------------

_LAYERS = {
    "app/Http": [f"app/Http/C{i}.php" for i in range(15)],
    "app/Services": [f"app/Services/S{i}.php" for i in range(15)],
    "app/Models": [f"app/Models/M{i}.php" for i in range(15)],
    "resources/views": [f"resources/views/V{i}.php" for i in range(15)],
}


def _wide_repo() -> tuple[
    list[tuple[str, str]], list[tuple[str, str]], list[str], list[str]
]:
    """60 modules across 4 responsibility bands; Models 0–2 form a 3-cycle (AC1/AC2)."""
    nodes: list[tuple[str, str]] = []
    edges: list[tuple[str, str]] = []
    for files in _LAYERS.values():
        for file in files:
            nodes.append(("Class", file))
    http, svc, mod, view = (
        _LAYERS["app/Http"], _LAYERS["app/Services"], _LAYERS["app/Models"],
        _LAYERS["resources/views"],
    )
    for i in range(15):
        edges += [(http[i], svc[i]), (svc[i], mod[i]), (http[i], view[i])]
    edges += [(mod[0], mod[1]), (mod[1], mod[2]), (mod[2], mod[0])]  # a 3-cycle in Domain / Data
    all_files = [file for files in _LAYERS.values() for file in files]
    return nodes, edges, all_files, list(http)


def _steps_of(
    nodes: Sequence[tuple[str, str]],
    edges: Sequence[tuple[str, str]],
    files: Sequence[str],
    entries: Sequence[str],
) -> tuple[GraphMetrics, LayerAssignment, tuple]:
    metrics = compute_metrics(nodes, edges)
    assignment = assign_layers(metrics)
    stops = ordered_stops(files, edges, entries)
    return metrics, assignment, build_steps(stops, assignment, metrics, edges, entries)


# --- AC1 ------------------------------------------------------------------------------------------


def test_ac1_sixty_modules_yield_between_five_and_fifteen_steps() -> None:
    """R6.5 red-guard: today's ``ordered_stops`` yields 60; ``build_steps`` clamps to [5, 15]."""
    nodes, edges, files, entries = _wide_repo()
    assert len(ordered_stops(files, edges, entries)) == 60  # the pre-111 stop-per-module count
    _, _, steps = _steps_of(nodes, edges, files, entries)
    assert MIN_STEPS <= len(steps) <= MAX_STEPS
    assert len(steps) < 60  # the whole point: a reading order, not one line per module


# --- AC2 ------------------------------------------------------------------------------------------


def test_ac2_an_scc_is_one_step_contribution_stating_its_size() -> None:
    """A cycle contributes one entry stating how many modules it holds, not a per-member list."""
    nodes, edges, files, entries = _wide_repo()
    _, _, steps = _steps_of(nodes, edges, files, entries)
    cyclic = [step for step in steps if step.cycle_size]
    assert len(cyclic) == 1 and cyclic[0].cycle_size == 3
    rendered = _render(steps)
    assert "cycle of 3 modules" in rendered
    # The three members are never all spelled out on their own lines (the 332-line defect).
    assert rendered.count("app/Models/M0.php") + rendered.count("app/Models/M1.php") <= 1


# --- AC3 ------------------------------------------------------------------------------------------


def test_ac3_steps_are_byte_stable_across_runs() -> None:
    """R4.2: identical input yields identical steps, titles, order and rendered bytes."""
    nodes, edges, files, entries = _wide_repo()
    _, _, first = _steps_of(nodes, edges, files, entries)
    _, _, second = _steps_of(nodes, edges, files, entries)
    assert first == second
    assert _render(first) == _render(second)


# --- AC4 ------------------------------------------------------------------------------------------


def test_ac4_no_step_is_empty() -> None:
    """Every step names at least one module (109's C4 becomes a real bound)."""
    nodes, edges, files, entries = _wide_repo()
    _, _, steps = _steps_of(nodes, edges, files, entries)
    assert steps
    assert all(step.modules for step in steps)
    assert all(1 <= len(step.modules) <= 5 for step in steps)
    assert all(step.covers >= len(step.modules) for step in steps)


def test_the_ceiling_holds_when_many_bands_exist() -> None:
    """A repo with far more than 15 bands is merged down to the ceiling, never over it."""
    nodes: list[tuple[str, str]] = []
    edges: list[tuple[str, str]] = []
    prev: str | None = None
    for i in range(40):  # a 40-deep chain: 40 distinct BFS depths in one layer
        file = f"src/step{i:02d}.php"
        nodes.append(("Class", file))
        if prev is not None:
            edges.append((prev, file))
        prev = file
    files = [f"src/step{i:02d}.php" for i in range(40)]
    _, _, steps = _steps_of(nodes, edges, files, [files[0]])
    assert len(steps) <= MAX_STEPS


# --- AC6 ------------------------------------------------------------------------------------------


def test_ac6_no_number_in_the_rendered_tour_is_a_literal() -> None:
    """Mutating the dataset moves the rendered numbers — nothing is hard-coded (regression bar)."""
    nodes, edges, files, entries = _wide_repo()
    _, _, before = _steps_of(nodes, edges, files, entries)
    covers_before = tuple(step.covers for step in before)

    # Grow the cycle from 3 to 4 and add a module: the covered counts and cycle size must move.
    edges = list(edges) + [
        ("app/Models/M2.php", "app/Models/M3.php"),
        ("app/Models/M3.php", "app/Models/M0.php"),
    ]
    _, _, after = _steps_of(nodes, edges, files, entries)
    covers_after = tuple(step.covers for step in after)
    assert covers_before != covers_after or any(
        step.cycle_size == 4 for step in after
    )
    assert "cycle of 4 modules" in _render(after)


# --- helpers --------------------------------------------------------------------------------------


class _Art:
    """A stand-in carrying only what ``render_tour`` reads — steps and the truncated flag."""

    def __init__(self, steps: tuple) -> None:
        self.steps = steps
        self.truncated = False


def _render(steps: tuple) -> str:
    return render_tour(_Art(steps), max_results=50)  # type: ignore[arg-type]
