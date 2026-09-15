"""Task 276 — per-answer cross_language caveat only when the census partitions something.

Field retro round 20 §5: an empty cross_language census on a multi-language index made
``authoritative: false`` fire on every find_callers / find_references hit, including a fully
correct in-language answer. Zeros keep 221; hits need census edges (linked+unlinked > 0).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from code_atlas.config import Config, load_config
from code_atlas.store import (
    COVERED_LANGUAGES_KEY,
    EDGE_HEALTH_BY_LANGUAGE_KEY,
    GraphStore,
)
from code_atlas.tools import find_callers, find_references
from code_atlas.tools.nav_result import CAVEAT_CROSS_LANGUAGE_UNMODELLED
from tests.test_nav_tools import edge, node

A_FILE = "src/a.php"
A_QNAME = "A\\Widget::ping"
A_CALLER = "A\\WidgetTest::testPing"
B_FILE = "src/b.ts"
B_QNAME = "src/b.ts::unrelated"
C_FILE = "src/c.sql"
C_QNAME = "dbo.otherProc"
PHP_CALLER_OF_SQL = "A\\Widget::loadOther"


def _seed(
    store: GraphStore, root: Path, path: str, language: str, nodes: list, edges: list
) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    body = b"# planted\n"
    target.write_bytes(body)
    store.upsert_file(path, hashlib.sha256(body).hexdigest(), language)
    store.replace_file_rows(path, nodes, edges)


def _stamp(store: GraphStore) -> None:
    census = store.edge_language_census()
    store.set_meta(COVERED_LANGUAGES_KEY, ",".join(store.indexed_languages()))
    store.set_meta(EDGE_HEALTH_BY_LANGUAGE_KEY, json.dumps(census.health, sort_keys=True))


def _config(root: Path, db_path: Path) -> Config:
    return load_config(root, {"CA_DB_PATH": str(db_path)})


def _three_lang_empty_census(root: Path, db_path: Path) -> Config:
    """php + typescript + sql with only in-language CALLS — linked+unlinked == 0."""
    with GraphStore(db_path) as store:
        _seed(
            store,
            root,
            A_FILE,
            "php",
            [
                node("Method", "ping", A_QNAME, A_FILE),
                node("Method", "testPing", A_CALLER, A_FILE),
            ],
            [
                edge(
                    "CALLS",
                    A_CALLER,
                    A_QNAME,
                    A_FILE,
                    target_qname=A_QNAME,
                    tier="RESOLVED",
                ),
            ],
        )
        _seed(
            store,
            root,
            B_FILE,
            "typescript",
            [node("Function", "unrelated", B_QNAME, B_FILE)],
            [],
        )
        _seed(
            store,
            root,
            C_FILE,
            "sql",
            [node("Function", "otherProc", C_QNAME, C_FILE)],
            [],
        )
        _stamp(store)
        census = store.stamped_cross_language_edges()
        assert census is not None
        assert int(census["linked"] or 0) + int(census["unlinked"] or 0) == 0
    return _config(root, db_path)


def _hits_with_outbound_crossing(root: Path, db_path: Path) -> Config:
    """In-language php hits plus a modelled php→sql edge — census edges, no *→php."""
    with GraphStore(db_path) as store:
        _seed(
            store,
            root,
            A_FILE,
            "php",
            [
                node("Method", "ping", A_QNAME, A_FILE),
                node("Method", "testPing", A_CALLER, A_FILE),
                node("Method", "loadOther", PHP_CALLER_OF_SQL, A_FILE),
            ],
            [
                edge(
                    "CALLS",
                    A_CALLER,
                    A_QNAME,
                    A_FILE,
                    target_qname=A_QNAME,
                    tier="RESOLVED",
                ),
                edge(
                    "CALLS",
                    PHP_CALLER_OF_SQL,
                    C_QNAME,
                    A_FILE,
                    target_qname=C_QNAME,
                    tier="RESOLVED",
                ),
            ],
        )
        _seed(
            store,
            root,
            C_FILE,
            "sql",
            [node("Function", "otherProc", C_QNAME, C_FILE)],
            [],
        )
        _stamp(store)
        census = store.stamped_cross_language_edges()
        assert census is not None
        assert "php->sql" in census["pairs"]
        assert not any(str(k).endswith("->php") for k in census["pairs"])
        assert int(census["linked"] or 0) + int(census["unlinked"] or 0) > 0
    return _config(root, db_path)


def test_empty_census_hits_stay_authoritative(tmp_path: Path) -> None:
    """AC: three-language index, empty cross_language census → hits carry no caveat."""
    config = _three_lang_empty_census(tmp_path, tmp_path / "graph.db")
    for tool in (find_callers, find_references):
        payload = tool.create(config)(qname=A_QNAME)
        assert payload["total_count"] == 1
        assert payload["reason"] == "ok"
        assert "authoritative" not in payload
        assert "cross_language" not in payload
        assert CAVEAT_CROSS_LANGUAGE_UNMODELLED not in (
            payload.get("authoritative_caveats") or []
        )


def test_census_with_edges_but_no_inbound_pair_keeps_hit_caveat(tmp_path: Path) -> None:
    """AC: real cross-language edges exist, no *→php → hit caveat stays (could have crossed)."""
    config = _hits_with_outbound_crossing(tmp_path, tmp_path / "graph.db")
    payload = find_callers.create(config)(qname=A_QNAME, sign=True)
    assert payload["total_count"] == 1
    assert payload["reason"] == "ok"
    assert payload["authoritative"] is False
    assert payload["authoritative_caveats"] == [CAVEAT_CROSS_LANGUAGE_UNMODELLED]
    assert int(payload["cross_language"]["linked"] or 0) > 0
    assert "authoritative=false" in str(payload["claim"])


def test_modelled_inbound_pair_stays_confident(tmp_path: Path) -> None:
    """AC: a real *→L pair → hits stay without the cross_language caveat (238 control)."""
    from tests.test_find_callers_cross_language_unmodelled import _hits_unmodelled_repo

    config = _hits_unmodelled_repo(
        tmp_path, tmp_path / "graph.db", link_the_crossing=True, second_language=True
    )
    payload = find_callers.create(config)(qname=A_QNAME)
    assert payload["total_count"] == 1
    assert "authoritative" not in payload
    assert "cross_language" not in payload
