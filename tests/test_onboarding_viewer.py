"""Task 116: the onboarding viewer is a navigable system map, not a paginated page dump.

089's viewer embedded a rendered body per module and answered the wrong question. This suite pins
the replacement: it renders the **112 dataset alone**, it is self-contained and offline, and every
figure on it is interpolated rather than written.

AC4, AC5 and AC6 have no static formulation — the page builds its content in the browser, so a
scan of the HTML sees zero rendered figures and a green grep would be a false green. These are
proven by running the page under ``node`` against ``tests/viewer_dom_stub.js``, which reports what
was actually rendered; every assertion stays here, in Python.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from code_atlas.config import Config
from code_atlas.onboarding.artifact import OUTPUT_DIR, VIEWER_NAME
from code_atlas.onboarding.dataset import (
    DATASET_VERSION,
    OnboardingDataset,
    build_dataset,
)
from code_atlas.onboarding.viewer import (
    _TEMPLATE,
    NAMESPACE,
    SECTION_IDS,
    render_viewer,
)
from code_atlas.store import GraphStore
from code_atlas.tools import generate_onboarding
from scripts.viewer_report import (
    ANCHOR_INDEX_BYTES,
    ANCHOR_PATHS,
    BUDGET_WITH_INDEX,
    BUDGET_WITHOUT_INDEX,
    PATH_INDEX_MAX,
    anchor_scale_paths,
    synthetic_dataset,
)
from tests.test_guided_tour import _cycle_repo
from tests.test_nav_tools import db_config, edge, node, seed_file

STUB = Path(__file__).with_name("viewer_dom_stub.js")
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

# The anchor-scale generator, the budgets and the anchor's measured index size all live in
# scripts/viewer_report.py, imported above: the committed measurement and this suite must assert the
# same thing, and two copies of a generator would silently drift (tests/test_cross_repo_validation
# imports from scripts/ on the same grounds).
_anchor_paths = anchor_scale_paths


def _dataset(
    paths: list[str],
    *,
    path_index_max: int = 20000,
    scale: int = 1,
    commit: str = "0123456789abcdef",
    dir_symbol_threshold: int = 400,
    reverse_graph: bool = False,
) -> OnboardingDataset:
    """A dataset built the real way — ``build_dataset`` over synthetic nodes and edges.

    ``scale`` multiplies every count the store would have supplied, which is how the AC4 mutation
    test moves every figure without changing the shape.
    """
    nodes = [(f"\\Sym{index}", path) for index, path in enumerate(paths)]
    edges = [
        (f"\\Sym{index}", f"\\Sym{(index * 7 + 1) % len(paths)}")
        for index in range(0, len(paths), 3)
    ]
    if reverse_graph:
        nodes, edges = nodes[::-1], edges[::-1]
    return build_dataset(
        nodes,
        edges,
        files=len(paths) * scale,
        parsed=(len(paths) - 3) * scale,
        node_kind_counts=[("Class", 11 * scale), ("Method", 97 * scale), ("Property", 41 * scale)],
        edge_kind_counts=[("CALLS", 53 * scale), ("EXTENDS", 17 * scale)],
        confidence={"EXACT": 29 * scale, "HEURISTIC": 13 * scale},
        hubs=[(paths[0], 71 * scale, 23 * scale), (paths[1], 67 * scale, 19 * scale)],
        classes=[("\\Big", paths[0], 83 * scale), ("\\Small", paths[1], 31 * scale)],
        file_symbol_counts=[(path, 199 * scale) for path in paths],
        file_paths=paths,
        path_index_max=path_index_max,
        dir_symbol_threshold=dir_symbol_threshold,
        reachability_sample_max=5,
        file_class_counts=[(path, 3 * scale) for path in paths],
        module_max=50,
        mirror_sample_max=5,
        file_kind_counts=[
            (path, kind, count * scale)
            for path in paths
            for kind, count in (("Class", 2), ("Method", 7), ("Property", 5))
        ],
        commit=commit,
    )


def _payload(html: str) -> dict[str, object]:
    match = re.search(
        r'<script type="application/json" id="dataset">(.*?)</script>', html, flags=re.DOTALL
    )
    assert match is not None
    found = json.loads(match.group(1))
    assert isinstance(found, dict)
    return found


def _report(
    tmp_path: Path, html: str, *queries: str, probes: tuple[str, ...] = ()
) -> dict:
    """Run the page under node and return the harness's report (AC4/AC5/AC6)."""
    page = tmp_path / "map.html"
    page.write_text(html, encoding="utf-8")
    argv = [shutil.which("node") or "node", str(STUB), str(page)]
    for query in queries:
        argv += ["--search", query]
    for probe in probes:
        argv += ["--path", probe]
    done = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    parsed = json.loads(done.stdout)
    assert isinstance(parsed, dict)
    return parsed


