"""313 — `impact` rows carry test role and mirror twin; `exclude_tests` filters before paging."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from code_atlas.mirror_search import (
    MIRROR_COUNTERPART_FIELD,
    MIRROR_NO_COUNTERPART_FIELD,
    MIRROR_SEARCH_KEY,
    build_mirror_search_stamp,
)
from code_atlas.store import GraphStore
from code_atlas.tools import impact, search_symbol
from tests.test_nav_tools import db_config, edge, node, seed_file
from tests.test_nav_tools import store as store  # noqa: F401 — pytest fixture

NEW_ROW_FIELDS = ("test_role_source", MIRROR_COUNTERPART_FIELD, MIRROR_NO_COUNTERPART_FIELD)
# Anything that would partition a multi-hop radius into roles (R5.5) — none may ship (AC4).
CENSUS_FIELDS = (
    "production_count",
    "test_count",
    "test_role_source",
    "total_count",
    "tests_excluded",
)


def _caller(store: GraphStore, root: Path, path: str, qname: str, **extra: object) -> None:
    row = node("Method", qname.rsplit("::", 1)[-1], qname, path)
    row.update(extra)
    seed_file(
        store, path, [row], [edge("CALLS", qname, "Target", path, target_qname="Target")], root=root
    )


def _target(store: GraphStore, root: Path) -> None:
    seed_file(
        store,
        "src/Target.php",
        [node("Class", "Target", "Target", "src/Target.php")],
        [],
        root=root,
    )


def _mixed(store: GraphStore, root: Path, *, tests: int) -> None:
    """Three production callers, ``tests`` path-convention test callers that sort first by qname."""
    _target(store, root)
    for i in range(3):
        _caller(store, root, f"src/c{i}.php", f"C{i}::run")
    for i in range(tests):
        _caller(store, root, f"tests/t{i}.php", f"A{i:02d}::test_it")


def _rows(payload: dict[str, object]) -> list[dict[str, object]]:
    return payload["results"]  # type: ignore[return-value]


def test_rows_name_their_test_role_and_its_basis(tmp_path: Path, store: GraphStore) -> None:
    """AC1 — production rows carry nothing; test rows name adapter vs path_convention."""
    _target(store, tmp_path)
    _caller(store, tmp_path, "src/c0.php", "C0::run")
    _caller(store, tmp_path, "tests/t0.php", "T0::test_it")
    _caller(store, tmp_path, "src/Probe.php", "Probe::check", is_test=1)
    rows = {
        row["qname"]: row for row in _rows(impact.create(db_config(tmp_path))(qnames=["Target"]))
    }
    assert "test_role_source" not in rows["C0::run"]
    assert "test_role_source" not in rows["Target"]
    assert rows["T0::test_it"]["test_role_source"] == "path_convention"
    assert rows["Probe::check"]["test_role_source"] == "adapter"


def test_exclude_tests_filters_before_the_node_budget(tmp_path: Path, store: GraphStore) -> None:
    """AC2 — tests outnumber the budget and sort first; the filtered page keeps all production."""
    _mixed(store, tmp_path, tests=10)
    tight = replace(db_config(tmp_path), impact_max_nodes=4)
    wide = replace(db_config(tmp_path), impact_max_nodes=500)
    unfiltered = impact.create(tight)(qnames=["Target"])
    # The failure a filter-after-paging implementation would ship: tests spent the whole page.
    assert unfiltered["truncated"] is True
    assert not [r for r in _rows(unfiltered) if str(r["qname"]).startswith("C")]
    production = [
        r["qname"]
        for r in _rows(impact.create(wide)(qnames=["Target"]))
        if "test_role_source" not in r
    ]
    filtered = impact.create(tight)(qnames=["Target"], exclude_tests=True)
    assert [r["qname"] for r in _rows(filtered)] == production
    assert production == ["Target", "C0::run", "C1::run", "C2::run"]
    assert filtered["truncated"] is False


def _stamp(store: GraphStore) -> None:
    stamp = build_mirror_search_stamp(store, min_shared=1, min_overlap=0.1)
    assert stamp.get("pairs"), stamp
    store.set_meta(MIRROR_SEARCH_KEY, json.dumps(stamp, sort_keys=True))
    store.reload_mirror_search_stamp()


def test_mirror_rows_name_the_indexed_twin_or_say_there_is_none(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC3 — counterpart when the twin is indexed; the honest negative when it is not (282)."""
    _target(store, tmp_path)
    seed_file(
        store,
        "legacy/Target.php",
        [node("Class", "Target", "Legacy\\Target", "legacy/Target.php")],
        [],
        root=tmp_path,
    )
    _caller(store, tmp_path, "src/Caller.php", "App\\Caller::run")
    _caller(store, tmp_path, "legacy/Caller.php", "Legacy\\Caller::run")
    _caller(store, tmp_path, "legacy/Only.php", "Legacy\\Only::run")
    _stamp(store)
    rows = {
        row["qname"]: row for row in _rows(impact.create(db_config(tmp_path))(qnames=["Target"]))
    }
    assert rows["Legacy\\Caller::run"][MIRROR_COUNTERPART_FIELD] == "src/Caller.php"
    assert rows["App\\Caller::run"][MIRROR_COUNTERPART_FIELD] == "legacy/Caller.php"
    only = rows["Legacy\\Only::run"]
    assert only[MIRROR_NO_COUNTERPART_FIELD] is True
    assert MIRROR_COUNTERPART_FIELD not in only  # never a path the index does not hold
    minimal = impact.create(db_config(tmp_path))(qnames=["Target"], detail_level="minimal")
    assert not [f for row in _rows(minimal) for f in NEW_ROW_FIELDS if f in row]  # AC6


