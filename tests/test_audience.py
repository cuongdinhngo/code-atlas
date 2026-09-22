"""210 — the committed artifact has a shape per reader, and says which one it is.

`detail_level` gated only fields of the MCP response, so the WRITTEN tree was byte-identical for a
first-week developer and for an engineer auditing coupling. Every assertion here reads the emitted
files, never a payload dict (R6.9 / LESSONS 127-C1).
"""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas.onboarding.artifact import (
    FLOWS_NAME,
    MANIFEST_NAME,
    OUTPUT_DIR,
    OVERVIEW_NAME,
    TOUR_NAME,
)
from code_atlas.onboarding.audience import (
    AUDIENCES,
    CONTRACTS,
    DEFAULT_AUDIENCE,
    FULL,
    MAINTAINER,
    NEWCOMER,
    contract_for,
    resolve_audience,
)
from code_atlas.store import GraphStore
from code_atlas.tools import generate_onboarding
from tests.test_nav_tools import db_config, edge, node, seed_file

README = "# Demo\n\nThe demo service that fronts the warehouse API for the retail estate.\n"
COMPOSER = '{\n  "scripts": {\n    "test": "phpunit --colors"\n  }\n}\n'


def _repo(tmp_path: Path) -> object:
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        for i in range(4):
            seed_file(
                store,
                f"app/Http/C{i}.aa",
                [node("Class", f"C{i}", f"\\App\\C{i}", f"app/Http/C{i}.aa")],
                [
                    edge(
                        "CALLS",
                        f"\\App\\C{i}",
                        f"\\App\\M{i}",
                        f"app/Http/C{i}.aa",
                        target_qname=f"\\App\\M{i}",
                    )
                ],
                root=tmp_path,
            )
            seed_file(
                store,
                f"app/Models/M{i}.aa",
                [node("Class", f"M{i}", f"\\App\\M{i}", f"app/Models/M{i}.aa")],
                [],
                root=tmp_path,
            )
    (tmp_path / "composer.json").write_text(COMPOSER, encoding="utf-8")
    (tmp_path / "README.md").write_text(README, encoding="utf-8")
    return config


def _overview(root: Path) -> str:
    return (root / OUTPUT_DIR / OVERVIEW_NAME).read_text(encoding="utf-8")


def _headings(text: str) -> list[str]:
    return [line[3:] for line in text.splitlines() if line.startswith("## ")]


def test_the_audience_changes_which_sections_the_written_tree_holds(tmp_path: Path) -> None:
    """AC1 — provably, on the emitted markdown, not in the discarded response."""
    config = _repo(tmp_path)
    shapes = {}
    bodies = {}
    for audience in AUDIENCES:
        generate_onboarding.create(config)(audience=audience)  # type: ignore[arg-type]
        bodies[audience] = _overview(tmp_path)
        shapes[audience] = _headings(bodies[audience])

    assert shapes[NEWCOMER] != shapes[MAINTAINER], "one shape for both readers is the defect"
    # 269: orientation is the doors question; appendix census uses ### under Appendix.
    assert "Where do I start reading?" in shapes[NEWCOMER]
    assert "Where do I start reading?" not in shapes[MAINTAINER], "the auditor knows how to run it"
    assert "### Cross-layer edges" in bodies[MAINTAINER]
    assert "### Cross-layer edges" not in bodies[NEWCOMER], "a 99-row table is noise on day one"
    # Neither is the other minus a few sections: that would be a flag wearing a bigger name (R7.4).
    newcomer, maintainer = set(shapes[NEWCOMER]), set(shapes[MAINTAINER])
    assert not newcomer <= maintainer and not maintainer <= newcomer


def test_an_audience_that_wants_no_tour_does_not_get_a_stale_one(tmp_path: Path) -> None:
    """A tree still holding a document its contract does not name is lying about who it is for."""
    config = _repo(tmp_path)
    generate_onboarding.create(config)(audience=NEWCOMER)  # type: ignore[arg-type]
    assert (tmp_path / OUTPUT_DIR / TOUR_NAME).is_file()

    generate_onboarding.create(config)(audience=MAINTAINER)  # type: ignore[arg-type]
    assert not (tmp_path / OUTPUT_DIR / TOUR_NAME).exists(), "the newcomer's tour survived"
    assert (tmp_path / OUTPUT_DIR / FLOWS_NAME).is_file(), "flows are evidence for both readers"