# --------------------------------------------------------------------------- the proving test


def test_the_map_answers_the_spatial_question_the_page_dump_could_not() -> None:
    """Proving test (R6.5). Observed red: 089's payload carried none of these keys.

    Its payload was ``crossings · layers · isolated · method · pages · stops · truncated`` — a
    reading order and a rendered body per module. The ticket's complaint is that a reader "cannot
    see from it where the system's classes and modules sit", so the spatial aggregates being
    *present* is the fix, and their absence is the defect.
    """
    html = render_viewer(_dataset(_anchor_paths(400, 80)), 50)
    payload = _payload(html)

    for key in (
        "tree",
        "matrix",
        "hubs",
        "classes",
        "modules",
        "mirrors",
        "reachability",
        "path_index",
        "commit",
        "dir_symbol_threshold",
    ):
        assert key in payload, key
    assert payload["version"] == DATASET_VERSION
    # And the dump itself is gone: no rendered module body rides along.
    assert "pages" not in payload and "stops" not in payload


# --------------------------------------------------------------------------- AC1, AC2, AC3, AC7


def test_ac1_the_page_is_self_contained_and_opens_from_the_filesystem() -> None:
    """AC1: no external stylesheet, script, font or image, and nothing that could fetch one."""
    html = render_viewer(_dataset(_anchor_paths(200, 40)), 50)

    assert html.startswith("<!DOCTYPE html>")
    assert '<html lang="en"' in html
    assert "connect-src 'none'" in html
    assert "default-src 'none'" in html
    for banned in ("<script src", "<link ", "fetch(", "XMLHttpRequest", "http://", "https://",
                   "@import", "url(http", "<img", "WebSocket"):
        assert banned not in html, banned
    low = html.lower()
    for banned in ("cdn", "googleapis", "unpkg", "jsdelivr"):
        assert banned not in low, banned
    # R2.2's unit twin, widened to every literal the prototype carried (task 116 analysis).
    denied = re.compile(
        r"laravel|symfony|wordpress|drupal|magento|nikic|roslyn"
        r"|\bphp\b|javascript|typescript|csharp|phpunit|psr-4"
        r"|legacy/|\baus\b|\bnz\b|webapp|databasewrapper|tcpdf|mpdf|assessments|wsdl"
        r"|\bzend\b|simplesaml|log4php",
        re.I,
    )
    assert denied.search(html) is None, denied.search(html)


def test_ac2_an_anchor_scale_dataset_renders_under_the_size_budget(tmp_path: Path) -> None:
    """AC2: under 1 MB with the path index, under 150 KB without it.

    Observed red: rendering an anchor-scale artifact through 089's viewer measured 921,746 B —
    6.1x over the without-index budget, because 500 embedded module bodies *were* the payload.
    """
    assert len(_anchor_paths()) == ANCHOR_PATHS

    # The dataset comes from scripts/viewer_report.py, so the number asserted here is the number
    # that script prints. An ad-hoc fixture is not a substitute: an earlier one used 199 symbols
    # per file, which put every directory over the prune threshold and doubled the page.
    with_index = render_viewer(synthetic_dataset(PATH_INDEX_MAX), 50)
    index_bytes = len(
        json.dumps(_payload(with_index)["path_index"], ensure_ascii=True).encode("utf-8")
    )
    # The synthetic must be at least as heavy as the real thing, or the budget proves nothing.
    assert index_bytes >= ANCHOR_INDEX_BYTES, (index_bytes, ANCHOR_INDEX_BYTES)
    assert len(with_index.encode("utf-8")) < BUDGET_WITH_INDEX

    without_index = render_viewer(synthetic_dataset(0), 50)
    assert len(without_index.encode("utf-8")) < BUDGET_WITHOUT_INDEX
    # Dropping the index must not drop a section: the map still renders without search.
    assert _payload(without_index)["path_index"]["truncated"] is True
    for section in SECTION_IDS:
        assert f'id="{section}"' in without_index


