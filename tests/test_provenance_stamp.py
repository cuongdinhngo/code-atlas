"""209 — a committed artifact says which implementation wrote its text.

The defect: with every seam on its deterministic default, an empty summary is indistinguishable
from a repo with no doc comments. Every assertion here reads the EMITTED `overview.md` or
`manifest.json`, never a payload dict (R6.9 / LESSONS 127-C1), and no test needs an API key (AC6).
"""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas.onboarding.artifact import MANIFEST_NAME, OUTPUT_DIR, OVERVIEW_NAME
from code_atlas.onboarding.dataset import DATASET_VERSION
from code_atlas.onboarding.provenance import NONE, Provenance, implementation_name
from code_atlas.onboarding.summary import NodeFacts, Summary
from code_atlas.store import GraphStore
from code_atlas.tools import generate_onboarding
from tests.test_nav_tools import db_config, edge, node, seed_file


class _ShoutySummarizer:
    """A Summarizer that is plainly not the structural default. No network, no key (AC6)."""

    def summarize(self, facts: NodeFacts) -> Summary:
        return Summary(
            key=facts.metric.key,
            signature=facts.signature,
            docline="SHOUTED SUMMARY",
            role="connector",
        )


def _seed(tmp_path: Path) -> object:
    """Two linked modules, enough for a layer table and a tour."""
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            "app/Http/C.aa",
            [node("Class", "C", "\\App\\C", "app/Http/C.aa")],
            [edge("CALLS", "\\App\\C", "\\App\\M", "app/Http/C.aa", target_qname="\\App\\M")],
            root=tmp_path,
        )
        seed_file(
            store,
            "app/Models/M.aa",
            [node("Class", "M", "\\App\\M", "app/Models/M.aa")],
            [],
            root=tmp_path,
        )
    return config


def _out(root: Path) -> Path:
    return root / OUTPUT_DIR


def test_the_default_run_names_every_seam_in_the_committed_overview(tmp_path: Path) -> None:
    """AC1, markdown half — the emitted overview attributes all three seams."""
    generate_onboarding.create(_seed(tmp_path))()  # type: ignore[arg-type]
    overview = (_out(tmp_path) / OVERVIEW_NAME).read_text(encoding="utf-8")
    assert "## How this was written" in overview
    assert "- module summaries (085): `StructuralSummarizer`" in overview
    assert "- map prose (117): the deterministic default" in overview
    assert "- layer names (091): `IdentityLayerRefiner`" in overview
    # The sentence that makes an empty summary attributable to the run rather than the repo.
    assert "a fact about the run above, not about the repo" in overview


def test_the_committed_manifest_carries_the_same_stamp(tmp_path: Path) -> None:
    """AC1, dataset half — one fact, read the same by the viewer and by an agent (R1.8)."""
    generate_onboarding.create(_seed(tmp_path))()  # type: ignore[arg-type]
    manifest = json.loads((_out(tmp_path) / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["provenance"] == {
        "layers": "IdentityLayerRefiner",
        "prose": NONE,
        "summarizer": "StructuralSummarizer",
    }
    assert manifest["version"] == DATASET_VERSION


def test_a_different_summarizer_changes_the_stamp_and_nothing_else_moves(
    tmp_path: Path,
) -> None:
    """AC4 — two artifacts on ONE index differ in their stamp, and differ there first."""
    config = _seed(tmp_path)
    generate_onboarding.create(config)()  # type: ignore[arg-type]
    default = (_out(tmp_path) / OVERVIEW_NAME).read_text(encoding="utf-8")

    generate_onboarding.create(config, summarizer=_ShoutySummarizer())()  # type: ignore[arg-type]
    shouted = (_out(tmp_path) / OVERVIEW_NAME).read_text(encoding="utf-8")

    assert default != shouted, "the artifact must record which summarizer wrote it"
    assert "- module summaries (085): `StructuralSummarizer`" in default
    assert "- module summaries (085): `_ShoutySummarizer`" in shouted
    manifest = json.loads((_out(tmp_path) / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["provenance"]["summarizer"] == "_ShoutySummarizer"


def test_the_same_summarizer_twice_is_byte_identical(tmp_path: Path) -> None:
    """AC4's other half — the stamp is a function of the configuration, not the clock (R4.2)."""
    config = _seed(tmp_path)
    generate_onboarding.create(config, summarizer=_ShoutySummarizer())()  # type: ignore[arg-type]
    first = [
        (name, (_out(tmp_path) / name).read_text(encoding="utf-8"))
        for name in (OVERVIEW_NAME, MANIFEST_NAME)
    ]
    generate_onboarding.create(config, summarizer=_ShoutySummarizer())()  # type: ignore[arg-type]
    for name, text in first:
        assert (_out(tmp_path) / name).read_text(encoding="utf-8") == text, name


def test_the_seam_name_is_read_off_the_object_that_ran(tmp_path: Path) -> None:
    """LESSONS 201-C2 — the label is derived from what ran, never from a config value."""
    assert implementation_name(None) == NONE
    assert implementation_name(_ShoutySummarizer()) == "_ShoutySummarizer"
    # An unset seam is not silently attributed to the default implementation's name.
    assert Provenance().as_dict() == {"layers": NONE, "prose": NONE, "summarizer": NONE}


def test_the_documented_prose_cap_is_the_real_one() -> None:
    """AC3's cost figure, guarded at its source — 198 added a slot and the doc's 33 went stale.

    A number written down beside its source rots at the speed of the source (LESSONS 200), so the
    fix is a guard, not a better copy.
    """
    from code_atlas.onboarding.prose import MAX_PROSE_CALLS, SLOT_LIMITS

    tools = Path("docs/TOOLS.md").read_text(encoding="utf-8")
    assert f"at most **{MAX_PROSE_CALLS}** whatever the repo's size" in tools
    for slot, limit in SLOT_LIMITS.items():
        assert f"{limit} {slot}" in tools, f"the per-slot table does not state {slot}={limit}"
    assert "one call per tour module" in tools, "the summarizer's own cost is not documented"
