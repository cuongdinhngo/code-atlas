"""Task 088: ``generate_onboarding`` writes structured markdown + a manifest (§12, PHASE3 §4).

CI asserts structure, dependency order, and determinism given a summarizer stub — not coherence
(PHASE3: coherence is a recorded manual check). The fixture uses the language-neutral ``.aa``
suffix so nothing in the proof knows which language produced the rows.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.config import Config
from code_atlas.onboarding.artifact import (
    ARTIFACT_VERSION,
    FLOWS_NAME,
    H_CROSSINGS,
    H_DIAGRAM,
    H_LAYERS,
    H_ORDER,
    H_OVERVIEW,
    H_SUMMARY,
    H_TOUR,
    MANIFEST_NAME,
    OUTPUT_DIR,
    OVERVIEW_NAME,
    TOUR_NAME,
    VIEWER_NAME,
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
from tests.test_guided_tour import LEAF, ROUTES, A, _cycle_repo
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

    for heading in (H_OVERVIEW, H_SUMMARY, H_LAYERS, H_DIAGRAM, H_CROSSINGS):
        assert heading in overview
    assert "```mermaid" in overview
    assert "flowchart LR" in overview
    for heading in (H_TOUR, H_ORDER):
        assert heading in tour

    # The tour is now 5–15 grouped steps, not one line per file (111). A step names ≤5 modules
    # and folds a cycle into one "cycle of N" line, so B rides A's step, unnamed.
    assert tour.index(f"`{ROUTES}`") < tour.index(f"`{A}`")
    assert tour.index(f"`{A}`") < tour.index(f"`{LEAF}`")
    assert tour.count(f"`{A}`") == 1
    assert "cycle of 2 modules" in tour

    # The manifest is the aggregate dataset (112) plus the doc pointers. The reading order lives
    # in tour.md (asserted above); the manifest dumps neither per-stop rows nor page paths (205).
    assert manifest["version"] >= 1
    assert isinstance(manifest["node_counts"], list) and isinstance(manifest["layers"], list)
    assert "pages" not in manifest  # 205 removed the per-module page tree with its record

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
    dumped = json.loads(cache)
    assert dumped["version"] == ARTIFACT_VERSION


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
    """A committed overview counting every module must say the walk covered only the budget."""
    config = replace(_cycle_repo(tmp_path), impact_max_nodes=1)
    payload = generate_onboarding.create(config)()
    overview = (_out(tmp_path) / "overview.md").read_text(encoding="utf-8")

    assert payload["truncated"] is True
    assert "- modules: 4" in overview
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


def test_the_overview_no_longer_counts_pages_or_isolated_modules(tmp_path: Path) -> None:
    """AC5' (205): the two page-count lines are gone, and so is the payload's ``isolated_modules``.

    Observed red against pre-205 code, which printed both lines and the key. 107's *isolated*
    bucket existed only to explain a page that was not written; with no page tree the fact it
    carried is the dataset's own no-edge-either-way reachability bucket.
    """
    config = _sparse_repo(tmp_path)
    payload = generate_onboarding.create(config)()
    overview = (_out(tmp_path) / "overview.md").read_text(encoding="utf-8")

    assert "- module pages:" not in overview
    assert "- modules with no page" not in overview
    assert "isolated_modules" not in payload
    # Every aggregate the ticket protects is still there, byte-for-byte (R4.2, ticket R6).
    assert "- modules: 5" in overview
    assert "- truncated: false" in overview


def test_generate_onboarding_composition_is_byte_stable(tmp_path: Path) -> None:
    """The emitted composition must stay deterministic (R4.2)."""
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


def test_a_pre_205_page_tree_is_cleaned_on_the_next_write(tmp_path: Path) -> None:
    """205's migration path (R5.7): the first write after 205 removes the pages a pre-205
    ``manifest.json`` recorded — exactly those, and nothing a hand wrote beside them.

    This is design assumption 4, proven rather than argued: the tool no longer writes a page, so
    without this the 500 pages already committed in a downstream repo would be stranded forever.
    """
    config = _sparse_repo(tmp_path)
    out = _out(tmp_path)
    pages = ("modules/src/A.aa.md", "modules/src/B.aa.md")
    for rel in pages:  # a tree in the pre-205 shape: the pages plus the manifest that records them
        page = out / Path(rel)
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("# a page the pre-205 tool wrote\n", encoding="utf-8")
    foreign = out / "modules" / "HAND-WRITTEN.md"
    foreign.write_text("# not ours\n", encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({"pages": list(pages)}), encoding="utf-8")

    generate_onboarding.create(config)()

    for rel in pages:
        assert not (out / Path(rel)).exists(), rel
    assert foreign.read_text(encoding="utf-8") == "# not ours\n"


# 205's ceiling on the committed Markdown. Measured on the anchor monorepo (24,535 indexed files,
# `max_results = 10`): overview.md 12,440 B + tour.md 5,798 B + flows.md 3,366 B = 21,604 B. The
# per-module tree that used to sit beside them was 481,616 B — 95.7 % of the Markdown — and it is
# gone (205). Nothing left in these three files scales with file count: the steps are capped by
# MAX_TOUR_STEPS (15), the layer lines by the prose slot limit (12), and every table by
# `max_results`. The tables DO scale with max_results, and the anchor runs it at 10 against a
# default of 50, so a default-configured repo of that size lands near 60-70 KB. 128 KiB is that
# figure with roughly 2x headroom. `tour_report.py`'s _TOUR_KB_CEILING = 64 is the same discipline
# on one file.
MAX_EMITTED_MARKDOWN_BYTES = 131_072


def _emitted(root: Path) -> dict[str, int]:
    """Every file the tool wrote, relative to the output dir, with its byte size."""
    out = _out(root)
    return {
        path.relative_to(out).as_posix(): path.stat().st_size
        for path in sorted(out.rglob("*"))
        if path.is_file()
    }


def test_the_emitted_tree_carries_no_module_pages(tmp_path: Path) -> None:
    """Proving test (AC1', 205): the emitted tree is the five documents and nothing else.

    Observed red against pre-205 code, which wrote one `modules/<path>.md` per tour stop — 500 of
    them on any repo the walk budget filled, because the count WAS `impact_max_nodes`. The file
    set is derived from the module's own name constants, never re-typed here (R6.7), so a sixth
    emitted file cannot ship unnoticed.
    """
    config = _cycle_repo(tmp_path)
    payload = generate_onboarding.create(config, _StubSummarizer())()

    expected = {OVERVIEW_NAME, TOUR_NAME, FLOWS_NAME, MANIFEST_NAME, VIEWER_NAME}
    assert set(_emitted(tmp_path)) == expected
    assert not (_out(tmp_path) / "modules").exists()
    assert payload["total_count"] == len(expected)
    assert all(not rel.startswith(f"{OUTPUT_DIR}/modules/") for rel in payload["results"])


def test_the_emitted_file_set_does_not_move_with_the_impact_budget(tmp_path: Path) -> None:
    """AC1': `impact_max_nodes` is the walk's budget and nothing else's.

    It used to decide how many files landed in a consumer's repo, through four hops that never
    meant to (124's class, second sighting). Two budgets, one file set.
    """
    tight = _cycle_repo(tmp_path)
    narrow = generate_onboarding.create(replace(tight, impact_max_nodes=1), _StubSummarizer())()
    narrow_set = set(_emitted(tmp_path))
    wide = generate_onboarding.create(replace(tight, impact_max_nodes=500), _StubSummarizer())()
    assert set(_emitted(tmp_path)) == narrow_set
    assert narrow["total_count"] == wide["total_count"] == len(narrow_set)


def test_no_emitted_file_cites_a_stop_position(tmp_path: Path) -> None:
    """AC2': one meaning for "stop".

    Observed red against pre-205 code: every page header read `Stop 65 of 500` while `tour.md`
    beside it numbered 15 narrative steps, so one word carried two units and nothing said so.
    """
    generate_onboarding.create(_cycle_repo(tmp_path), _StubSummarizer())()
    out = _out(tmp_path)
    files = [path for path in sorted(out.rglob("*")) if path.is_file()]
    citing = [
        path.name
        for path in files
        if re.search(r"Stop \d+ of \d+", path.read_text(encoding="utf-8", errors="replace"))
    ]
    assert files, "the sweep must not be able to empty itself (R6.5)"
    assert citing == []


def test_the_emitted_markdown_stays_under_its_ceiling(tmp_path: Path) -> None:
    """AC6: the committed Markdown has an asserted total, argued above, not merely recorded."""
    generate_onboarding.create(_cycle_repo(tmp_path), _StubSummarizer())()
    sizes = _emitted(tmp_path)
    markdown = {name: size for name, size in sizes.items() if name.endswith(".md")}

    assert set(markdown) == {OVERVIEW_NAME, TOUR_NAME, FLOWS_NAME}
    assert sum(markdown.values()) <= MAX_EMITTED_MARKDOWN_BYTES, markdown


def test_the_emitted_markdown_does_not_grow_with_the_repo(tmp_path: Path) -> None:
    """AC6, the half that makes the ceiling bite: the total is bounded by caps, not by file count.

    A ceiling asserted only on a four-file fixture would be slack by construction — the number
    could be anything. 133-C1's class: a per-element ceiling leaves the total free while the
    element count is free. Here a repo 20x larger must not produce 20x the Markdown.
    """
    small = _cycle_repo(tmp_path)
    generate_onboarding.create(small, _StubSummarizer())()
    small_bytes = sum(size for name, size in _emitted(tmp_path).items() if name.endswith(".md"))

    big_root = tmp_path / "big"
    big = _many_module_repo(big_root)
    generate_onboarding.create(big, _StubSummarizer())()
    big_bytes = sum(size for name, size in _emitted(big_root).items() if name.endswith(".md"))

    assert big_bytes <= MAX_EMITTED_MARKDOWN_BYTES, big_bytes
    assert big_bytes < small_bytes * 4, (small_bytes, big_bytes)


def _many_module_repo(root: Path) -> Config:
    """80 modules in one chain — 20x the cycle fixture, to show the Markdown does not follow."""
    from tests.test_nav_tools import edge, node, seed_file

    config = db_config(root)
    with GraphStore(config.db_path) as store:
        for index in range(80):
            path = f"src/M{index:02d}.aa"
            nxt = f"\\M{index + 1:02d}"
            seed_file(
                store,
                path,
                [node("Class", f"M{index:02d}", f"\\M{index:02d}", path)],
                [edge("CALLS", f"\\M{index:02d}", nxt, path, target_qname=nxt)]
                if index < 79
                else [],
                root=root,
            )
    return config


def _wide_repo(root: Path) -> Config:
    """A hub with 2*max_results callees and a 2*max_results-member cycle (task 108's shape).

    Pre-205 this index set `truncated` — not because the walk cut anything, but because a page's
    neighbour list was capped. It is the fixture that separates the flag's two old meanings.
    """
    from tests.test_nav_tools import edge, node, seed_file

    cap = 5
    config = replace(db_config(root), max_results=cap, impact_max_nodes=500)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            "src/Hub.aa",
            [node("Class", "Hub", "\\Hub", "src/Hub.aa")],
            [
                edge("CALLS", "\\Hub", f"\\L{i:02d}", "src/Hub.aa", target_qname=f"\\L{i:02d}")
                for i in range(2 * cap)
            ],
            root=root,
        )
        for i in range(2 * cap):
            path = f"leaf/L{i:02d}.aa"
            seed_file(
                store, path, [node("Class", f"L{i:02d}", f"\\L{i:02d}", path)], [], root=root
            )
    return config


def test_truncated_now_answers_only_the_walk_question(tmp_path: Path) -> None:
    """AC5', the exception the byte comparison alone did not cover.

    `list_truncated` folded *"a page's neighbour or SCC list was capped"* into the same flag as
    *"the walk left an indexed file out"* — one field, two questions (189/022/202). With no page
    there is no neighbour list to cut, so reporting a cut would attest to something the artifact no
    longer contains (R5.6). The flag therefore narrows, and `overview.md`'s `- truncated:` line
    moves with it on exactly this class of index — which is a THIRD difference from the pre-change
    run, beside the two deleted count lines, and it is pinned here rather than left to a claim.

    Observed red against pre-205 code, which reported `truncated: true` on the wide fixture.
    """
    wide = _wide_repo(tmp_path)
    payload = generate_onboarding.create(wide, _StubSummarizer())()
    overview = (_out(tmp_path) / OVERVIEW_NAME).read_text(encoding="utf-8")

    assert payload["truncated"] is False, "no page, so no capped page list to report"
    assert "- truncated: false" in overview

    cut_root = tmp_path / "cut"
    cut = replace(_cycle_repo(cut_root), impact_max_nodes=1)
    assert generate_onboarding.create(cut, _StubSummarizer())()["truncated"] is True


def test_the_tool_surfaces_do_not_promise_a_module_page_tree() -> None:
    """AC7 (R7.6): the superseded promises are deleted from both surfaces, not stacked on."""
    tools_md = (Path(__file__).resolve().parent.parent / "docs" / "TOOLS.md").read_text(
        encoding="utf-8"
    )
    for superseded in (
        "Tour and pages bounded by",
        "isolated_modules",
        "tour · flows · per-module",
    ):
        assert superseded not in tools_md, superseded
    assert "There is no per-module page tree" in tools_md

    doc = generate_onboarding.create(db_config(Path(__file__).parent)).__doc__ or ""
    assert "per-module page tree" in doc
    assert "isolated_modules" not in doc