def test_ac3_the_same_dataset_renders_identical_bytes() -> None:
    """AC3 (R4.2): the dataset is the sole input, so rendering is a pure function of it."""
    paths = _anchor_paths(600, 120)
    first = render_viewer(_dataset(paths), 50)
    assert render_viewer(_dataset(paths), 50) == first
    # And the graph's argument order cannot move a byte. The path list is deliberately NOT in
    # this claim: `_path_index` caps a prefix, so its order is part of the dataset's content,
    # not of its assembly (dataset.py).
    assert render_viewer(_dataset(paths, reverse_graph=True), 50) == first


def test_ac7_there_is_one_viewer_and_it_no_longer_reads_the_artifact() -> None:
    """AC7: replaced, not duplicated — one renderer, and it does not touch the page bodies."""
    source = Path("code_atlas/onboarding/viewer.py").read_text(encoding="utf-8")
    assert "render_module" not in source
    assert "OnboardingArtifact" not in source
    assert "viewer_payload" not in source, "089's second payload shape must be gone, not kept"

    viewers = sorted(
        path.name
        for path in Path("code_atlas/onboarding").glob("*.py")
        if "render_viewer" in path.read_text(encoding="utf-8")
    )
    assert viewers == ["viewer.py"]


def test_ac7_generate_onboarding_writes_the_map(tmp_path: Path) -> None:
    """AC7: the tool emits it, and regenerating is deterministic."""
    config = _cycle_repo(tmp_path)
    tool = generate_onboarding.create(config)
    payload = tool()
    html = (tmp_path / OUTPUT_DIR / VIEWER_NAME).read_text(encoding="utf-8")

    assert f"{OUTPUT_DIR}/{VIEWER_NAME}" in payload["results"]
    assert _payload(html)["version"] == DATASET_VERSION
    assert payload == tool()
    assert (tmp_path / OUTPUT_DIR / VIEWER_NAME).read_text(encoding="utf-8") == html


# --------------------------------------------------------------------------- AC4, AC5, AC6


def test_ac4_the_markup_itself_carries_no_number() -> None:
    """AC4, statically: strip the style and script blocks and no digit is left in the markup.

    This is the half of AC4 that can be checked without running anything, and it is exact: a
    figure written into the HTML by hand would show up here. It is also why the numbered section
    badges the prototype had (``01``..``11``) are gone — they were literal numbers, they carried
    nothing, and they would have made the behavioural half below inexact.
    """
    markup = re.sub(r"<style>.*?</style>", "", _TEMPLATE, flags=re.DOTALL)
    markup = re.sub(r"<script.*?</script>", "", markup, flags=re.DOTALL)
    assert "<style>" not in markup and "<script" not in markup
    # Only the visible text: an attribute may legitimately carry a digit (a charset, a viewport
    # scale, a padding), and none of those is a figure a reader could mistake for a measurement.
    text = re.sub(r"<[^>]*>", " ", markup)
    text = re.sub(r"&#\d+;|&[a-z]+;", " ", text)

    assert re.search(r"\d", text) is None, re.findall(r".{0,40}\d.{0,40}", text)


@needs_node
def test_ac4_every_counted_figure_moves_when_the_counts_move(tmp_path: Path) -> None:
    """AC4, behaviourally: scale every count and no rendered count survives.

    Scoped to figures of four digits or more, and that scoping is not a hedge — it is what makes
    the assertion exact. A short figure can legitimately be scale-invariant: the number of layers,
    of node kinds, of reachability buckets, and the prune threshold are all read from the dataset
    yet do not move when counts do. Anything with four digits here *is* a count, so it must move.
    """
    paths = _anchor_paths(900, 150)
    plain = _report(tmp_path, render_viewer(_dataset(paths), 50))
    moved = _report(
        tmp_path, render_viewer(_dataset(paths, scale=1009, commit="fedcba9876543210"), 50)
    )

    def counts(report: dict, section: str) -> set[str]:
        return {
            figure
            for figure in report["sections"][section]["figures"]
            if len(figure.replace(",", "")) >= 4
        }

    checked = 0
    for section in SECTION_IDS:
        before, after = counts(plain, section), counts(moved, section)
        if not before and not after:
            continue
        checked += 1
        # Either direction is the same claim: a count that moved cannot appear on both pages.
        survived = before & after
        assert not survived, (section, sorted(survived))
    assert checked >= 4, f"only {checked} sections displayed a four-digit count at all"


