"""Task 243 — the crossing census rides at ``standard``, not only inside verbose's 183 field.

Round 17 called ``get_index_status`` at the default ``standard`` and never saw ``cross_language``,
so the one number that says whether a multi-language index models crossings at all sat one
``detail_level`` above the reader. Spec-driven fixtures reuse 183's ``fake``/``second`` adapters
(R2/R6.2) — never a consumer language name.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from code_atlas import adapter
from code_atlas.config import load_config
from code_atlas.store import EDGE_HEALTH_BY_LANGUAGE_KEY, GraphStore
from code_atlas.tools import get_index_status
from code_atlas.tools.build_or_update_index import create as build_tool
from code_atlas.tools.get_index_status import EDGE_HEALTH_BY_LANGUAGE_FIELD
from tests.test_edge_health_per_language import (
    ONE_ADAPTER,
    TWO_ADAPTERS,
    seed_two_languages,
    write,
)

FIELD = "cross_language"
VERBOSE_FIELD = EDGE_HEALTH_BY_LANGUAGE_FIELD

# Bounded summary on the two-language fixture is small; gate the cheap path (061 / 223).
STANDARD_DELTA_BUDGET_BYTES = 200


@pytest.fixture(autouse=True)
def only_these_adapters_ship(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "shipped"
    for name in ("fake", "second"):
        (root / name / "src").mkdir(parents=True)
    monkeypatch.setattr(adapter, "ADAPTERS_DIR", root)


def config_for(root: Path, env: dict[str, str]):
    return load_config(root, {**env, "CA_DB_PATH": str(root / ".code-atlas" / "graph.db")})


def build(root: Path, env: dict[str, str]):
    config = config_for(root, env)
    build_tool(config)(full=True)
    return config


def seed_two_languages_unlinked(root: Path) -> None:
    """Two languages, no linked crossing — the ``linked: 0`` reader signal."""
    write(root, "lib/core.aa")
    write(root, "dep/a.aa")
    write(root, "dep/extends_b.cc")
    write(root, "other/x.cc")


def standard(config) -> dict[str, object]:
    return get_index_status.create(config, (get_index_status.NAME,))(detail_level="standard")


def test_standard_carries_bounded_cross_language_on_a_multi_language_index(
    tmp_path: Path,
) -> None:
    """AC1: ``standard`` carries the census without ``pairs``; verbose still nests the full row."""
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    tool = get_index_status.create(config, (get_index_status.NAME,))
    payload = tool(detail_level="standard")

    assert FIELD in payload
    block = payload[FIELD]
    assert set(block) == {"by_tier", "linked", "unlinked"}
    assert "pairs" not in block
    assert int(block["linked"]) == 2  # type: ignore[index]
    assert FIELD not in tool(detail_level="minimal")

    verbose = tool(detail_level="verbose")
    assert FIELD in verbose
    assert "pairs" not in verbose[FIELD]  # type: ignore[operator]
    nested = verbose[VERBOSE_FIELD]["cross_language"]  # type: ignore[index]
    assert "pairs" in nested
    assert nested["pairs"] == {"second->fake": 2}


def test_linked_zero_is_the_reader_facing_signal(tmp_path: Path) -> None:
    """AC4: multi-language + ``linked: 0`` on ``standard`` (field, not a fake tool hint)."""
    seed_two_languages_unlinked(tmp_path)
    payload = standard(build(tmp_path, TWO_ADAPTERS))

    assert FIELD in payload
    assert payload[FIELD]["linked"] == 0  # type: ignore[index]
    assert "pairs" not in payload[FIELD]  # type: ignore[operator]
    assert "next_tool_suggestions" not in payload


def test_single_language_standard_stays_byte_identical(tmp_path: Path) -> None:
    """AC2/061: one language bucket omits the field — same as today."""
    write(tmp_path, "lib/core.aa")
    write(tmp_path, "dep/a.aa")
    config = build(tmp_path, ONE_ADAPTER)
    tool = get_index_status.create(config, (get_index_status.NAME,))
    before_keys = set(tool(detail_level="standard"))
    payload = tool(detail_level="standard")
    assert FIELD not in payload
    assert set(payload) == before_keys
    assert VERBOSE_FIELD not in tool(detail_level="verbose")


def test_pre_204_index_says_nothing_rather_than_linked_zero(tmp_path: Path) -> None:
    """AC2/R5.6: no stamp → silence, never a fabricated ``linked: 0``."""
    seed_two_languages(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    with GraphStore(config.db_path) as store:
        store.delete_meta(EDGE_HEALTH_BY_LANGUAGE_KEY)
        assert store.stamped_cross_language_edges() is None

    payload = standard(config)
    assert FIELD not in payload


def test_standard_payload_delta_is_bounded(tmp_path: Path) -> None:
    """AC3: added bytes at ``standard`` stay under the cheap-path budget (061/223)."""
    seed_two_languages_unlinked(tmp_path)
    config = build(tmp_path, TWO_ADAPTERS)
    tool = get_index_status.create(config, (get_index_status.NAME,))
    with_field = tool(detail_level="standard")
    assert FIELD in with_field
    without = dict(with_field)
    without.pop(FIELD)
    delta = len(json.dumps(with_field, sort_keys=True)) - len(
        json.dumps(without, sort_keys=True)
    )
    # Fixture-scale delta; the summary drops ``pairs``, so anchor-scale cost is the same shape.
    assert 0 < delta < STANDARD_DELTA_BUDGET_BYTES, delta
