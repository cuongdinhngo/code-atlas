"""Task 221 — a modelled zero when every caller is in another language.

Field round 14, a PHP-over-T-SQL repo: `find_callers` on a stored proc whose only callers were PHP
`querySP('name')` string calls returned `reason=no_matches` — a confident "no caller exists" on a
proc with five live callers. 214's honest-zero arm keys on an unlinked edge whose `target_raw`
**is** the proc name (a SQL-side bare `EXEC`); a PHP `querySP('proc')` leaves an edge whose
`target_raw` is `querySP`, so nothing matches and the zero stays `no_matches`. The index already
knows the crossing is unmodelled (`_cross_language_edges` reads `linked: 0` on that corpus) — this
ticket reads that build-time census on the answer it invalidates.

Direct-seed, generic language tags: the fixture encodes the *language crossing*, not the field
repo's `querySP` (E1 / R2). Runs natively (no adapter subprocess).
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
from code_atlas.tools import find_callers
from code_atlas.tools.nav_result import (
    CAVEAT_CROSS_LANGUAGE_UNMODELLED,
    REASON_NO_MATCHES,
    REASON_RELATION_UNMODELLED_FOR_LANGUAGE,
    TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE,
)
from tests.test_nav_tools import edge, node

# The subject: a stored proc whose only callers are in another language, by string argument.
PROC_QNAME = "dbo.getUnplannedChange"
PROC_FILE = "src/procs.sql"
PHP_FILE = "src/data.php"


def _seed(
    store: GraphStore, root: Path, path: str, language: str, nodes: list, edges: list
) -> None:
    """Plant rows and matching on-disk bytes (FreshnessGuard) under a chosen language."""
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    body = b"# planted\n"
    target.write_bytes(body)
    store.upsert_file(path, hashlib.sha256(body).hexdigest(), language)
    store.replace_file_rows(path, nodes, edges)


def _stamp_census(store: GraphStore) -> None:
    """Stamp the two build-time keys the predicate reads — the census and the covered languages."""
    census = store.edge_language_census()
    store.set_meta(COVERED_LANGUAGES_KEY, ",".join(store.indexed_languages()))
    store.set_meta(EDGE_HEALTH_BY_LANGUAGE_KEY, json.dumps(census.health, sort_keys=True))


def _drop_census(store: GraphStore) -> None:
    """Re-stamp edge health as a pre-204 build would: every row but the nested one."""
    health = store.edge_language_census().health
    health.pop("cross_language", None)
    store.set_meta(EDGE_HEALTH_BY_LANGUAGE_KEY, json.dumps(health, sort_keys=True))


def _config(root: Path, db_path: Path) -> Config:
    return load_config(root, {"CA_DB_PATH": str(db_path)})


def _cross_language_repo(root: Path, db_path: Path, *, link_the_crossing: bool) -> Config:
    """A proc (`sql`) and a caller (`php`) that reaches it only by a string argument.

    ``link_the_crossing`` seeds a genuine linked ``php->sql`` edge to a *second* proc, so the census
    records that the crossing into ``sql`` IS modelled — the AC2 control where a zero stays honest.
    """
    with GraphStore(db_path) as store:
        _seed(
            store,
            root,
            PROC_FILE,
            "sql",
            [node("Function", "getUnplannedChange", PROC_QNAME, PROC_FILE),
             node("Function", "otherProc", "dbo.otherProc", PROC_FILE)],
            [],
        )
        php_edges = [
            # `querySP('getUnplannedChange')` — the proc name is an ARGUMENT, so the edge's
            # target_raw is the helper and target_qname stays NULL (the crossing is unmodelled).
            edge("CALLS", f"{PHP_FILE}::loadChange", "querySP", PHP_FILE, tier="DYNAMIC"),
        ]
        if link_the_crossing:
            php_edges.append(
                edge("CALLS", f"{PHP_FILE}::loadOther", "dbo.otherProc", PHP_FILE,
                     target_qname="dbo.otherProc", tier="RESOLVED")
            )
        _seed(
            store,
            root,
            PHP_FILE,
            "php",
            [node("Function", "loadChange", f"{PHP_FILE}::loadChange", PHP_FILE),
             node("Function", "loadOther", f"{PHP_FILE}::loadOther", PHP_FILE)],
            php_edges,
        )
        _stamp_census(store)
    return _config(root, db_path)


def test_a_cross_language_zero_is_not_no_matches(tmp_path: Path) -> None:
    """AC1 (proving test): the zero is named unmeasured, non-authoritative, and it reaches `claim`.

    R6.5 guard-fails-first is proven in the same test: deleting the stamp (an index built before it
    existed — today's shape) makes the identical call return `no_matches`.
    """
    config = _cross_language_repo(tmp_path, tmp_path / "graph.db", link_the_crossing=False)

    payload = find_callers.create(config)(qname=PROC_QNAME, sign=True)

    assert payload["results"] == []
    assert payload["total_count"] == 0
    assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
    assert payload["reason"] != REASON_NO_MATCHES
    assert payload["authoritative"] is False
    assert payload["authoritative_caveats"] == [CAVEAT_CROSS_LANGUAGE_UNMODELLED]
    assert payload["try_instead_hint"] == TRY_INSTEAD_HINT_RELATION_UNMODELLED_FOR_LANGUAGE
    # Scope 4: the census that explains the zero rides the answer it invalidates.
    assert payload["cross_language"]["linked"] == 0
    assert payload["cross_language"]["pairs"] == {}
    # AC1: the reason and the caveat reach the signed one-line claim.
    claim = str(payload["claim"])
    assert f"reason={REASON_RELATION_UNMODELLED_FOR_LANGUAGE}" in claim
    assert "authoritative=false" in claim

    # R6.5 / AC4: without the stamp, the same call is the confident zero it is today.
    with GraphStore(config.db_path) as store:
        _drop_census(store)
    today = find_callers.create(config)(qname=PROC_QNAME, sign=True)
    assert today["reason"] == REASON_NO_MATCHES
    assert "authoritative" not in today
    assert "cross_language" not in today


def test_a_modelled_crossing_with_a_genuine_zero_is_still_no_matches(tmp_path: Path) -> None:
    """AC2: when the index DOES model a `*->sql` crossing, a real zero stays `no_matches`."""
    config = _cross_language_repo(tmp_path, tmp_path / "graph.db", link_the_crossing=True)

    with GraphStore(config.db_path) as store:
        census = store.stamped_cross_language_edges()
    assert census is not None and "php->sql" in census["pairs"], census

    payload = find_callers.create(config)(qname=PROC_QNAME)
    assert payload["reason"] == REASON_NO_MATCHES
    assert "authoritative" not in payload
    assert "cross_language" not in payload


def test_a_single_language_zero_is_still_no_matches(tmp_path: Path) -> None:
    """AC2's other half: with no other language present, no crossing is possible — a zero is a zero.

    This is the guard against widening the honest zero into "every zero is unmeasured".
    """
    db_path = tmp_path / "graph.db"
    with GraphStore(db_path) as store:
        _seed(
            store,
            tmp_path,
            PHP_FILE,
            "php",
            [node("Function", "loadChange", f"{PHP_FILE}::loadChange", PHP_FILE)],
            [],
        )
        _stamp_census(store)
        assert store.indexed_languages() == ("php",)
    config = _config(tmp_path, db_path)

    payload = find_callers.create(config)(qname=f"{PHP_FILE}::loadChange")
    assert payload["reason"] == REASON_NO_MATCHES
    assert "cross_language" not in payload


def test_the_predicate_is_a_stamp_read_not_a_scan(
    tmp_path: Path, monkeypatch: object
) -> None:
    """AC3: answering reads the census from meta — it never re-runs `_cross_language_edges`."""
    import sqlite3

    config = _cross_language_repo(tmp_path, tmp_path / "graph.db", link_the_crossing=False)

    seen: list[str] = []
    real_connect = sqlite3.connect

    def _tracing_connect(*args: object, **kwargs: object) -> sqlite3.Connection:
        conn = real_connect(*args, **kwargs)  # type: ignore[arg-type]
        conn.set_trace_callback(seen.append)
        return conn

    monkeypatch.setattr(sqlite3, "connect", _tracing_connect)  # type: ignore[attr-defined]
    payload = find_callers.create(config)(qname=PROC_QNAME)
    assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE

    # The build-time scan's signature is `src.language <> tgt.language`; it must not appear.
    offenders = [s for s in seen if "tgt.language" in s or "GROUP BY src.language" in s]
    assert offenders == [], offenders


def test_a_pre_221_index_says_nothing_rather_than_guessing(tmp_path: Path) -> None:
    """AC4 / R5.6: a pre-204 stamp → the reader says None → today's `no_matches`."""
    config = _cross_language_repo(tmp_path, tmp_path / "graph.db", link_the_crossing=False)
    with GraphStore(config.db_path) as store:
        _drop_census(store)
        assert store.stamped_cross_language_edges() is None

    payload = find_callers.create(config)(qname=PROC_QNAME)
    assert payload["reason"] == REASON_NO_MATCHES
    assert "cross_language" not in payload


def test_a_confident_answer_is_byte_identical(tmp_path: Path) -> None:
    """AC5 (061): the census + authoritative ride an EMPTY answer only — a hit answer is untouched.

    The proof: the same hit answer with the stamp present and with it deleted is byte-identical.
    """
    db_path = tmp_path / "graph.db"
    with GraphStore(db_path) as store:
        _seed(
            store,
            tmp_path,
            PROC_FILE,
            "sql",
            [node("Function", "getUnplannedChange", PROC_QNAME, PROC_FILE)],
            [],
        )
        _seed(
            store,
            tmp_path,
            PHP_FILE,
            "php",
            [node("Function", "loadChange", f"{PHP_FILE}::loadChange", PHP_FILE)],
            # A genuine linked caller into the proc — this answer HAS a hit.
            [edge("CALLS", f"{PHP_FILE}::loadChange", PROC_QNAME, PHP_FILE,
                  target_qname=PROC_QNAME, tier="RESOLVED")],
        )
        _stamp_census(store)
    config = _config(tmp_path, db_path)

    with_stamp = find_callers.create(config)(qname=PROC_QNAME)
    assert with_stamp["total_count"] == 1
    assert "cross_language" not in with_stamp
    assert "authoritative" not in with_stamp

    with GraphStore(config.db_path) as store:
        _drop_census(store)
    without_stamp = find_callers.create(config)(qname=PROC_QNAME)
    assert with_stamp == without_stamp
