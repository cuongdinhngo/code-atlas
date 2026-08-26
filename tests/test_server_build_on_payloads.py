"""Task 162 — a build swap is visible on every mechanism answer, not only get_index_status.

125 stamped ``server_version`` / ``server_build`` on ``get_index_status``; 162 carries the same two
fields (one source, ``build_info.server_provenance``) on the default payload of the read / nav /
mechanism tools, drawn from the lru-cached identity so the hot path spawns no git.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from code_atlas.build_info import server_identity, server_provenance
from code_atlas.config import load_config
from code_atlas.tools import impact, reach_shared, read_symbol, search_symbol
from code_atlas.tools import nav_result as nr
from tests.test_claim_signing import SUBJECT, configured, indexed_repo

_KEYS = frozenset({"server_version", "server_build"})


def _prov() -> dict[str, str]:
    ident = server_identity()
    return {"server_version": ident["version"], "server_build": ident["build"]}


def test_server_provenance_is_the_get_index_status_spelling() -> None:
    """AC3: one source of truth — the helper spells the two fields get_index_status uses."""
    assert set(server_provenance()) == _KEYS
    assert server_provenance() == _prov()


def test_nav_builders_carry_server_provenance() -> None:
    """AC1: every call-level nav/list/empty/batch payload names the build."""
    built = [
        nr.nav_result("Foo", [], detail_level="standard", index_root="/r", truncated=False),
        nr.empty_nav("Foo", detail_level="standard", index_root="/r"),
        nr.list_result(
            [], detail_level="standard", index_root="/r", truncated=False,
            reason=nr.REASON_NO_MATCHES, total_count=0,
        ),
        nr.batch_result([], index_root="/r"),
        nr.batch_not_indexed("/r"),
    ]
    for payload in built:
        assert _KEYS <= set(payload)
        assert {k: payload[k] for k in _KEYS} == _prov()


def test_read_symbol_builders_carry_server_provenance() -> None:
    """AC1: read_symbol — found and empty shapes both name the build."""
    empty = read_symbol._empty("Foo", detail_level="standard", db_path="", index_root="/r")
    result = read_symbol._result(
        "Foo", "src", detail_level="standard", db_path="", index_root="/r", found=True,
    )
    for payload in (empty, result):
        assert {k: payload[k] for k in _KEYS} == _prov()


def test_subject_answer_does_not_repeat_the_build_per_subject() -> None:
    """AC4 / 061: the build is a call-level fact — it rides the batch envelope, not each subject."""
    answer = nr.subject_answer(
        "Foo", [], truncated=False, reason=nr.REASON_NO_MATCHES, total_count=0,
    )
    assert not (_KEYS & set(answer))


def test_two_builds_are_distinguishable_from_a_nav_payload() -> None:
    """AC1: two builds of the same version differ from any such payload alone."""
    with patch.object(nr, "server_provenance", return_value={
        "server_version": "0.1.0", "server_build": "aaaaaaa",
    }):
        first = nr.nav_result("Foo", [], detail_level="standard", index_root="/r", truncated=False)
    with patch.object(nr, "server_provenance", return_value={
        "server_version": "0.1.0", "server_build": "bbbbbbb",
    }):
        second = nr.nav_result("Foo", [], detail_level="standard", index_root="/r", truncated=False)
    assert first["server_build"] != second["server_build"]
    assert first["server_version"] == second["server_version"] == "0.1.0"


def test_impact_hot_path_carries_build_without_computing_staleness(tmp_path: Path) -> None:
    """AC1/AC2: the default (sign=false) impact payload names the build and reads no git.

    ``compute_staleness`` is the git HEAD read + dirty scan; impact.py guards it behind sign=True.
    Patched to blow up, a default call still answers — proving the stamp is off the git path.
    """
    db_path = indexed_repo(tmp_path)
    config = configured(tmp_path, db_path)
    with patch.object(impact, "compute_staleness", side_effect=AssertionError("git on hot path")):
        payload = impact.create(config)(qnames=[SUBJECT], sign=False)
    ident = server_identity()
    assert payload["server_build"] == ident["build"]
    assert payload["server_version"] == ident["version"]


def test_search_symbol_names_the_build(tmp_path: Path) -> None:
    """AC1: a search answer carries the build (integration — needs the PHP adapter index)."""
    db_path = indexed_repo(tmp_path)
    config = configured(tmp_path, db_path)
    payload = search_symbol.create(config)(query=SUBJECT.split("\\")[-1])
    ident = server_identity()
    assert payload["server_build"] == ident["build"]
    assert payload["server_version"] == ident["version"]


def test_reach_shared_no_roots_answer_names_the_build(tmp_path: Path) -> None:
    """AC1: the reachable_from / find_orphans 'no roots configured' answer is attributable too."""
    config = load_config(tmp_path, {})
    payload = reach_shared.no_roots("standard", config)
    assert {k: payload[k] for k in _KEYS} == _prov()


def test_server_provenance_byte_cost_is_small_and_measured() -> None:
    """AC4 / 061: the stamp adds only the two short fields — measured, and bounded by a test.

    Measured delta on a payload's JSON: ~53 bytes (clean 7-char build) to ~60 (``+dirty``); the
    field never scales with the answer, so it is negligible on any non-empty result.
    """
    with_fields = nr.nav_result(
        "Foo", [], detail_level="standard", index_root="/r", truncated=False
    )
    without = {k: v for k, v in with_fields.items() if k not in _KEYS}
    delta = len(json.dumps(with_fields)) - len(json.dumps(without))
    assert 0 < delta <= 80, f"server stamp added {delta} bytes; expected the two short fields only"