def test_the_artifact_states_its_audience(tmp_path: Path) -> None:
    """AC3 — a committed tree that cannot say who it is for cannot be judged, or regenerated."""
    config = _repo(tmp_path)
    generate_onboarding.create(config)(audience=MAINTAINER)  # type: ignore[arg-type]
    overview = _overview(tmp_path)
    assert "### Who this was written for" in overview
    assert f"- audience: `{MAINTAINER}`" in overview
    manifest = json.loads(
        (tmp_path / OUTPUT_DIR / MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert manifest["audience"]["audience"] == MAINTAINER
    # The contract rides with it, so a reader can see WHY each section is there (Scope 2).
    assert set(manifest["audience"]["sections"]) == set(CONTRACTS[MAINTAINER].sections)
    assert manifest["audience"]["purpose"]


def test_regenerating_with_the_same_audience_is_byte_identical(tmp_path: Path) -> None:
    """AC3's other half — the audience is a resolved setting, never inferred (R4.2 / 269 Q6)."""
    config = _repo(tmp_path)
    generate_onboarding.create(config)(audience=NEWCOMER)  # type: ignore[arg-type]
    generate_onboarding.create(config)(audience=NEWCOMER)  # type: ignore[arg-type]
    first = _overview(tmp_path)
    generate_onboarding.create(config)(audience=NEWCOMER)  # type: ignore[arg-type]
    assert _overview(tmp_path) == first


def test_the_default_audience_is_todays_artifact(tmp_path: Path) -> None:
    """`full` is kept as an explicit third audience so a pre-210 tree is still describable."""
    config = _repo(tmp_path)
    generate_onboarding.create(config)()  # type: ignore[arg-type]
    generate_onboarding.create(config)()  # type: ignore[arg-type]  # seed prior for Q6
    default = _overview(tmp_path)
    generate_onboarding.create(config)(audience=FULL)  # type: ignore[arg-type]
    assert _overview(tmp_path) == default
    assert DEFAULT_AUDIENCE == FULL


def test_an_unrecognised_audience_falls_back_and_says_so(tmp_path: Path) -> None:
    """R5.3's posture — a bad setting must not stop a build, and the fallback is never silent."""
    assert resolve_audience("nonsense") == FULL
    assert resolve_audience(None) == FULL
    config = _repo(tmp_path)
    generate_onboarding.create(config)(audience="nonsense")  # type: ignore[arg-type]
    assert f"- audience: `{FULL}`" in _overview(tmp_path)


def test_every_contracted_section_states_why_that_reader_needs_it() -> None:
    """Scope 2 — a content contract, not a verbosity dial. Every entry carries its reason."""
    for name, contract in CONTRACTS.items():
        assert contract.audience == name
        assert contract.purpose.strip(), f"{name} states no purpose"
        assert contract.sections, f"{name} contracts no section"
        for section, why in contract.sections.items():
            assert why.strip().endswith("."), f"{name}/{section} states no reason"
        for document, why in contract.documents.items():
            assert why.strip().endswith("."), f"{name}/{document} states no reason"


def test_the_contracts_are_not_near_identical() -> None:
    """R7.4 / AC6 — the measurement that decides whether this ticket ships at all.

    Two audiences with one real difference between them is a configuration flag wearing a bigger
    name, and the ticket says that is the finding, not the feature. Recorded as a live assertion
    rather than a paragraph, so a later edit that collapses the two is a red build.
    """
    newcomer, maintainer = CONTRACTS[NEWCOMER], CONTRACTS[MAINTAINER]
    sections = set(newcomer.sections) ^ set(maintainer.sections)
    documents = set(newcomer.documents) ^ set(maintainer.documents)
    assert len(sections) >= 5, f"only {len(sections)} sections differ: {sorted(sections)}"
    assert documents, "the two audiences receive the same set of documents"
    assert not set(newcomer.sections) <= set(maintainer.sections)
    assert not set(maintainer.sections) <= set(newcomer.sections)


def test_one_place_decides_what_an_audience_emits() -> None:
    """R1.8 / 127's lesson — no renderer re-derives the section list."""
    import code_atlas.onboarding.artifact as artifact_module
    import code_atlas.onboarding.viewer as viewer_module

    for module in (artifact_module, viewer_module):
        source = Path(module.__file__ or "").read_text(encoding="utf-8")
        assert "CONTRACTS" not in source, f"{module.__name__} reads the table instead of asking"
    assert contract_for(NEWCOMER) is CONTRACTS[NEWCOMER]


def test_a_sections_presence_never_depends_on_another_sections(tmp_path: Path) -> None:
    """A contract decides what an audience emits; control flow must not decide it again.

    An early return once a section is absent couples one section's presence to another's, so an
    audience wanting the diagram but not the layer list would silently lose the diagram. There is
    no such audience today, which is exactly why nothing else would catch it.
    """
    from dataclasses import replace

    from code_atlas.onboarding.artifact import build_artifact, render_overview
    from code_atlas.onboarding.audience import CROSSINGS, DIAGRAM, LAYERS, SUMMARY
    from code_atlas.onboarding.summary import StructuralSummarizer

    nodes = [("\\App\\C", "app/Http/C.aa"), ("\\App\\M", "app/Models/M.aa")]
    edges = [("\\App\\C", "\\App\\M")]
    files = ["app/Http/C.aa", "app/Models/M.aa"]
    artifact = build_artifact(
        nodes, edges, files, edges, ["app/Http/C.aa"], False, StructuralSummarizer(),
        max_results=10, file_paths=files,
    )
    assert artifact is not None

    contract = CONTRACTS[FULL]
    no_layers = replace(
        contract,
        audience="probe",
        sections={
            key: why
            for key, why in contract.sections.items()
            if key in (SUMMARY, DIAGRAM, CROSSINGS)
        },
    )
    assert LAYERS not in no_layers.sections

    # Rendered through the probe contract: the diagram and crossings must both survive.
    import code_atlas.onboarding.artifact as module

    original = module.contract_for
    module.contract_for = lambda _audience: no_layers  # type: ignore[assignment]
    try:
        rendered = render_overview(artifact, node_cap=10, audience="probe")
    finally:
        module.contract_for = original  # type: ignore[assignment]

    assert "### Layers" not in rendered
    assert "### Layer graph" in rendered, "diagram must survive without Layers"
    assert "### Cross-layer edges" in rendered
