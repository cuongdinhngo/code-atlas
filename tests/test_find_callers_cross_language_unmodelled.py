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
    CAPABILITIES_BY_LANGUAGE_KEY,
    COVERED_LANGUAGES_KEY,
    EDGE_HEALTH_BY_LANGUAGE_KEY,
    GraphStore,
)
from code_atlas.tools import find_callers, find_references
from code_atlas.tools.nav_result import (
    CAVEAT_ARGS_NOT_CAPTURED,
    CAVEAT_CROSS_LANGUAGE_UNMODELLED,
    CAVEAT_SIBLING_DEFINITIONS,
    CROSS_LANGUAGE_UNMEASURED,
    REASON_CAPABILITY_NOT_CONFIGURED,
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


def _cross_language_repo(
    root: Path, db_path: Path, *, link_the_crossing: bool, named: bool = True
) -> Config:
    """A proc (`sql`) and a caller (`php`) that reaches it only by a string argument.

    ``named=False`` drops that argument, as no adapter emitted one before 398 (409).
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
        # `querySP('getUnplannedChange')` — the proc name is an ARGUMENT, so the edge's
        # target_raw is the helper and target_qname stays NULL (the crossing is unmodelled).
        query_sp = edge("CALLS", f"{PHP_FILE}::loadChange", "querySP", PHP_FILE, tier="DYNAMIC")
        if named:
            query_sp["arg_strings"] = ["getUnplannedChange"]
        php_edges = [query_sp]
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
    """AC2/AC5 (061, narrowed by 238): a modelled *->L hit answer stays untouched.

    The hit itself is a linked php->sql edge, so the census records the crossing as modelled
    and the caveat does not fire. Proof: stamp present vs deleted is byte-identical.
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


# --- 238: the same predicate, now on a hits-bearing answer (round 15) ---
# Language A has in-language callers; language B is indexed; no linked *->A pair.
# Generic names: the fixture encodes the crossing, never the field repo (E1 / R2).

A_FILE = "src/a.php"
A_QNAME = "A\\Widget::ping"
A_CALLER = "A\\WidgetTest::testPing"
A_OTHER = "A\\Widget::other"
B_FILE = "src/b.ts"
B_QNAME = "src/b.ts::unrelated"


def _hits_unmodelled_repo(
    root: Path, db_path: Path, *, link_the_crossing: bool, second_language: bool
) -> Config:
    """A PHP method with a PHP caller; optionally a second language and a modelled *->php pair."""
    with GraphStore(db_path) as store:
        _seed(
            store,
            root,
            A_FILE,
            "php",
            [
                node("Method", "ping", A_QNAME, A_FILE),
                node("Method", "testPing", A_CALLER, A_FILE),
                node("Method", "other", A_OTHER, A_FILE),
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
        if second_language:
            ts_edges = []
            if link_the_crossing:
                ts_edges.append(
                    edge(
                        "CALLS",
                        B_QNAME,
                        A_OTHER,
                        B_FILE,
                        target_qname=A_OTHER,
                        tier="RESOLVED",
                    )
                )
            _seed(
                store,
                root,
                B_FILE,
                "typescript",
                [node("Function", "unrelated", B_QNAME, B_FILE)],
                ts_edges,
            )
        _stamp_census(store)
    return _config(root, db_path)


def test_in_language_hits_on_an_unmodelled_crossing_are_not_authoritative(
    tmp_path: Path,
) -> None:
    """238 hit-path, narrowed by 276: empty census + hits → confident ok (no caveat).

    A multi-language index with linked+unlinked == 0 no longer raises authoritative:false
    on every in-language hit — that standing fact lives on get_index_status (243/276).
    """
    config = _hits_unmodelled_repo(
        tmp_path, tmp_path / "graph.db", link_the_crossing=False, second_language=True
    )

    payload = find_callers.create(config)(qname=A_QNAME, sign=True)

    assert payload["total_count"] == 1
    assert payload["reason"] == "ok"
    assert "authoritative" not in payload
    assert "cross_language" not in payload
    assert "authoritative=false" not in str(payload.get("claim", ""))


def test_modelled_crossing_hits_stay_byte_identical(tmp_path: Path) -> None:
    """AC2: a *->php pair is modelled, so in-language hits stay a confident answer."""
    config = _hits_unmodelled_repo(
        tmp_path, tmp_path / "graph.db", link_the_crossing=True, second_language=True
    )
    with GraphStore(config.db_path) as store:
        census = store.stamped_cross_language_edges()
    assert census is not None and "typescript->php" in census["pairs"], census

    payload = find_callers.create(config)(qname=A_QNAME)
    assert payload["total_count"] == 1
    assert payload["reason"] == "ok"
    assert "authoritative" not in payload
    assert "cross_language" not in payload


def test_single_language_hits_stay_byte_identical(tmp_path: Path) -> None:
    """AC2's other half: no other language ⇒ the caveat is not the default on every hit."""
    config = _hits_unmodelled_repo(
        tmp_path, tmp_path / "graph.db", link_the_crossing=False, second_language=False
    )
    payload = find_callers.create(config)(qname=A_QNAME)
    assert payload["total_count"] == 1
    assert payload["reason"] == "ok"
    assert "authoritative" not in payload
    assert "cross_language" not in payload


def test_zero_path_reason_is_unchanged(tmp_path: Path) -> None:
    """AC3: the 221 zero still names relation_unmodelled_for_language; hits keep reason=ok."""
    zero = _cross_language_repo(tmp_path, tmp_path / "graph.db", link_the_crossing=False)
    payload = find_callers.create(zero)(qname=PROC_QNAME)
    assert payload["total_count"] == 0
    assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE


def test_pre_stamp_hits_say_nothing(tmp_path: Path) -> None:
    """AC5 / R5.6: a pre-204 stamp on a hits-bearing answer is today's confident ok."""
    config = _hits_unmodelled_repo(
        tmp_path, tmp_path / "graph.db", link_the_crossing=False, second_language=True
    )
    with GraphStore(config.db_path) as store:
        _drop_census(store)
        assert store.stamped_cross_language_edges() is None

    payload = find_callers.create(config)(qname=A_QNAME)
    assert payload["reason"] == "ok"
    assert payload["total_count"] == 1
    assert "authoritative" not in payload
    assert "cross_language" not in payload


def test_the_hit_answer_is_a_stamp_read_not_a_scan(
    tmp_path: Path, monkeypatch: object
) -> None:
    """C2: answering a HITS payload still reads meta — it never re-runs `_cross_language_edges`."""
    import sqlite3

    config = _hits_unmodelled_repo(
        tmp_path, tmp_path / "graph.db", link_the_crossing=False, second_language=True
    )

    seen: list[str] = []
    real_connect = sqlite3.connect

    def _tracing_connect(*args: object, **kwargs: object) -> sqlite3.Connection:
        conn = real_connect(*args, **kwargs)  # type: ignore[arg-type]
        conn.set_trace_callback(seen.append)
        return conn

    monkeypatch.setattr(sqlite3, "connect", _tracing_connect)  # type: ignore[attr-defined]
    payload = find_callers.create(config)(qname=A_QNAME)
    assert payload["reason"] == "ok"
    assert payload["total_count"] == 1

    offenders = [s for s in seen if "tgt.language" in s or "GROUP BY src.language" in s]
    assert offenders == [], offenders


def test_find_references_in_language_hits_on_an_unmodelled_crossing(
    tmp_path: Path,
) -> None:
    """find_references: empty census + hits → no cross_language caveat (276)."""
    config = _hits_unmodelled_repo(
        tmp_path, tmp_path / "graph.db", link_the_crossing=False, second_language=True
    )
    payload = find_references.create(config)(qname=A_QNAME, sign=True)
    assert payload["total_count"] == 1
    assert payload["reason"] == "ok"
    assert "authoritative" not in payload
    assert "cross_language" not in payload


def test_find_references_modelled_and_single_language_and_pre_stamp(
    tmp_path: Path,
) -> None:
    """AC4/AC5: find_references — modelled, single-language, and pre-stamp stay today's ok."""
    modelled = _hits_unmodelled_repo(
        tmp_path / "modelled",
        tmp_path / "modelled.db",
        link_the_crossing=True,
        second_language=True,
    )
    payload = find_references.create(modelled)(qname=A_QNAME)
    assert payload["total_count"] == 1
    assert payload["reason"] == "ok"
    assert "cross_language" not in payload
    assert CAVEAT_CROSS_LANGUAGE_UNMODELLED not in (payload.get("authoritative_caveats") or [])

    single = _hits_unmodelled_repo(
        tmp_path / "single",
        tmp_path / "single.db",
        link_the_crossing=False,
        second_language=False,
    )
    payload = find_references.create(single)(qname=A_QNAME)
    assert payload["total_count"] == 1
    assert "cross_language" not in payload

    prestamp = _hits_unmodelled_repo(
        tmp_path / "pre",
        tmp_path / "pre.db",
        link_the_crossing=False,
        second_language=True,
    )
    with GraphStore(prestamp.db_path) as store:
        _drop_census(store)
    payload = find_references.create(prestamp)(qname=A_QNAME)
    assert payload["reason"] == "ok"
    assert "cross_language" not in payload
    assert "authoritative" not in payload


# --- 238 review: the crossing caveat must ADD a reason, never replace one already named ---

SIB_QNAME = "A\\Other::ping"


def _hits_with_a_sibling(root: Path, db_path: Path, *, no_args_capture: bool) -> Config:
    """The 238 hits shape plus a same-named definition under another qname — a 165 partition too."""
    with GraphStore(db_path) as store:
        _seed(
            store,
            root,
            A_FILE,
            "php",
            [node("Method", "ping", A_QNAME, A_FILE),
             node("Method", "testPing", A_CALLER, A_FILE),
             node("Method", "ping", SIB_QNAME, A_FILE)],
            [edge("CALLS", A_CALLER, A_QNAME, A_FILE, target_qname=A_QNAME, tier="RESOLVED")],
        )
        _seed(
            store,
            root,
            B_FILE,
            "typescript",
            [node("Function", "unrelated", B_QNAME, B_FILE)],
            [],
        )
        _stamp_census(store)
        if no_args_capture:
            store.set_meta(
                CAPABILITIES_BY_LANGUAGE_KEY,
                json.dumps({"php": {"args": False}, "typescript": {"args": False}}),
            )
    return _config(root, db_path)


def test_the_crossing_caveat_does_not_erase_the_sibling_partition(tmp_path: Path) -> None:
    """Sibling partition is named; empty census no longer adds the crossing caveat (276)."""
    config = _hits_with_a_sibling(tmp_path, tmp_path / "graph.db", no_args_capture=False)

    payload = find_callers.create(config)(qname=A_QNAME)

    assert payload["reason"] == "ok"
    assert "sibling_definitions" in payload
    assert payload["authoritative_caveats"] == [CAVEAT_SIBLING_DEFINITIONS]
    assert CAVEAT_CROSS_LANGUAGE_UNMODELLED not in payload["authoritative_caveats"]


def test_the_crossing_caveat_does_not_erase_the_args_partition(tmp_path: Path) -> None:
    """231's caveat outranks every reason; empty census does not add a crossing caveat (276)."""
    config = _hits_with_a_sibling(tmp_path, tmp_path / "graph.db", no_args_capture=True)

    payload = find_callers.create(config)(qname=A_QNAME, arg_position=1, arg_is="string")

    assert payload["reason"] == REASON_CAPABILITY_NOT_CONFIGURED
    assert CAVEAT_ARGS_NOT_CAPTURED in payload["authoritative_caveats"]
    assert CAVEAT_CROSS_LANGUAGE_UNMODELLED not in (
        payload.get("authoritative_caveats") or []
    )


# Task 409: a PHP method nothing calls, on an index where no language links into PHP.
METHOD_QNAME = "\\App\\Mailer::sendAlert"
METHOD_FILE = "src/Mailer.php"
SQL_FILE = "src/reports.sql"


def _measured_zero_repo(root: Path, db_path: Path, sql_edges: list, php_edges: list) -> Config:
    """A caller-less PHP method beside SQL; ``*_edges`` add what the other language says."""
    with GraphStore(db_path) as store:
        _seed(
            store,
            root,
            METHOD_FILE,
            "php",
            [node("Method", "sendAlert", METHOD_QNAME, METHOD_FILE),
             node("Method", "other", "\\App\\Mailer::other", METHOD_FILE)],
            php_edges,
        )
        _seed(
            store,
            root,
            SQL_FILE,
            "sql",
            [node("Function", "monthly", "dbo.monthly", SQL_FILE)],
            sql_edges,
        )
        _stamp_census(store)
    return _config(root, db_path)


def test_a_caller_less_method_nothing_names_is_a_measured_zero(tmp_path: Path) -> None:
    """409 AC1: no other language names it, so the zero is `no_matches`, the crossing a field."""
    config = _measured_zero_repo(tmp_path, tmp_path / "graph.db", [], [])
    payload = find_callers.create(config)(qname=METHOD_QNAME)
    assert payload["total_count"] == 0
    assert payload["reason"] == REASON_NO_MATCHES
    assert payload[CROSS_LANGUAGE_UNMEASURED] == ["sql"]
    assert "authoritative" not in payload
    assert "cross_language" not in payload
    minimal = find_callers.create(config)(qname=METHOD_QNAME, detail_level="minimal")
    assert minimal[CROSS_LANGUAGE_UNMEASURED] == ["sql"]


def test_another_language_naming_the_subject_keeps_it_unmeasured(tmp_path: Path) -> None:
    """409 AC2: by callee name, or by a whole literal argument, the zero stays unmodelled."""
    by_callee = [edge("CALLS", "dbo.monthly", "sendAlert", SQL_FILE, tier="DYNAMIC")]
    by_argument = edge("CALLS", "dbo.monthly", "invoke", SQL_FILE, tier="DYNAMIC")
    by_argument["arg_strings"] = ["sendAlert", None]
    for i, sql_edges in enumerate(([*by_callee], [by_argument])):
        root = tmp_path / str(i)
        config = _measured_zero_repo(root, root / "graph.db", sql_edges, [])
        payload = find_callers.create(config)(qname=METHOD_QNAME)
        assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE, sql_edges
        assert payload["authoritative"] is False
        assert CROSS_LANGUAGE_UNMEASURED not in payload


def test_a_partial_string_or_a_same_language_mention_is_not_evidence(tmp_path: Path) -> None:
    """409: a substring is not the name, and the subject's own language is measured already."""
    partial = edge("CALLS", "dbo.monthly", "invoke", SQL_FILE, tier="DYNAMIC")
    partial["arg_strings"] = ["sendAlerts", "x_sendAlert"]
    own = edge("CALLS", "\\App\\Mailer::other", "invoke", METHOD_FILE, tier="DYNAMIC")
    own["arg_strings"] = ["sendAlert"]
    config = _measured_zero_repo(tmp_path, tmp_path / "graph.db", [partial], [own])
    payload = find_callers.create(config)(qname=METHOD_QNAME)
    assert payload["reason"] == REASON_NO_MATCHES
    assert payload[CROSS_LANGUAGE_UNMEASURED] == ["sql"]


def test_221_without_its_argument_is_a_measured_zero(tmp_path: Path) -> None:
    """409 AC3, re-decided: a caller naming the proc nowhere is no evidence of a crossing."""
    config = _cross_language_repo(
        tmp_path, tmp_path / "graph.db", link_the_crossing=False, named=False
    )
    payload = find_callers.create(config)(qname=PROC_QNAME)
    assert payload["reason"] == REASON_NO_MATCHES
    assert payload[CROSS_LANGUAGE_UNMEASURED] == ["php"]
    assert "authoritative" not in payload


def test_a_qualified_or_keyword_literal_names_the_subject(tmp_path: Path) -> None:
    """409 (challenger F3): `'Mailer::sendAlert'`, `'dbo.sendAlert'` and a keyword value count."""
    shapes: list[tuple[str, object]] = [
        ("arg_strings", ["App\\Mailer::sendAlert"]),
        ("arg_strings", ["dbo.sendAlert"]),
        ("kwarg_strings", {"proc": "sendAlert"}),
    ]
    for i, (column, value) in enumerate(shapes):
        call = edge("CALLS", "dbo.monthly", "invoke", SQL_FILE, tier="DYNAMIC")
        call[column] = value
        root = tmp_path / str(i)
        config = _measured_zero_repo(root, root / "graph.db", [call], [])
        payload = find_callers.create(config)(qname=METHOD_QNAME)
        assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE, (column, value)


def test_like_wildcards_in_the_name_match_only_themselves(tmp_path: Path) -> None:
    """`_` and `%` in a name are literal: `send_alert` is not named by `sendXalert`."""
    call = edge("CALLS", "dbo.monthly", "invoke", SQL_FILE, tier="DYNAMIC")
    call["arg_strings"] = ["sendXalert", "send%alert"]
    with GraphStore(tmp_path / "graph.db") as store:
        _seed(store, tmp_path, SQL_FILE, "sql", [], [call])
        assert not store.named_from_another_language(
            ("send_alert",), language="php", kinds=("CALLS",)
        )
        assert store.named_from_another_language(
            ("send%alert",), language="php", kinds=("CALLS",)
        )


def test_the_field_rides_only_a_no_matches_answer(tmp_path: Path) -> None:
    """409 (challenger F1): another reason's zero is not called measured."""
    own = edge("CALLS", "dbo.monthly", "monthly", SQL_FILE, tier="DYNAMIC")
    config = _measured_zero_repo(tmp_path, tmp_path / "graph.db", [own], [])
    payload = find_callers.create(config)(qname="dbo.monthly")
    # 214: an unlinked same-name EXEC in its own language — unmodelled, not a measured zero.
    assert payload["reason"] == REASON_RELATION_UNMODELLED_FOR_LANGUAGE
    assert CROSS_LANGUAGE_UNMEASURED not in payload
