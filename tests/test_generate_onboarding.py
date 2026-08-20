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

from code_atlas.config import Config
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

    # The tour is now 5–15 grouped steps, not one line per file (111). A step names ≤5 modules
    # and folds a cycle into one "cycle of N" line, so B rides A's step, unnamed.
    assert tour.index(f"`{ROUTES}`") < tour.index(f"`{A}`")
    assert tour.index(f"`{A}`") < tour.index(f"`{LEAF}`")
    assert tour.count(f"`{A}`") == 1
    assert "cycle of 2 modules" in tour

    # The manifest is now the aggregate dataset (112) + the operational page-delete record. The
    # reading order lives in tour.md (asserted above); the manifest no longer dumps per-stop rows.
    assert manifest["version"] >= 1
    assert isinstance(manifest["node_counts"], list) and isinstance(manifest["layers"], list)
    assert manifest["pages"] == sorted(manifest["pages"])
    assert "modules/" + A + ".md" in manifest["pages"]

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
    assert recorded_pages('{"pages": ["modules/app/A.aa.md"]}') == ("modules/app/A.aa.md",)
    assert recorded_pages("not json") == ()
    assert recorded_pages("[]") == ()
    assert recorded_pages('{"pages": "nope"}') == ()
    for hostile in ("../../etc/passwd", "/etc/passwd", "modules/../../x.md", "notes.md"):
        assert recorded_pages(json.dumps({"pages": [hostile]})) == ()


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
    assert payload["isolated_modules"] == 3
    # The manifest's page record (the 050 delete-list) names only the pages actually written:
    # the connected pair, never a suppressed isolated module.
    assert set(manifest["pages"]) == {"modules/src/A.aa.md", "modules/src/B.aa.md"}
    for path in isolated:
        assert "modules/" + path + ".md" not in manifest["pages"]


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


def test_generate_onboarding_path_index_cap_trims_and_states_both_numbers(tmp_path: Path) -> None:
    """AC6 (112): a small path-index cap trims the dataset, which then carries both numbers, and
    the artifact still passes the 109 quality gate (build_artifact runs it, so a green run proves
    C5 survives the dataset reduction)."""
    config = replace(_sparse_repo(tmp_path), path_index_max=2)
    payload = generate_onboarding.create(config)()
    assert payload["reason"] == REASON_OK  # the gate did not reject the tree
    manifest = json.loads((_out(tmp_path) / "manifest.json").read_text(encoding="utf-8"))
    path_index = manifest["path_index"]
    assert path_index["truncated"] is True
    assert path_index["total"] == 5  # three isolated modules + the connected pair
    assert path_index["shown"] == 2
    assert len(path_index["entries"]) == 2


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


CAP = 5


def _wide_repo(tmp_path: Path) -> Config:
    """A hub with 2*CAP callees and a 2*CAP-member cycle — both exceed a CAP-sized cap (108)."""
    from tests.test_nav_tools import edge, node, seed_file

    config = replace(db_config(tmp_path), max_results=CAP, impact_max_nodes=500)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            "src/Hub.aa",
            [node("Class", "Hub", "\\Hub", "src/Hub.aa")],
            [
                edge("CALLS", "\\Hub", f"\\L{i:02d}", "src/Hub.aa", target_qname=f"\\L{i:02d}")
                for i in range(2 * CAP)
            ],
            root=tmp_path,
        )
        for i in range(2 * CAP):
            path = f"leaf/L{i:02d}.aa"
            seed_file(
                store, path, [node("Class", f"L{i:02d}", f"\\L{i:02d}", path)], [], root=tmp_path
            )
        for i in range(2 * CAP):
            path = f"cyc/C{i:02d}.aa"
            nxt = (i + 1) % (2 * CAP)
            seed_file(
                store,
                path,
                [node("Class", f"C{i:02d}", f"\\C{i:02d}", path)],
                [edge("CALLS", f"\\C{i:02d}", f"\\C{nxt:02d}", path, target_qname=f"\\C{nxt:02d}")],
                root=tmp_path,
            )
    return config


def _page(tmp_path: Path, relpath: str) -> str:
    return (_out(tmp_path) / "modules" / Path(relpath + ".md")).read_text(encoding="utf-8")


