"""195: the two reachability payloads carry the per-language split beside the blend.

183 split `edge_health` per language and wired it into `get_index_status`. Round 12 §13 asked the
question the split exists for — *"HEURISTIC share for the JS/TS slice?"* — and recorded **"Cannot
answer. No per-language breakdown exists in any payload."* `find_orphans` and `reachable_from` were
two of the payloads it could not answer from: both walk **across** languages, so the blended figure
is genuinely this answer's denominator, and it is still uninterpretable on its own.

The two-language harness is 183's, imported rather than rebuilt — its languages are the fixture
adapter's arbitrary tokens `fake` and `second`, never a real language name (R6.2/R2).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from code_atlas.store import EDGE_HEALTH_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import find_orphans, reachable_from
from tests.test_edge_health_per_language import (
    ONE_ADAPTER,
    TWO_ADAPTERS,
    build,
    only_these_adapters_ship,  # noqa: F401 — an autouse fixture, used by being imported
    seed_two_languages,
    total_by_tier,
)

FIELD = "edge_health_by_language"
ENTRY = "dep/a.aa"

TOOLS = ("find_orphans", "reachable_from")


def _call(name: str, config) -> dict[str, object]:
    if name == "find_orphans":
        return find_orphans.create(config)(detail_level="standard")
    return reachable_from.create(config)(detail_level="standard")


def _two_language_index(tmp_path: Path):
    seed_two_languages(tmp_path)
    return build(tmp_path, {**TWO_ADAPTERS, "CA_ENTRY_POINTS": ENTRY})


@pytest.mark.parametrize("tool", TOOLS)
def test_the_payload_carries_the_split_beside_the_blend(tmp_path: Path, tool: str) -> None:
    """AC2 — the blended `edge_health` alone is what round 12 could not attribute."""
    payload = _call(tool, _two_language_index(tmp_path))

    assert "edge_health" in payload, "the blend is the denominator and must not be dropped"
    block = payload[FIELD]
    assert sorted(dict(block["by_language"])) == ["fake", "second"]  # type: ignore[index]


@pytest.mark.parametrize("tool", TOOLS)
def test_the_slices_still_sum_to_the_blend_in_this_payload(tmp_path: Path, tool: str) -> None:
    """AC3 / C1 — 183's reconciliation is the only check an outside reader has, so it is pinned
    HERE too: a split that does not sum to the number beside it is worse than no split."""
    payload = _call(tool, _two_language_index(tmp_path))

    assert total_by_tier(payload[FIELD]) == payload["edge_health"]["by_tier"]  # type: ignore[index]


@pytest.mark.parametrize("tool", TOOLS)
def test_each_language_has_its_own_heuristic_share(tmp_path: Path, tool: str) -> None:
    """The +9.6 pp round 12 could not attribute is attributable from this payload alone."""
    by_language = dict(_call(tool, _two_language_index(tmp_path))[FIELD]["by_language"])  # type: ignore[index]

    assert by_language["fake"]["by_tier"]["HEURISTIC"] > 0  # type: ignore[index]
    assert by_language["second"]["by_tier"]["HEURISTIC"] > 0  # type: ignore[index]


@pytest.mark.parametrize("tool", TOOLS)
def test_a_one_language_index_still_carries_the_split(tmp_path: Path, tool: str) -> None:
    """One language is a measurement, not a reason to omit the field: a reader cannot otherwise
    tell a single-language graph from an index that never measured itself."""
    seed_two_languages(tmp_path)
    payload = _call(tool, build(tmp_path, {**ONE_ADAPTER, "CA_ENTRY_POINTS": ENTRY}))

    assert sorted(dict(payload[FIELD]["by_language"])) == ["fake"]  # type: ignore[index]


@pytest.mark.parametrize("tool", TOOLS)
def test_a_pre_183_index_omits_the_field_rather_than_claiming_one_language(
    tmp_path: Path, tool: str
) -> None:
    """R5.6 — the stamp is absent on an index built before 183, and a computed fallback would put
    the GROUP BY the stamp exists to avoid back on the answer path. Absent, never invented."""
    config = _two_language_index(tmp_path)
    with GraphStore(config.db_path) as store:
        store.set_meta(EDGE_HEALTH_BY_LANGUAGE_KEY, "")

    payload = _call(tool, config)

    assert FIELD not in payload
    assert "edge_health" in payload  # the blend it could always report is unaffected


@pytest.mark.parametrize("tool", TOOLS)
def test_minimal_asks_for_neither_number(tmp_path: Path, tool: str) -> None:
    """The split rides with the blend: 061 — a detail level that dropped one must drop both."""
    config = _two_language_index(tmp_path)

    payload = (
        find_orphans.create(config)(detail_level="minimal")
        if tool == "find_orphans"
        else reachable_from.create(config)(detail_level="minimal")
    )

    assert FIELD not in payload and "edge_health" not in payload
