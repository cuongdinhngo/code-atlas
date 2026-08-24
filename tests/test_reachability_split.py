"""Task 113 — the zero-inbound total is four populations, and one number misleads.

Each test names the acceptance criterion it proves. The fixtures are path-shape only: the classifier
never sees a language, and no library, framework or product name appears here either (AC2).
"""

from __future__ import annotations

import re
from pathlib import Path

from code_atlas.onboarding.layers import (
    LAYER_DESCRIPTIONS,
    assign_layers,
    responsibility_layer,
)
from code_atlas.onboarding.metrics import compute_metrics
from code_atlas.onboarding.reachability import (
    BUCKET_SPECS,
    BUCKETS,
    DYNAMIC,
    ISOLATED,
    LAYER_TESTS,
    LAYER_VENDOR,
    LAYER_WEB_ENTRY,
    NO_VOCABULARY_SIGNAL,
    TEST,
    VENDOR,
    WEB_ENTRY,
    classify_reachability,
)

# One file per bucket. `src/controller/Front` names a request role, `vendor/pkg/Lib` third-party
# code, `tests/unit/Case` a test; `src/domain/Loader` has an outbound edge but nothing inbound;
# `src/domain/Stray` has no edge either way. Every path is generic (AC2).
_NODES: list[tuple[str, str]] = [
    ("App\\Front", "src/controller/Front.x"),
    ("Pkg\\Lib", "vendor/pkg/Lib.x"),
    ("Tests\\Case", "tests/unit/Case.x"),
    ("App\\Loader", "src/domain/Loader.x"),
    ("App\\Stray", "src/domain/Stray.x"),
    ("App\\Target", "src/domain/Target.x"),
    ("App\\Caller", "src/service/Caller.x"),
]
# Caller → Target gives Target an inbound edge, so Target is NOT zero-inbound and must not appear
# in any bucket. Loader → Target gives Loader an outbound edge and no inbound one; Caller is the
# same shape (`src/service` names no bucket role), so the dynamic bucket legitimately holds two.
_EDGES: list[tuple[str, str]] = [("App\\Caller", "App\\Target"), ("App\\Loader", "App\\Target")]


def _split(**kwargs: object) -> object:
    metrics = compute_metrics(_NODES, _EDGES)
    return classify_reachability(metrics, sample_limit=10, **kwargs)  # type: ignore[arg-type]


def _counts(split: object) -> dict[str, int]:
    return {bucket.bucket: bucket.count for bucket in split.buckets}  # type: ignore[attr-defined]


def test_ac1_fixture_yields_one_count_per_bucket() -> None:
    """AC1 (R6.5) — the proving test: five populations, five counts, not one number."""
    split = _split()
    counts = _counts(split)
    assert set(counts) == set(BUCKETS), "every bucket must render, even at zero (AC4)"
    assert counts == {
        WEB_ENTRY: 1,
        VENDOR: 1,
        TEST: 1,
        DYNAMIC: 2,
        ISOLATED: 1,
    }
    # The raw total stays available and equals the sum: buckets partition the zero-inbound set.
    assert split.total == 6  # type: ignore[attr-defined]
    assert sum(counts.values()) == split.total  # type: ignore[attr-defined]


def test_ac1_buckets_are_disjoint_and_exclude_reached_modules() -> None:
    """AC1 — a module with an inbound edge is in no bucket, and no path lands in two."""
    split = _split()
    seen: list[str] = []
    for bucket in split.buckets:  # type: ignore[attr-defined]
        seen.extend(bucket.sample)
    assert len(seen) == len(set(seen)), "a path must land in exactly one bucket"
    assert "src/domain/Target.x" not in seen, "Target has an inbound edge — not zero-inbound"


def test_ac2_classifier_names_no_framework() -> None:
    """AC2 — no library, framework or product name in the classifier (the CI gate's unit twin)."""
    source = Path("code_atlas/onboarding/reachability.py").read_text(encoding="utf-8")
    denied = re.compile(r"laravel|symfony|wordpress|drupal|magento|tcpdf|mpdf|adodb", re.I)
    assert denied.search(source) is None


def test_ac2_bucket_membership_is_path_shape_only() -> None:
    """AC2 — membership is decided by path segments the 110 vocabulary already ratified."""
    assert responsibility_layer("src/controller/Front.x") == LAYER_WEB_ENTRY
    assert responsibility_layer("vendor/pkg/Lib.x") == LAYER_VENDOR
    assert responsibility_layer("tests/unit/Case.x") == LAYER_TESTS
    # Derived-from-source (R6.7): every layer the classifier keys off is one 110 can emit.
    for layer in (LAYER_WEB_ENTRY, LAYER_VENDOR, LAYER_TESTS):
        assert layer in LAYER_DESCRIPTIONS


def test_ac3_dynamic_is_not_dead_and_isolated_is_a_suspicion() -> None:
    """AC3 — a no-inbound file with outbound edges is never called dead; no-edge-either-way is a
    suspicion, not a verdict."""
    notes = {bucket.bucket: bucket.note for bucket in _split().buckets}  # type: ignore[attr-defined]
    assert "not dead code" in notes[DYNAMIC]
    assert "a list to check, not a conclusion" in notes[ISOLATED].lower()
    assert "dead" not in notes[ISOLATED].lower(), "the wording must not pronounce a verdict"


def test_ac3_a_view_like_file_with_no_inbound_is_not_in_the_suspicion_bucket() -> None:
    """AC3 — a template-shaped file loaded dynamically has outbound edges, so it is not suspect."""
    nodes = [("V\\Page", "src/view/Page.x"), ("A\\Helper", "src/lib/Helper.x")]
    edges = [("V\\Page", "A\\Helper")]
    split = classify_reachability(compute_metrics(nodes, edges), sample_limit=10)
    placement = {
        path: bucket.bucket
        for bucket in split.buckets
        for path in bucket.sample
    }
    assert placement["src/view/Page.x"] == DYNAMIC