def test_module_page_caps_neighbours_and_scc(tmp_path: Path) -> None:
    """Proving test (AC1, R6.5): a page with 2*CAP neighbours lists exactly CAP and names the cut.

    Observed red against pre-108 code: ``render_module`` joined the whole tuple, so the page listed
    all 2*CAP paths and carried no ``(N shown of M)`` marker.
    """
    generate_onboarding.create(_wide_repo(tmp_path))()

    hub = _page(tmp_path, "src/Hub.aa")
    out_line = next(line for line in hub.splitlines() if line.startswith("- outgoing:"))
    assert out_line.count("`") == 2 * CAP  # CAP back-ticked paths, two ticks each
    assert f"({CAP} shown of {2 * CAP})" in out_line
    assert "`leaf/L04.aa`" in out_line and "`leaf/L05.aa`" not in out_line

    stop_line = next(line for line in _page(tmp_path, "cyc/C00.aa").splitlines()
                     if line.startswith("Stop "))
    assert "cycle with " in stop_line
    assert f"({CAP} shown of {2 * CAP})" in stop_line
    assert "cyc/C04.aa" in stop_line and "cyc/C05.aa" not in stop_line


def test_page_distinguishes_cut_empty_and_uncut(tmp_path: Path) -> None:
    """AC2: a cut list names both numbers; a real zero keeps 107's ``_absent`` wording."""
    generate_onboarding.create(_wide_repo(tmp_path))()

    hub = _page(tmp_path, "src/Hub.aa")
    assert "- outgoing: `leaf/L00.aa`" in hub  # cut list starts with the paths, not a marker
    assert f"({CAP} shown of {2 * CAP})" in hub
    assert "- incoming: (none)\n" in hub  # a genuine zero, not a cut

    leaf = _page(tmp_path, "leaf/L00.aa")
    assert "- outgoing: (none)\n" in leaf
    assert "- incoming: `src/Hub.aa`\n" in leaf  # one neighbour, uncut, no marker
    assert "shown of" not in leaf


def test_scc_stop_line_is_capped_and_byte_identical_across_members(tmp_path: Path) -> None:
    """AC3: every member of a > CAP cycle prints the same capped cycle description (R4.2)."""
    generate_onboarding.create(_wide_repo(tmp_path))()

    def cycle_desc(name: str) -> str:
        page = _page(tmp_path, f"cyc/{name}.aa")
        line = next(row for row in page.splitlines() if row.startswith("Stop "))
        return line[line.index("cycle with"):]

    first, last = cycle_desc("C00"), cycle_desc("C09")
    assert first == last  # byte-identical capped member list
    assert f"({CAP} shown of {2 * CAP})" in first


def test_manifest_and_payload_agree_with_pages_on_the_cut(tmp_path: Path) -> None:
    """AC5: the cut is carried by ``truncated`` in both the payload and the manifest."""
    payload = generate_onboarding.create(_wide_repo(tmp_path))()
    manifest = json.loads((_out(tmp_path) / "manifest.json").read_text(encoding="utf-8"))

    assert payload["truncated"] is True
    assert manifest["truncated"] is True
    assert "shown of" in _page(tmp_path, "src/Hub.aa")  # the flag is not lying


def test_capped_page_stays_small_where_uncapped_blows_past_8kb() -> None:
    """AC4: on a page reproducing the 82 KB shape, the default cap brings it well under 8 KB.

    Rendering with an enormous cap reproduces pre-108 (uncapped) bytes, so this is a before/after.
    """
    from code_atlas.onboarding.artifact import ModulePage, render_module

    scc = tuple(f"app/domain/service/module/Component{i:03d}.aa" for i in range(300))
    neighbours = tuple(f"app/domain/service/module/Neighbour{i:03d}.aa" for i in range(300))
    page = ModulePage(
        file="app/domain/service/module/Hub.aa",
        relpath="modules/app/domain/service/module/Hub.aa.md",
        layer="app",
        rank=0,
        role="entry-point",
        docline="",
        rationale="cycle with " + ", ".join(scc),
        scc=scc,
        index=1,
        of=300,
        outgoing=neighbours,
        incoming=neighbours,
        fan_in=300,
        fan_out=300,
    )
    before = len(render_module(page, 10**9).encode("utf-8"))
    after = len(render_module(page, 50).encode("utf-8"))
    assert before > 8192, before
    assert after < 8192, after
