"""Task 088: ``generate_onboarding`` writes structured markdown + a manifest (§12, PHASE3 §4).

CI asserts structure, dependency order, and determinism given a summarizer stub — not coherence
(PHASE3: coherence is a recorded manual check). The fixture uses the language-neutral ``.aa``
suffix so nothing in the proof knows which language produced the rows.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.onboarding.artifact import (
    H_CROSSINGS,
    H_IN_TOUR,
    H_LAYER,
    H_LAYERS,
    H_MODULE_SUMMARY,
    H_NEIGHBOURS,
    H_ORDER,
    H_OVERVIEW,
    H_ROLE,
    H_SUMMARY,
    H_TOUR,
    OUTPUT_DIR,
    recorded_pages,
)
from code_atlas.onboarding.summary import NodeFacts, Summary
from code_atlas.store import GraphStore
from code_atlas.tools import generate_onboarding
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
)
from tests.test_guided_tour import LEAF, ROUTES, A, B, _cycle_repo
from tests.test_nav_tools import db_config


class _StubSummarizer:
    """Fixed stub: every module page carries the same docline so the seam is observable."""

    def summarize(self, facts: NodeFacts) -> Summary:
        return Summary(
            key=facts.metric.key,
            signature="stub-sig",
            docline="STUB-DOCLINE",
            role="entry-point",
        )


def _out(root: Path) -> Path:
    return root / OUTPUT_DIR


def test_generate_onboarding_writes_structured_markdown_in_dependency_order(
    tmp_path: Path,
) -> None:
    """Proving test: expected sections, tour order, one file per stop, stub-stable bytes."""
    config = _cycle_repo(tmp_path)
    tool = generate_onboarding.create(config, _StubSummarizer())
    payload = tool()

    assert payload["indexed"] is True
    assert payload["reason"] == REASON_OK
    assert payload["output_dir"] == OUTPUT_DIR
    out = _out(tmp_path)
    overview = (out / "overview.md").read_text(encoding="utf-8")
    tour = (out / "tour.md").read_text(encoding="utf-8")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))

    for heading in (H_OVERVIEW, H_SUMMARY, H_LAYERS, H_CROSSINGS):
        assert heading in overview
    for heading in (H_TOUR, H_ORDER):
        assert heading in tour

    assert tour.index(f"`{ROUTES}`") < tour.index(f"`{A}`")
    assert tour.index(f"`{ROUTES}`") < tour.index(f"`{B}`")
    assert tour.index(f"`{A}`") < tour.index(f"`{LEAF}`")
    assert tour.index(f"`{B}`") < tour.index(f"`{LEAF}`")
    assert tour.count(f"`{A}`") == 1
    assert tour.count(f"`{B}`") == 1

    stops = [row["file"] for row in manifest["stops"]]
    assert stops[0] == ROUTES
    assert set(stops[1:3]) == {A, B}
    assert stops[-1] == LEAF
    assert stops == [row["file"] for row in manifest["stops"]]

    for path in (ROUTES, A, B, LEAF):
        page = out / "modules" / Path(path + ".md")
        text = page.read_text(encoding="utf-8")
        for heading in (H_ROLE, H_LAYER, H_MODULE_SUMMARY, H_IN_TOUR, H_NEIGHBOURS):
            assert heading in text
        assert f"# `{path}`" in text
        assert "STUB-DOCLINE" in text

    second = tool()
    assert payload == second
    assert (out / "overview.md").read_text(encoding="utf-8") == overview
    assert (out / "tour.md").read_text(encoding="utf-8") == tour
    assert (out / "manifest.json").read_text(encoding="utf-8") == json.dumps(
        manifest, sort_keys=True, ensure_ascii=False, indent=2
    ) + "\n"


def test_generate_onboarding_is_byte_stable_across_two_runs(tmp_path: Path) -> None:
    config = _cycle_repo(tmp_path)
    first = generate_onboarding.create(config)()
    overview = (_out(tmp_path) / "overview.md").read_bytes()
    tour = (_out(tmp_path) / "tour.md").read_bytes()
    manifest = (_out(tmp_path) / "manifest.json").read_bytes()
    cache = (tmp_path / ".code-atlas" / "onboarding" / "artifact.json").read_bytes()
    second = generate_onboarding.create(config)()
    assert first == second
    assert (_out(tmp_path) / "overview.md").read_bytes() == overview
    assert (_out(tmp_path) / "tour.md").read_bytes() == tour
    assert (_out(tmp_path) / "manifest.json").read_bytes() == manifest
    assert (tmp_path / ".code-atlas" / "onboarding" / "artifact.json").read_bytes() == cache


def test_generate_onboarding_unbuilt_is_not_indexed_and_writes_nothing(tmp_path: Path) -> None:
    unbuilt = generate_onboarding.create(db_config(tmp_path))()
    assert unbuilt["indexed"] is False
    assert unbuilt["reason"] == REASON_NOT_INDEXED
    assert unbuilt["results"] == []
    assert not _out(tmp_path).exists()
    assert not (tmp_path / "graph.db").exists()


def test_generate_onboarding_empty_index_is_no_matches(tmp_path: Path) -> None:
    config = db_config(tmp_path)
    with GraphStore(config.db_path):
        pass
    empty = generate_onboarding.create(config)()
    assert empty["indexed"] is True
    assert empty["reason"] == REASON_NO_MATCHES
    assert empty["results"] == []
    assert not _out(tmp_path).exists()


def test_generate_onboarding_minimal_omits_cache_path(tmp_path: Path) -> None:
    config = _cycle_repo(tmp_path)
    minimal = generate_onboarding.create(config)(detail_level="minimal")
    standard = generate_onboarding.create(config)()
    assert "cache" not in minimal
    assert "cache" in standard
    assert set(minimal) <= set(standard)
    assert minimal["results"] == standard["results"]


def test_generate_onboarding_names_no_language(tmp_path: Path) -> None:
    config = _cycle_repo(tmp_path)
    generate_onboarding.create(config)()
    blob = " ".join(
        path.read_text(encoding="utf-8").lower()
        for path in _out(tmp_path).rglob("*")
        if path.is_file()
    )
    for lang in ("php", "javascript", "typescript", "csharp", "roslyn", "nikic"):
        assert lang not in blob


def test_generate_onboarding_removes_its_own_stale_pages_but_not_a_hand_written_one(
    tmp_path: Path,
) -> None:
    """Regenerating is not a wipe: only pages the last manifest recorded are removed."""
    config = _cycle_repo(tmp_path)
    tool = generate_onboarding.create(config)
    tool()
    out = _out(tmp_path)
    mine = out / "modules" / Path(LEAF + ".md")
    hand = out / "modules" / "HAND_WRITTEN.md"
    hand.write_text("# a human wrote this\n", encoding="utf-8")
    assert mine.is_file()

    generate_onboarding.create(replace(config, impact_max_nodes=1))()

    assert not mine.exists(), "a page the previous manifest recorded should be regenerated away"
    assert hand.read_text(encoding="utf-8") == "# a human wrote this\n"


def test_generate_onboarding_refuses_a_tree_it_did_not_write(tmp_path: Path) -> None:
    """Our filenames without our manifest belong to somebody else — refuse, do not overwrite."""
    config = _cycle_repo(tmp_path)
    foreign = _out(tmp_path) / "overview.md"
    foreign.parent.mkdir(parents=True, exist_ok=True)
    foreign.write_text("# somebody else's overview\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not written by generate_onboarding"):
        generate_onboarding.create(config)()

    assert foreign.read_text(encoding="utf-8") == "# somebody else's overview\n"
    assert not (_out(tmp_path) / "manifest.json").exists()


def test_generate_onboarding_overview_discloses_a_truncated_map(tmp_path: Path) -> None:
    """A committed overview counting every module must say the pages cover only the budget."""
    config = replace(_cycle_repo(tmp_path), impact_max_nodes=1)
    payload = generate_onboarding.create(config)()
    overview = (_out(tmp_path) / "overview.md").read_text(encoding="utf-8")

    assert payload["truncated"] is True
    assert "- modules: 4" in overview
    assert "- module pages: 1" in overview
    assert "- truncated: true" in overview


def test_recorded_pages_deletes_nothing_it_cannot_prove_it_wrote() -> None:
    """A foreign, tampered or unparseable manifest yields no deletion list."""
    assert recorded_pages('{"modules": [{"page": "modules/app/A.aa.md"}]}') == (
        "modules/app/A.aa.md",
    )
    assert recorded_pages("not json") == ()
    assert recorded_pages("[]") == ()
    assert recorded_pages('{"modules": "nope"}') == ()
    for hostile in ("../../etc/passwd", "/etc/passwd", "modules/../../x.md", "notes.md"):
        assert recorded_pages(json.dumps({"modules": [{"page": hostile}]})) == ()


def _sparse_repo(tmp_path: Path) -> Path:
    """Isolated modules plus one connected pair — the shape task 107 measured on real repos.

    `laravel/laravel` emits 20 such pages of 26, `symfony/demo` 7 of 51: a module with no
    resolved edge in either direction and no docblock has nothing a page can say.
    """
    from tests.test_nav_tools import edge, node, seed_file

    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        for index in range(3):
            path = f"scripts/s{index:02d}.aa"
            seed_file(
                store,
                path,
                [node("Class", f"S{index:02d}", f"\\S{index:02d}", path)],
                [],
                root=tmp_path,
            )
        seed_file(
            store,
            "src/A.aa",
            [node("Class", "A", "\\A", "src/A.aa")],
            [edge("CALLS", "\\A", "\\B", "src/A.aa", target_qname="\\B")],
            root=tmp_path,
        )
        seed_file(
            store, "src/B.aa", [node("Class", "B", "\\B", "src/B.aa")], [], root=tmp_path
        )
    return config


def test_generate_onboarding_suppresses_a_contentless_page_and_counts_it(
    tmp_path: Path,
) -> None:
    """Proving test (107): a page saying only path + role + layer + three ``(none)``s is filler.

    It is not written, the overview counts what has no page, and the manifest names those
    modules with ``page: null`` instead of a dead link. The connected pair keeps its pages.
    """
    config = _sparse_repo(tmp_path)
    payload = generate_onboarding.create(config)()
    out = _out(tmp_path)
    overview = (out / "overview.md").read_text(encoding="utf-8")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))

    isolated = [f"scripts/s{index:02d}.aa" for index in range(3)]
    for path in isolated:
        assert not (out / "modules" / Path(path + ".md")).exists(), path
    for path in ("src/A.aa", "src/B.aa"):
        assert (out / "modules" / Path(path + ".md")).is_file(), path

    assert "- module pages: 2" in overview
    assert "- modules with no page (isolated, no summary): 3" in overview
    assert manifest["isolated"] == isolated
    assert payload["isolated_modules"] == 3
    # The reading order keeps every module; only the empty page is gone.
    stops = {row["file"]: row["page"] for row in manifest["stops"]}
    assert set(stops) == set(isolated) | {"src/A.aa", "src/B.aa"}
    assert [stops[path] for path in isolated] == [None, None, None]
    assert stops["src/A.aa"] == "modules/src/A.aa.md"


def test_generate_onboarding_keeps_a_page_whose_neighbours_the_budget_cut(
    tmp_path: Path,
) -> None:
    """A module with edges the walk could not afford keeps its page and states the count (102)."""
    config = replace(_cycle_repo(tmp_path), impact_max_nodes=1)
    generate_onboarding.create(config)()
    page = _out(tmp_path) / "modules" / Path(ROUTES + ".md")

    assert page.is_file(), "a module with real edges must not be suppressed as contentless"
    text = page.read_text(encoding="utf-8")
    assert "- outgoing: (none admitted in this tour; 1 in the full graph)" in text
    assert "- incoming: (none)" in text


def test_generate_onboarding_composition_is_byte_stable(tmp_path: Path) -> None:
    """The suppressed-page shape must stay deterministic (R4.2)."""
    config = _sparse_repo(tmp_path)
    first = generate_onboarding.create(config)()
    manifest = (_out(tmp_path) / "manifest.json").read_bytes()
    overview = (_out(tmp_path) / "overview.md").read_bytes()
    assert generate_onboarding.create(config)() == first
    assert (_out(tmp_path) / "manifest.json").read_bytes() == manifest
    assert (_out(tmp_path) / "overview.md").read_bytes() == overview


def test_generate_onboarding_deletes_a_page_that_became_contentless(tmp_path: Path) -> None:
    """AC3: a page the last manifest recorded is still removed once it is suppressed (050/088)."""
    config = _sparse_repo(tmp_path)
    with GraphStore(config.db_path) as store:  # give an isolated module one edge, then remove it
        from tests.test_nav_tools import edge, node, seed_file

        seed_file(
            store,
            "scripts/s00.aa",
            [node("Class", "S00", "\\S00", "scripts/s00.aa")],
            [edge("CALLS", "\\S00", "\\B", "scripts/s00.aa", target_qname="\\B")],
            root=tmp_path,
        )
    generate_onboarding.create(config)()
    page = _out(tmp_path) / "modules" / Path("scripts/s00.aa.md")
    assert page.is_file()

    with GraphStore(config.db_path) as store:
        from tests.test_nav_tools import node, seed_file

        seed_file(
            store,
            "scripts/s00.aa",
            [node("Class", "S00", "\\S00", "scripts/s00.aa")],
            [],
            root=tmp_path,
        )
    generate_onboarding.create(config)()
    assert not page.exists(), "the tool must remove a page it wrote once it turns contentless"
