"""Task 277 — mirror-aware search order within the exactness band."""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas.mirror_search import (
    MIRROR_COUNTERPART_FIELD,
    MIRROR_SEARCH_KEY,
    SEARCH_ORDER_FIELD,
    SEARCH_ORDER_MIRROR,
    build_mirror_search_stamp,
)
from code_atlas.store import GraphStore
from code_atlas.tools import search_symbol
from tests.test_nav_tools import db_config, node, seed_file
from tests.test_nav_tools import store as store  # noqa: F401 — pytest fixture


def _stamp_for_test(store: GraphStore) -> None:
    """Plant the search stamp with open mirror thresholds (tiny fixture)."""
    stamp = build_mirror_search_stamp(store, min_shared=1, min_overlap=0.1)
    assert stamp.get("pairs"), stamp
    store.set_meta(MIRROR_SEARCH_KEY, json.dumps(stamp, sort_keys=True))
    store.reload_mirror_search_stamp()


def test_outside_mirror_ranks_above_copies_and_names_counterpart(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1 — live tree first; each mirrored hit names its counterpart."""
    shared = "Widget.php"
    seed_file(
        store,
        f"src/{shared}",
        [node("Class", "Widget", "App\\Widget", f"src/{shared}")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        f"mirrors/east/{shared}",
        [node("Class", "Widget", "East\\Widget", f"mirrors/east/{shared}")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        f"mirrors/west/{shared}",
        [node("Class", "Widget", "West\\Widget", f"mirrors/west/{shared}")],
        [],
        root=tmp_path,
    )
    for side in ("east", "west"):
        seed_file(
            store,
            f"mirrors/{side}/Extra.php",
            [node("Class", "Extra", f"{side}\\Extra", f"mirrors/{side}/Extra.php")],
            [],
            root=tmp_path,
        )
    _stamp_for_test(store)
    payload = search_symbol.create(db_config(tmp_path))(
        query="Widget", kind="Class", limit=10
    )
    files = [str(hit["file"]) for hit in payload["results"]]  # type: ignore[index]
    assert files[0] == f"src/{shared}"
    assert set(files[1:3]) == {f"mirrors/east/{shared}", f"mirrors/west/{shared}"}
    mirrored = [
        hit
        for hit in payload["results"]  # type: ignore[index]
        if str(hit["file"]).startswith("mirrors/")
    ]
    assert all(MIRROR_COUNTERPART_FIELD in hit for hit in mirrored)
    assert payload[SEARCH_ORDER_FIELD] == SEARCH_ORDER_MIRROR


def test_no_mirrors_byte_identical_and_no_new_field(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2 / 061 — no mirror pairs ⇒ no search_order field."""
    seed_file(
        store,
        "src/Only.php",
        [node("Class", "OnlyOne", "App\\OnlyOne", "src/Only.php")],
        [],
        root=tmp_path,
    )
    stamp = build_mirror_search_stamp(store)
    assert stamp.get("pairs") == []
    payload = search_symbol.create(db_config(tmp_path))(
        query="OnlyOne", kind="Class"
    )
    assert SEARCH_ORDER_FIELD not in payload
    assert payload["results"]
    assert MIRROR_COUNTERPART_FIELD not in payload["results"][0]  # type: ignore[index]


def test_search_order_rule_is_named(tmp_path: Path, store: GraphStore) -> None:
    """AC3 — the deciding rule is a stated payload field."""
    seed_file(
        store,
        "alpha/Shared.php",
        [node("Class", "SharedName", "A\\SharedName", "alpha/Shared.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "beta/Shared.php",
        [node("Class", "SharedName", "B\\SharedName", "beta/Shared.php")],
        [],
        root=tmp_path,
    )
    _stamp_for_test(store)
    payload = search_symbol.create(db_config(tmp_path))(
        query="SharedName", kind="Class"
    )
    assert payload[SEARCH_ORDER_FIELD] == SEARCH_ORDER_MIRROR


def test_absent_sibling_gets_no_counterpart(tmp_path: Path, store: GraphStore) -> None:
    """282 — synthesized sibling not in the index ⇒ no mirror_counterpart field."""
    seed_file(
        store,
        "alpha/Lone.php",
        [node("Class", "LoneName", "A\\LoneName", "alpha/Lone.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "beta/Shared.php",
        [node("Class", "SharedName", "B\\SharedName", "beta/Shared.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "alpha/Shared.php",
        [node("Class", "SharedName", "A\\SharedName", "alpha/Shared.php")],
        [],
        root=tmp_path,
    )
    _stamp_for_test(store)
    # Lone exists only on alpha; synthesized beta/Lone.php is not indexed.
    payload = search_symbol.create(db_config(tmp_path))(
        query="LoneName", kind="Class"
    )
    assert payload["results"]
    hit = payload["results"][0]  # type: ignore[index]
    assert str(hit["file"]) == "alpha/Lone.php"
    assert MIRROR_COUNTERPART_FIELD not in hit
    # Shared still names its indexed sibling (AC2 unchanged).
    shared = search_symbol.create(db_config(tmp_path))(
        query="SharedName", kind="Class"
    )
    by_file = {str(h["file"]): h for h in shared["results"]}  # type: ignore[misc]
    assert by_file["alpha/Shared.php"][MIRROR_COUNTERPART_FIELD] == "beta/Shared.php"
    assert by_file["beta/Shared.php"][MIRROR_COUNTERPART_FIELD] == "alpha/Shared.php"


def test_path_scan_is_once_per_call_not_per_subject(
    tmp_path: Path, store: GraphStore, monkeypatch
) -> None:
    """282 — the indexed path set backs every subject of a sweep, read once."""
    for side in ("alpha", "beta"):
        for name in ("Shared", "Second"):
            seed_file(
                store,
                f"{side}/{name}.php",
                [node("Class", f"{name}Name", f"{side}\\{name}Name", f"{side}/{name}.php")],
                [],
                root=tmp_path,
            )
    _stamp_for_test(store)
    calls = {"n": 0}
    real = GraphStore.file_paths

    def spy(self: GraphStore) -> tuple[str, ...]:
        calls["n"] += 1
        return real(self)

    monkeypatch.setattr(GraphStore, "file_paths", spy)
    payload = search_symbol.create(db_config(tmp_path))(
        queries=["SharedName", "SecondName"], kind="Class"
    )
    assert payload["subject_count"] == 2
    assert calls["n"] == 1


def test_no_pairs_never_scans_the_path_set(
    tmp_path: Path, store: GraphStore, monkeypatch
) -> None:
    """282 — without mirror pairs no hit can carry a counterpart; skip the scan."""
    seed_file(
        store,
        "src/Only.php",
        [node("Class", "OnlyOne", "App\\OnlyOne", "src/Only.php")],
        [],
        root=tmp_path,
    )
    calls = {"n": 0}
    real = GraphStore.file_paths

    def spy(self: GraphStore) -> tuple[str, ...]:
        calls["n"] += 1
        return real(self)

    monkeypatch.setattr(GraphStore, "file_paths", spy)
    payload = search_symbol.create(db_config(tmp_path))(query="OnlyOne", kind="Class")
    assert payload["results"]
    assert calls["n"] == 0
