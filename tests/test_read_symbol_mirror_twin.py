"""Task 286 — ``read_symbol`` names an indexed mirror twin (or the honest negative)."""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas.mirror_search import (
    MIRROR_COUNTERPART_FIELD,
    MIRROR_NO_COUNTERPART_FIELD,
    MIRROR_SEARCH_KEY,
    build_mirror_search_stamp,
)
from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol, search_symbol
from code_atlas.tools.nav_result import (
    AUTHORITATIVE_CAVEATS,
    CAVEAT_LIMITS_KEY,
    CAVEAT_MIRROR_TWIN,
)
from tests.test_nav_tools import db_config, node, seed_file
from tests.test_nav_tools import store as store  # noqa: F401 — pytest fixture


def _stamp_for_test(store: GraphStore) -> None:
    stamp = build_mirror_search_stamp(store, min_shared=1, min_overlap=0.1)
    assert stamp.get("pairs"), stamp
    store.set_meta(MIRROR_SEARCH_KEY, json.dumps(stamp, sort_keys=True))
    store.reload_mirror_search_stamp()


def _plant_pair(tmp_path: Path, store: GraphStore, *, with_west: bool = True) -> None:
    shared = "Widget.php"
    seed_file(
        store,
        f"mirrors/east/{shared}",
        [node("Class", "Widget", "East\\Widget", f"mirrors/east/{shared}")],
        [],
        root=tmp_path,
    )
    if with_west:
        seed_file(
            store,
            f"mirrors/west/{shared}",
            [node("Class", "Widget", "West\\Widget", f"mirrors/west/{shared}")],
            [],
            root=tmp_path,
        )
    for side in ("east", "west") if with_west else ("east",):
        seed_file(
            store,
            f"mirrors/{side}/Extra.php",
            [node("Class", "Extra", f"{side}\\Extra", f"mirrors/{side}/Extra.php")],
            [],
            root=tmp_path,
        )
    if with_west:
        _stamp_for_test(store)
    else:
        # Pair stamp with west prefix but west file missing from index.
        stamp = {
            "pairs": [
                {
                    "left": "mirrors/east",
                    "right": "mirrors/west",
                    "shared": 2,
                    "overlap": 1.0,
                }
            ],
            "external_inbound": {"mirrors/east": 0, "mirrors/west": 0},
        }
        store.set_meta(MIRROR_SEARCH_KEY, json.dumps(stamp, sort_keys=True))
        store.reload_mirror_search_stamp()


def test_read_symbol_names_indexed_counterpart(tmp_path: Path, store: GraphStore) -> None:
    """AC1: hit inside a stamped pair whose twin is indexed names it + dispatch caveat."""
    _plant_pair(tmp_path, store, with_west=True)
    out = read_symbol.create(db_config(tmp_path))("East\\Widget")
    assert out["found"] is True
    assert out[MIRROR_COUNTERPART_FIELD] == "mirrors/west/Widget.php"
    assert MIRROR_NO_COUNTERPART_FIELD not in out
    assert CAVEAT_MIRROR_TWIN in out[AUTHORITATIVE_CAVEATS]  # type: ignore[operator]
    assert CAVEAT_MIRROR_TWIN in out[CAVEAT_LIMITS_KEY]  # type: ignore[operator]
    # Boundary, not a verdict — no field claims which side is live.
    blob = repr(out)
    assert "live" not in blob.lower() or "cannot say" in str(out[CAVEAT_LIMITS_KEY]).lower()


def test_read_symbol_honest_negative_when_counterpart_missing(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2: counterpart not indexed → honest negative, never a synthesized path."""
    _plant_pair(tmp_path, store, with_west=False)
    out = read_symbol.create(db_config(tmp_path))("East\\Widget")
    assert out.get(MIRROR_NO_COUNTERPART_FIELD) is True
    assert MIRROR_COUNTERPART_FIELD not in out
    assert "mirrors/west/Widget.php" not in repr(out)
    assert CAVEAT_MIRROR_TWIN in out[AUTHORITATIVE_CAVEATS]  # type: ignore[operator]


def test_no_stamp_byte_identical(tmp_path: Path, store: GraphStore) -> None:
    """AC3: no stamped pairs → no mirror fields (061)."""
    seed_file(
        store,
        "src/Alone.php",
        [node("Class", "Alone", "App\\Alone", "src/Alone.php")],
        [],
        root=tmp_path,
    )
    out = read_symbol.create(db_config(tmp_path))("App\\Alone")
    assert MIRROR_COUNTERPART_FIELD not in out
    assert MIRROR_NO_COUNTERPART_FIELD not in out
    assert AUTHORITATIVE_CAVEATS not in out or CAVEAT_MIRROR_TWIN not in (
        out.get(AUTHORITATIVE_CAVEATS) or []
    )


def test_search_mirror_tests_still_pass(tmp_path: Path, store: GraphStore) -> None:
    """AC5: 277/282 search counterpart wiring unchanged."""
    _plant_pair(tmp_path, store, with_west=True)
    payload = search_symbol.create(db_config(tmp_path))(query="Widget", kind="Class", limit=10)
    mirrored = [
        hit
        for hit in payload["results"]  # type: ignore[index]
        if str(hit["file"]).startswith("mirrors/")
    ]
    assert mirrored
    assert all(MIRROR_COUNTERPART_FIELD in hit for hit in mirrored)