def test_no_census_partitions_the_radius(tmp_path: Path, store: GraphStore) -> None:
    """AC4 — row properties only: no count/total/census, with or without the filter (R5.5)."""
    _mixed(store, tmp_path, tests=3)
    tool = impact.create(db_config(tmp_path))
    for payload in (tool(qnames=["Target"]), tool(qnames=["Target"], exclude_tests=True)):
        present = [field for field in CENSUS_FIELDS if field in payload]
        assert not present, f"impact ships a radius census: {present}"


def test_search_symbol_rows_carry_the_role_and_keep_their_order(
    tmp_path: Path, store: GraphStore
) -> None:
    """AC5 — same per-row role on search hits; the band order is the store's, unchanged."""
    _mixed(store, tmp_path, tests=2)
    payload = search_symbol.create(db_config(tmp_path))(query="run", limit=10)
    hits = _rows(payload)
    expected = [row["qualified_name"] for row in store.search_nodes("run", limit=10)]
    assert [hit["qname"] for hit in hits] == expected
    assert all("test_role_source" not in hit for hit in hits)
    tests = _rows(search_symbol.create(db_config(tmp_path))(query="test_it", limit=10))
    assert {hit["test_role_source"] for hit in tests} == {"path_convention"}
    assert "search_order" not in payload


def test_minimal_omits_every_new_field_on_both_tools(tmp_path: Path, store: GraphStore) -> None:
    """AC6 — standard carries the labels, minimal carries none of them."""
    _mixed(store, tmp_path, tests=2)
    cfg = db_config(tmp_path)
    for level, expect in (("standard", True), ("minimal", False)):
        rows = _rows(impact.create(cfg)(qnames=["Target"], detail_level=level))
        rows += _rows(search_symbol.create(cfg)(query="test_it", detail_level=level))
        labelled = any(field in row for row in rows for field in NEW_ROW_FIELDS)
        assert labelled is expect, level


# Captured from `impact` / `search_symbol` on main before this change (index_root and the
# server_* provenance stripped — they name the host, not the answer).
_PRE_313_IMPACT = (
    '{"answered_about_ref": null, "depth": 2, "frontier_skipped_non_resolved": 0, '
    '"indexed": true, "qname": "Target", "results": [{"confidence_tier": "RESOLVED", '
    '"depth": 0, "file": "src/Target.php", "line": 1, "qname": "Target", "score": 1.0}, '
    '{"confidence_tier": "RESOLVED", "depth": 1, "file": "src/c0.php", "line": 1, '
    '"qname": "C0::run", "score": 0.7}, {"confidence_tier": "RESOLVED", "depth": 1, '
    '"file": "src/c1.php", "line": 1, "qname": "C1::run", "score": 0.7}], '
    '"seeds_dropped": 0, "truncated": false}'
)
_PRE_313_SEARCH = (
    '{"answered_about_ref": null, "indexed": true, "reason": "ok", "results": '
    '[{"file": "src/c0.php", "kind": "Method", "line": 1, "qname": "C0::run"}, '
    '{"file": "src/c1.php", "kind": "Method", "line": 1, "qname": "C1::run"}], '
    '"total_count": 2, "truncated": false}'
)
_HOST_FIELDS = ("index_root", "staleness", "last_commit", "unconfigured_adapters")


def _stable(payload: dict[str, object]) -> str:
    kept = {
        k: v for k, v in payload.items() if k not in _HOST_FIELDS and not k.startswith("server_")
    }
    return json.dumps(kept, sort_keys=True)


def test_unmirrored_test_free_repo_pays_nothing(tmp_path: Path, store: GraphStore) -> None:
    """AC7 — no stamp and no test node: both tools answer byte-identically to pre-313 (061)."""
    _target(store, tmp_path)
    for i in range(2):
        _caller(store, tmp_path, f"src/c{i}.php", f"C{i}::run")
    cfg = db_config(tmp_path)
    for level in ("minimal", "standard"):
        assert _stable(impact.create(cfg)(qnames=["Target"], detail_level=level)) == _PRE_313_IMPACT
        assert (
            _stable(impact.create(cfg)(qnames=["Target"], detail_level=level, exclude_tests=True))
            == _PRE_313_IMPACT
        )
        assert (
            _stable(search_symbol.create(cfg)(query="run", detail_level=level)) == _PRE_313_SEARCH
        )
