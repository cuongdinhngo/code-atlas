"""Task 244 — stamped capabilities ride ``get_index_status`` at ``standard``.

Honesty fields that only appear in a tool *response* never reach a non-caller. The session's
first call is ``get_index_status`` at default ``standard``; ``capabilities_by_language`` was
already stamped (231) but never attached there. Spec-driven fixtures reuse 183's ``fake``/
``second`` adapters (R2/R6.2).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from code_atlas import adapter
from code_atlas.config import load_config
from code_atlas.store import (
    CAPABILITIES_BY_LANGUAGE_KEY,
    COVERED_LANGUAGES_KEY,
    GraphStore,
)
from code_atlas.tools import get_index_status
from code_atlas.tools.build_or_update_index import create as build_tool
from tests.test_edge_health_per_language import (
    ONE_ADAPTER,
    TWO_ADAPTERS,
    write,
)

FIELD = get_index_status.CAPABILITIES_BY_LANGUAGE_FIELD

# Stamp-shaped field on the fixture; gate the cheap path (061 / 223).
STANDARD_DELTA_BUDGET_BYTES = 200

CAPS_TWO = {"fake": {"params": True}, "second": {"params": True, "args": False}}
CAPS_ONE = {"fake": {"params": True}}


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


def plant_caps(config, caps: dict[str, dict[str, bool]]) -> None:
    with GraphStore(config.db_path) as store:
        store.set_meta(CAPABILITIES_BY_LANGUAGE_KEY, json.dumps(caps))


def standard(config) -> dict[str, object]:
    return get_index_status.create(config, (get_index_status.NAME,))(detail_level="standard")


def test_standard_carries_stamped_capabilities_by_language(tmp_path: Path) -> None:
    """AC: ``standard`` carries the stamp; ``minimal`` stays quiet; stamp mutation is visible."""
    write(tmp_path, "lib/core.aa")
    write(tmp_path, "other/x.cc")
    config = build(tmp_path, TWO_ADAPTERS)
    plant_caps(config, CAPS_TWO)
    tool = get_index_status.create(config, (get_index_status.NAME,))
    payload = tool(detail_level="standard")

    assert FIELD in payload
    assert payload[FIELD] == CAPS_TWO
    assert FIELD not in tool(detail_level="minimal")

    # Guard: if the mechanism stops reflecting a stamped capability change, this fails.
    plant_caps(config, {"fake": {"params": True}, "second": {"params": False}})
    updated = tool(detail_level="standard")
    assert updated[FIELD] == {
        "fake": {"params": True},
        "second": {"params": False},
    }


def test_nothing_to_disclose_stays_byte_identical(tmp_path: Path) -> None:
    """R5.6 / 061: pre-stamp, empty stamp, and all-false flags omit the field."""
    write(tmp_path, "lib/core.aa")
    config = build(tmp_path, ONE_ADAPTER)
    tool = get_index_status.create(config, (get_index_status.NAME,))

    with GraphStore(config.db_path) as store:
        store.delete_meta(CAPABILITIES_BY_LANGUAGE_KEY)
    silent = tool(detail_level="standard")
    assert FIELD not in silent

    plant_caps(config, {})
    empty = tool(detail_level="standard")
    assert FIELD not in empty
    assert empty == silent

    plant_caps(config, {"fake": {"params": False, "args": False}})
    all_false = tool(detail_level="standard")
    assert FIELD not in all_false
    assert all_false == silent


def test_single_language_with_a_true_flag_announces(tmp_path: Path) -> None:
    """A single language with a true flag is something to disclose (instance 1)."""
    write(tmp_path, "lib/core.aa")
    config = build(tmp_path, ONE_ADAPTER)
    plant_caps(config, CAPS_ONE)
    assert standard(config)[FIELD] == CAPS_ONE


def test_standard_payload_delta_under_budget(tmp_path: Path) -> None:
    """AC: added cost on the cheap path is measured and bounded."""
    write(tmp_path, "lib/core.aa")
    write(tmp_path, "other/x.cc")
    config = build(tmp_path, TWO_ADAPTERS)
    plant_caps(config, CAPS_TWO)
    tool = get_index_status.create(config, (get_index_status.NAME,))
    with_field = tool(detail_level="standard")
    assert FIELD in with_field
    without = {k: v for k, v in with_field.items() if k != FIELD}
    delta = len(json.dumps(with_field, sort_keys=True)) - len(
        json.dumps(without, sort_keys=True)
    )
    assert 0 < delta <= STANDARD_DELTA_BUDGET_BYTES


def test_a_configured_language_with_no_indexed_file_is_not_announced(tmp_path: Path) -> None:
    """Review: 231 stamps every adapter that announced, not every language the graph holds.

    An unfiltered map answers for a language this index has no file of — paid on the session's
    most expensive call, about a question this index cannot answer either way (061 / 173).
    """
    write(tmp_path, "lib/core.aa")  # only `fake` has files; `second` is configured and empty
    config = build(tmp_path, TWO_ADAPTERS)
    plant_caps(config, CAPS_TWO)
    assert standard(config)[FIELD] == {"fake": {"params": True}}


def test_a_pre_173_index_is_not_filtered_on_a_stamp_it_lacks(tmp_path: Path) -> None:
    """R5.6: no coverage stamp is not evidence of no coverage — announce the whole map."""
    write(tmp_path, "lib/core.aa")
    config = build(tmp_path, TWO_ADAPTERS)
    plant_caps(config, CAPS_TWO)
    with GraphStore(config.db_path) as store:
        store.delete_meta(COVERED_LANGUAGES_KEY)
    assert standard(config)[FIELD] == CAPS_TWO