@needs_node
def test_ac5_the_legend_and_the_matrix_cover_every_layer(tmp_path: Path) -> None:
    """AC5: no silent cut — a "who calls whom" that omits participants is a trust bug."""
    report = _report(tmp_path, render_viewer(_dataset(_anchor_paths(900, 150)), 50))
    layers = report["layers"]

    assert len(layers) > 1
    assert sorted(report["legend"]) == sorted(layers)
    assert report["matrix"]["rows"] == len(layers)
    assert report["matrix"]["cols"] == len(layers)
    assert report["matrix"]["cells"] == len(layers) ** 2


@needs_node
def test_ac5_a_capped_section_says_so_in_the_section(tmp_path: Path) -> None:
    """AC5: a section that does cap states it, rather than looking exhaustive."""
    paths = _anchor_paths(900, 150)
    capped = _report(tmp_path, render_viewer(_dataset(paths, path_index_max=100), 50), "tree")
    whole = _report(tmp_path, render_viewer(_dataset(paths), 50), "tree")

    assert capped["search"]["tree"]["incomplete"] is True
    assert "may be a cap rather than an absence" in capped["sections"]["prov"]["text"]
    assert whole["search"]["tree"]["incomplete"] is False
    assert "a search miss is a real absence" in whole["sections"]["prov"]["text"]
    # The distinction is the point: an uncapped index must NOT hedge, or the hedge means nothing.
    assert "may be a cap" not in whole["sections"]["prov"]["text"]


@needs_node
def test_ac5_an_empty_sitemap_states_the_threshold_that_emptied_it(tmp_path: Path) -> None:
    """A blank treemap is a display bug indistinguishable from a data bug (task 116 analysis).

    Measured on the pinned public repos: at the shipped threshold, two of the three prune every
    directory away, so this is the common case on a small repo, not an edge case.
    """
    html = render_viewer(_dataset(_anchor_paths(60, 12), dir_symbol_threshold=10**9), 50)
    report = _report(tmp_path, html)

    assert report["tree"]["rows"] == 0
    text = report["sections"]["sitemap"]["text"]
    assert "1,000,000,000 symbols" in text
    assert "the pruning threshold, not a missing map" in text


@needs_node
def test_ac6_search_answers_hits_and_misses_over_the_embedded_index(tmp_path: Path) -> None:
    """AC6: search exercised headlessly, negative cases included."""
    paths = _anchor_paths(900, 150)
    report = _report(
        tmp_path,
        render_viewer(_dataset(paths), 50),
        "CompiledModule00007.aa",
        "component000",
        "zzz-no-such-path",
        "x",
    )

    exact = report["search"]["CompiledModule00007.aa"]
    assert exact["paths"] == 1 and exact["first"].endswith("CompiledModule00007.aa")

    broad = report["search"]["component000"]
    assert broad["paths"] > 40 and broad["cut"] > 0, broad

    assert report["search"]["zzz-no-such-path"]["shown"] == 0
    assert report["search"]["x"]["short"] is True


@needs_node
def test_ac6_counterpart_lookup_gives_all_four_answers(tmp_path: Path) -> None:
    """AC6: 115's four outcomes, in the browser — including the qualified negative (H6)."""
    left = [f"one/m/File{index:04d}.aa" for index in range(40)]
    right = [f"two/m/File{index:04d}.aa" for index in range(39)]
    paths = sorted(left + right)

    shared, only_left = "one/m/File0000.aa", "one/m/File0039.aa"
    whole = _report(
        tmp_path, render_viewer(_dataset(paths), 50), probes=(shared, only_left)
    )
    answers = whole["counterpart"]
    assert answers[shared]["status"] == "counterpart"
    assert answers[shared]["path"] == "two/m/File0000.aa"
    assert answers["definitely/not/indexed.xyz"]["status"] == "outside_mirror"
    assert answers[only_left]["status"] == "no_counterpart"
    assert answers[only_left]["qualified"] is False

    # H6: over a capped index a negative cannot tell a diverged file from a trimmed one, so it
    # is qualified. Without this, the two are indistinguishable and divergence is the whole point.
    trimmed = _report(
        tmp_path,
        render_viewer(_dataset(paths, path_index_max=20), 50),
        probes=(only_left,),
    )
    assert trimmed["counterpart"][only_left]["status"] == "no_counterpart"
    assert trimmed["counterpart"][only_left]["qualified"] is True


