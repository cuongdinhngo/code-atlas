"""Task 196 — the committed system map says which language earned its confidence figure.

195 re-pointed the two payload consumers of the whole-graph `edge_health()` blend and deferred the
third: `generate_onboarding`. Its figure is a genuinely whole-repo headline, so the number is right
— and on a two-language index it is a blend that names no language, in front of the one audience
PILLAR 2 exists for. This suite pins the attribution, and pins the three states where it may not be
shown at all.

Spec-driven (R2): the two languages are the fixture adapter's arbitrary tokens `fake` and `second`,
never a real language name.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.onboarding.artifact import OUTPUT_DIR, VIEWER_NAME
from code_atlas.onboarding.dataset import (
    DATASET_VERSION,
    MISMATCH_NOTE,
    NO_EDGES_NOTE,
    NO_STAMP_NOTE,
    ConfidenceSplit,
    KindCount,
    LanguageConfidence,
    _confidence_split,
)
from code_atlas.onboarding.viewer import render_viewer
from code_atlas.store import EDGE_HEALTH_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import generate_onboarding
from tests.test_edge_health_per_language import (
    TWO_ADAPTERS,
    build,
    only_these_adapters_ship,  # noqa: F401  — autouse fixture, imported for its side effect
    seed_two_languages,
)
from tests.test_onboarding_viewer import _dataset, _payload, _report, needs_node

WHOLE = {"EXACT": 6, "HEURISTIC": 4, "RESOLVED": 0}


def block(exact: int, heuristic: int, linked: int = 0) -> dict[str, object]:
    """One `_tier_block`-shaped bucket — the shape `store.py:660` writes into the stamp."""
    return {
        "by_tier": {"EXACT": exact, "HEURISTIC": heuristic, "RESOLVED": 0},
        "linked": linked,
        "unlinked": exact + heuristic - linked,
    }


# --------------------------------------------------------------------------- the proving test


@needs_node
def test_the_map_names_the_language_that_earned_the_figure(tmp_path: Path) -> None:
    """Proving test (R6.5). Observed red before the change: the rendered overview named no language.

    The whole path, not the field (198's lesson): a real two-adapter index, the real tool, and the
    page run under `node`, because a grep over the HTML sees zero rendered figures.
    """
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    generate_onboarding.create(config)()
    html = (tmp_path / OUTPUT_DIR / VIEWER_NAME).read_text(encoding="utf-8")

    overview = _report(tmp_path, html)["sections"]["overview"]["text"]
    assert "fake" in overview
    assert "second" in overview

    split = _payload(html)["confidence_by_language"]
    assert split["available"] is True
    assert [row["language"] for row in split["rows"]] == ["fake", "second"]


# --------------------------------------------------------------------------- AC1 — it reconciles


def test_ac1_the_split_is_read_from_the_stamp_and_adds_up_to_the_whole(tmp_path: Path) -> None:
    """AC1 + C1: the rows come from the 183 stamp and their tier counts sum to `confidence`."""
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    generate_onboarding.create(config)()
    payload = _payload((tmp_path / OUTPUT_DIR / VIEWER_NAME).read_text(encoding="utf-8"))

    whole = {row["tier"]: row["count"] for row in payload["confidence"]}
    summed: dict[str, int] = {}
    for row in payload["confidence_by_language"]["rows"]:
        for tier in row["tiers"]:
            summed[tier["tier"]] = summed.get(tier["tier"], 0) + tier["count"]

    assert {t: c for t, c in summed.items() if c} == {t: c for t, c in whole.items() if c}

    with GraphStore(config.db_path) as store:
        stamped = store.stamped_edge_health_by_language()
    assert stamped is not None
    assert sorted(dict(stamped["by_language"])) == ["fake", "second"]


def test_ac1_the_fold_sums_every_bucket_including_the_unattributed_one() -> None:
    """The `unattributed` bucket counts: dropping it would break the identity silently (183)."""
    split = _confidence_split(
        WHOLE, {"by_language": {"aa": block(4, 1)}, "unattributed": block(2, 3)}
    )
    assert split.available is True
    assert [row.language for row in split.rows] == ["aa", ""]


# ------------------------------------------------------- AC2 — the three states that show nothing


def test_ac2_a_pre_183_index_states_the_attribution_is_unavailable() -> None:
    """AC2 + R5.6: no stamp is *said*, never silently omitted and never guessed at."""
    split = _confidence_split(WHOLE, None)
    assert split.available is False
    assert split.rows == ()
    assert split.note == NO_STAMP_NOTE


@needs_node
def test_ac2_the_unavailable_statement_reaches_the_rendered_page(tmp_path: Path) -> None:
    """The consumer, not the field (198's F1): a note no renderer prints is not a statement."""
    dataset = _dataset_with(ConfidenceSplit(note=NO_STAMP_NOTE))
    overview = _report(tmp_path, render_viewer(dataset, 50))["sections"]["overview"]["text"]

    # The constant itself, so the assertion cannot drift from the wording it is checking.
    assert NO_STAMP_NOTE in overview


def test_ac2_a_stamp_that_does_not_add_up_is_refused_rather_than_shown() -> None:
    """A stale stamp describes an earlier tree; attributing this figure to it would be false."""
    split = _confidence_split(WHOLE, {"by_language": {"aa": block(1, 1)}})
    assert split.available is False
    assert split.rows == ()
    assert split.note == MISMATCH_NOTE


def test_ac2_an_index_with_no_dependencies_says_so_rather_than_claiming_a_mismatch() -> None:
    """Nothing to attribute is a different answer from a broken stamp, and reads as one."""
    split = _confidence_split({"EXACT": 0, "HEURISTIC": 0}, {"by_language": {}})
    assert split.available is False
    assert split.note == NO_EDGES_NOTE


# --------------------------------------------------------------- W2 — a single bucket is not hidden


def test_a_single_language_index_is_still_attributed_not_suppressed() -> None:
    """W2: `get_index_status` suppresses below two buckets for a payload's bytes (061).

    This is a document a human reads, and "every dependency here is one language" is a coverage
    fact they otherwise have to infer. The divergence is deliberate.
    """
    split = _confidence_split(WHOLE, {"by_language": {"aa": block(6, 4)}})
    assert split.available is True
    assert [row.language for row in split.rows] == ["aa"]


# ------------------------------------------------------------------------ AC3/AC4 — the versions


def test_ac3_the_dataset_version_moved_with_the_shape() -> None:
    """AC3: `confidence_by_language` is a new key on a published shape, so the version moves.

    196's key arrived AT version 10, and a bare `== 10` froze the future: 208 added a per-bucket
    caveat and broke this pin without breaking 196's claim. The durable form of that claim is the
    key's presence beside a version at or past the one it arrived at — `test_onboarding_dataset.py`
    owns the double-pin that makes each bump deliberate.
    """
    assert DATASET_VERSION >= 10


def test_ac4_the_adapter_contract_is_untouched() -> None:
    """AC4: `DATASET_VERSION` is the dataset's own version, never `contract_version` (R3)."""
    from code_atlas import contract

    assert "confidence_by_language" not in dir(contract)
    assert contract.CONTRACT_VERSION == 11


# ------------------------------------------- F1 — the stamp is READ, never recomputed on the spot


def test_the_split_is_read_from_the_stamp_and_not_recomputed_from_the_graph(tmp_path: Path) -> None:
    """The rule the ticket is most explicit about, made falsifiable (Scope 1, *not in scope*: no
    second measurement).

    Every other test builds once, so a live re-fold and the stamp agree and the two are
    indistinguishable. This doctors the stamp's language NAMES while keeping its arithmetic intact:
    the numbers still reconcile, so the split is shown — but it can only carry these names if it
    came from the stamp. Swap `stamped_edge_health_by_language()` for a live fold and this is the
    assertion that goes red.
    """
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    with GraphStore(config.db_path) as store:
        stamped = store.stamped_edge_health_by_language()
        assert stamped is not None
        renamed = {
            "by_language": {
                f"stamped_{name}": bucket
                for name, bucket in dict(stamped["by_language"]).items()
            }
        }
        if "unattributed" in stamped:
            renamed["unattributed"] = stamped["unattributed"]
        store.set_meta(EDGE_HEALTH_BY_LANGUAGE_KEY, json.dumps(renamed))

    generate_onboarding.create(config)()
    split = _payload((tmp_path / OUTPUT_DIR / VIEWER_NAME).read_text(encoding="utf-8"))[
        "confidence_by_language"
    ]

    assert split["available"] is True, "the doctored stamp still reconciles, so it must be shown"
    assert [row["language"] for row in split["rows"]] == ["stamped_fake", "stamped_second"]


# --------------------------------------- F2 — every refusal note reaches the page, not just one


@needs_node
@pytest.mark.parametrize("note", [NO_STAMP_NOTE, NO_EDGES_NOTE, MISMATCH_NOTE])
def test_every_refusal_state_reaches_the_rendered_page(tmp_path: Path, note: str) -> None:
    """All three, not only the one a single test happened to exercise."""
    overview = _report(tmp_path, render_viewer(_dataset_with(ConfidenceSplit(note=note)), 50))[
        "sections"
    ]["overview"]["text"]
    assert note in overview


# ------------------------------------------------ F4 — the per-language percentage is arithmetic


@needs_node
def test_the_rendered_share_is_the_heuristic_share_of_that_language(tmp_path: Path) -> None:
    """`pct(heur, all)` per row, asserted on a fixture whose answer is written down here.

    Without this, inverting the ternary or swapping the two arguments renders a wrong percentage
    that every other assertion in this file accepts.
    """
    split = ConfidenceSplit(
        rows=(
            LanguageConfidence("aa", (KindCount("EXACT", 3), KindCount("HEURISTIC", 1))),
            LanguageConfidence("bb", (KindCount("EXACT", 1), KindCount("HEURISTIC", 5))),
        ),
        available=True,
    )
    overview = _report(tmp_path, render_viewer(_dataset_with(split), 50))["sections"]["overview"][
        "text"
    ]

    assert "aa 4 dependencies (25% below exact)" in overview
    assert "bb 6 dependencies (83% below exact)" in overview


# --------------------------------------------------------------------------------------- helpers


def _dataset_with(split: ConfidenceSplit):
    """A real dataset, built the real way, carrying one confidence split."""
    return replace(_dataset(["a/one.aa", "a/two.aa", "b/three.aa"]), confidence_by_language=split)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
