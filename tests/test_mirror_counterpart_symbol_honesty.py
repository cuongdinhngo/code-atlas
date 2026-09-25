"""Task 331 — mirror_counterpart on a symbol hit means the twin defines that name."""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas.mirror_search import (
    MIRROR_COUNTERPART_FIELD,
    MIRROR_COUNTERPART_FILE_FIELD,
    MIRROR_SEARCH_KEY,
    MIRROR_SYMBOL_ABSENT_FIELD,
    build_mirror_search_stamp,
)
from code_atlas.store import GraphStore
from code_atlas.tools import search_symbol
from tests.test_nav_tools import db_config, node, seed_file
from tests.test_nav_tools import store as store  # noqa: F401 — pytest fixture


def _stamp_for_test(store: GraphStore) -> None:
    stamp = build_mirror_search_stamp(store, min_shared=1, min_overlap=0.1)
    assert stamp.get("pairs"), stamp
    store.set_meta(MIRROR_SEARCH_KEY, json.dumps(stamp, sort_keys=True))
    store.reload_mirror_search_stamp()


def test_one_sided_function_does_not_bare_name_counterpart(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC1 — function only on one mirror side ⇒ no bare mirror_counterpart."""
    seed_file(
        store,
        "mirrors/east/Page.php",
        [
            node("File", "Page.php", "mirrors/east/Page.php", "mirrors/east/Page.php"),
            node("Function", "renderPage", "east\\renderPage", "mirrors/east/Page.php"),
        ],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "mirrors/west/Page.php",
        [
            node("File", "Page.php", "mirrors/west/Page.php", "mirrors/west/Page.php"),
            node("Class", "PageShell", "west\\PageShell", "mirrors/west/Page.php"),
        ],
        [],
        root=tmp_path,
    )
    _stamp_for_test(store)
    payload = search_symbol.create(db_config(tmp_path))(
        query="renderPage", kind="Function", limit=10
    )
    assert payload["results"]
    hit = payload["results"][0]  # type: ignore[index]
    assert str(hit["file"]) == "mirrors/east/Page.php"
    assert MIRROR_COUNTERPART_FIELD not in hit
    assert hit[MIRROR_COUNTERPART_FILE_FIELD] == "mirrors/west/Page.php"
    assert hit[MIRROR_SYMBOL_ABSENT_FIELD] is True


def test_both_sides_keep_mirror_counterpart(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC2 — function present on both sides keeps today's mirror_counterpart."""
    for side in ("east", "west"):
        seed_file(
            store,
            f"mirrors/{side}/Page.php",
            [
                node(
                    "Function",
                    "renderPage",
                    f"{side}\\renderPage",
                    f"mirrors/{side}/Page.php",
                ),
            ],
            [],
            root=tmp_path,
        )
    _stamp_for_test(store)
    payload = search_symbol.create(db_config(tmp_path))(
        query="renderPage", kind="Function", limit=10
    )
    by_file = {str(h["file"]): h for h in payload["results"]}  # type: ignore[misc]
    assert by_file["mirrors/east/Page.php"][MIRROR_COUNTERPART_FIELD] == (
        "mirrors/west/Page.php"
    )
    assert by_file["mirrors/west/Page.php"][MIRROR_COUNTERPART_FIELD] == (
        "mirrors/east/Page.php"
    )
    assert MIRROR_SYMBOL_ABSENT_FIELD not in by_file["mirrors/east/Page.php"]
    assert MIRROR_COUNTERPART_FILE_FIELD not in by_file["mirrors/east/Page.php"]


def test_presence_query_once_per_page(
    tmp_path: Path, store: GraphStore, monkeypatch
) -> None:
    """AC3 — names_defined_in_files runs once per search page, not per hit."""
    for side in ("east", "west"):
        seed_file(
            store,
            f"mirrors/{side}/Page.php",
            [
                node(
                    "Function",
                    "alphaFn",
                    f"{side}\\alphaFn",
                    f"mirrors/{side}/Page.php",
                ),
                node(
                    "Function",
                    "betaFn",
                    f"{side}\\betaFn",
                    f"mirrors/{side}/Page.php",
                ),
            ],
            [],
            root=tmp_path,
        )
    # One-sided gamma on the same page files — still one presence query.
    seed_file(
        store,
        "mirrors/east/Extra.php",
        [node("Function", "gammaFn", "east\\gammaFn", "mirrors/east/Extra.php")],
        [],
        root=tmp_path,
    )
    seed_file(
        store,
        "mirrors/west/Extra.php",
        [node("Class", "ExtraShell", "west\\ExtraShell", "mirrors/west/Extra.php")],
        [],
        root=tmp_path,
    )
    _stamp_for_test(store)
    calls = {"n": 0}
    real = GraphStore.names_defined_in_files

    def spy(
        self: GraphStore,
        file_paths: object,
        names: object,
    ) -> frozenset[tuple[str, str]]:
        calls["n"] += 1
        return real(self, file_paths, names)  # type: ignore[arg-type]

    monkeypatch.setattr(GraphStore, "names_defined_in_files", spy)
    # Prefix hits both alphaFn and … no — use queries=False single subject that matches many?
    # Page of two mirrored alphaFn hits: one presence call for both.
    payload = search_symbol.create(db_config(tmp_path))(
        query="alphaFn", kind="Function", limit=10
    )
    assert len(payload["results"]) == 2  # type: ignore[arg-type]
    assert calls["n"] == 1
    # Separate page for the one-sided gamma still pays once, not per field.
    calls["n"] = 0
    gamma_payload = search_symbol.create(db_config(tmp_path))(
        query="gammaFn", kind="Function", limit=10
    )
    assert calls["n"] == 1
    hit = gamma_payload["results"][0]  # type: ignore[index]
    assert MIRROR_COUNTERPART_FIELD not in hit
    assert hit[MIRROR_SYMBOL_ABSENT_FIELD] is True