def test_ac4_an_empty_bucket_renders_an_honest_zero() -> None:
    """AC4 — a repo with no vendored code still renders the vendor row, at zero."""
    nodes = [("App\\Front", "src/controller/Front.x"), ("T\\Case", "tests/unit/Case.x")]
    split = classify_reachability(compute_metrics(nodes, []), sample_limit=10)
    counts = {bucket.bucket: bucket.count for bucket in split.buckets}
    assert counts[VENDOR] == 0
    assert VENDOR in counts, "an empty bucket is a rendered zero, never an omitted row"
    assert split.dropped == ()


def test_ac5_unfillable_bucket_is_dropped_with_a_reason() -> None:
    """AC5 — when no path names any responsibility, the vocabulary buckets are dropped with the
    reason, never merged into another bucket and never shown as a misleading zero."""
    nodes = [("A\\One", "a/One.x"), ("A\\Two", "a/Two.x")]
    edges = [("A\\One", "A\\Two")]
    metrics = compute_metrics(nodes, edges)
    assert assign_layers(metrics).method != "responsibility"
    split = classify_reachability(metrics, sample_limit=10)
    counts = {bucket.bucket: bucket.count for bucket in split.buckets}
    assert set(counts) == {DYNAMIC, ISOLATED}, "structural buckets are always fillable"
    assert dict(split.dropped) == {
        WEB_ENTRY: NO_VOCABULARY_SIGNAL,
        VENDOR: NO_VOCABULARY_SIGNAL,
        TEST: NO_VOCABULARY_SIGNAL,
    }
    # The dropped counts went nowhere else: the remaining buckets still sum to the raw total.
    assert sum(counts.values()) == split.total


def test_ac5_an_operator_declaration_keeps_its_bucket_alive() -> None:
    """AC5 — a declared dependency root stands on its own, whatever the paths look like."""
    nodes = [("A\\One", "a/One.x"), ("D\\Two", "d/Two.x")]
    split = classify_reachability(
        compute_metrics(nodes, []), stub_roots=("d",), sample_limit=10
    )
    counts = {bucket.bucket: bucket.count for bucket in split.buckets}
    assert counts[VENDOR] == 1, "the declaration filled the bucket without the path signal"
    assert dict(split.dropped) == {WEB_ENTRY: NO_VOCABULARY_SIGNAL, TEST: NO_VOCABULARY_SIGNAL}


def test_declared_entry_point_glob_outranks_the_path_signal() -> None:
    """The operator's own statement is the highest-trust signal, so it is checked first."""
    nodes = [("T\\Case", "tests/unit/Case.x")]
    split = classify_reachability(
        compute_metrics(nodes, []), entry_points=("tests/**",), sample_limit=10
    )
    counts = {bucket.bucket: bucket.count for bucket in split.buckets}
    assert counts[WEB_ENTRY] == 1
    assert counts[TEST] == 0


def test_ac3_test_path_outranks_request_handling_vocabulary() -> None:
    """AC3 (130) — deepest-wins would call this HTTP / Entry; reachability puts it in test."""
    fixture = Path("tests/fixtures/php/reachability_collision")
    assert (fixture / "src/controller/Front.php").is_file()
    assert (fixture / "tests/controller/FrontTest.php").is_file()
    web = "src/controller/Front.php"
    collision = "tests/controller/FrontTest.php"
    nodes = [("App\\Front", web), ("Tests\\FrontTest", collision)]
    split = classify_reachability(compute_metrics(nodes, []), sample_limit=10)
    placement = {
        path: bucket.bucket for bucket in split.buckets for path in bucket.sample
    }
    assert placement[web] == WEB_ENTRY
    assert placement[collision] == TEST
    counts = _counts(split)
    assert sum(counts.values()) == split.total
    web_bucket = next(b for b in split.buckets if b.bucket == WEB_ENTRY)
    test_bucket = next(b for b in split.buckets if b.bucket == TEST)
    assert sum(count for _, count in web_bucket.signals) == web_bucket.count
    assert sum(count for _, count in test_bucket.signals) == test_bucket.count


def test_sample_is_bounded_and_says_so() -> None:
    """The worth-investigating bucket is a bounded sample plus a count (ticket Scope, bullet 2)."""
    nodes = [(f"A\\N{i}", f"a/N{i}.x") for i in range(5)]
    split = classify_reachability(compute_metrics(nodes, []), sample_limit=2)
    isolated = next(b for b in split.buckets if b.bucket == ISOLATED)
    assert isolated.count == 5
    assert len(isolated.sample) == 2
    assert isolated.sample_truncated is True


def test_output_is_byte_stable_and_bucket_order_is_fixed() -> None:
    """R4.2 — identical input yields an identical split, in the BUCKET_SPECS reading order."""
    first = _split().as_dict()  # type: ignore[attr-defined]
    second = classify_reachability(
        compute_metrics(list(reversed(_NODES)), list(reversed(_EDGES))), sample_limit=10
    ).as_dict()
    assert first == second
    order = [bucket["bucket"] for bucket in first["buckets"]]  # type: ignore[index]
    assert order == [spec[0] for spec in BUCKET_SPECS]


def test_every_bucket_spec_carries_a_label_signal_and_note() -> None:
    """109's no-filler principle, at bucket grain: no row may ship with empty prose."""
    for bucket_id, label, signal, note in BUCKET_SPECS:
        assert bucket_id and label and signal and note
    assert len(BUCKETS) == len(set(BUCKETS)) == len(BUCKET_SPECS)
