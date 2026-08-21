"""Task 117 — the headline facts: which ones exist is derived, only the wording is written.

Fixtures go through the real detectors (115's mirrors, 114's modules, 113's split) rather than
hand-built dataclasses, so a shape change upstream fails here instead of being papered over — the
`fixture-shape-begs-the-question` retro. Every path is shape only: no repo, framework or language
name appears here or in the module under test (R2.2).
"""

from __future__ import annotations

import re
from pathlib import Path

from code_atlas.contract import CALLABLE_KINDS, NODE_KINDS, TYPE_KINDS
from code_atlas.onboarding.headlines import HEADLINE_FAMILIES, headline_candidates
from code_atlas.onboarding.metrics import compute_metrics
from code_atlas.onboarding.mirrors import find_mirror_subtrees
from code_atlas.onboarding.modules import find_business_modules
from code_atlas.onboarding.prose import ProseRequest, ProseRun
from code_atlas.onboarding.reachability import classify_reachability

NODES = [
    ("Ctrl", "app/controller/Home.aa"),
    ("Svc", "app/service/Billing.aa"),
    ("Model", "app/model/Invoice.aa"),
    ("Lib", "app/lib/Money.aa"),
]
EDGES = [("Ctrl", "Svc"), ("Svc", "Model"), ("Model", "Lib")]
PATHS = [path for _, path in NODES]
MIRRORED = [f"{side}/s{index}.aa" for side in ("one", "two") for index in range(40)]


def _parts(*, paths: list[str] | None = None, mirror_paths: list[str] | None = None):
    """Every input `headline_candidates` takes, built by the real detectors."""
    metrics = compute_metrics(NODES, EDGES)
    files = paths if paths is not None else PATHS
    return {
        "node_kind_counts": [("Class", 4), ("Method", 12), ("Function", 4)],
        "edge_kind_counts": [("CALLS", 30), ("IMPORTS", 20)],
        "confidence": {"EXACT": 40, "HEURISTIC": 10},
        "hubs": [("app/lib/Money.aa", 25, 0)],
        "reachability": classify_reachability(metrics, sample_limit=5),
        "modules": find_business_modules(
            files, class_counts=dict.fromkeys(files, 1), fan_in={}, limit=10
        ),
        "mirrors": find_mirror_subtrees(mirror_paths or files, sample_limit=3),
    }


def test_every_family_that_has_something_to_say_says_it_once_in_a_fixed_order() -> None:
    """The candidate set is derived: fixed reading order, one row per family, no duplicates."""
    rows = headline_candidates(**_parts(mirror_paths=MIRRORED))
    keys = [row.key for row in rows]
    assert keys == [family for family in HEADLINE_FAMILIES if family in keys]
    assert len(keys) == len(set(keys))
    assert all(row.text.strip() and row.label for row in rows)


def test_a_family_with_no_fact_emits_no_sentence_rather_than_a_hollow_one() -> None:
    """AC6's premise — an absent fact is an absent row, so 109's C1 has nothing to catch."""
    parts = _parts()  # unmirrored paths, so 115 finds no pair
    rows = headline_candidates(**parts)
    assert "duplication" not in {row.key for row in rows}
    bare = dict(parts, hubs=[], edge_kind_counts=[], confidence={}, node_kind_counts=[])
    assert {row.key for row in headline_candidates(**bare)} <= {"reachability", "coverage"}


def test_the_duplication_headline_reports_the_pair_and_carries_its_caveat() -> None:
    """115's limit rides into the headline: paths compared, never file contents."""
    rows = {row.key: row for row in headline_candidates(**_parts(mirror_paths=MIRRORED))}
    text = rows["duplication"].text
    assert "one" in text and "two" in text and "40" in text
    assert "not file contents" in text


def test_the_abstraction_headline_reads_the_contract_and_never_re_lists_kinds() -> None:
    """R3/R6.7 — the type/callable split is a named subset of the contract's own vocabulary."""
    assert set(TYPE_KINDS) <= set(NODE_KINDS)
    assert set(CALLABLE_KINDS) <= set(NODE_KINDS)
    assert not set(TYPE_KINDS) & set(CALLABLE_KINDS)
    rows = {row.key: row for row in headline_candidates(**_parts())}
    # 4 Class, 12 Method + 4 Function = 16 callables, so 4 of 20 are types.
    assert "4 indexed symbols declare a type and 16 are callables" in rows["abstraction"].text
    assert "20 % of the 20" in rows["abstraction"].text


def test_the_seam_can_reword_a_headline_but_not_add_remove_or_reorder_one() -> None:
    """AC2 at the headline grain — enrichment owns wording and nothing else."""
    parts = _parts(mirror_paths=MIRRORED)
    plain = headline_candidates(**parts)

    class _Writer:
        def write(self, request: ProseRequest) -> str:
            return f"A rewritten sentence about the {request.key} of this codebase."

    written = headline_candidates(**parts, prose=ProseRun(_Writer()))
    assert [row.key for row in written] == [row.key for row in plain]
    assert [row.label for row in written] == [row.label for row in plain]
    assert all(row.text.startswith("A rewritten sentence") for row in written)


def test_the_candidates_are_byte_stable_under_input_reordering() -> None:
    """R4.2 — the derivation is order-free, so the headline block never churns a diff."""
    forward = _parts(mirror_paths=MIRRORED)
    backward = _parts(mirror_paths=list(reversed(MIRRORED)))
    assert [row.as_dict() for row in headline_candidates(**forward)] == [
        row.as_dict() for row in headline_candidates(**backward)
    ]


def test_no_repo_framework_or_language_name_in_the_headline_derivation() -> None:
    """R2.2 — the CI gate's unit twin over the two new core modules."""
    denied = re.compile(
        r"laravel|symfony|wordpress|drupal|magento|nikic|roslyn|\bphp\b|javascript|typescript"
        r"|csharp|phpunit|psr-4|legacy/|\baus\b|\bnz\b",
        re.I,
    )
    for name in ("headlines.py", "prose.py"):
        source = Path("code_atlas/onboarding") / name
        assert denied.search(source.read_text(encoding="utf-8")) is None, name