@needs_node
def test_the_flat_tree_is_closed_under_its_parents(tmp_path: Path) -> None:
    """The treemap nests a flat list; a missing parent would silently drop a whole subtree.

    Symbols accumulate on every prefix in ``dataset._tree``, so a kept child implies a kept
    parent. This asserts the invariant rather than the implementation.
    """
    report = _report(tmp_path, render_viewer(_dataset(_anchor_paths(3000, 400)), 50))
    assert report["tree"]["rows"] > 0
    assert report["tree"]["closed_under_parents"] is True


# --------------------------------------------------------------------------- kept from 089


BREAKOUT_FILE = "a</script><img src=x onerror=alert(1)>.aa"


def _breakout_repo(tmp_path: Path) -> Config:
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            BREAKOUT_FILE,
            [node("Class", "X", "\\X", BREAKOUT_FILE)],
            [edge("CALLS", "\\X", "\\Z", BREAKOUT_FILE, target_qname="\\Z")],
            root=tmp_path,
        )
        seed_file(store, "z.aa", [node("Class", "Z", "\\Z", "z.aa")], [], root=tmp_path)
    return config


def test_a_repo_path_cannot_break_out_of_the_dataset_script_tag(tmp_path: Path) -> None:
    """Made to fail: drop the ``<`` escape in ``render_viewer`` and this goes red."""
    generate_onboarding.create(_breakout_repo(tmp_path))()
    html = (tmp_path / OUTPUT_DIR / VIEWER_NAME).read_text(encoding="utf-8")

    assert html.count("</script>") == 2, "only the two template script tags may close"
    assert "<img src=x onerror" not in html
    # The index is front-coded, so a path is its directory plus its file name — and this path
    # holds a `/` inside the injected markup, which is exactly why it must be reassembled.
    index = _payload(html)["path_index"]
    dirs = index["dirs"]
    rebuilt = {f"{dirs[i]}/{name}" if dirs[i] else name for i, name in index["entries"]}
    assert BREAKOUT_FILE in rebuilt, "the path is still readable, just not executable"


def test_the_page_degrades_without_scripting_and_names_its_companions(tmp_path: Path) -> None:
    """A blank page is not an offline viewer: say where the markdown is."""
    generate_onboarding.create(_cycle_repo(tmp_path))()
    html = (tmp_path / OUTPUT_DIR / VIEWER_NAME).read_text(encoding="utf-8")

    assert "<noscript" in html
    assert "overview.md" in html and "tour.md" in html
    assert NAMESPACE in html


def test_the_viewer_is_refused_when_the_tree_is_not_ours(tmp_path: Path) -> None:
    """index.html without a manifest is someone else's file (088-C1 / 050)."""
    config = _cycle_repo(tmp_path)
    foreign = tmp_path / OUTPUT_DIR / VIEWER_NAME
    foreign.parent.mkdir(parents=True, exist_ok=True)
    foreign.write_text("<!DOCTYPE html><title>hand</title>\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not written by generate_onboarding"):
        generate_onboarding.create(config)()

    assert foreign.read_text(encoding="utf-8") == "<!DOCTYPE html><title>hand</title>\n"


def test_unbuilt_generate_does_not_write_a_viewer(tmp_path: Path) -> None:
    generate_onboarding.create(db_config(tmp_path))()
    assert not (tmp_path / OUTPUT_DIR / VIEWER_NAME).exists()


def test_the_harness_itself_is_committed_and_runnable() -> None:
    """A headless gate that silently vanishes proves nothing (R6.5)."""
    assert STUB.is_file()
    assert shutil.which("node") is not None or sys.platform == "win32"


# --- 117: the headline strip reaches the page ------------------------------------------------


@needs_node
def test_the_headline_facts_reach_the_overview_section(tmp_path: Path) -> None:
    """117 — the dataset's headlines render as prose in the overview, not just in the payload."""
    dataset = _dataset(_anchor_paths(400, 80))
    report = _report(tmp_path, render_viewer(dataset, 50))
    text = report["sections"]["overview"]["text"]
    assert dataset.headlines, "the fixture produced no headline candidate"
    for row in dataset.headlines:
        assert row.label.upper() in text.upper(), row.key
        assert row.text[:40] in text, row.key


@needs_node
def test_a_dataset_with_no_headline_renders_the_page_without_one(tmp_path: Path) -> None:
    """A repo the families have nothing to say about gets no strip, not an empty box."""
    from dataclasses import replace

    bare = replace(_dataset(_anchor_paths(400, 80)), headlines=())
    report = _report(tmp_path, render_viewer(bare, 50))
    assert report["sections"]["overview"]["text"], "the overview lost its own content"
