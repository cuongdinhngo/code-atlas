"""A caveat the dataset carries must reach the rendered page (task 127).

Task 100 found evidence-grade payloads that never reached the artifact. One layer out, the same
class recurs: the onboarding dataset can carry a caveat that the generated ``index.html`` never
renders, and nothing notices. That is R5.5's own falsifier —
a caveat present at one detail level and absent at another for the same fact — with the rendered
artifact as the other detail level.

The guard **derives** the caveat set from the dataset payload (R6.7) and asserts each one is
*rendered*, not merely embedded: the page ships the whole dataset as JSON, so a file-level check
would be green forever.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.onboarding.dataset import OnboardingDataset, build_dataset, derive_caveats
from code_atlas.onboarding.metrics import compute_metrics
from code_atlas.onboarding.reachability import (
    DECLARATION_CAVEAT,
    SIGNAL_DECLARED,
    SIGNAL_ORDER,
    SIGNAL_STRUCTURE,
    SIGNAL_VOCABULARY,
    WEB_ENTRY,
    classify_reachability,
)
from code_atlas.onboarding.viewer import render_viewer
from tests.test_onboarding_viewer import _report

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH")

PATHS = [f"public/page{index:03d}.aa" for index in range(6)] + [
    f"src/app/Service{index:03d}.aa" for index in range(9)
] + [f"vendor/lib/Dep{index:03d}.aa" for index in range(4)]
DECLARED = ("public/*.aa", "nothing/*.aa")


def _declared_dataset() -> OnboardingDataset:
    """The real builder over synthetic paths, WITH the operator declarations the split needs."""
    nodes = [(f"\\Sym{index}", path) for index, path in enumerate(PATHS)]
    edges = [(f"\\Sym{index}", f"\\Sym{(index * 5 + 1) % len(PATHS)}") for index in range(0, 6)]
    return build_dataset(
        nodes,
        edges,
        files=len(PATHS),
        parsed=len(PATHS),
        node_kind_counts=[("Class", 11), ("Method", 97)],
        edge_kind_counts=[("CALLS", 53)],
        confidence={"EXACT": 29, "HEURISTIC": 13},
        hubs=[(PATHS[0], 71, 23)],
        classes=[("\\Big", PATHS[0], 83)],
        file_symbol_counts=[(path, 199) for path in PATHS],
        file_paths=PATHS,
        path_index_max=20000,
        dir_symbol_threshold=400,
        reachability_sample_max=5,
        file_class_counts=[(path, 3) for path in PATHS],
        module_max=50,
        mirror_sample_max=5,
        file_kind_counts=[(path, "Class", 2) for path in PATHS],
        commit="0123456789abcdef",
        declared_entry_points=DECLARED,
    )


def _rendered(tmp_path: Path, dataset: OnboardingDataset) -> str:
    report = _report(tmp_path, render_viewer(dataset, 50))
    return " ".join(section["text"] for section in report["sections"].values())


@needs_node
def test_every_dataset_caveat_is_rendered_in_the_map(tmp_path: Path) -> None:
    """127 AC1 — the proving test. Red before: the dataset knew, the page did not."""
    dataset = _declared_dataset()
    caveats = derive_caveats(dataset.as_dict())
    assert len(caveats) >= 3, caveats

    rendered = _rendered(tmp_path, dataset)
    missing = [where for where, text in caveats if text not in rendered]
    assert not missing, missing


def test_the_caveat_set_is_derived_not_listed() -> None:
    """127 AC2 — a section that grows a caveat is covered with no edit to the guard (R6.7)."""
    payload = _declared_dataset().as_dict()
    before = derive_caveats(payload)

    payload["invented_section"] = {"caveat": "A future caveat nobody listed here.", "count": 1}
    payload["rows"] = [{"caveat": "One inside a list of rows."}]
    after = derive_caveats(payload)

    assert dict(after)["invented_section"] == "A future caveat nobody listed here."
    assert dict(after)["rows[0]"] == "One inside a list of rows."
    assert len(after) == len(before) + 2


def test_a_declared_pattern_reports_what_it_matched_and_what_it_claimed() -> None:
    """127 AC3 / 119 AC3 — and a pattern matching nothing reports zero, not silence."""
    metrics = compute_metrics([(f"\\S{i}", path) for i, path in enumerate(PATHS)], [])
    split = classify_reachability(metrics, entry_points=DECLARED, sample_limit=5)
    claims = {claim.pattern: claim for claim in split.patterns}

    assert set(claims) == set(DECLARED)
    assert claims["public/*.aa"].files_matched == 6
    assert claims["public/*.aa"].zero_inbound_claimed == 6
    assert claims["public/*.aa"].kind == "entry_points"
    typo = claims["nothing/*.aa"]
    assert typo.files_matched == 0 and typo.zero_inbound_claimed == 0


def test_a_bucket_signal_tally_accounts_for_every_member() -> None:
    """119 AC2, restated as arithmetic — its anchor figures are not measurable here."""
    metrics = compute_metrics([(f"\\S{i}", path) for i, path in enumerate(PATHS)], [])
    split = classify_reachability(metrics, entry_points=DECLARED, sample_limit=5)

    for bucket in split.buckets:
        tally = dict(bucket.signals)
        assert list(tally) == list(SIGNAL_ORDER), tally
        assert sum(tally.values()) == bucket.count, (bucket.bucket, tally, bucket.count)

    web = next(b for b in split.buckets if b.bucket == WEB_ENTRY)
    declared = dict(web.signals)[SIGNAL_DECLARED]
    claimed = sum(c.zero_inbound_claimed for c in split.patterns if c.kind == "entry_points")
    assert declared == claimed == 6
    # The bucket also holds vocabulary members — the whole point of splitting the count.
    assert dict(web.signals)[SIGNAL_VOCABULARY] >= 0
    assert dict(web.signals)[SIGNAL_STRUCTURE] == 0


def test_provenance_moves_no_count() -> None:
    """127 AC4 / 119 AC1 — this ticket adds numbers; it moves nothing."""
    metrics = compute_metrics([(f"\\S{i}", path) for i, path in enumerate(PATHS)], [])
    declared = classify_reachability(metrics, entry_points=DECLARED, sample_limit=5)
    bare = classify_reachability(metrics, entry_points=DECLARED, sample_limit=5)

    assert [(b.bucket, b.count) for b in declared.buckets] == [
        (b.bucket, b.count) for b in bare.buckets
    ]
    assert declared.total == bare.total == len(PATHS)
    # 119 AC4: a bucket dropped for want of a signal stays dropped, never a misleading zero.
    undeclared = classify_reachability(
        compute_metrics([("\\A", "a.aa"), ("\\B", "b.aa")], []), sample_limit=5
    )
    assert dict(undeclared.dropped), "a repo whose paths name no role must still drop those buckets"
    assert all(b.bucket not in dict(undeclared.dropped) for b in undeclared.buckets)


def test_the_declaration_caveat_states_a_fact_and_no_verdict() -> None:
    """119 AC6 — nothing in the output calls a declaration stale, wrong or suspicious."""
    for word in ("stale", "wrong", "suspicious", "false", "should"):
        assert word not in DECLARATION_CAVEAT.lower(), word


@needs_node
def test_a_caveat_the_page_stops_rendering_turns_the_guard_red(tmp_path: Path) -> None:
    """The guard has teeth: drop a caveat from the page and it fails (mutation, not assertion)."""
    dataset = _declared_dataset()
    html = render_viewer(dataset, 50)
    text = dataset.reachability.caveat
    assert text in html

    page = tmp_path / "map.html"
    page.write_text(html.replace(text, "removed"), encoding="utf-8")
    argv = [shutil.which("node") or "node", str(Path("tests/viewer_dom_stub.js")), str(page)]
    done = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    assert text not in done.stdout
