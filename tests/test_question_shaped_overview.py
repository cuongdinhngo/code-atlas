"""Task 269 — question-shaped overview headings; never an empty table."""

from __future__ import annotations

import re

from code_atlas.onboarding.artifact import (
    H_APPENDIX,
    H_ARCH_DIFF,
    H_AUDIENCE,
    H_LANDMINES,
    H_MODULES,
    H_ORIENTATION,
    H_PROVENANCE,
    H_SPINE,
    H_SUMMARY,
    H_TRUST,
    OVERVIEW_CHAR_CEILING,
    LayerRow,
    OnboardingArtifact,
    render_overview,
)


def _artifact(**summary_extra: object) -> OnboardingArtifact:
    layer = LayerRow(
        layer="HTTP / Entry",
        description="entry",
        rank=0,
        modules=2,
        fan_in=0,
        fan_out=1,
        entry_points=1,
    )
    summary: dict[str, object] = {
        "layers": 1,
        "modules": 2,
        "symbols": 3,
        "cross_layer_edges": 0,
        "business_modules": {
            "source": "empty_explained",
            "modules": [],
            "coverage": {
                "covered": 0,
                "total": 2,
                "percent": 0.0,
                "excluded": 0,
                "note": "n",
            },
            "empty_reason": "nothing configured",
            "candidate_globs": [{"glob": "public/**", "files_matched": 0}],
        },
        "mirrors": {"caveat": "path identity only", "pairs": []},
        "hubs": [],
        "headlines": [],
        "confidence": {"RESOLVED": 8, "HEURISTIC": 2, "DYNAMIC": 0},
    }
    summary.update(summary_extra)
    return OnboardingArtifact(
        method="test",
        truncated=False,
        summary=summary,
        layers=(layer,),
        crossings=(),
        stops=(),
        steps=(),
        diagram_edges=(),
        omitted_dynamic=0,
    )


def test_seven_questions_in_order() -> None:
    text = render_overview(_artifact())
    headings = (
        H_SUMMARY,
        H_LANDMINES,
        H_ORIENTATION,
        H_MODULES,
        H_SPINE,
        H_ARCH_DIFF,
        H_TRUST,
    )
    positions = [text.index(h) for h in headings]
    assert positions == sorted(positions)
    assert text.index(H_APPENDIX) > positions[-1]


def test_no_empty_pipe_table() -> None:
    """Property: a markdown table header must be followed by at least one data row."""
    text = render_overview(
        _artifact(
            headlines=[{"family": "x", "text": "landmine A", "action": "open the file"}]
        )
    )
    for match in re.finditer(r"^\|[^|\n]+\|[^|\n]+\|\n\|---\|---\|\n", text, re.M):
        after = text[match.end() :]
        assert after.startswith("|"), f"empty table at {match.group()!r}"


def test_never_empty_sections_name_reason_and_what_to_set() -> None:
    """AC property: every Q section appears; empty ones name reason + what to set."""
    text = render_overview(_artifact())
    for heading in (
        H_SUMMARY,
        H_LANDMINES,
        H_ORIENTATION,
        H_MODULES,
        H_SPINE,
        H_ARCH_DIFF,
        H_TRUST,
    ):
        assert heading in text, f"silent omission of {heading}"
    # Q3 / Q4 / Q6 refusals name the knob or the next step.
    assert "CA_ENTRY_POINTS" in text or "doors" in text
    assert (
        "candidate" in text.lower()
        or "empty_reason" in text.lower()
        or "nothing configured" in text
    )
    assert "DiffRefusal" in text or "no previous generate" in text
    assert "single-tree repo, normal" in text


def test_mirrors_never_empty_silence() -> None:
    text = render_overview(_artifact())
    assert "single-tree repo, normal" in text


def test_overview_states_size_ceiling() -> None:
    text = render_overview(_artifact())
    assert "size ceiling:" in text
    assert "_(dataset.layers)_" in text


def test_oversized_overview_trims_the_appendix_but_keeps_the_footer() -> None:
    """Past the ceiling the census goes; the provenance stamp and audience line stay."""
    crossings = tuple(
        (f"layer/source_{i}", f"layer/target_{i}", i) for i in range(4_000)
    )
    artifact = _artifact()
    text = render_overview(
        OnboardingArtifact(
            method=artifact.method,
            truncated=artifact.truncated,
            summary=artifact.summary,
            layers=artifact.layers,
            crossings=crossings,
            stops=(),
            steps=(),
            diagram_edges=(),
            omitted_dynamic=0,
        )
    )
    assert "appendix truncated" in text
    assert H_SUMMARY in text and H_TRUST in text
    assert H_PROVENANCE in text, "provenance must survive the size trim"
    assert H_AUDIENCE in text, "the audience line must survive the size trim"
    assert text.index(H_APPENDIX) < text.index(H_PROVENANCE)
    assert len(text) <= OVERVIEW_CHAR_CEILING


def test_arch_diff_first_run_refusal_prose() -> None:
    text = render_overview(_artifact())
    assert "no previous generate" in text
    assert "DiffRefusal" in text


def test_arch_diff_renders_prior_markdown() -> None:
    text = render_overview(
        _artifact(),
        arch_diff_markdown="# Architecture diff\n\n- before: `a`\n- after: `b`\n",
    )
    assert "- before: `a`" in text
    assert "DiffRefusal" not in text


def test_landmine_answers_before_table() -> None:
    text = render_overview(
        _artifact(
            headlines=[
                {
                    "family": "confidence",
                    "text": "half the edges are heuristic",
                    "action": "open HEURISTIC call sites before trusting them",
                }
            ]
        )
    )
    q2 = text.split(H_LANDMINES, 1)[1].split(H_ORIENTATION, 1)[0]
    assert "landmine family" in q2
    assert q2.index("landmine family") < q2.index("| Finding | Action |")
    assert "open HEURISTIC call sites" in q2


def test_uncategorised_worklist_lists_segments() -> None:
    layer = LayerRow(
        layer="Uncategorised",
        description="x",
        rank=0,
        modules=5,
        fan_in=0,
        fan_out=0,
        entry_points=0,
    )
    art = _artifact(uncategorised_segments=[{"segment": "legacy", "dirs": 3}])
    art = OnboardingArtifact(
        method=art.method,
        truncated=art.truncated,
        summary=art.summary,
        layers=(layer,),
        crossings=(),
        stops=(),
        steps=(),
        diagram_edges=(),
        omitted_dynamic=0,
    )
    text = render_overview(art)
    assert "`legacy`" in text
    assert "vocabulary worklist" in text
